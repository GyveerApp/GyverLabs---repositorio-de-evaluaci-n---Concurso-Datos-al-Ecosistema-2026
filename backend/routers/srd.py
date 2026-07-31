"""Score de Riesgo de Deserción PRO: tablero, ranking, FICHA 360° del
estudiante (datos, acudiente, antigüedad, asistencia reciente, notas,
observador con firma del acudiente, pendientes, WhatsApp, bitácora),
notificaciones (padre → WhatsApp simulado) e intervención."""
from datetime import datetime, date, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (Estudiante, Salon, SRDScore, SRDLog, Institucion, Asistencia,
                    NotaPeriodo, Periodo, ObservadorEntrada, NotaPendiente,
                    MensajeWhatsApp, NotificacionCoord)
from services import srd_service
import metadatos

router = APIRouter()


def _scope_ids(db, institucion_id=None, salon_id=None):
    q = db.query(Estudiante)
    if institucion_id:
        q = q.filter(Estudiante.institucion_id == institucion_id)
    if salon_id:
        q = q.filter(Estudiante.salon_id == salon_id)
    return [e.id for e in q.all()]


@router.post("/recalcular")
def recalcular(db: Session = Depends(get_db)):
    n = srd_service.recalcular_todos(db)
    metadatos.registrar_evento("SRD_RECALCULO", "Sistema", payload={"n": n})
    return {"ok": True, "msg": f"Score de Riesgo recalculado para {n} estudiantes.", "n": n}


@router.get("/tablero")
def tablero(institucion_id: int | None = None, db: Session = Depends(get_db)):
    ids = _scope_ids(db, institucion_id)
    if not ids:
        return {"total": 0, "criticos": 0, "moderados": 0, "leves": 0, "mapa": []}
    scores = db.query(SRDScore).filter(SRDScore.estudiante_id.in_(ids)).all()
    est = {e.id: e for e in db.query(Estudiante).filter(Estudiante.id.in_(ids)).all()}
    salones = {s.id: s for s in db.query(Salon).all()}
    criticos = sum(1 for s in scores if s.nivel == "CRÍTICO")
    moderados = sum(1 for s in scores if s.nivel == "MODERADO")
    leves = sum(1 for s in scores if s.nivel == "LEVE")
    por_salon = defaultdict(lambda: {"total": 0, "riesgo": 0})
    for s in scores:
        e = est.get(s.estudiante_id)
        if not e:
            continue
        por_salon[e.salon_id]["total"] += 1
        if s.nivel in ("CRÍTICO", "MODERADO"):
            por_salon[e.salon_id]["riesgo"] += 1
    mapa = []
    for sid, d in por_salon.items():
        sal = salones.get(sid)
        mapa.append({
            "salon": sal.nombre if sal else str(sid),
            "grado": sal.grado if sal else "",
            "total": d["total"],
            "pct_riesgo": round(100 * d["riesgo"] / d["total"], 1) if d["total"] else 0,
        })
    mapa.sort(key=lambda x: x["salon"])
    return {"total": len(scores), "criticos": criticos, "moderados": moderados, "leves": leves, "mapa": mapa}


@router.get("/ranking")
def ranking(institucion_id: int | None = None, salon_id: int | None = None,
            limite: int = 50, db: Session = Depends(get_db)):
    ids = _scope_ids(db, institucion_id, salon_id)
    if not ids:
        return []
    scores = db.query(SRDScore).filter(SRDScore.estudiante_id.in_(ids)).all()
    est = {e.id: e for e in db.query(Estudiante).filter(Estudiante.id.in_(ids)).all()}
    salones = {s.id: s for s in db.query(Salon).all()}
    out = []
    for s in scores:
        e = est.get(s.estudiante_id)
        if not e:
            continue
        sal = salones.get(e.salon_id)
        out.append({
            "estudiante_id": s.estudiante_id, "nombre": e.nombre,
            "salon": sal.nombre if sal else "—",
            "score": round(s.score * 100), "nivel": s.nivel,
            "faltas_acumuladas": s.faltas_acumuladas, "faltas_recientes": s.faltas_recientes,
            "pct_asistencia": s.pct_asistencia, "promedio": s.promedio, "tendencia": s.tendencia,
            "factores": s.factores.split(" | ") if s.factores else [],
            "notificado_padre": bool(s.notificado_padre),
            "notificado_rectoria": bool(s.notificado_rectoria),
            "intervencion_estado": s.intervencion_estado,
            "acudiente": e.acudiente, "telefono": e.telefono,
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:limite]


# ═════════ FICHA 360° ═════════
@router.get("/ficha")
def ficha(estudiante_id: int, db: Session = Depends(get_db)):
    e = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not e:
        raise HTTPException(404, "Estudiante no encontrado")
    sal = db.query(Salon).filter(Salon.id == e.salon_id).first()
    ie = db.query(Institucion).filter(Institucion.id == e.institucion_id).first()
    rec = db.query(SRDScore).filter(SRDScore.estudiante_id == e.id).first()

    hoy = date.today()
    antig = None
    es_nuevo = False
    if e.fecha_ingreso:
        antig = round((hoy - e.fecha_ingreso).days / 365.0, 1)
        es_nuevo = e.fecha_ingreso.year == hoy.year

    # asistencia últimos 15 días hábiles
    asis = db.query(Asistencia).filter(Asistencia.estudiante_id == e.id).order_by(
        Asistencia.fecha.desc()).limit(15).all()
    asis_mini = [{"fecha": a.fecha.isoformat(), "estado": a.estado} for a in reversed(asis)]

    # notas por período (promedio de materias)
    pnum = {p.id: (p.numero, p.nombre, bool(p.cerrado)) for p in db.query(Periodo).all()}
    notas = defaultdict(list)
    for n in db.query(NotaPeriodo).filter(NotaPeriodo.estudiante_id == e.id).all():
        info = pnum.get(n.periodo_id)
        if info:
            notas[info].append(n.nota)
    notas_out = [{"periodo": k[0], "nombre": k[1], "cerrado": k[2],
                  "promedio": round(sum(v) / len(v), 1)} for k, v in sorted(notas.items())]

    obs = db.query(ObservadorEntrada).filter(ObservadorEntrada.estudiante_id == e.id).order_by(
        ObservadorEntrada.fecha.desc()).limit(20).all()
    pend = db.query(NotaPendiente).filter(NotaPendiente.estudiante_id == e.id).order_by(
        NotaPendiente.done, NotaPendiente.fecha.desc()).limit(15).all()
    whats = db.query(MensajeWhatsApp).filter(MensajeWhatsApp.estudiante_id == e.id).order_by(
        MensajeWhatsApp.fecha.desc()).limit(10).all()
    logs = db.query(SRDLog).filter(SRDLog.estudiante_id == e.id).order_by(
        SRDLog.fecha.desc()).limit(15).all()
    alertas_abiertas = db.query(NotificacionCoord).filter(
        NotificacionCoord.estudiante_id == e.id, NotificacionCoord.estado == "abierta").count()

    return {
        "id": e.id, "nombre": e.nombre, "grado": e.grado,
        "salon": sal.nombre if sal else "—", "institucion": ie.nombre if ie else "—",
        "zona": e.zona, "nivel_sisben": e.nivel_sisben,
        "direccion": e.direccion, "barrio_vereda": e.barrio_vereda,
        "acudiente": e.acudiente, "parentesco": e.parentesco, "telefono": e.telefono,
        "fecha_ingreso": e.fecha_ingreso.isoformat() if e.fecha_ingreso else None,
        "antiguedad_anios": antig, "es_nuevo": es_nuevo,
        "alertas_abiertas": alertas_abiertas,
        "srd": {
            "score": round(rec.score * 100) if rec else None, "nivel": rec.nivel if rec else "—",
            "faltas_acumuladas": rec.faltas_acumuladas if rec else 0,
            "faltas_recientes": rec.faltas_recientes if rec else 0,
            "pct_asistencia": rec.pct_asistencia if rec else None,
            "promedio": rec.promedio if rec else None,
            "tendencia": rec.tendencia if rec else 0,
            "factores": rec.factores.split(" | ") if rec and rec.factores else [],
            "notificado_padre": bool(rec.notificado_padre) if rec else False,
            "fecha_notif_padre": rec.fecha_notif_padre.isoformat(sep=" ", timespec="minutes") if rec and rec.fecha_notif_padre else None,
            "notificado_rectoria": bool(rec.notificado_rectoria) if rec else False,
            "fecha_notif_rectoria": rec.fecha_notif_rectoria.isoformat(sep=" ", timespec="minutes") if rec and rec.fecha_notif_rectoria else None,
            "intervencion_estado": rec.intervencion_estado if rec else "pendiente",
            "intervencion_nota": rec.intervencion_nota if rec else "",
        },
        "asistencia_reciente": asis_mini,
        "notas": notas_out,
        "observador": [{
            "id": o.id, "fecha": o.fecha.isoformat(sep=" ", timespec="minutes"),
            "tipo": o.tipo, "descripcion": o.descripcion, "registrado_por": o.registrado_por,
            "firmado": bool(o.firmado_acudiente), "firma_metodo": o.firma_metodo,
            "fecha_firma": o.fecha_firma.isoformat(sep=" ", timespec="minutes") if o.fecha_firma else None,
        } for o in obs],
        "pendientes": [{
            "id": p.id, "texto": p.texto, "creado_por": p.creado_por, "done": bool(p.done),
            "fecha": p.fecha.isoformat(sep=" ", timespec="minutes"),
        } for p in pend],
        "whatsapp": [{
            "contenido": w.contenido, "estado": w.estado, "contexto": w.contexto,
            "fecha": w.fecha.isoformat(sep=" ", timespec="minutes"),
        } for w in whats],
        "bitacora": [{
            "accion": ln.accion, "detalle": ln.detalle, "actor": ln.actor,
            "fecha": ln.fecha.isoformat(sep=" ", timespec="minutes") if ln.fecha else "",
        } for ln in logs],
    }


class NotifIn(BaseModel):
    estudiante_id: int
    tipo: str  # padre | rectoria


@router.post("/notificar")
def notificar(payload: NotifIn, db: Session = Depends(get_db)):
    rec = db.query(SRDScore).filter(SRDScore.estudiante_id == payload.estudiante_id).first()
    if not rec:
        raise HTTPException(404, "Estudiante no encontrado")
    e = db.query(Estudiante).filter(Estudiante.id == payload.estudiante_id).first()
    ahora = datetime.now()
    if payload.tipo == "padre":
        rec.notificado_padre = True
        rec.fecha_notif_padre = ahora
        label = "padre/acudiente"
        if e:
            db.add(MensajeWhatsApp(
                estudiante_id=e.id, destinatario=f"{e.acudiente} ({e.parentesco or 'acudiente'})",
                telefono=e.telefono,
                contenido=(f"Buen día {e.acudiente}. Desde la institución queremos coordinar un "
                           f"acompañamiento para {e.nombre.split()[0]}: hemos identificado señales de "
                           "riesgo académico y de asistencia. ¿Podemos agendar una reunión esta semana? "
                           "— Coordinación (GyverLabs)"),
                fecha=ahora, estado="ENVIADO (simulado)", contexto="riesgo"))
    elif payload.tipo == "rectoria":
        rec.notificado_rectoria = True
        rec.fecha_notif_rectoria = ahora
        label = "rectoría"
    else:
        raise HTTPException(400, "Tipo inválido")
    db.commit()
    srd_service.log(db, payload.estudiante_id, f"Notificación a {label}", "", "Directivo")
    metadatos.registrar_evento("NOTIFICACION", "Directivo", estudiante_id=payload.estudiante_id,
                               payload={"a": label})
    extra = " 📱 WhatsApp enviado al acudiente (simulado)." if payload.tipo == "padre" else ""
    return {"ok": True, "msg": f"Notificación a {label} registrada con fecha y hora.{extra}"}


class IntervIn(BaseModel):
    estudiante_id: int
    estado: str
    nota: str | None = ""


@router.post("/intervencion")
def intervencion(payload: IntervIn, db: Session = Depends(get_db)):
    rec = db.query(SRDScore).filter(SRDScore.estudiante_id == payload.estudiante_id).first()
    if not rec:
        raise HTTPException(404, "Estudiante no encontrado")
    estado = payload.estado if payload.estado in ("pendiente", "en_proceso", "resuelto") else "pendiente"
    rec.intervencion_estado = estado
    rec.intervencion_nota = payload.nota or ""
    db.commit()
    srd_service.log(db, payload.estudiante_id, f"Intervención: {estado}", payload.nota or "", "Directivo")
    metadatos.registrar_evento("INTERVENCION", "Directivo", estudiante_id=payload.estudiante_id,
                               payload={"estado": estado})
    return {"ok": True, "msg": "Intervención actualizada."}


# ═════════ OBSERVADOR ═════════
class ObsIn(BaseModel):
    estudiante_id: int
    tipo: str
    descripcion: str
    registrado_por: str | None = "Coordinación"


@router.post("/observador/guardar")
def observador_guardar(payload: ObsIn, db: Session = Depends(get_db)):
    if not payload.descripcion.strip():
        return {"ok": False, "msg": "La descripción es obligatoria."}
    tipo = payload.tipo if payload.tipo in ("comportamiento", "academico", "felicitacion", "compromiso") else "academico"
    db.add(ObservadorEntrada(estudiante_id=payload.estudiante_id, fecha=datetime.now(),
                             tipo=tipo, descripcion=payload.descripcion.strip()[:400],
                             registrado_por=payload.registrado_por or "Coordinación"))
    db.commit()
    metadatos.registrar_evento("OBSERVADOR", payload.registrado_por or "Coordinación",
                               estudiante_id=payload.estudiante_id, payload={"tipo": tipo})
    return {"ok": True, "msg": "Anotación registrada en el observador."}


class ObsFirmaIn(BaseModel):
    id: int


@router.post("/observador/firmar")
def observador_firmar(payload: ObsFirmaIn, db: Session = Depends(get_db)):
    o = db.query(ObservadorEntrada).filter(ObservadorEntrada.id == payload.id).first()
    if not o:
        return {"ok": False, "msg": "Anotación no encontrada."}
    if o.firmado_acudiente:
        return {"ok": False, "msg": "Esta anotación ya fue firmada."}
    o.firmado_acudiente = True
    o.firma_metodo = "OTP WhatsApp (simulado)"
    o.fecha_firma = datetime.now()
    db.commit()
    metadatos.registrar_evento("OBSERVADOR_FIRMA", "Acudiente", estudiante_id=o.estudiante_id)
    return {"ok": True, "msg": "✍️ Firma del acudiente registrada con verificación OTP (simulada). En producción: código de 6 dígitos por WhatsApp."}


# ═════════ PENDIENTES (bitácora) ═════════
class PendIn(BaseModel):
    estudiante_id: int
    texto: str
    creado_por: str | None = "Coordinación"


@router.post("/pendientes/guardar")
def pendiente_guardar(payload: PendIn, db: Session = Depends(get_db)):
    if not payload.texto.strip():
        return {"ok": False, "msg": "Escribe el pendiente."}
    db.add(NotaPendiente(estudiante_id=payload.estudiante_id, texto=payload.texto.strip()[:200],
                         creado_por=payload.creado_por or "Coordinación", fecha=datetime.now()))
    db.commit()
    return {"ok": True, "msg": "Pendiente agregado a la bitácora."}


class PendDoneIn(BaseModel):
    id: int
    done: bool


@router.post("/pendientes/done")
def pendiente_done(payload: PendDoneIn, db: Session = Depends(get_db)):
    p = db.query(NotaPendiente).filter(NotaPendiente.id == payload.id).first()
    if not p:
        return {"ok": False, "msg": "Pendiente no encontrado."}
    p.done = payload.done
    db.commit()
    return {"ok": True, "msg": "Pendiente actualizado."}


@router.get("/bitacora")
def bitacora(estudiante_id: int, db: Session = Depends(get_db)):
    filas = db.query(SRDLog).filter(SRDLog.estudiante_id == estudiante_id).order_by(SRDLog.fecha.desc()).limit(20).all()
    return [{
        "accion": ln.accion, "detalle": ln.detalle, "actor": ln.actor,
        "fecha": ln.fecha.isoformat(sep=" ", timespec="minutes") if ln.fecha else "",
    } for ln in filas]
