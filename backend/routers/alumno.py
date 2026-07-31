"""Portal del ESTUDIANTE (punto 4, 6, 9).

El alumno entra con su código, ve sus clases del salón (contenido, materiales,
guías), sus tareas/talleres/evaluaciones con fecha límite, entrega respuestas
que el docente previsualiza y califica, ve sus notas, entra a salas virtuales
(chat en vivo con el docente como moderador) y hace el curso de Contabilidad."""
import json
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (Estudiante, Salon, ActividadAula, EntregaAula, Personal,
                    NotaPeriodo, Periodo, LeccionCurso, ProgresoAlumno, SalaVirtual,
                    MensajeSala, MensajeWhatsApp, SRDScore)
import metadatos

router = APIRouter()


def _mats(a):
    try:
        return json.loads(a.materiales) if a.materiales else []
    except Exception:
        return []


@router.get("/login")
def login(codigo: str, db: Session = Depends(get_db)):
    e = db.query(Estudiante).filter(Estudiante.codigo_acceso == codigo.strip().upper()).first()
    if not e:
        return {"ok": False, "msg": "Código no válido. Pídele tu código a tu docente."}
    sal = db.query(Salon).filter(Salon.id == e.salon_id).first()
    return {"ok": True, "estudiante_id": e.id, "nombre": e.nombre,
            "salon_id": e.salon_id, "salon": sal.nombre if sal else None,
            "institucion_id": e.institucion_id}


@router.get("/tablero")
def tablero(estudiante_id: int, db: Session = Depends(get_db)):
    e = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not e:
        return {"ok": False, "msg": "Estudiante no encontrado."}
    sal = db.query(Salon).filter(Salon.id == e.salon_id).first()
    hoy = date.today()
    # tareas pendientes con fecha límite
    entregas = (db.query(EntregaAula, ActividadAula)
                .join(ActividadAula, EntregaAula.actividad_id == ActividadAula.id)
                .filter(EntregaAula.estudiante_id == estudiante_id).all())
    pendientes = []
    for en, a in entregas:
        if en.estado == "pendiente":
            dias = (a.fecha_limite - hoy).days if a.fecha_limite else None
            pendientes.append({"actividad_id": a.id, "titulo": a.titulo, "tipo": a.tipo,
                               "materia": a.materia, "fecha_limite": a.fecha_limite.isoformat() if a.fecha_limite else None,
                               "dias": dias, "urgente": dias is not None and dias <= 2})
    pendientes.sort(key=lambda x: (x["dias"] is None, x["dias"] if x["dias"] is not None else 999))
    # salas en vivo
    salas = db.query(SalaVirtual).filter(SalaVirtual.salon_id == e.salon_id,
                                         SalaVirtual.estado.in_(["programada", "en_vivo"])).all()
    # progreso curso contabilidad
    total_lec = db.query(LeccionCurso).filter(LeccionCurso.curso == "contabilidad").count()
    hechas = db.query(ProgresoAlumno).filter(ProgresoAlumno.estudiante_id == estudiante_id,
                                             ProgresoAlumno.completada == True).count()  # noqa: E712
    return {
        "ok": True, "nombre": e.nombre, "salon": sal.nombre if sal else "—",
        "pendientes": pendientes[:20],
        "n_clases": db.query(ActividadAula).filter(ActividadAula.salon_id == e.salon_id).count(),
        "salas_vivo": [{"id": s.id, "titulo": s.titulo, "estado": s.estado} for s in salas],
        "curso_contabilidad": {"total": total_lec, "completadas": hechas,
                               "pct": round(100 * hechas / total_lec) if total_lec else 0},
    }


@router.get("/clases")
def clases(estudiante_id: int, db: Session = Depends(get_db)):
    e = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not e:
        return []
    acts = db.query(ActividadAula).filter(ActividadAula.salon_id == e.salon_id,
                                          ActividadAula.padre_id == None).order_by(  # noqa: E711
        ActividadAula.id.desc()).all()
    out = []
    for a in acts:
        en = db.query(EntregaAula).filter(EntregaAula.actividad_id == a.id,
                                          EntregaAula.estudiante_id == estudiante_id).first()
        doc = db.query(Personal).filter(Personal.id == (
            db.query(Salon).filter(Salon.id == a.salon_id).first().director_id)).first()
        subs = db.query(ActividadAula).filter(ActividadAula.padre_id == a.id).count()
        out.append({
            "id": a.id, "titulo": a.titulo, "tipo": a.tipo, "materia": a.materia,
            "descripcion": a.descripcion, "materiales": _mats(a),
            "fecha_limite": a.fecha_limite.isoformat() if a.fecha_limite else None,
            "docente": doc.nombre if doc else "—", "portada": None,
            "n_sub": subs, "generado_ia": bool(a.generado_ia),
            "mi_estado": en.estado if en else "sin_entrega",
            "mi_nota": en.nota if en else None,
        })
    return out


@router.get("/actividad")
def actividad(actividad_id: int, estudiante_id: int, db: Session = Depends(get_db)):
    a = db.query(ActividadAula).filter(ActividadAula.id == actividad_id).first()
    if not a:
        return {"ok": False}
    en = db.query(EntregaAula).filter(EntregaAula.actividad_id == a.id,
                                      EntregaAula.estudiante_id == estudiante_id).first()
    subs = db.query(ActividadAula).filter(ActividadAula.padre_id == a.id).all()
    return {"ok": True, "id": a.id, "titulo": a.titulo, "tipo": a.tipo, "materia": a.materia,
            "descripcion": a.descripcion, "reglas": a.reglas, "materiales": _mats(a),
            "tiempo_limite_min": a.tiempo_limite_min,
            "fecha_limite": a.fecha_limite.isoformat() if a.fecha_limite else None,
            "sub": [{"id": s.id, "titulo": s.titulo, "tipo": s.tipo,
                     "fecha_limite": s.fecha_limite.isoformat() if s.fecha_limite else None} for s in subs],
            "mi_entrega": {"estado": en.estado, "respuesta": en.respuesta or "", "archivo": en.archivo,
                           "nota": en.nota, "retro": en.retro} if en else None}


class EntregarIn(BaseModel):
    actividad_id: int
    estudiante_id: int
    respuesta: str | None = ""
    archivo: str | None = None


@router.post("/entregar")
def entregar(payload: EntregarIn, db: Session = Depends(get_db)):
    en = db.query(EntregaAula).filter(EntregaAula.actividad_id == payload.actividad_id,
                                      EntregaAula.estudiante_id == payload.estudiante_id).first()
    if not en:
        en = EntregaAula(actividad_id=payload.actividad_id, estudiante_id=payload.estudiante_id)
        db.add(en)
    if not (payload.respuesta or "").strip() and not payload.archivo:
        return {"ok": False, "msg": "Escribe tu respuesta o adjunta un archivo."}
    en.respuesta = (payload.respuesta or "")[:5000]
    en.archivo = payload.archivo
    en.estado = "entregado"
    en.fecha_entrega = datetime.now()
    db.commit()
    metadatos.registrar_evento("ALUMNO_ENTREGA", "Alumno", estudiante_id=payload.estudiante_id,
                               payload={"actividad": payload.actividad_id})
    return {"ok": True, "msg": "✅ ¡Entrega enviada! Tu docente la revisará y calificará."}


@router.get("/notas")
def notas(estudiante_id: int, db: Session = Depends(get_db)):
    periodos = db.query(Periodo).order_by(Periodo.numero).all()
    filas = db.query(NotaPeriodo).filter(NotaPeriodo.estudiante_id == estudiante_id).all()
    por_mat = {}
    for n in filas:
        por_mat.setdefault(n.materia, {})[n.periodo_id] = n.nota
    pid_num = {p.id: p.numero for p in periodos}
    out = []
    for mat, vals in por_mat.items():
        pers = {pid_num[pid]: v for pid, v in vals.items() if pid in pid_num}
        prom = round(sum(pers.values()) / len(pers), 1) if pers else None
        out.append({"materia": mat, "periodos": pers, "promedio": prom,
                    "riesgo": prom is not None and prom < 3.0})
    out.sort(key=lambda x: x["materia"])
    return {"periodos": [{"numero": p.numero, "cerrado": bool(p.cerrado)} for p in periodos],
            "materias": out}


# ═════════ CURSO DE CONTABILIDAD ═════════
@router.get("/curso")
def curso(estudiante_id: int, db: Session = Depends(get_db)):
    lecciones = db.query(LeccionCurso).filter(LeccionCurso.curso == "contabilidad").order_by(
        LeccionCurso.orden).all()
    prog = {p.leccion_id: p for p in db.query(ProgresoAlumno).filter(
        ProgresoAlumno.estudiante_id == estudiante_id).all()}
    niveles = {"basico": [], "moderado": [], "avanzado": []}
    for l in lecciones:
        p = prog.get(l.id)
        niveles.setdefault(l.nivel, []).append({
            "id": l.id, "orden": l.orden, "titulo": l.titulo, "icono": l.icono,
            "resumen": l.resumen, "tipo_practica": l.tipo_practica,
            "completada": bool(p and p.completada),
            "quiz_puntaje": p.quiz_puntaje if p else None})
    total = len(lecciones)
    hechas = sum(1 for p in prog.values() if p.completada)
    return {"niveles": niveles, "total": total, "completadas": hechas,
            "pct": round(100 * hechas / total) if total else 0}


@router.get("/leccion")
def leccion(leccion_id: int, estudiante_id: int, db: Session = Depends(get_db)):
    l = db.query(LeccionCurso).filter(LeccionCurso.id == leccion_id).first()
    if not l:
        return {"ok": False}
    try:
        cont = json.loads(l.contenido) if l.contenido else {}
    except Exception:
        cont = {}
    p = db.query(ProgresoAlumno).filter(ProgresoAlumno.estudiante_id == estudiante_id,
                                        ProgresoAlumno.leccion_id == leccion_id).first()
    return {"ok": True, "id": l.id, "titulo": l.titulo, "icono": l.icono, "nivel": l.nivel,
            "resumen": l.resumen, "secciones": cont.get("secciones", []),
            "quiz": cont.get("quiz", []), "tipo_practica": l.tipo_practica,
            "completada": bool(p and p.completada), "quiz_puntaje": p.quiz_puntaje if p else None,
            "practica_data": json.loads(p.practica_data) if (p and p.practica_data) else None}


class CompletarLeccionIn(BaseModel):
    leccion_id: int
    estudiante_id: int
    quiz_puntaje: int | None = None
    practica_data: dict | None = None


@router.post("/leccion/completar")
def completar_leccion(payload: CompletarLeccionIn, db: Session = Depends(get_db)):
    p = db.query(ProgresoAlumno).filter(ProgresoAlumno.estudiante_id == payload.estudiante_id,
                                        ProgresoAlumno.leccion_id == payload.leccion_id).first()
    if not p:
        p = ProgresoAlumno(estudiante_id=payload.estudiante_id, leccion_id=payload.leccion_id)
        db.add(p)
    p.completada = True
    p.quiz_puntaje = payload.quiz_puntaje
    if payload.practica_data is not None:
        p.practica_data = json.dumps(payload.practica_data, ensure_ascii=False)
    p.fecha = datetime.now()
    db.commit()
    metadatos.registrar_evento("ALUMNO_LECCION", "Alumno", estudiante_id=payload.estudiante_id,
                               payload={"leccion": payload.leccion_id, "quiz": payload.quiz_puntaje})
    return {"ok": True, "msg": "🎉 ¡Lección completada! Sigue con la siguiente."}


# ═════════ SALAS VIRTUALES (chat en vivo, docente modera) ═════════
@router.get("/sala")
def sala(sala_id: int, db: Session = Depends(get_db)):
    s = db.query(SalaVirtual).filter(SalaVirtual.id == sala_id).first()
    if not s:
        return {"ok": False}
    msgs = db.query(MensajeSala).filter(MensajeSala.sala_id == sala_id).order_by(
        MensajeSala.id).all()
    return {"ok": True, "titulo": s.titulo, "estado": s.estado,
            "mensajes": [{"autor_tipo": m.autor_tipo, "autor": m.autor_nombre, "texto": m.texto,
                          "fecha": m.fecha.strftime("%H:%M") if m.fecha else ""} for m in msgs]}


class MsgSalaIn(BaseModel):
    sala_id: int
    autor_tipo: str = "alumno"
    autor_id: int | None = None
    autor_nombre: str
    texto: str


@router.post("/sala/mensaje")
def sala_mensaje(payload: MsgSalaIn, db: Session = Depends(get_db)):
    s = db.query(SalaVirtual).filter(SalaVirtual.id == payload.sala_id).first()
    if not s:
        return {"ok": False, "msg": "Sala no encontrada."}
    if not payload.texto.strip():
        return {"ok": False, "msg": "Escribe un mensaje."}
    db.add(MensajeSala(sala_id=payload.sala_id, autor_tipo=payload.autor_tipo,
                       autor_id=payload.autor_id, autor_nombre=payload.autor_nombre,
                       texto=payload.texto.strip()[:500], fecha=datetime.now()))
    db.commit()
    return {"ok": True}


# ═════════ MI SALÓN: compañeros, director, horario (puntos 11, 12, 13) ═════════
from models import (Salon as _SalA, Personal as _PerA,
                    EventoCalendario as _EvA, ObservadorEntrada as _ObsA,
                    Asistencia as _AsisA, Corte as _CorA, TemaClase as _TemCl,
                    ProgresoTemaClase as _ProgCl)
from datetime import date as _dA, timedelta as _tdA


@router.get("/mi_salon")
def mi_salon(estudiante_id: int, db: Session = Depends(get_db)):
    """Todo lo de mi salón: quién es mi director, mis compañeros, mi horario."""
    e = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not e:
        return {"ok": False, "msg": "Estudiante no encontrado."}
    sal = db.query(_SalA).filter(_SalA.id == e.salon_id).first()
    if not sal:
        return {"ok": False, "msg": "Todavía no estás asignado a un salón. Habla con secretaría."}
    dire = db.query(_PerA).filter(_PerA.id == sal.director_id).first()
    comps = db.query(Estudiante).filter(Estudiante.salon_id == sal.id).order_by(Estudiante.nombre).all()
    try:
        horarios = json.loads(sal.horarios) if sal.horarios else []
    except Exception:
        horarios = []
    materias = sorted({h.get("materia") for h in horarios if h.get("materia")})
    docentes = []
    for m in materias:
        d = db.query(_PerA).filter(_PerA.institucion_id == e.institucion_id,
                                   _PerA.rol == "docente", _PerA.area == m).first()
        docentes.append({"materia": m, "nombre": d.nombre if d else (dire.nombre if dire else "Por asignar"),
                         "foto": d.foto if d else (dire.foto if dire else None),
                         "email": d.email if d else None, "telefono": d.telefono if d else None,
                         "personal_id": d.id if d else (dire.id if dire else None)})
    DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    grid = {d: [] for d in DIAS}
    for h in horarios:
        if h.get("dia") in grid:
            grid[h["dia"]].append({"hora": h.get("hora"), "materia": h.get("materia")})
    for d in grid:
        grid[d].sort(key=lambda x: x["hora"] or "")
    return {
        "ok": True,
        "salon": {"id": sal.id, "nombre": sal.nombre, "grado": sal.grado, "jornada": sal.jornada,
                  "n_estudiantes": len(comps)},
        "director": {"nombre": dire.nombre, "foto": dire.foto, "email": dire.email,
                     "telefono": dire.telefono, "area": dire.area,
                     "personal_id": dire.id} if dire else None,
        "docentes": docentes,
        "companeros": [{"id": c.id, "nombre": c.nombre, "yo": c.id == estudiante_id}
                       for c in comps],
        "horario": grid,
    }


@router.get("/mi_calendario")
def mi_calendario(estudiante_id: int, dias: int = 45, db: Session = Depends(get_db)):
    """Calendario del alumno: entregas, evaluaciones y fechas de rectoría."""
    e = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not e:
        return {"eventos": []}
    hoy = _dA.today()
    hasta = hoy + _tdA(days=dias)
    eventos = []
    # entregas pendientes
    filas = (db.query(EntregaAula, ActividadAula)
             .join(ActividadAula, EntregaAula.actividad_id == ActividadAula.id)
             .filter(EntregaAula.estudiante_id == estudiante_id,
                     ActividadAula.fecha_limite != None).all())  # noqa: E711
    for en, a in filas:
        if not (hoy - _tdA(days=10) <= a.fecha_limite <= hasta):
            continue
        eventos.append({
            "fecha": a.fecha_limite.isoformat(), "tipo": a.tipo,
            "titulo": a.titulo, "materia": a.materia,
            "hecho": en.estado in ("entregado", "revisado"),
            "nota": en.nota, "actividad_id": a.id,
            "vencido": a.fecha_limite < hoy and en.estado == "pendiente",
            "origen": "aula",
        })
    # cortes de la institución
    for c in db.query(_CorA).filter(_CorA.institucion_id == e.institucion_id).all():
        if c.fecha_fin and hoy - _tdA(days=10) <= c.fecha_fin <= hasta:
            eventos.append({"fecha": c.fecha_fin.isoformat(), "tipo": "corte",
                            "titulo": f"Cierre de {c.nombre}", "materia": None,
                            "hecho": False, "origen": "institucion"})
    # eventos institucionales del calendario del director de grupo
    sal = db.query(_SalA).filter(_SalA.id == e.salon_id).first()
    if sal and sal.director_id:
        for ev in db.query(_EvA).filter(_EvA.personal_id == sal.director_id,
                                        _EvA.fecha >= hoy - _tdA(days=5),
                                        _EvA.fecha <= hasta).all():
            if ev.tipo in ("obligacion", "reunion", "evaluacion"):
                eventos.append({"fecha": ev.fecha.isoformat(), "tipo": ev.tipo,
                                "titulo": ev.titulo, "materia": None,
                                "hecho": bool(ev.done), "hora": ev.hora,
                                "origen": "rectoria"})
    eventos.sort(key=lambda x: x["fecha"])
    prox = [x for x in eventos if x["fecha"] >= hoy.isoformat() and not x["hecho"]]
    return {
        "eventos": eventos,
        "proximos": prox[:8],
        "vencidos": [x for x in eventos if x.get("vencido")],
        "hoy": hoy.isoformat(),
    }


@router.get("/mis_alertas")
def mis_alertas(estudiante_id: int, db: Session = Depends(get_db)):
    """Todo lo que el alumno debe saber: pendientes, notas bajas, faltas."""
    e = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not e:
        return {"alertas": []}
    hoy = _dA.today()
    alertas = []
    # entregas próximas o vencidas
    filas = (db.query(EntregaAula, ActividadAula)
             .join(ActividadAula, EntregaAula.actividad_id == ActividadAula.id)
             .filter(EntregaAula.estudiante_id == estudiante_id,
                     EntregaAula.estado == "pendiente",
                     ActividadAula.fecha_limite != None).all())  # noqa: E711
    for en, a in filas:
        d = (a.fecha_limite - hoy).days
        if d < 0:
            alertas.append({"nivel": "critico", "icono": "🚨",
                            "titulo": f"«{a.titulo}» está VENCIDA",
                            "detalle": f"Se venció hace {abs(d)} día(s). Habla con tu docente.",
                            "accion": "abrir_actividad", "id": a.id})
        elif d <= 3:
            alertas.append({"nivel": "alto" if d <= 1 else "medio", "icono": "⏰",
                            "titulo": f"«{a.titulo}» {'vence HOY' if d == 0 else 'vence mañana' if d == 1 else f'vence en {d} días'}",
                            "detalle": f"{a.materia or ''} · {a.tipo}",
                            "accion": "abrir_actividad", "id": a.id})
    # materias en riesgo
    periodos = {p.id: p.numero for p in db.query(Periodo).all()}
    notas = db.query(NotaPeriodo).filter(NotaPeriodo.estudiante_id == estudiante_id).all()
    por_mat = {}
    for n in notas:
        por_mat.setdefault(n.materia, []).append(n.nota)
    bajas = [(m, round(sum(v) / len(v), 1)) for m, v in por_mat.items() if sum(v) / len(v) < 3.0]
    for m, prom in bajas:
        alertas.append({"nivel": "critico" if prom < 2.5 else "alto", "icono": "📉",
                        "titulo": f"Vas perdiendo {m}",
                        "detalle": f"Tu promedio es {prom}. Necesitas 3.0 para pasar. Aún estás a tiempo.",
                        "accion": "ver_notas", "id": None})
    # asistencia
    faltas = db.query(_AsisA).filter(_AsisA.estudiante_id == estudiante_id,
                                     _AsisA.estado == "absent").count()
    if faltas >= 5:
        alertas.append({"nivel": "alto" if faltas < 10 else "critico", "icono": "📋",
                        "titulo": f"Llevas {faltas} faltas",
                        "detalle": "Muchas faltas afectan tus notas y pueden hacerte perder el año.",
                        "accion": None, "id": None})
    # observador sin firmar
    sin_firma = db.query(_ObsA).filter(_ObsA.estudiante_id == estudiante_id,
                                       _ObsA.firmado_acudiente == False).count()  # noqa: E712
    if sin_firma:
        alertas.append({"nivel": "medio", "icono": "✍️",
                        "titulo": f"Tienes {sin_firma} anotación(es) sin firmar",
                        "detalle": "Debes firmarlas tú y tu acudiente.",
                        "accion": "ver_observador", "id": None})
    orden = {"critico": 0, "alto": 1, "medio": 2, "bajo": 3}
    alertas.sort(key=lambda x: orden.get(x["nivel"], 9))
    return {"alertas": alertas,
            "n_criticas": sum(1 for a in alertas if a["nivel"] == "critico"),
            "n_total": len(alertas)}


@router.get("/mi_observador")
def mi_observador(estudiante_id: int, db: Session = Depends(get_db)):
    filas = db.query(_ObsA).filter(_ObsA.estudiante_id == estudiante_id).order_by(
        _ObsA.fecha.desc()).all()
    return [{"id": o.id, "fecha": o.fecha.isoformat(sep=" ", timespec="minutes") if o.fecha else "",
             "tipo": o.tipo, "descripcion": o.descripcion,
             "registrado_por": o.registrado_por,
             "firmado": bool(o.firmado_acudiente),
             "metodo": o.firma_metodo} for o in filas]


@router.get("/resumen_academico")
def resumen_academico(estudiante_id: int, db: Session = Depends(get_db)):
    """Lo que ve un papá al entrar con la cuenta de su hijo (punto 13)."""
    e = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not e:
        return {"ok": False}
    total = db.query(_AsisA).filter(_AsisA.estudiante_id == estudiante_id).count()
    faltas = db.query(_AsisA).filter(_AsisA.estudiante_id == estudiante_id,
                                     _AsisA.estado == "absent").count()
    tardes = db.query(_AsisA).filter(_AsisA.estudiante_id == estudiante_id,
                                     _AsisA.estado == "late").count()
    notas = db.query(NotaPeriodo).filter(NotaPeriodo.estudiante_id == estudiante_id).all()
    prom = round(sum(n.nota for n in notas) / len(notas), 1) if notas else None
    por_mat = {}
    for n in notas:
        por_mat.setdefault(n.materia, []).append(n.nota)
    perdiendo = [m for m, v in por_mat.items() if sum(v) / len(v) < 3.0]
    ents = db.query(EntregaAula).filter(EntregaAula.estudiante_id == estudiante_id).all()
    srd = db.query(SRDScore).filter(SRDScore.estudiante_id == estudiante_id).first()
    temas = db.query(_ProgCl).filter(_ProgCl.estudiante_id == estudiante_id,
                                     _ProgCl.completado == True).count()  # noqa: E712
    return {
        "ok": True, "nombre": e.nombre, "acudiente": e.acudiente,
        "asistencia": {"total": total, "faltas": faltas, "tardanzas": tardes,
                       "pct": round(100 * (total - faltas) / total, 1) if total else 100},
        "notas": {"promedio": prom, "materias_perdiendo": perdiendo,
                  "n_materias": len(por_mat)},
        "entregas": {"total": len(ents),
                     "entregadas": sum(1 for x in ents if x.estado in ("entregado", "revisado")),
                     "pendientes": sum(1 for x in ents if x.estado == "pendiente")},
        "temas_vistos": temas,
        "riesgo": {"nivel": srd.nivel, "score": round(srd.score, 1)} if srd else None,
    }


# ═════════ MI NEGOCIO: contabilidad de práctica (punto 24) ═════════
from models import (NegocioAlumno as _Neg, ProductoAlumno as _Prod,
                    MovimientoAlumno as _MovA)

IVA = 0.19


@router.get("/negocio")
def negocio(estudiante_id: int, db: Session = Depends(get_db)):
    """El negocio de práctica del alumno con su inventario y su caja."""
    n = db.query(_Neg).filter(_Neg.estudiante_id == estudiante_id).first()
    if not n:
        return {"ok": True, "existe": False,
                "msg": "Todavía no has creado tu negocio de práctica."}
    prods = db.query(_Prod).filter(_Prod.negocio_id == n.id).order_by(_Prod.nombre).all()
    movs = db.query(_MovA).filter(_MovA.negocio_id == n.id).order_by(_MovA.id.desc()).all()
    ventas = [m for m in movs if m.tipo == "venta"]
    compras = [m for m in movs if m.tipo == "compra"]
    gastos = [m for m in movs if m.tipo == "gasto"]
    total_v = sum(m.total for m in ventas)
    total_c = sum(m.total for m in compras)
    total_g = sum(m.total for m in gastos)
    costo_vendido = 0
    for m in ventas:
        p = next((x for x in prods if x.id == m.producto_id), None)
        if p:
            costo_vendido += (p.costo or 0) * m.cantidad
    inv_costo = sum((p.cantidad or 0) * (p.costo or 0) for p in prods)
    inv_venta = sum((p.cantidad or 0) * (p.precio or 0) for p in prods)
    iva_cobrado = sum(m.iva for m in ventas)
    iva_pagado = sum(m.iva for m in compras)
    utilidad = total_v - costo_vendido - total_g
    bajos = [p for p in prods if (p.cantidad or 0) <= (p.minimo or 5)]
    alertas = []
    for p in bajos:
        alertas.append({"nivel": "alto" if (p.cantidad or 0) == 0 else "medio",
                        "texto": (f"Te quedaste sin {p.nombre}." if (p.cantidad or 0) == 0
                                  else f"Quedan solo {p.cantidad} unidades de {p.nombre}."),
                        "accion": "comprar"})
    if n.caja < 50000:
        alertas.append({"nivel": "alto", "texto": "Tu caja está muy baja. Cuidado con quedarte sin efectivo para el vuelto.", "accion": None})
    if iva_cobrado - iva_pagado > 0:
        alertas.append({"nivel": "medio",
                        "texto": f"Debes ${round(iva_cobrado - iva_pagado):,} de IVA a la DIAN. Guárdalo aparte, no te lo gastes.".replace(",", "."),
                        "accion": "declarar"})
    if utilidad < 0:
        alertas.append({"nivel": "alto",
                        "texto": "Estás perdiendo plata: tus gastos superan la ganancia de las ventas.",
                        "accion": None})
    return {
        "ok": True, "existe": True,
        "negocio": {"id": n.id, "nombre": n.nombre, "tipo": n.tipo,
                    "caja": round(n.caja), "banco": round(n.banco),
                    "capital_inicial": round(n.capital_inicial)},
        "productos": [{"id": p.id, "nombre": p.nombre, "foto": p.foto,
                       "cantidad": p.cantidad, "costo": round(p.costo),
                       "precio": round(p.precio), "minimo": p.minimo,
                       "margen": round(100 * (p.precio - p.costo) / p.precio) if p.precio else 0,
                       "valor_inventario": round((p.cantidad or 0) * (p.costo or 0)),
                       "bajo": (p.cantidad or 0) <= (p.minimo or 5)} for p in prods],
        "movimientos": [{"id": m.id, "tipo": m.tipo, "descripcion": m.descripcion,
                         "cantidad": m.cantidad, "total": round(m.total),
                         "iva": round(m.iva), "metodo": m.metodo,
                         "fecha": m.fecha.isoformat(sep=" ", timespec="minutes") if m.fecha else ""}
                        for m in movs[:40]],
        "estado_resultados": {
            "ventas": round(total_v), "costo_vendido": round(costo_vendido),
            "utilidad_bruta": round(total_v - costo_vendido),
            "gastos": round(total_g), "utilidad_neta": round(utilidad),
            "margen_pct": round(100 * (total_v - costo_vendido) / total_v, 1) if total_v else 0,
        },
        "balance": {
            "activo": round(n.caja + n.banco + inv_costo),
            "caja": round(n.caja), "banco": round(n.banco), "inventario": round(inv_costo),
            "pasivo": round(max(0, iva_cobrado - iva_pagado)),
            "patrimonio": round(n.caja + n.banco + inv_costo - max(0, iva_cobrado - iva_pagado)),
        },
        "iva": {"cobrado": round(iva_cobrado), "pagado": round(iva_pagado),
                "a_pagar": round(max(0, iva_cobrado - iva_pagado))},
        "inventario": {"valor_costo": round(inv_costo), "valor_venta": round(inv_venta),
                       "ganancia_potencial": round(inv_venta - inv_costo),
                       "n_productos": len(prods), "bajos": len(bajos)},
        "alertas": alertas,
        "n_ventas": len(ventas), "n_compras": len(compras),
    }


class CrearNegocioIn(BaseModel):
    estudiante_id: int
    nombre: str
    tipo: str | None = "tienda"


@router.post("/negocio/crear")
def negocio_crear(payload: CrearNegocioIn, db: Session = Depends(get_db)):
    if db.query(_Neg).filter(_Neg.estudiante_id == payload.estudiante_id).first():
        return {"ok": False, "msg": "Ya tienes un negocio creado."}
    if not payload.nombre.strip():
        return {"ok": False, "msg": "Ponle un nombre a tu negocio."}
    n = _Neg(estudiante_id=payload.estudiante_id, nombre=payload.nombre.strip()[:80],
             tipo=payload.tipo or "tienda", capital_inicial=500000, caja=500000,
             banco=0, creado=datetime.now())
    db.add(n)
    db.commit()
    metadatos.registrar_evento("NEGOCIO_CREADO", "Alumno", estudiante_id=payload.estudiante_id)
    return {"ok": True, "id": n.id,
            "msg": f"🏪 «{n.nombre}» creado con $500.000 de capital. Ahora compra productos para empezar a vender."}


class ProductoIn(BaseModel):
    negocio_id: int
    id: int | None = 0
    nombre: str
    costo: float
    precio: float
    cantidad: int | None = 0
    minimo: int | None = 5
    foto: str | None = None


@router.post("/negocio/producto")
def negocio_producto(payload: ProductoIn, db: Session = Depends(get_db)):
    if not payload.nombre.strip():
        return {"ok": False, "msg": "Escribe el nombre del producto."}
    if payload.precio <= payload.costo:
        return {"ok": False,
                "msg": f"⚠️ Estás vendiendo a ${payload.precio:,.0f} algo que te costó ${payload.costo:,.0f}. Así pierdes en cada venta.".replace(",", ".")}
    if payload.id:
        p = db.query(_Prod).filter(_Prod.id == payload.id).first()
        if not p:
            return {"ok": False, "msg": "Producto no encontrado."}
    else:
        p = _Prod(negocio_id=payload.negocio_id)
        db.add(p)
    p.nombre = payload.nombre.strip()[:80]
    p.costo = max(0, payload.costo)
    p.precio = max(0, payload.precio)
    p.minimo = max(0, payload.minimo or 5)
    if payload.foto is not None:
        p.foto = payload.foto
    if not payload.id:
        p.cantidad = 0
    db.commit()
    margen = round(100 * (p.precio - p.costo) / p.precio) if p.precio else 0
    return {"ok": True, "id": p.id,
            "msg": f"📦 {p.nombre} guardado. Margen: {margen}%." +
                   (" Un margen bajo deja poco para cubrir gastos." if margen < 20 else "")}


class MovNegocioIn(BaseModel):
    negocio_id: int
    tipo: str                    # compra | venta | gasto | ingreso
    producto_id: int | None = None
    descripcion: str | None = ""
    cantidad: int | None = 1
    valor_unitario: float | None = 0
    metodo: str | None = "efectivo"
    con_iva: bool = True


@router.post("/negocio/movimiento")
def negocio_movimiento(payload: MovNegocioIn, db: Session = Depends(get_db)):
    """Registrar una compra, una venta o un gasto — con toda la lógica real."""
    n = db.query(_Neg).filter(_Neg.id == payload.negocio_id).first()
    if not n:
        return {"ok": False, "msg": "Negocio no encontrado."}
    cant = max(1, payload.cantidad or 1)
    p = db.query(_Prod).filter(_Prod.id == payload.producto_id).first() if payload.producto_id else None
    if payload.tipo in ("compra", "venta") and not p:
        return {"ok": False, "msg": "Escoge el producto."}
    if payload.tipo == "venta":
        if (p.cantidad or 0) < cant:
            return {"ok": False,
                    "msg": f"⛔ Solo tienes {p.cantidad} unidades de {p.nombre}. No puedes vender {cant}. Primero compra más."}
        vu = p.precio
    elif payload.tipo == "compra":
        vu = payload.valor_unitario or p.costo
    else:
        vu = payload.valor_unitario or 0
    sub = vu * cant
    iva = round(sub * IVA) if payload.con_iva and payload.tipo in ("compra", "venta") else 0
    total = sub + iva
    if payload.tipo in ("compra", "gasto"):
        if payload.metodo == "efectivo" and n.caja < total:
            return {"ok": False,
                    "msg": f"⛔ No tienes suficiente efectivo. Caja: ${n.caja:,.0f}, necesitas ${total:,.0f}.".replace(",", ".")}
        if payload.metodo == "banco" and n.banco < total:
            return {"ok": False, "msg": "No tienes suficiente saldo en el banco."}
    if payload.tipo == "compra":
        p.cantidad = (p.cantidad or 0) + cant
        if payload.valor_unitario:
            p.costo = payload.valor_unitario
        if payload.metodo == "efectivo":
            n.caja -= total
        else:
            n.banco -= total
        desc = f"Compra de {cant} × {p.nombre}"
    elif payload.tipo == "venta":
        p.cantidad = (p.cantidad or 0) - cant
        if payload.metodo == "efectivo":
            n.caja += total
        else:
            n.banco += total
        desc = f"Venta de {cant} × {p.nombre}"
    elif payload.tipo == "gasto":
        if payload.metodo == "efectivo":
            n.caja -= total
        else:
            n.banco -= total
        desc = payload.descripcion or "Gasto"
    else:
        if payload.metodo == "efectivo":
            n.caja += total
        else:
            n.banco += total
        desc = payload.descripcion or "Ingreso"
    m = _MovA(negocio_id=n.id, tipo=payload.tipo, producto_id=p.id if p else None,
              descripcion=desc, cantidad=cant, valor_unitario=vu, total=total,
              iva=iva, metodo=payload.metodo or "efectivo", fecha=datetime.now())
    db.add(m)
    db.commit()
    extra = ""
    if payload.tipo == "venta":
        util = (p.precio - p.costo) * cant
        extra = f" Ganaste ${util:,.0f} en esta venta.".replace(",", ".")
        if iva:
            extra += f" Ojo: ${iva:,.0f} de eso es IVA de la DIAN, no tuyo.".replace(",", ".")
        if (p.cantidad or 0) <= (p.minimo or 5):
            extra += f" ⚠️ Te quedan {p.cantidad} unidades."
    return {"ok": True, "msg": f"✅ {desc} por ${total:,.0f}.".replace(",", ".") + extra,
            "caja": round(n.caja), "banco": round(n.banco)}


class ArqueoIn(BaseModel):
    negocio_id: int
    efectivo_contado: float


@router.post("/negocio/arqueo")
def negocio_arqueo(payload: ArqueoIn, db: Session = Depends(get_db)):
    """El arqueo de caja de verdad: contra los movimientos reales del alumno."""
    n = db.query(_Neg).filter(_Neg.id == payload.negocio_id).first()
    if not n:
        return {"ok": False, "msg": "Negocio no encontrado."}
    esperado = n.caja
    dif = payload.efectivo_contado - esperado
    db.add(_MovA(negocio_id=n.id, tipo="arqueo",
                 descripcion=f"Arqueo de caja · diferencia ${round(dif):,}".replace(",", "."),
                 total=dif, fecha=datetime.now()))
    db.commit()
    if dif == 0:
        msg = f"✅ ¡La caja cuadra perfecto! Contaste ${round(esperado):,} y eso es exactamente lo que debía haber.".replace(",", ".")
        leccion = "Así debe quedar siempre: cada peso justificado por un movimiento registrado."
    elif dif > 0:
        msg = f"⚠️ Te SOBRAN ${round(dif):,}.".replace(",", ".")
        leccion = "Un sobrante también es un error: significa que hiciste una venta que no registraste, o cobraste de más. Revisa tus movimientos."
    else:
        msg = f"🚨 Te FALTAN ${round(abs(dif)):,}.".replace(",", ".")
        leccion = "Un faltante hay que investigarlo: ¿un vuelto mal dado? ¿una salida de plata sin registrar? Nunca lo dejes pasar."
    return {"ok": True, "esperado": round(esperado), "contado": round(payload.efectivo_contado),
            "diferencia": round(dif), "cuadra": dif == 0, "msg": msg, "leccion": leccion}


@router.get("/negocio/factura", response_class=HTMLResponse)
def negocio_factura(movimiento_id: int, db: Session = Depends(get_db)):
    """Genera la factura de una venta, como la haría un negocio real."""
    m = db.query(_MovA).filter(_MovA.id == movimiento_id).first()
    if not m or m.tipo != "venta":
        return HTMLResponse("<h3>Venta no encontrada</h3>", status_code=404)
    n = db.query(_Neg).filter(_Neg.id == m.negocio_id).first()
    e = db.query(Estudiante).filter(Estudiante.id == (n.estudiante_id if n else None)).first()
    sub = m.total - m.iva
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Factura</title>
<style>body{{font-family:ui-monospace,monospace;max-width:400px;margin:24px auto;padding:18px;
 border:1px dashed #94A3B8;font-size:.86rem}}
 h2{{text-align:center;margin:0 0 4px;font-size:1.05rem}}
 .c{{text-align:center;color:#64748B;font-size:.76rem}}
 table{{width:100%;margin:14px 0;border-collapse:collapse}}
 td{{padding:3px 0}}
 .tot{{border-top:1px dashed #94A3B8;font-weight:bold}}
 .noprint{{background:#FEF3C7;padding:8px;border-radius:6px;margin-bottom:12px;font-family:system-ui;font-size:.8rem}}
 @media print{{.noprint{{display:none}} body{{border:none}}}}
</style></head><body onload="setTimeout(()=>window.print(),400)">
<div class="noprint">💡 Elige «Guardar como PDF» para descargar tu factura.</div>
<h2>{n.nombre if n else 'MI NEGOCIO'}</h2>
<div class="c">NIT 900.000.000-0 · Régimen simplificado<br>
{e.nombre if e else ''}<br>FACTURA DE VENTA N° {m.id:05d}</div>
<table>
 <tr><td>Fecha:</td><td style="text-align:right">{m.fecha.strftime('%Y-%m-%d %H:%M') if m.fecha else ''}</td></tr>
 <tr><td colspan="2" style="border-top:1px dashed #94A3B8;padding-top:8px"><b>DETALLE</b></td></tr>
 <tr><td>{m.descripcion}</td><td style="text-align:right">{m.cantidad} und</td></tr>
 <tr><td>Valor unitario</td><td style="text-align:right">${round(m.valor_unitario):,}</td></tr>
 <tr class="tot"><td>Subtotal</td><td style="text-align:right">${round(sub):,}</td></tr>
 <tr><td>IVA (19%)</td><td style="text-align:right">${round(m.iva):,}</td></tr>
 <tr class="tot"><td>TOTAL</td><td style="text-align:right">${round(m.total):,}</td></tr>
 <tr><td>Forma de pago</td><td style="text-align:right">{m.metodo}</td></tr>
</table>
<div class="c">Gracias por su compra<br>Documento de práctica escolar</div>
</body></html>""".replace(",", ".")
    return HTMLResponse(html)
