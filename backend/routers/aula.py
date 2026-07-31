"""Aula Virtual PRO.

- Actividades completas: clase / taller / lectura / video / foro / evaluación /
  curso / recuperación, con materiales (PDF, video, enlace), período, fecha
  límite, tiempo límite y reglas (evaluaciones), y recuperación.
- Asistente IA (simulado): a partir del tema, la materia, el grado, las horas
  y los archivos subidos, genera el plan de clase completo (objetivos,
  momentos, actividades, evaluación y distribución del tiempo). En producción
  este endpoint invoca el modelo generativo del motor GyverLabs.
- Calendario del docente: clases (derivadas del horario de sus salones),
  obligaciones, pendientes y fechas límite de actividades.
- Calificación de entregas con retroalimentación.
"""
import json
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import ActividadAula, EntregaAula, Salon, Estudiante, EventoCalendario, Personal
import metadatos

router = APIRouter()

TIPOS = ("clase", "taller", "lectura", "video", "foro", "evaluacion", "curso", "recuperacion")


def _parse_mats(txt):
    try:
        m = json.loads(txt) if txt else []
        return m if isinstance(m, list) else []
    except Exception:
        return []


@router.get("/actividades")
def actividades(salon_id: int | None = None, institucion_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(ActividadAula)
    if salon_id:
        q = q.filter(ActividadAula.salon_id == salon_id)
    elif institucion_id:
        sal_ids = [s.id for s in db.query(Salon).filter(Salon.institucion_id == institucion_id).all()]
        q = q.filter(ActividadAula.salon_id.in_(sal_ids)) if sal_ids else q.filter(ActividadAula.id < 0)
    salones = {s.id: s.nombre for s in db.query(Salon).all()}
    out = []
    for a in q.order_by(ActividadAula.id.desc()).limit(80).all():
        entregas = db.query(EntregaAula).filter(EntregaAula.actividad_id == a.id).all()
        n_entregado = sum(1 for e in entregas if e.estado != "pendiente")
        n_revisado = sum(1 for e in entregas if e.estado == "revisado")
        out.append({
            "id": a.id, "salon": salones.get(a.salon_id, "—"), "salon_id": a.salon_id,
            "titulo": a.titulo, "descripcion": a.descripcion, "tipo": a.tipo, "materia": a.materia,
            "periodo": a.periodo_numero,
            "fecha_limite": a.fecha_limite.isoformat() if a.fecha_limite else None,
            "tiempo_limite_min": a.tiempo_limite_min, "reglas": a.reglas,
            "permite_recuperacion": bool(a.permite_recuperacion),
            "materiales": _parse_mats(a.materiales),
            "estado": a.estado, "generado_ia": bool(a.generado_ia),
            "padre_id": a.padre_id,
            "n_sub": db.query(ActividadAula).filter(ActividadAula.padre_id == a.id).count(),
            "n_entregas": n_entregado, "n_revisadas": n_revisado, "n_total": len(entregas),
        })
    return out


class ActividadIn(BaseModel):
    salon_id: int
    padre_id: int | None = None
    titulo: str
    descripcion: str | None = ""
    tipo: str | None = "taller"
    materia: str | None = ""
    periodo_numero: int | None = 3
    fecha_limite: str | None = None
    tiempo_limite_min: int | None = None
    reglas: str | None = ""
    permite_recuperacion: bool | None = False
    materiales: list | None = []
    generado_ia: bool | None = False


@router.post("/actividades/guardar")
def guardar_actividad(payload: ActividadIn, db: Session = Depends(get_db)):
    if not payload.titulo.strip():
        return {"ok": False, "msg": "El título es obligatorio."}
    fl = None
    if payload.fecha_limite:
        try:
            fl = date.fromisoformat(payload.fecha_limite)
        except ValueError:
            fl = None
    mats = []
    for m in (payload.materiales or [])[:10]:
        if isinstance(m, dict) and m.get("nombre"):
            mats.append({"tipo": str(m.get("tipo", "pdf"))[:10], "nombre": str(m["nombre"])[:80]})
    act = ActividadAula(
        salon_id=payload.salon_id, padre_id=payload.padre_id or None,
        titulo=payload.titulo.strip()[:120],
        descripcion=(payload.descripcion or "")[:4000],
        tipo=payload.tipo if payload.tipo in TIPOS else "taller",
        materia=payload.materia or "", periodo_numero=payload.periodo_numero or 3,
        fecha_limite=fl,
        tiempo_limite_min=payload.tiempo_limite_min if payload.tipo == "evaluacion" else None,
        reglas=(payload.reglas or "")[:300] or None,
        permite_recuperacion=bool(payload.permite_recuperacion),
        materiales=json.dumps(mats, ensure_ascii=False),
        estado="publicada", creado_por="Docente", generado_ia=bool(payload.generado_ia))
    db.add(act)
    db.flush()
    n = 0
    for e in db.query(Estudiante).filter(Estudiante.salon_id == payload.salon_id).all():
        db.add(EntregaAula(actividad_id=act.id, estudiante_id=e.id, estado="pendiente"))
        n += 1
    db.commit()
    metadatos.registrar_evento("AULA_ACTIVIDAD", "Docente", payload={
        "tipo": act.tipo, "salon_id": act.salon_id, "materiales": len(mats),
        "generado_ia": bool(payload.generado_ia)})
    return {"ok": True, "msg": f"«{act.titulo}» publicada para {n} estudiantes." +
            (" 🤖 Plan generado con el asistente IA." if payload.generado_ia else ""),
            "id": act.id}


@router.get("/entregas")
def entregas(actividad_id: int, db: Session = Depends(get_db)):
    filas = db.query(EntregaAula).filter(EntregaAula.actividad_id == actividad_id).all()
    est = {e.id: e.nombre for e in db.query(Estudiante).all()}
    out = [{
        "id": e.id, "estudiante": est.get(e.estudiante_id, "—"), "estudiante_id": e.estudiante_id,
        "estado": e.estado, "nota": e.nota, "retro": e.retro,
        "fecha_entrega": e.fecha_entrega.isoformat(sep=" ", timespec="minutes") if e.fecha_entrega else None,
    } for e in filas]
    out.sort(key=lambda x: x["estudiante"])
    return out


class CalificarIn(BaseModel):
    id: int
    nota: float
    retro: str | None = ""


@router.post("/entregas/calificar")
def calificar(payload: CalificarIn, db: Session = Depends(get_db)):
    if payload.nota < 0 or payload.nota > 5:
        return {"ok": False, "msg": "La nota debe estar entre 0.0 y 5.0."}
    e = db.query(EntregaAula).filter(EntregaAula.id == payload.id).first()
    if not e:
        return {"ok": False, "msg": "Entrega no encontrada."}
    e.nota = payload.nota
    e.retro = (payload.retro or "")[:300]
    e.estado = "revisado"
    if not e.fecha_entrega:
        e.fecha_entrega = datetime.now()
    db.commit()
    metadatos.registrar_evento("AULA_CALIFICACION", "Docente", estudiante_id=e.estudiante_id,
                               payload={"nota": payload.nota})
    return {"ok": True, "msg": f"Calificada con {payload.nota:.1f}. Retroalimentación enviada al estudiante."}


# ═════════ ASISTENTE IA (simulado) ═════════
class IAIn(BaseModel):
    tema: str
    materia: str | None = ""
    grado: str | None = ""
    horas: float | None = 2
    archivos: list[str] | None = []


@router.post("/ia_preparar")
def ia_preparar(payload: IAIn, db: Session = Depends(get_db)):
    tema = payload.tema.strip() or "el tema de la clase"
    materia = payload.materia or "la asignatura"
    grado = payload.grado or "el grado"
    horas = max(1, min(8, payload.horas or 2))
    archivos = [a for a in (payload.archivos or []) if a][:6]
    total_min = int(horas * 55)
    t_exp = max(10, int(total_min * 0.15))
    t_est = max(15, int(total_min * 0.30))
    t_pra = max(15, int(total_min * 0.35))
    t_eva = max(10, total_min - t_exp - t_est - t_pra)

    uso_archivos = []
    for a in archivos:
        low = a.lower()
        if low.endswith(".pdf") or "guia" in low or "guía" in low:
            uso_archivos.append(f"«{a}» → lectura guiada por parejas con preguntas orientadoras (momento de estructuración).")
        elif any(x in low for x in (".mp4", "video", ".avi", ".mov")):
            uso_archivos.append(f"«{a}» → proyección con dos pausas activas para preguntas (momento de exploración).")
        elif any(x in low for x in (".ppt", "diapositiva")):
            uso_archivos.append(f"«{a}» → apoyo visual del docente durante la explicación central.")
        elif any(x in low for x in (".jpg", ".png", "imagen", "mapa")):
            uso_archivos.append(f"«{a}» → análisis de imagen: qué veo, qué pienso, qué me pregunto.")
        else:
            uso_archivos.append(f"«{a}» → material de consulta para la actividad práctica.")

    plan = {
        "titulo_sugerido": f"{tema} — {materia} (grado {grado})",
        "objetivo_general": f"Al finalizar, el estudiante comprende y aplica {tema.lower()} en situaciones de su contexto (grado {grado}).",
        "objetivos_especificos": [
            f"Identificar los conceptos clave de {tema.lower()}.",
            f"Resolver ejercicios/situaciones aplicando {tema.lower()}.",
            "Comunicar los resultados con vocabulario propio del área.",
        ],
        "momentos": [
            {"nombre": "1 · Exploración (saberes previos)", "minutos": t_exp,
             "detalle": f"Pregunta detonante sobre {tema.lower()} conectada con la vida en el municipio. Lluvia de ideas en el tablero."},
            {"nombre": "2 · Estructuración (explicación)", "minutos": t_est,
             "detalle": "Explicación central con ejemplos resueltos paso a paso." + (" Uso del material subido (ver abajo)." if archivos else "")},
            {"nombre": "3 · Práctica (trabajo del estudiante)", "minutos": t_pra,
             "detalle": "Taller en parejas con 4-6 ejercicios graduados; el docente rota resolviendo dudas."},
            {"nombre": "4 · Transferencia y evaluación", "minutos": t_eva,
             "detalle": "Cierre: 3 preguntas de salida (ticket de salida) para verificar el logro del objetivo."},
        ],
        "uso_de_materiales": uso_archivos or ["Sin archivos: se sugiere una guía impresa corta y el tablero."],
        "evaluacion_sugerida": {
            "tipo": "Formativa (ticket de salida) + taller calificable",
            "criterios": ["Comprensión del concepto (40%)", "Procedimiento correcto (40%)", "Participación y trabajo en clase (20%)"],
        },
        "recomendacion_aula_virtual": (
            f"Publica esta clase en el Aula Virtual con los materiales adjuntos y una fecha límite a 5 días; "
            f"activa 'permite recuperación' para estudiantes con inasistencia justificada."),
        "distribucion_horas": f"{horas} h de clase ≈ {total_min} min efectivos.",
        "nota": "Plan generado por el asistente (versión demo determinística). En producción: modelo generativo del motor GyverLabs entrenado con planes de aula del MEN.",
    }
    metadatos.registrar_evento("IA_ASISTENTE", "Docente", payload={
        "tema": tema[:60], "materia": materia, "archivos": len(archivos), "horas": horas})
    return {"ok": True, "plan": plan}


# ═════════ CALENDARIO DEL DOCENTE ═════════
DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


@router.get("/calendario")
def calendario(personal_id: int, dias: int = 14, db: Session = Depends(get_db)):
    hoy = date.today()
    fin = hoy + timedelta(days=max(1, min(30, dias)))
    eventos = db.query(EventoCalendario).filter(
        EventoCalendario.personal_id == personal_id,
        EventoCalendario.fecha >= hoy, EventoCalendario.fecha <= fin).all()
    out = [{
        "id": ev.id, "fecha": ev.fecha.isoformat(), "hora": ev.hora, "titulo": ev.titulo,
        "tipo": ev.tipo, "detalle": ev.detalle, "done": bool(ev.done), "fuente": "agenda",
    } for ev in eventos]

    # clases derivadas del horario de los salones que dirige
    salones = db.query(Salon).filter(Salon.director_id == personal_id).all()
    for sal in salones:
        try:
            horario = json.loads(sal.horarios) if sal.horarios else []
        except Exception:
            horario = []
        f = hoy
        while f <= fin:
            dia_nombre = DIAS_ES[f.weekday()]
            for h in horario:
                if h.get("dia") == dia_nombre:
                    out.append({
                        "id": None, "fecha": f.isoformat(), "hora": h.get("hora"),
                        "titulo": f"Clase de {h.get('materia','—')} · Salón {sal.nombre}",
                        "tipo": "clase", "detalle": None, "done": False, "fuente": "horario"})
            f += timedelta(days=1)
        # fechas límite de actividades del salón
        for a in db.query(ActividadAula).filter(ActividadAula.salon_id == sal.id,
                                                ActividadAula.fecha_limite != None).all():  # noqa: E711
            if hoy <= a.fecha_limite <= fin:
                out.append({
                    "id": None, "fecha": a.fecha_limite.isoformat(), "hora": None,
                    "titulo": f"⏰ Cierre: {a.titulo} · Salón {sal.nombre}",
                    "tipo": "evaluacion" if a.tipo == "evaluacion" else "obligacion",
                    "detalle": None, "done": False, "fuente": "aula"})
    out.sort(key=lambda x: (x["fecha"], x["hora"] or "99"))
    return {"desde": hoy.isoformat(), "hasta": fin.isoformat(), "eventos": out}


class EventoIn(BaseModel):
    personal_id: int
    fecha: str
    hora: str | None = None
    titulo: str
    tipo: str | None = "obligacion"
    detalle: str | None = ""


@router.post("/calendario/guardar")
def calendario_guardar(payload: EventoIn, db: Session = Depends(get_db)):
    if not payload.titulo.strip():
        return {"ok": False, "msg": "El título es obligatorio."}
    try:
        f = date.fromisoformat(payload.fecha)
    except ValueError:
        return {"ok": False, "msg": "Fecha inválida."}
    tipo = payload.tipo if payload.tipo in ("clase", "obligacion", "pendiente", "evaluacion") else "obligacion"
    db.add(EventoCalendario(personal_id=payload.personal_id, fecha=f, hora=payload.hora or None,
                            titulo=payload.titulo.strip()[:120], tipo=tipo,
                            detalle=(payload.detalle or "")[:200] or None))
    db.commit()
    return {"ok": True, "msg": "Agregado a tu calendario."}


class DoneIn(BaseModel):
    id: int
    done: bool


@router.post("/calendario/done")
def calendario_done(payload: DoneIn, db: Session = Depends(get_db)):
    ev = db.query(EventoCalendario).filter(EventoCalendario.id == payload.id).first()
    if not ev:
        return {"ok": False, "msg": "Evento no encontrado."}
    ev.done = payload.done
    db.commit()
    return {"ok": True, "msg": "¡Listo! ✔" if payload.done else "Reabierto."}


# ═════════ EDITAR ACTIVIDAD (punto 2: ajustes) ═════════
class ActEditIn(BaseModel):
    id: int
    titulo: str | None = None
    descripcion: str | None = None
    fecha_limite: str | None = None
    tiempo_limite_min: int | None = None
    reglas: str | None = None
    permite_recuperacion: bool | None = None
    materiales: list | None = None
    estado: str | None = None   # publicada|cerrada


@router.post("/actividades/editar")
def editar_actividad(payload: ActEditIn, db: Session = Depends(get_db)):
    a = db.query(ActividadAula).filter(ActividadAula.id == payload.id).first()
    if not a:
        return {"ok": False, "msg": "Actividad no encontrada."}
    if payload.titulo is not None and payload.titulo.strip():
        a.titulo = payload.titulo.strip()[:120]
    if payload.descripcion is not None:
        a.descripcion = payload.descripcion[:4000]
    if payload.fecha_limite is not None:
        try:
            a.fecha_limite = date.fromisoformat(payload.fecha_limite) if payload.fecha_limite else None
        except ValueError:
            pass
    if payload.tiempo_limite_min is not None:
        a.tiempo_limite_min = payload.tiempo_limite_min
    if payload.reglas is not None:
        a.reglas = payload.reglas[:300] or None
    if payload.permite_recuperacion is not None:
        a.permite_recuperacion = payload.permite_recuperacion
    if payload.materiales is not None:
        mats = []
        for m in payload.materiales[:10]:
            if isinstance(m, dict) and m.get("nombre"):
                mats.append({"tipo": str(m.get("tipo", "pdf"))[:10], "nombre": str(m["nombre"])[:80]})
        a.materiales = json.dumps(mats, ensure_ascii=False)
    if payload.estado in ("publicada", "cerrada"):
        a.estado = payload.estado
    db.commit()
    metadatos.registrar_evento("AULA_EDITADA", "Docente", payload={"id": a.id})
    return {"ok": True, "msg": f"«{a.titulo}» actualizada."}


# ═════════ GUÍA DESCARGABLE EN PDF (punto 2) ═════════
from fastapi.responses import HTMLResponse


@router.get("/actividades/guia", response_class=HTMLResponse)
def guia_pdf(id: int, db: Session = Depends(get_db)):
    """Guía imprimible de la actividad. Se abre en pestaña nueva y dispara el
    diálogo de impresión del navegador → 'Guardar como PDF'. Así el estudiante
    (o el docente) descarga la guía sin depender de librerías externas."""
    a = db.query(ActividadAula).filter(ActividadAula.id == id).first()
    if not a:
        return HTMLResponse("<h3>Actividad no encontrada</h3>", status_code=404)
    sal = db.query(Salon).filter(Salon.id == a.salon_id).first()
    mats = _parse_mats(a.materiales)
    subs = db.query(ActividadAula).filter(ActividadAula.padre_id == a.id).all()
    desc_html = (a.descripcion or "").replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br>")
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>{a.titulo} — Guía</title>
<style>
 body{{font-family:Georgia,'Times New Roman',serif;max-width:760px;margin:26px auto;color:#1B2530;line-height:1.55;padding:0 18px}}
 .head{{border-bottom:3px solid #0E7C86;padding-bottom:10px;margin-bottom:16px}}
 .logo{{color:#0E7C86;font-weight:bold;font-size:.85rem;letter-spacing:.06em}}
 h1{{font-size:1.5rem;margin:6px 0 2px}}
 .meta{{color:#64748B;font-size:.85rem}}
 .box{{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:10px 14px;margin:12px 0;font-size:.9rem}}
 .mat{{display:inline-block;background:#EEF2F7;border-radius:6px;padding:3px 10px;margin:3px 4px 0 0;font-size:.82rem}}
 h2{{font-size:1.05rem;color:#0F2138;border-bottom:1px solid #E2E8F0;padding-bottom:4px;margin-top:20px}}
 .firma{{margin-top:44px;display:flex;justify-content:space-between;gap:30px}}
 .firma div{{flex:1;border-top:1px solid #94A3B8;padding-top:5px;font-size:.8rem;color:#64748B;text-align:center}}
 .foot{{margin-top:30px;font-size:.72rem;color:#94A3B8;text-align:center}}
 @media print{{ .noprint{{display:none}} }}
</style></head><body onload="setTimeout(()=>window.print(),400)">
<div class="noprint" style="background:#FEF3C7;border:1px solid #FCD34D;border-radius:8px;padding:10px 14px;margin-bottom:14px;font-family:sans-serif;font-size:.85rem">
 💡 En el diálogo de impresión elige <b>«Guardar como PDF»</b> para descargar esta guía.
 <button onclick="window.print()" style="margin-left:10px">🖨️ Imprimir / PDF</button></div>
<div class="head"><div class="logo">SISTEMA EDUCATIVO INTELIGENTE</div>
 <h1>{a.titulo}</h1>
 <div class="meta">{(a.materia or '—')} · Salón {sal.nombre if sal else '—'} · Período {a.periodo_numero or 3} · Tipo: {a.tipo}
 {(' · Fecha límite: ' + a.fecha_limite.isoformat()) if a.fecha_limite else ''}</div></div>
{('<div class="box">⏱️ <b>Evaluación con tiempo límite:</b> ' + str(a.tiempo_limite_min) + ' minutos. <b>Reglas:</b> ' + (a.reglas or '—') + '</div>') if a.tipo == 'evaluacion' else ''}
<h2>Descripción y plan de trabajo</h2>
<p>{desc_html or 'Sin descripción.'}</p>
<h2>Materiales</h2>
<div>{''.join('<span class="mat">📎 ' + m.get('nombre','') + '</span>' for m in mats) or '<span class="meta">Sin materiales adjuntos.</span>'}</div>
{('<h2>Actividades asociadas a esta clase</h2><ul>' + ''.join('<li><b>' + s.tipo + ':</b> ' + s.titulo + (' (límite ' + s.fecha_limite.isoformat() + ')' if s.fecha_limite else '') + '</li>' for s in subs) + '</ul>') if subs else ''}
<div class="firma"><div>Firma del estudiante</div><div>Firma del acudiente</div></div>
<div class="foot">Generado automáticamente · Documento de demostración con datos simulados</div>
</body></html>"""
    return HTMLResponse(html)


# ═════════ RECORDATORIOS (punto 3: alarmas hoy y mañana) ═════════
@router.get("/recordatorios")
def recordatorios(personal_id: int, db: Session = Depends(get_db)):
    """Eventos de HOY y de MAÑANA (agenda propia + cierres del aula) para
    disparar notificaciones push / toasts al entrar al sistema."""
    hoy = date.today()
    man = hoy + timedelta(days=1)
    out = []
    evs = db.query(EventoCalendario).filter(EventoCalendario.personal_id == personal_id,
                                            EventoCalendario.fecha.in_([hoy, man]),
                                            EventoCalendario.done == False).all()  # noqa: E712
    for ev in evs:
        out.append({"cuando": "HOY" if ev.fecha == hoy else "MAÑANA",
                    "hora": ev.hora, "titulo": ev.titulo, "tipo": ev.tipo})
    for sal in db.query(Salon).filter(Salon.director_id == personal_id).all():
        for a in db.query(ActividadAula).filter(ActividadAula.salon_id == sal.id,
                                                ActividadAula.fecha_limite.in_([hoy, man])).all():
            out.append({"cuando": "HOY" if a.fecha_limite == hoy else "MAÑANA",
                        "hora": None, "titulo": f"Cierre: {a.titulo} · Salón {sal.nombre}",
                        "tipo": "evaluacion" if a.tipo == "evaluacion" else "obligacion"})
    out.sort(key=lambda x: (x["cuando"] != "HOY", x["hora"] or "99"))
    return out


# ═════════ SALAS VIRTUALES / CLASE EN VIVO (puntos 4 y 12) ═════════
# Una clase presencial puede transmitirse "en vivo" para los alumnos que no
# pueden ir al colegio: misma clase, misma hora, con chat moderado por el docente.
from models import SalaVirtual as _Sala, MensajeSala as _MsgSala
from datetime import datetime as _dtsala


class SalaIn(BaseModel):
    salon_id: int
    titulo: str
    docente_id: int | None = None
    actividad_id: int | None = None


@router.post("/salas/crear")
def sala_crear(payload: SalaIn, db: Session = Depends(get_db)):
    if not payload.titulo.strip():
        return {"ok": False, "msg": "Ponle un título a la sala (ej: Clase de Matemáticas en vivo)."}
    s = _Sala(salon_id=payload.salon_id, titulo=payload.titulo.strip()[:100],
              docente_id=payload.docente_id, actividad_id=payload.actividad_id,
              estado="programada", fecha=_dtsala.now())
    db.add(s)
    db.commit()
    metadatos.registrar_evento("SALA_CREADA", "Docente", payload={"sala": s.titulo[:40]})
    return {"ok": True, "id": s.id,
            "msg": f"🎥 Sala «{s.titulo}» creada. Cuando la pongas EN VIVO, los alumnos del salón podrán entrar desde su portal — los que están en casa ven la misma clase a la misma hora."}


@router.get("/salas")
def salas(salon_id: int | None = None, institucion_id: int | None = None,
          db: Session = Depends(get_db)):
    q = db.query(_Sala)
    if salon_id:
        q = q.filter(_Sala.salon_id == salon_id)
    elif institucion_id:
        ids = [s.id for s in db.query(Salon).filter(Salon.institucion_id == institucion_id).all()]
        q = q.filter(_Sala.salon_id.in_(ids))
    out = []
    for s in q.order_by(_Sala.id.desc()).limit(40).all():
        sal = db.query(Salon).filter(Salon.id == s.salon_id).first()
        out.append({"id": s.id, "titulo": s.titulo, "estado": s.estado,
                    "salon": sal.nombre if sal else "—", "salon_id": s.salon_id,
                    "n_mensajes": db.query(_MsgSala).filter(_MsgSala.sala_id == s.id).count(),
                    "fecha": s.fecha.isoformat(sep=" ", timespec="minutes") if s.fecha else ""})
    return out


class SalaEstadoIn(BaseModel):
    id: int
    estado: str   # programada | en_vivo | finalizada


@router.post("/salas/estado")
def sala_estado(payload: SalaEstadoIn, db: Session = Depends(get_db)):
    s = db.query(_Sala).filter(_Sala.id == payload.id).first()
    if not s:
        return {"ok": False, "msg": "Sala no encontrada."}
    if payload.estado not in ("programada", "en_vivo", "finalizada"):
        return {"ok": False, "msg": "Estado inválido."}
    s.estado = payload.estado
    db.commit()
    if payload.estado == "en_vivo":
        n = db.query(Estudiante).filter(Estudiante.salon_id == s.salon_id).count()
        return {"ok": True, "msg": f"🔴 EN VIVO. Los {n} estudiantes del salón ya pueden entrar desde su portal (presenciales y virtuales, misma clase)."}
    if payload.estado == "finalizada":
        return {"ok": True, "msg": "⏹️ Clase finalizada. El chat queda guardado como evidencia."}
    return {"ok": True, "msg": "Sala programada."}


@router.get("/salas/detalle")
def sala_detalle(sala_id: int, db: Session = Depends(get_db)):
    s = db.query(_Sala).filter(_Sala.id == sala_id).first()
    if not s:
        return {"ok": False}
    msgs = db.query(_MsgSala).filter(_MsgSala.sala_id == sala_id).order_by(_MsgSala.id).all()
    sal = db.query(Salon).filter(Salon.id == s.salon_id).first()
    return {"ok": True, "id": s.id, "titulo": s.titulo, "estado": s.estado,
            "salon": sal.nombre if sal else "—",
            "mensajes": [{"autor_tipo": m.autor_tipo, "autor": m.autor_nombre, "texto": m.texto,
                          "fecha": m.fecha.strftime("%H:%M") if m.fecha else ""} for m in msgs]}


class EvDelIn(BaseModel):
    id: int


@router.post("/calendario/eliminar")
def calendario_eliminar(payload: EvDelIn, db: Session = Depends(get_db)):
    ev = db.query(EventoCalendario).filter(EventoCalendario.id == payload.id).first()
    if not ev:
        return {"ok": False, "msg": "Evento no encontrado."}
    titulo = ev.titulo
    db.delete(ev)
    db.commit()
    return {"ok": True, "msg": f"«{titulo}» eliminado del calendario."}
