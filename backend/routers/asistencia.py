"""Asistencia PRO.

Estudiantes: al GUARDAR, cada ausencia dispara automáticamente
  1) una alerta al coordinador (NotificacionCoord, dedup por estudiante/día),
  2) un WhatsApp simulado al acudiente,
  3) un evento ASISTENCIA en el log unificado de metadatos,
  4) el recálculo del Score de Riesgo.
Docentes: registro de asistencia del personal + reporte de ausentismo.
"""
from datetime import date, datetime, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (Estudiante, Asistencia, NotificacionCoord, MensajeWhatsApp,
                    Personal, AsistenciaPersonal, Salon)
from services import srd_service
try:
    from routers.vivo import marcar_cambio
except Exception:  # noqa: BLE001
    def marcar_cambio(*a, **k):
        pass
import metadatos

router = APIRouter()


@router.get("/cargar")
def cargar(salon_id: int, fecha: str, db: Session = Depends(get_db)):
    estudiantes = db.query(Estudiante).filter(Estudiante.salon_id == salon_id).all()
    try:
        f = date.fromisoformat(fecha)
    except ValueError:
        f = date.today()
    existentes = {}
    for a in db.query(Asistencia).filter(Asistencia.salon_id == salon_id, Asistencia.fecha == f).all():
        existentes[a.estudiante_id] = a
    filas = []
    for e in estudiantes:
        a = existentes.get(e.id)
        filas.append({
            "estudiante_id": e.id, "nombre": e.nombre,
            "estado": a.estado if a else "present",
            "observacion": (a.observacion if a and a.observacion else ""),
        })
    return {"fecha": f.isoformat(), "filas": filas}


class FilaAsistencia(BaseModel):
    estudiante_id: int
    estado: str
    observacion: str | None = ""


class GuardarAsistencia(BaseModel):
    salon_id: int
    fecha: str
    filas: list[FilaAsistencia]


@router.post("/guardar")
def guardar(payload: GuardarAsistencia, db: Session = Depends(get_db)):
    try:
        f = date.fromisoformat(payload.fecha)
    except ValueError:
        f = date.today()
    validos = {"present", "late", "excused", "absent"}
    n = 0
    ausentes_ids = []
    for fila in payload.filas:
        estado = fila.estado if fila.estado in validos else "present"
        existente = db.query(Asistencia).filter(
            Asistencia.salon_id == payload.salon_id,
            Asistencia.estudiante_id == fila.estudiante_id,
            Asistencia.fecha == f).first()
        if existente:
            existente.estado = estado
            existente.observacion = fila.observacion or ""
        else:
            db.add(Asistencia(estudiante_id=fila.estudiante_id, salon_id=payload.salon_id,
                              fecha=f, estado=estado, observacion=fila.observacion or ""))
        if estado == "absent":
            ausentes_ids.append(fila.estudiante_id)
        n += 1

    # ── Automatización: alerta al coordinador + WhatsApp al acudiente ──
    n_alertas = 0
    n_whats = 0
    ausentes_nombres = []
    if ausentes_ids:
        ests = {e.id: e for e in db.query(Estudiante).filter(Estudiante.id.in_(ausentes_ids)).all()}
        for eid in ausentes_ids:
            e = ests.get(eid)
            if not e:
                continue
            ausentes_nombres.append(e.nombre.split()[0] + " " + e.nombre.split()[1])
            ya = db.query(NotificacionCoord).filter(
                NotificacionCoord.estudiante_id == eid,
                NotificacionCoord.tipo == "ausencia",
                NotificacionCoord.fecha >= datetime.combine(f, datetime.min.time()),
                NotificacionCoord.fecha < datetime.combine(f + timedelta(days=1), datetime.min.time())).first()
            if not ya:
                db.add(NotificacionCoord(
                    institucion_id=e.institucion_id, estudiante_id=eid, tipo="ausencia",
                    titulo=f"Ausencia de {e.nombre.split()[0]} {e.nombre.split()[1]}",
                    detalle=f"No asistió el {f.isoformat()} · Grado {e.grado} · Acudiente: {e.acudiente} ({e.parentesco or 'acudiente'}) · Tel {e.telefono}",
                    fecha=datetime.now(), estado="abierta"))
                n_alertas += 1
                db.add(MensajeWhatsApp(
                    estudiante_id=eid, destinatario=f"{e.acudiente} ({e.parentesco or 'acudiente'})",
                    telefono=e.telefono,
                    contenido=(f"Buen día. Le informamos que {e.nombre.split()[0]} no asistió hoy "
                               f"({f.strftime('%d/%m')}) a la institución. Si existe una causa justificada, "
                               "responda este mensaje o comuníquese con coordinación. — GyverLabs"),
                    fecha=datetime.now(), estado="ENVIADO (simulado)", contexto="ausencia"))
                n_whats += 1
    db.commit()

    # Avisar a los demás usuarios en vivo: coordinación ve las ausencias al instante
    _sal = db.query(Salon).filter(Salon.id == payload.salon_id).first()
    marcar_cambio(_sal.institucion_id if _sal else None, "asistencia",
                  f"Asistencia del salón {_sal.nombre if _sal else ''}: {len(ausentes_ids)} ausente(s)")

    metadatos.registrar_evento("ASISTENCIA", "Docente", payload={
        "salon_id": payload.salon_id, "fecha": f.isoformat(), "registros": n,
        "ausentes": len(ausentes_ids)})

    recalc = srd_service.recalcular_todos(db)
    msg = f"Asistencia guardada ({n} estudiantes)."
    if n_alertas:
        msg += f" 🔔 {n_alertas} alerta(s) enviadas a coordinación y 📱 {n_whats} WhatsApp al acudiente (simulado)."
    msg += " Riesgo recalculado."
    return {"ok": True, "msg": msg, "n": n, "recalc": recalc,
            "ausentes": ausentes_nombres, "alertas": n_alertas}


@router.get("/resumen")
def resumen(institucion_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Asistencia)
    if institucion_id:
        ids = [e.id for e in db.query(Estudiante).filter(Estudiante.institucion_id == institucion_id).all()]
        q = q.filter(Asistencia.estudiante_id.in_(ids)) if ids else q.filter(Asistencia.id < 0)
    filas = q.all()
    por_semana = defaultdict(lambda: [0, 0])
    for a in filas:
        semana = a.fecha.isocalendar()[1]
        por_semana[semana][1] += 1
        if a.estado in ("present", "excused", "late"):
            por_semana[semana][0] += 1
    puntos = [{"semana": s, "pct": round(100 * p / t, 1) if t else 0}
              for s, (p, t) in sorted(por_semana.items())]
    total = len(filas)
    presentes = sum(1 for a in filas if a.estado in ("present", "excused", "late"))
    return {"pct_global": round(100 * presentes / total, 1) if total else 0, "tendencia": puntos}


# ═════════ ASISTENCIA DEL PERSONAL DOCENTE ═════════
@router.get("/docentes/cargar")
def docentes_cargar(institucion_id: int, fecha: str, db: Session = Depends(get_db)):
    try:
        f = date.fromisoformat(fecha)
    except ValueError:
        f = date.today()
    docentes = db.query(Personal).filter(Personal.institucion_id == institucion_id,
                                         Personal.rol == "docente",
                                         Personal.activo == True).all()  # noqa: E712
    ids = [d.id for d in docentes]
    existentes = {}
    if ids:
        for a in db.query(AsistenciaPersonal).filter(AsistenciaPersonal.personal_id.in_(ids),
                                                     AsistenciaPersonal.fecha == f).all():
            existentes[a.personal_id] = a
    return {"fecha": f.isoformat(), "filas": [{
        "personal_id": d.id, "nombre": d.nombre, "area": d.area, "foto": d.foto,
        "estado": existentes[d.id].estado if d.id in existentes else "present",
        "observacion": existentes[d.id].observacion if d.id in existentes and existentes[d.id].observacion else "",
    } for d in docentes]}


class FilaDocente(BaseModel):
    personal_id: int
    estado: str
    observacion: str | None = ""


class GuardarDocentes(BaseModel):
    institucion_id: int
    fecha: str
    filas: list[FilaDocente]


@router.post("/docentes/guardar")
def docentes_guardar(payload: GuardarDocentes, db: Session = Depends(get_db)):
    try:
        f = date.fromisoformat(payload.fecha)
    except ValueError:
        f = date.today()
    validos = {"present", "late", "excused", "absent"}
    n = 0
    for fila in payload.filas:
        estado = fila.estado if fila.estado in validos else "present"
        ex = db.query(AsistenciaPersonal).filter(AsistenciaPersonal.personal_id == fila.personal_id,
                                                 AsistenciaPersonal.fecha == f).first()
        if ex:
            ex.estado = estado
            ex.observacion = fila.observacion or ""
        else:
            db.add(AsistenciaPersonal(personal_id=fila.personal_id, fecha=f,
                                      estado=estado, observacion=fila.observacion or ""))
        n += 1
    db.commit()
    metadatos.registrar_evento("ASISTENCIA_DOCENTE", "Coordinación",
                               institucion_id=payload.institucion_id,
                               payload={"fecha": f.isoformat(), "registros": n})
    return {"ok": True, "msg": f"Asistencia de {n} docentes guardada."}


@router.get("/docentes/reporte")
def docentes_reporte(institucion_id: int, db: Session = Depends(get_db)):
    docentes = db.query(Personal).filter(Personal.institucion_id == institucion_id,
                                         Personal.rol == "docente",
                                         Personal.activo == True).all()  # noqa: E712
    ids = [d.id for d in docentes]
    regs = db.query(AsistenciaPersonal).filter(AsistenciaPersonal.personal_id.in_(ids)).all() if ids else []
    agg = defaultdict(lambda: {"pres": 0, "tarde": 0, "aus": 0, "tot": 0})
    for a in regs:
        d = agg[a.personal_id]
        d["tot"] += 1
        if a.estado == "absent":
            d["aus"] += 1
        elif a.estado == "late":
            d["tarde"] += 1
            d["pres"] += 1
        else:
            d["pres"] += 1
    out = []
    for d in docentes:
        v = agg.get(d.id, {"pres": 0, "tarde": 0, "aus": 0, "tot": 0})
        pct = round(100 * v["pres"] / v["tot"], 1) if v["tot"] else None
        out.append({
            "personal_id": d.id, "nombre": d.nombre, "area": d.area, "foto": d.foto,
            "dias": v["tot"], "ausencias": v["aus"], "tardanzas": v["tarde"],
            "pct": pct,
            "riesgo": ("ALTO" if pct is not None and pct < 85 else
                       "MEDIO" if pct is not None and pct < 93 else "OK"),
        })
    out.sort(key=lambda x: (x["pct"] if x["pct"] is not None else 101))
    return out


# ═════════ HISTORIAL Y SCORE POR ESTUDIANTE (punto 5) ═════════
from models import SRDScore as _SRDA, NotaPendiente as _PendA, EntregaAula as _EntA, ActividadAula as _ActA


@router.get("/historial_salon")
def historial_salon(salon_id: int, dias: int = 30, db: Session = Depends(get_db)):
    """Historial de los últimos días + score de faltas y pendientes de cada
    estudiante: el docente ve de un vistazo quién suele faltar y quién debe."""
    desde = date.today() - timedelta(days=dias)
    ests = db.query(Estudiante).filter(Estudiante.salon_id == salon_id).order_by(Estudiante.nombre).all()
    ids = [e.id for e in ests]
    regs = db.query(Asistencia).filter(Asistencia.salon_id == salon_id,
                                       Asistencia.fecha >= desde).all()
    fechas = sorted({r.fecha for r in regs}, reverse=True)[:20]
    por_est = {}
    for r in regs:
        por_est.setdefault(r.estudiante_id, {})[r.fecha] = r.estado
    srds = {s.estudiante_id: s for s in db.query(_SRDA).filter(_SRDA.estudiante_id.in_(ids)).all()} if ids else {}
    # pendientes académicos (entregas sin entregar)
    pend_aula = {}
    if ids:
        filas = (db.query(_EntA, _ActA).join(_ActA, _EntA.actividad_id == _ActA.id)
                 .filter(_EntA.estudiante_id.in_(ids), _EntA.estado == "pendiente").all())
        for en, a in filas:
            pend_aula[en.estudiante_id] = pend_aula.get(en.estudiante_id, 0) + 1
    pend_obs = {}
    if ids:
        for p in db.query(_PendA).filter(_PendA.estudiante_id.in_(ids),
                                         _PendA.done == False).all():  # noqa: E712
            pend_obs[p.estudiante_id] = pend_obs.get(p.estudiante_id, 0) + 1
    out = []
    for e in ests:
        h = por_est.get(e.id, {})
        faltas = sum(1 for v in h.values() if v == "absent")
        tardes = sum(1 for v in h.values() if v == "late")
        total = len(h)
        srd = srds.get(e.id)
        out.append({
            "estudiante_id": e.id, "nombre": e.nombre,
            "historial": [{"fecha": f.isoformat(), "estado": h.get(f, "—")} for f in fechas],
            "faltas": faltas, "tardanzas": tardes, "registros": total,
            "pct_asistencia": round(100 * (total - faltas) / total, 1) if total else 100,
            "faltas_totales": srd.faltas_acumuladas if srd else faltas,
            "score_riesgo": round(srd.score, 1) if srd else None,
            "nivel_riesgo": srd.nivel if srd else None,
            "pendientes_aula": pend_aula.get(e.id, 0),
            "pendientes_obs": pend_obs.get(e.id, 0),
            "acudiente": e.acudiente, "telefono": e.telefono,
        })
    out.sort(key=lambda x: (-x["faltas"], -(x["pendientes_aula"] + x["pendientes_obs"])))
    return {"fechas": [f.isoformat() for f in fechas], "estudiantes": out, "dias": dias}
