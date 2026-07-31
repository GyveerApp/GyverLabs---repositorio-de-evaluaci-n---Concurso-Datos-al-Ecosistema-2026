"""Clases estructuradas como un curso (puntos 7, 8, 14, 38).

Una clase ya no es un bloque plano de texto: tiene PORTADA, DURACION,
OBJETIVOS y una lista de TEMAS. Cada tema puede llevar su video de YouTube
incrustado, sus bloques de contenido, sus materiales descargables y su quiz.
El alumno la recorre igual que un curso: tema por tema, viendo su avance.

Incluye ademas:
  - previsualizacion de lo que entrego cada estudiante (punto 4)
  - materiales con validacion segun el tipo escogido (puntos 5 y 6)
  - editar / eliminar / duplicar clases (punto 8)
  - biblioteca de clases grabadas (punto 17)
"""
import json
import re
from datetime import datetime, date
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (ActividadAula, TemaClase, ProgresoTemaClase, EntregaAula,
                    Estudiante, Salon, Personal, GrabacionClase, SalaVirtual,
                    MensajeSala, TemaPlan)
import metadatos

router = APIRouter()

# ── Tipos de material y que extensiones acepta cada uno (puntos 5 y 6) ──
TIPOS_MATERIAL = {
    "pdf":          {"label": "📄 Documento PDF", "accept": ".pdf", "exts": ["pdf"], "modo": "archivo"},
    "documento":    {"label": "📝 Documento de texto", "accept": ".doc,.docx,.odt,.txt,.rtf",
                     "exts": ["doc", "docx", "odt", "txt", "rtf"], "modo": "archivo"},
    "hoja":         {"label": "📊 Hoja de cálculo", "accept": ".xls,.xlsx,.csv,.ods",
                     "exts": ["xls", "xlsx", "csv", "ods"], "modo": "archivo"},
    "presentacion": {"label": "📽️ Presentación", "accept": ".ppt,.pptx,.odp",
                     "exts": ["ppt", "pptx", "odp"], "modo": "archivo"},
    "imagen":       {"label": "🖼️ Imagen", "accept": ".jpg,.jpeg,.png,.gif,.webp",
                     "exts": ["jpg", "jpeg", "png", "gif", "webp", "heic"], "modo": "archivo"},
    "video_archivo": {"label": "🎬 Video (archivo)", "accept": ".mp4,.mov,.webm,.mkv",
                      "exts": ["mp4", "mov", "webm", "mkv", "avi"], "modo": "archivo"},
    "audio":        {"label": "🎧 Audio", "accept": ".mp3,.wav,.m4a,.ogg",
                     "exts": ["mp3", "wav", "m4a", "ogg"], "modo": "archivo"},
    "video_enlace": {"label": "▶️ Video de YouTube / Vimeo", "accept": "", "exts": [], "modo": "enlace"},
    "enlace":       {"label": "🔗 Enlace web", "accept": "", "exts": [], "modo": "enlace"},
}


def _ext(nombre):
    return (nombre or "").split(".")[-1].lower() if "." in (nombre or "") else ""


def validar_material(tipo, nombre, url):
    """Comprueba que lo adjuntado corresponda al tipo escogido."""
    cfg = TIPOS_MATERIAL.get(tipo)
    if not cfg:
        return False, "Tipo de material no válido."
    if cfg["modo"] == "enlace":
        u = (url or nombre or "").strip()
        if not u:
            return False, f"Pega el enlace para «{cfg['label']}»."
        if not re.match(r"^https?://", u, re.I):
            return False, "El enlace debe empezar por http:// o https://"
        if tipo == "video_enlace" and not re.search(r"(youtube\.com|youtu\.be|vimeo\.com)", u, re.I):
            return False, "Ese enlace no parece de YouTube ni de Vimeo. Usa «🔗 Enlace web» si es otra página."
        return True, None
    if not nombre:
        return False, f"Selecciona un archivo para «{cfg['label']}»."
    e = _ext(nombre)
    if e not in cfg["exts"]:
        return False, (f"El archivo «{nombre}» no corresponde a «{cfg['label']}». "
                       f"Se esperaba: {', '.join('.' + x for x in cfg['exts'])}.")
    return True, None


def youtube_id(url):
    """Saca el id del video para poder incrustarlo."""
    if not url:
        return None
    m = re.search(r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    return m.group(1) if m else None


@router.get("/tipos_material")
def tipos_material():
    return [{"id": k, **v} for k, v in TIPOS_MATERIAL.items()]


def _jl(t, d):
    try:
        return json.loads(t) if t else d
    except Exception:
        return d


# ═════════════ LA CLASE COMPLETA (vista del alumno y del docente) ═════════════
@router.get("/clase")
def clase(actividad_id: int, estudiante_id: int | None = None, db: Session = Depends(get_db)):
    a = db.query(ActividadAula).filter(ActividadAula.id == actividad_id).first()
    if not a:
        return {"ok": False, "msg": "Clase no encontrada."}
    sal = db.query(Salon).filter(Salon.id == a.salon_id).first()
    doc = db.query(Personal).filter(Personal.id == (sal.director_id if sal else None)).first()
    temas = db.query(TemaClase).filter(TemaClase.actividad_id == a.id).order_by(TemaClase.orden).all()
    prog = {}
    if estudiante_id:
        for p in db.query(ProgresoTemaClase).filter(
                ProgresoTemaClase.estudiante_id == estudiante_id,
                ProgresoTemaClase.actividad_id == a.id).all():
            prog[p.tema_id] = p
    # el primer tema no completado es el actual
    idx = 0
    for i, t in enumerate(temas):
        p = prog.get(t.id)
        if not (p and p.completado):
            idx = i
            break
    else:
        idx = len(temas)
    filas = []
    for i, t in enumerate(temas):
        p = prog.get(t.id)
        filas.append({
            "id": t.id, "titulo": t.titulo, "resumen": t.resumen,
            "duracion_min": t.duracion_min, "orden": t.orden,
            "video_url": t.video_url, "youtube_id": youtube_id(t.video_url),
            "n_materiales": len(_jl(t.materiales, [])), "n_quiz": len(_jl(t.quiz, [])),
            "completado": bool(p and p.completado),
            "quiz_puntaje": p.quiz_puntaje if p else None,
            "actual": i == idx, "bloqueado": False,   # en clases no se bloquea: el alumno decide
        })
    sub = db.query(ActividadAula).filter(ActividadAula.padre_id == a.id).all()
    mi_entrega = None
    if estudiante_id:
        en = db.query(EntregaAula).filter(EntregaAula.actividad_id == a.id,
                                          EntregaAula.estudiante_id == estudiante_id).first()
        if en:
            mi_entrega = {"estado": en.estado, "respuesta": en.respuesta or "",
                          "archivo": en.archivo, "nota": en.nota, "retro": en.retro}
    hechos = sum(1 for f in filas if f["completado"])
    return {
        "ok": True, "id": a.id, "titulo": a.titulo, "tipo": a.tipo, "materia": a.materia,
        "descripcion": a.descripcion, "portada": a.portada, "color": a.color or "#0E7C86",
        "duracion_min": a.duracion_min, "objetivos": _jl(a.objetivos, []),
        "video_url": a.video_url, "youtube_id": youtube_id(a.video_url),
        "materiales": _jl(a.materiales, []), "reglas": a.reglas,
        "fecha_limite": a.fecha_limite.isoformat() if a.fecha_limite else None,
        "corte": a.corte, "periodo": a.periodo_numero,
        "salon": sal.nombre if sal else "—", "salon_id": a.salon_id,
        "docente": doc.nombre if doc else "—", "docente_id": doc.id if doc else None,
        "docente_foto": doc.foto if doc else None,
        "temas": filas, "n_temas": len(filas), "completados": hechos,
        "pct": round(100 * hechos / len(filas)) if filas else 0,
        "tema_actual": filas[idx]["id"] if idx < len(filas) else (filas[0]["id"] if filas else None),
        "actividades": [{"id": s.id, "titulo": s.titulo, "tipo": s.tipo,
                         "fecha_limite": s.fecha_limite.isoformat() if s.fecha_limite else None}
                        for s in sub],
        "mi_entrega": mi_entrega,
        "generado_ia": bool(a.generado_ia), "estado": a.estado,
    }


@router.get("/tema")
def tema(tema_id: int, estudiante_id: int | None = None, db: Session = Depends(get_db)):
    t = db.query(TemaClase).filter(TemaClase.id == tema_id).first()
    if not t:
        return {"ok": False, "msg": "Tema no encontrado."}
    a = db.query(ActividadAula).filter(ActividadAula.id == t.actividad_id).first()
    hermanos = db.query(TemaClase).filter(TemaClase.actividad_id == t.actividad_id).order_by(
        TemaClase.orden).all()
    ids = [x.id for x in hermanos]
    i = ids.index(t.id) if t.id in ids else 0
    p = None
    if estudiante_id:
        p = db.query(ProgresoTemaClase).filter(ProgresoTemaClase.estudiante_id == estudiante_id,
                                               ProgresoTemaClase.tema_id == tema_id).first()
    return {
        "ok": True, "id": t.id, "titulo": t.titulo, "resumen": t.resumen,
        "contenido": _jl(t.contenido, []), "quiz": _jl(t.quiz, []),
        "materiales": _jl(t.materiales, []),
        "video_url": t.video_url, "youtube_id": youtube_id(t.video_url),
        "duracion_min": t.duracion_min,
        "clase": {"id": a.id, "titulo": a.titulo, "materia": a.materia,
                  "color": a.color or "#0E7C86"} if a else None,
        "posicion": i + 1, "total": len(hermanos),
        "anterior": ids[i - 1] if i > 0 else None,
        "siguiente": ids[i + 1] if i < len(ids) - 1 else None,
        "completado": bool(p and p.completado),
        "quiz_puntaje": p.quiz_puntaje if p else None,
    }


class CompletarTemaIn(BaseModel):
    tema_id: int
    estudiante_id: int
    quiz_puntaje: int | None = None
    minutos: int | None = 0


@router.post("/tema/completar")
def completar_tema(payload: CompletarTemaIn, db: Session = Depends(get_db)):
    t = db.query(TemaClase).filter(TemaClase.id == payload.tema_id).first()
    if not t:
        return {"ok": False, "msg": "Tema no encontrado."}
    p = db.query(ProgresoTemaClase).filter(
        ProgresoTemaClase.estudiante_id == payload.estudiante_id,
        ProgresoTemaClase.tema_id == payload.tema_id).first()
    if not p:
        p = ProgresoTemaClase(estudiante_id=payload.estudiante_id, tema_id=payload.tema_id,
                              actividad_id=t.actividad_id)
        db.add(p)
    p.completado = True
    if payload.quiz_puntaje is not None:
        p.quiz_puntaje = max(p.quiz_puntaje or 0, payload.quiz_puntaje)
    p.minutos = (p.minutos or 0) + max(0, payload.minutos or 0)
    p.fecha = datetime.now()
    db.commit()
    hermanos = db.query(TemaClase).filter(TemaClase.actividad_id == t.actividad_id).order_by(
        TemaClase.orden).all()
    ids = [x.id for x in hermanos]
    i = ids.index(t.id) if t.id in ids else -1
    hechos = db.query(ProgresoTemaClase).filter(
        ProgresoTemaClase.estudiante_id == payload.estudiante_id,
        ProgresoTemaClase.actividad_id == t.actividad_id,
        ProgresoTemaClase.completado == True).count()  # noqa: E712
    metadatos.registrar_evento("CLASE_TEMA", "Alumno", estudiante_id=payload.estudiante_id,
                               payload={"tema": t.titulo[:40]})
    return {"ok": True, "msg": "✅ Tema visto.",
            "siguiente": ids[i + 1] if 0 <= i < len(ids) - 1 else None,
            "completados": hechos, "total": len(ids),
            "pct": round(100 * hechos / len(ids)) if ids else 0}


# ═════════════ CREAR / EDITAR LA ESTRUCTURA (docente) ═════════════
class ClaseIn(BaseModel):
    id: int | None = 0
    salon_id: int
    padre_id: int | None = None
    titulo: str
    tipo: str | None = "clase"
    materia: str | None = ""
    descripcion: str | None = ""
    periodo_numero: int | None = 3
    corte: str | None = ""
    fecha_limite: str | None = None
    duracion_min: int | None = 45
    portada: str | None = None
    color: str | None = "#0E7C86"
    video_url: str | None = ""
    objetivos: list | None = None
    materiales: list | None = None
    reglas: str | None = ""
    tiempo_limite_min: int | None = 45
    generado_ia: bool | None = False
    temas: list | None = None       # [{titulo,resumen,contenido,video_url,materiales,quiz,duracion_min}]
    estado: str | None = "publicada"


@router.post("/clase/guardar")
def clase_guardar(payload: ClaseIn, db: Session = Depends(get_db)):
    if not payload.titulo.strip():
        return {"ok": False, "msg": "Ponle un título a la clase."}
    # validar materiales de la clase
    mats = []
    for m in (payload.materiales or [])[:20]:
        if not isinstance(m, dict):
            continue
        ok, err = validar_material(m.get("tipo"), m.get("nombre"), m.get("url"))
        if not ok:
            return {"ok": False, "msg": err}
        mats.append({"tipo": m.get("tipo"), "nombre": (m.get("nombre") or m.get("url") or "")[:120],
                     "url": (m.get("url") or "")[:400] or None, "tamano": m.get("tamano")})
    if payload.video_url and not youtube_id(payload.video_url) and not re.match(r"^https?://", payload.video_url):
        return {"ok": False, "msg": "El video principal debe ser un enlace válido de YouTube o Vimeo."}

    nuevo = not payload.id
    if payload.id:
        a = db.query(ActividadAula).filter(ActividadAula.id == payload.id).first()
        if not a:
            return {"ok": False, "msg": "Clase no encontrada."}
    else:
        a = ActividadAula(salon_id=payload.salon_id, padre_id=payload.padre_id or None,
                          creado_por="Docente")
        db.add(a)
    a.titulo = payload.titulo.strip()[:120]
    a.tipo = payload.tipo or "clase"
    a.materia = (payload.materia or "").strip()[:60]
    a.descripcion = (payload.descripcion or "")[:6000]
    a.periodo_numero = payload.periodo_numero or 3
    a.corte = (payload.corte or "").strip()[:30] or None
    a.duracion_min = max(5, payload.duracion_min or 45)
    a.portada = payload.portada
    a.color = payload.color or "#0E7C86"
    a.video_url = (payload.video_url or "").strip()[:400] or None
    a.objetivos = json.dumps([str(o)[:200] for o in (payload.objetivos or [])][:8], ensure_ascii=False)
    a.materiales = json.dumps(mats, ensure_ascii=False)
    a.reglas = (payload.reglas or "")[:300] or None
    a.tiempo_limite_min = payload.tiempo_limite_min
    a.generado_ia = bool(payload.generado_ia)
    a.estado = payload.estado if payload.estado in ("publicada", "borrador", "cerrada") else "publicada"
    if payload.fecha_limite:
        try:
            a.fecha_limite = date.fromisoformat(payload.fecha_limite)
        except ValueError:
            pass
    elif payload.fecha_limite == "":
        a.fecha_limite = None
    db.flush()

    # temas
    if payload.temas is not None:
        db.query(TemaClase).filter(TemaClase.actividad_id == a.id).delete()
        for i, t in enumerate(payload.temas[:30], start=1):
            if not isinstance(t, dict) or not (t.get("titulo") or "").strip():
                continue
            tmats = []
            for m in (t.get("materiales") or [])[:12]:
                if not isinstance(m, dict):
                    continue
                ok, err = validar_material(m.get("tipo"), m.get("nombre"), m.get("url"))
                if not ok:
                    return {"ok": False, "msg": f"Tema «{t.get('titulo')}»: {err}"}
                tmats.append({"tipo": m.get("tipo"), "nombre": (m.get("nombre") or m.get("url") or "")[:120],
                              "url": (m.get("url") or "")[:400] or None, "tamano": m.get("tamano")})
            db.add(TemaClase(
                actividad_id=a.id, titulo=str(t["titulo"])[:120],
                resumen=str(t.get("resumen") or "")[:250] or None,
                contenido=json.dumps(t.get("contenido") or [], ensure_ascii=False),
                video_url=str(t.get("video_url") or "")[:400] or None,
                duracion_min=int(t.get("duracion_min") or 10),
                materiales=json.dumps(tmats, ensure_ascii=False),
                quiz=json.dumps(t.get("quiz") or [], ensure_ascii=False),
                orden=i))

    # crear las entregas de los estudiantes si es nueva y publicada
    n = 0
    if nuevo and a.estado == "publicada":
        for e in db.query(Estudiante).filter(Estudiante.salon_id == a.salon_id).all():
            ya = db.query(EntregaAula).filter(EntregaAula.actividad_id == a.id,
                                              EntregaAula.estudiante_id == e.id).first()
            if not ya:
                db.add(EntregaAula(actividad_id=a.id, estudiante_id=e.id, estado="pendiente"))
                n += 1
    db.commit()
    metadatos.registrar_evento("CLASE_GUARDADA", "Docente",
                               payload={"titulo": a.titulo[:40], "temas": len(payload.temas or [])})
    n_temas = db.query(TemaClase).filter(TemaClase.actividad_id == a.id).count()
    return {"ok": True, "id": a.id,
            "msg": (f"«{a.titulo}» {'publicada' if nuevo else 'actualizada'} con {n_temas} tema(s)."
                    + (f" {n} estudiantes la tienen en su portal." if n else ""))}


class IdIn(BaseModel):
    id: int


@router.post("/clase/eliminar")
def clase_eliminar(payload: IdIn, db: Session = Depends(get_db)):
    a = db.query(ActividadAula).filter(ActividadAula.id == payload.id).first()
    if not a:
        return {"ok": False, "msg": "Clase no encontrada."}
    n_ent = db.query(EntregaAula).filter(EntregaAula.actividad_id == a.id,
                                         EntregaAula.estado != "pendiente").count()
    titulo = a.titulo
    hijos = db.query(ActividadAula).filter(ActividadAula.padre_id == a.id).all()
    for h in hijos:
        db.query(TemaClase).filter(TemaClase.actividad_id == h.id).delete()
        db.query(EntregaAula).filter(EntregaAula.actividad_id == h.id).delete()
        db.delete(h)
    db.query(TemaClase).filter(TemaClase.actividad_id == a.id).delete()
    db.query(ProgresoTemaClase).filter(ProgresoTemaClase.actividad_id == a.id).delete()
    db.query(EntregaAula).filter(EntregaAula.actividad_id == a.id).delete()
    db.delete(a)
    db.commit()
    metadatos.registrar_evento("CLASE_ELIMINADA", "Docente", payload={"titulo": titulo[:40]})
    return {"ok": True,
            "msg": (f"«{titulo}» eliminada" + (f", junto con {n_ent} entrega(s) ya recibida(s)." if n_ent else ".")
                    + (f" También se borraron {len(hijos)} actividad(es) asociada(s)." if hijos else ""))}


@router.post("/clase/duplicar")
def clase_duplicar(payload: IdIn, db: Session = Depends(get_db)):
    a = db.query(ActividadAula).filter(ActividadAula.id == payload.id).first()
    if not a:
        return {"ok": False, "msg": "Clase no encontrada."}
    n = ActividadAula(
        salon_id=a.salon_id, titulo=f"{a.titulo} (copia)", tipo=a.tipo, materia=a.materia,
        descripcion=a.descripcion, periodo_numero=a.periodo_numero, corte=a.corte,
        duracion_min=a.duracion_min, portada=a.portada, color=a.color, video_url=a.video_url,
        objetivos=a.objetivos, materiales=a.materiales, reglas=a.reglas,
        tiempo_limite_min=a.tiempo_limite_min, estado="borrador", creado_por="Docente")
    db.add(n)
    db.flush()
    for t in db.query(TemaClase).filter(TemaClase.actividad_id == a.id).order_by(TemaClase.orden).all():
        db.add(TemaClase(actividad_id=n.id, titulo=t.titulo, resumen=t.resumen,
                         contenido=t.contenido, video_url=t.video_url,
                         duracion_min=t.duracion_min, materiales=t.materiales,
                         quiz=t.quiz, orden=t.orden))
    db.commit()
    return {"ok": True, "id": n.id,
            "msg": f"Clase duplicada como borrador: «{n.titulo}». Edítala y publícala cuando quieras."}


class EstadoIn(BaseModel):
    id: int
    estado: str


@router.post("/clase/estado")
def clase_estado(payload: EstadoIn, db: Session = Depends(get_db)):
    a = db.query(ActividadAula).filter(ActividadAula.id == payload.id).first()
    if not a:
        return {"ok": False, "msg": "Clase no encontrada."}
    if payload.estado not in ("publicada", "borrador", "cerrada"):
        return {"ok": False, "msg": "Estado inválido."}
    antes = a.estado
    a.estado = payload.estado
    n = 0
    if payload.estado == "publicada" and antes != "publicada":
        for e in db.query(Estudiante).filter(Estudiante.salon_id == a.salon_id).all():
            ya = db.query(EntregaAula).filter(EntregaAula.actividad_id == a.id,
                                              EntregaAula.estudiante_id == e.id).first()
            if not ya:
                db.add(EntregaAula(actividad_id=a.id, estudiante_id=e.id, estado="pendiente"))
                n += 1
    db.commit()
    msg = {"publicada": f"«{a.titulo}» publicada." + (f" {n} estudiantes ya la ven." if n else ""),
           "borrador": f"«{a.titulo}» pasó a borrador: los estudiantes dejan de verla.",
           "cerrada": f"«{a.titulo}» cerrada: no recibe más entregas."}[payload.estado]
    return {"ok": True, "msg": msg}


# ═════════════ ENTREGAS: previsualizar lo que entregó el alumno (punto 4) ═════════════
@router.get("/entregas_detalle")
def entregas_detalle(actividad_id: int, db: Session = Depends(get_db)):
    """Todo lo que entregaron los estudiantes, con su contenido para revisarlo."""
    a = db.query(ActividadAula).filter(ActividadAula.id == actividad_id).first()
    if not a:
        return {"ok": False, "msg": "Actividad no encontrada."}
    filas = (db.query(EntregaAula, Estudiante)
             .join(Estudiante, EntregaAula.estudiante_id == Estudiante.id)
             .filter(EntregaAula.actividad_id == actividad_id)
             .order_by(Estudiante.nombre).all())
    hoy = date.today()
    out = []
    for en, e in filas:
        tarde = None
        if en.fecha_entrega and a.fecha_limite:
            tarde = en.fecha_entrega.date() > a.fecha_limite
        out.append({
            "entrega_id": en.id, "estudiante_id": e.id, "estudiante": e.nombre,
            "estado": en.estado, "nota": en.nota, "retro": en.retro,
            "respuesta": en.respuesta or "", "archivo": en.archivo,
            "n_palabras": len((en.respuesta or "").split()),
            "fecha_entrega": en.fecha_entrega.isoformat(sep=" ", timespec="minutes") if en.fecha_entrega else None,
            "entregado_tarde": tarde,
            "vencida": bool(a.fecha_limite and en.estado == "pendiente" and a.fecha_limite < hoy),
        })
    n_ent = sum(1 for x in out if x["estado"] in ("entregado", "revisado"))
    n_rev = sum(1 for x in out if x["estado"] == "revisado")
    notas = [x["nota"] for x in out if x["nota"] is not None]
    return {
        "ok": True, "actividad": a.titulo, "tipo": a.tipo,
        "fecha_limite": a.fecha_limite.isoformat() if a.fecha_limite else None,
        "entregas": out,
        "resumen": {
            "total": len(out), "entregadas": n_ent, "revisadas": n_rev,
            "pendientes": len(out) - n_ent,
            "vencidas": sum(1 for x in out if x["vencida"]),
            "tarde": sum(1 for x in out if x["entregado_tarde"]),
            "promedio": round(sum(notas) / len(notas), 1) if notas else None,
        },
    }


class CalificarIn(BaseModel):
    entrega_id: int
    nota: float | None = None
    retro: str | None = ""


@router.post("/calificar")
def calificar(payload: CalificarIn, db: Session = Depends(get_db)):
    en = db.query(EntregaAula).filter(EntregaAula.id == payload.entrega_id).first()
    if not en:
        return {"ok": False, "msg": "Entrega no encontrada."}
    if payload.nota is not None:
        if not (0 <= payload.nota <= 5):
            return {"ok": False, "msg": "La nota debe estar entre 0.0 y 5.0."}
        en.nota = round(payload.nota, 1)
        en.estado = "revisado"
    en.retro = (payload.retro or "").strip()[:400] or None
    db.commit()
    e = db.query(Estudiante).filter(Estudiante.id == en.estudiante_id).first()
    metadatos.registrar_evento("ENTREGA_CALIFICADA", "Docente",
                               estudiante_id=en.estudiante_id, payload={"nota": en.nota})
    return {"ok": True, "msg": f"{(e.nombre.split()[0] if e else 'Estudiante')}: nota {en.nota if en.nota is not None else '—'} guardada."}


# ═════════════ BIBLIOTECA DE CLASES GRABADAS (punto 17) ═════════════
@router.get("/biblioteca")
def biblioteca(institucion_id: int | None = None, salon_id: int | None = None,
               materia: str | None = None, db: Session = Depends(get_db)):
    q = db.query(GrabacionClase)
    if salon_id:
        q = q.filter(GrabacionClase.salon_id == salon_id)
    elif institucion_id:
        ids = [s.id for s in db.query(Salon).filter(Salon.institucion_id == institucion_id).all()]
        q = q.filter(GrabacionClase.salon_id.in_(ids))
    if materia:
        q = q.filter(GrabacionClase.materia == materia)
    filas = q.order_by(GrabacionClase.fecha.desc()).limit(60).all()
    out = []
    for g in filas:
        sal = db.query(Salon).filter(Salon.id == g.salon_id).first()
        out.append({
            "id": g.id, "titulo": g.titulo, "materia": g.materia, "docente": g.docente,
            "salon": sal.nombre if sal else "—", "salon_id": g.salon_id,
            "fecha": g.fecha.isoformat(sep=" ", timespec="minutes") if g.fecha else "",
            "duracion_min": g.duracion_min, "video_url": g.video_url,
            "youtube_id": youtube_id(g.video_url), "resumen": g.resumen,
            "n_vistas": g.n_vistas or 0,
        })
    materias = sorted({g.materia for g in filas if g.materia})
    return {"grabaciones": out, "materias": materias, "total": len(out)}


@router.get("/biblioteca/ver")
def biblioteca_ver(id: int, db: Session = Depends(get_db)):
    g = db.query(GrabacionClase).filter(GrabacionClase.id == id).first()
    if not g:
        return {"ok": False, "msg": "Grabación no encontrada."}
    g.n_vistas = (g.n_vistas or 0) + 1
    db.commit()
    chat = []
    if g.sala_id:
        chat = [{"autor": m.autor_nombre, "tipo": m.autor_tipo, "texto": m.texto,
                 "hora": m.fecha.strftime("%H:%M") if m.fecha else ""}
                for m in db.query(MensajeSala).filter(MensajeSala.sala_id == g.sala_id).order_by(MensajeSala.id).all()]
    sal = db.query(Salon).filter(Salon.id == g.salon_id).first()
    return {"ok": True, "id": g.id, "titulo": g.titulo, "materia": g.materia,
            "docente": g.docente, "salon": sal.nombre if sal else "—",
            "fecha": g.fecha.isoformat(sep=" ", timespec="minutes") if g.fecha else "",
            "duracion_min": g.duracion_min, "video_url": g.video_url,
            "youtube_id": youtube_id(g.video_url), "resumen": g.resumen,
            "transcripcion": g.transcripcion, "n_vistas": g.n_vistas, "chat": chat}


class GrabarIn(BaseModel):
    sala_id: int
    video_url: str | None = ""
    resumen: str | None = ""


@router.post("/biblioteca/guardar_sala")
def guardar_sala(payload: GrabarIn, db: Session = Depends(get_db)):
    """Al finalizar una clase en vivo, queda guardada en la biblioteca."""
    s = db.query(SalaVirtual).filter(SalaVirtual.id == payload.sala_id).first()
    if not s:
        return {"ok": False, "msg": "Sala no encontrada."}
    ya = db.query(GrabacionClase).filter(GrabacionClase.sala_id == s.id).first()
    if ya:
        return {"ok": False, "msg": "Esta clase ya está en la biblioteca."}
    sal = db.query(Salon).filter(Salon.id == s.salon_id).first()
    doc = db.query(Personal).filter(Personal.id == s.docente_id).first()
    n_msg = db.query(MensajeSala).filter(MensajeSala.sala_id == s.id).count()
    g = GrabacionClase(
        sala_id=s.id, salon_id=s.salon_id,
        institucion_id=sal.institucion_id if sal else None,
        titulo=s.titulo, docente=doc.nombre if doc else None,
        fecha=s.fecha or datetime.now(), duracion_min=45,
        video_url=(payload.video_url or "").strip() or None,
        resumen=(payload.resumen or "").strip() or
                f"Clase en vivo con {n_msg} intervenciones en el chat.",
        n_vistas=0)
    db.add(g)
    s.estado = "finalizada"
    db.commit()
    return {"ok": True, "id": g.id,
            "msg": "📼 Clase guardada en la biblioteca. Los estudiantes que no pudieron conectarse ya pueden verla."}


# ═════════ GENERADOR DE CLASES CON IA (punto 6) ═════════
BANCO_IA = {
    "matemáticas": {
        "bloques": [
            ("texto", "¿De dónde sale esto?", "Antes de las fórmulas, entiende el problema que resuelven. {tema} aparece cuando necesitamos {aplicacion}. Sin eso, los números no significan nada."),
            ("ejemplo", "En la vida real", "Piensa en la tienda de tu barrio: {ejemplo_local}. Ahí está {tema} funcionando sin que nadie lo llame así."),
            ("formula", "Lo que hay que recordar", "{formula}"),
            ("tip", "El truco", "Cuando te bloquees, vuelve al dibujo. La mayoría de problemas de {tema} se resuelven dibujando la situación antes de escribir números."),
            ("ojo", "El error de siempre", "El error más común en {tema} es apurarse a calcular sin leer bien qué piden. Lee dos veces la pregunta."),
        ],
        "quiz": [("Si el problema pide {tema}, lo primero que debes identificar es:",
                  ["El resultado", "Qué datos tengo y qué me piden", "La fórmula más larga"], 1,
                  "Primero se entiende el problema; la fórmula viene después."),
                 ("¿Para qué sirve {tema} en la vida diaria?",
                  ["Para nada práctico", "Para {aplicacion}", "Solo para el examen"], 1,
                  "Las matemáticas de la escuela son herramientas de la vida real.")],
        "aplicacion": "medir, repartir o comparar cantidades",
        "ejemplo_local": "cuando doña Rosa calcula cuánto le queda de ganancia después de pagar el proveedor",
        "formula": "Identifica los datos → Escribe la relación → Resuelve → Verifica",
    },
    "ciencias": {
        "bloques": [
            ("texto", "Qué vamos a entender", "{tema} explica algo que ves todos los días pero que quizá nunca te habías preguntado por qué pasa."),
            ("texto", "Cómo funciona", "El proceso ocurre en etapas. Cada una depende de la anterior, y si una falla, se rompe la cadena."),
            ("ejemplo", "Aquí en nuestro territorio", "{ejemplo_local}"),
            ("tip", "Para recordarlo", "Asócialo con algo que veas: la naturaleza repite los mismos patrones a distinta escala."),
            ("ojo", "Cuidado con esto", "Muchos confunden causa con consecuencia. Pregúntate siempre: ¿esto pasa POR qué, o pasa DESPUÉS de qué?"),
        ],
        "quiz": [("¿Por qué es importante entender {tema}?",
                  ["Solo para el examen", "Porque explica procesos que nos afectan directamente", "No es importante"], 1,
                  "La ciencia escolar sirve para entender y cuidar el entorno donde vives."),
                 ("Al estudiar un proceso natural, lo clave es identificar:",
                  ["El nombre científico", "Las etapas y qué las conecta", "La fecha del descubrimiento"], 1,
                  "Entender la secuencia es más útil que memorizar nombres.")],
        "ejemplo_local": "En el Sur de Bolívar lo vemos claramente en el río y en las épocas de lluvia y verano.",
    },
    "lenguaje": {
        "bloques": [
            ("texto", "Por qué importa", "{tema} no es una regla para el examen: es lo que hace que la gente te entienda cuando hablas o escribes."),
            ("ejemplo", "Nota la diferencia", "Compara estas dos formas de decir lo mismo. Una se entiende de una; la otra toca leerla dos veces."),
            ("tip", "Practica así", "Escribe primero como te salga, y después revisa. Editar es donde de verdad se aprende a escribir."),
            ("ojo", "Error frecuente", "Escribir como se habla. En la conversación se perdona todo; en el texto, no."),
        ],
        "quiz": [("El objetivo de dominar {tema} es:",
                  ["Sacar buena nota", "Que los demás te entiendan mejor", "Escribir más largo"], 1,
                  "Comunicar bien te abre puertas en cualquier trabajo."),
                 ("Al escribir un texto, lo primero es:",
                  ["Empezar por la introducción", "Saber a quién le escribes y para qué", "Buscar palabras difíciles"], 1,
                  "Sin destinatario y propósito, el texto sale sin rumbo.")],
    },
    "sociales": {
        "bloques": [
            ("texto", "El contexto", "{tema} no ocurrió por casualidad. Hubo causas que se venían acumulando y consecuencias que todavía vivimos."),
            ("ejemplo", "Qué tiene que ver con nosotros", "Lo que estudiamos hoy explica cosas de nuestro municipio: por qué la tierra se reparte así, por qué llegaron ciertas familias, por qué hay o no hay carretera."),
            ("tabla", "Causas y consecuencias",
             [["Antes", "Lo que ya venía pasando"], ["Durante", "Lo que detonó el cambio"], ["Después", "Lo que quedó y todavía se siente"]]),
            ("tip", "Para estudiar historia", "No memorices fechas sueltas: arma la línea de tiempo y pregúntate qué causó qué."),
        ],
        "quiz": [("Estudiar {tema} sirve para:",
                  ["Memorizar fechas", "Entender por qué el presente es como es", "Ganar concursos"], 1,
                  "La historia explica el presente; por eso importa."),
                 ("Al analizar un hecho histórico, lo esencial es:",
                  ["La fecha exacta", "Las causas y las consecuencias", "Los nombres de todos"], 1,
                  "Causas y consecuencias son el esqueleto del análisis histórico.")],
    },
    "general": {
        "bloques": [
            ("texto", "De qué se trata", "En esta clase vamos a entender {tema}: qué es, para qué sirve y cómo se usa."),
            ("ejemplo", "Un caso concreto", "Veamos un ejemplo del día a día donde {tema} aparece sin que lo notemos."),
            ("tip", "Consejo para aprenderlo", "Explícaselo a alguien más con tus palabras. Si logras eso, ya lo entendiste."),
            ("ojo", "Ojo con esto", "No pases al siguiente punto sin tener claro el anterior: todo se va construyendo."),
        ],
        "quiz": [("¿Cuál es la idea central de {tema}?",
                  ["Memorizar la definición", "Entender para qué sirve y cómo aplicarlo", "Copiar el ejemplo"], 1,
                  "Entender el para qué es lo que hace que se te quede.")],
    },
}


def _perfil_materia(materia):
    m = (materia or "").lower()
    if "matem" in m or "física" in m or "fisica" in m or "estadís" in m:
        return "matemáticas"
    if "cien" in m or "biolog" in m or "quím" in m or "quim" in m or "natural" in m:
        return "ciencias"
    if "lengua" in m or "españ" in m or "espan" in m or "literat" in m or "inglés" in m or "ingles" in m:
        return "lenguaje"
    if "social" in m or "histor" in m or "geogra" in m or "polít" in m or "filos" in m:
        return "sociales"
    return "general"


class GenerarClaseIn(BaseModel):
    salon_id: int
    materia: str
    tema: str
    duracion_min: int = 45
    n_temas: int | None = None
    tipo: str = "clase"
    archivos: list | None = None      # nombres de PDFs que el docente subió
    incluir_quiz: bool = True
    incluir_taller: bool = True
    periodo_numero: int | None = 3
    corte: str | None = ""


@router.post("/generar_ia")
def generar_ia(payload: GenerarClaseIn, db: Session = Depends(get_db)):
    """El docente dice salón, materia, tema y duración; el sistema arma la clase.

    Si además sube sus PDFs, la clase se construye alrededor de ese material
    (en producción el motor los lee de verdad; aquí se simula la estructura).
    """
    if not payload.tema.strip():
        return {"ok": False, "msg": "Escribe el tema de la clase."}
    perfil = BANCO_IA[_perfil_materia(payload.materia)]
    tema = payload.tema.strip()
    dur = max(15, payload.duracion_min)
    n = payload.n_temas or max(2, min(5, dur // 15))
    archivos = [str(a)[:120] for a in (payload.archivos or [])][:8]

    SUB = ["Introducción a {t}", "Conceptos clave de {t}", "{t} paso a paso",
           "{t} en la práctica", "Repaso y aplicación de {t}"]
    ctx = {"tema": tema, "aplicacion": perfil.get("aplicacion", "resolver problemas cotidianos"),
           "ejemplo_local": perfil.get("ejemplo_local", "un caso de nuestro municipio"),
           "formula": perfil.get("formula", "Identifica → Analiza → Resuelve → Verifica")}

    temas = []
    for i in range(n):
        titulo = SUB[i % len(SUB)].format(t=tema)
        bloques = []
        fuente = perfil["bloques"]
        for j, b in enumerate(fuente):
            if j % n != i % n and len(fuente) > n:
                continue
            if b[0] == "tabla":
                bloques.append({"t": "tabla", "h": b[1], "filas": b[2]})
            else:
                try:
                    p = b[2].format(**ctx)
                except (KeyError, IndexError):
                    p = b[2]
                bloques.append({"t": b[0], "h": b[1], "p": p})
        if not bloques:
            b = fuente[i % len(fuente)]
            bloques = [{"t": b[0], "h": b[1],
                        "p": (b[2].format(**ctx) if b[0] != "tabla" else "")}]
        if archivos:
            bloques.insert(0, {"t": "texto", "h": "Material base de esta clase",
                               "p": f"Esta parte se trabaja con el material que subió tu docente: "
                                    f"{', '.join(archivos[:3])}. Revísalo antes de continuar."})
        quiz = []
        if payload.incluir_quiz:
            for q, op, corr, exp in perfil["quiz"]:
                try:
                    quiz.append({"q": q.format(**ctx), "op": [o.format(**ctx) for o in op],
                                 "correcta": corr, "explica": exp})
                except (KeyError, IndexError):
                    quiz.append({"q": q, "op": op, "correcta": corr, "explica": exp})
        temas.append({"titulo": titulo,
                      "resumen": f"Lo esencial de {titulo.lower()} explicado con ejemplos.",
                      "contenido": bloques, "video_url": "",
                      "duracion_min": max(8, dur // n),
                      "materiales": [{"tipo": "pdf", "nombre": a, "url": None} for a in archivos[:2]],
                      "quiz": quiz[:2]})

    objetivos = [f"Explicar qué es {tema} y para qué sirve",
                 f"Resolver situaciones aplicando {tema}",
                 f"Relacionar {tema} con casos de nuestro contexto"]
    PORTADAS = {"matemáticas": "➗", "ciencias": "🔬", "lenguaje": "✍️",
                "sociales": "🌎", "general": "📘"}
    COLORES = {"matemáticas": "#0E7C86", "ciencias": "#0EA5E9", "lenguaje": "#7C3AED",
               "sociales": "#B45309", "general": "#0F766E"}
    p = _perfil_materia(payload.materia)
    propuesta = {
        "titulo": f"{tema}",
        "tipo": payload.tipo, "materia": payload.materia,
        "salon_id": payload.salon_id,
        "descripcion": (f"Clase de {payload.materia} sobre {tema}, organizada en {n} temas "
                        f"para {dur} minutos. Cada tema trae su explicación, ejemplos del "
                        f"contexto y su quiz."
                        + (f" Se construyó a partir del material que subiste: {', '.join(archivos)}."
                           if archivos else "")),
        "objetivos": objetivos, "portada": PORTADAS[p], "color": COLORES[p],
        "duracion_min": dur, "periodo_numero": payload.periodo_numero or 3,
        "corte": payload.corte or "",
        "materiales": [{"tipo": "pdf", "nombre": a, "url": None} for a in archivos],
        "temas": temas,
    }
    taller = None
    if payload.incluir_taller:
        taller = {
            "titulo": f"Taller: {tema}",
            "tipo": "taller", "materia": payload.materia, "salon_id": payload.salon_id,
            "descripcion": (f"Resuelve los siguientes puntos sobre {tema}:\n\n"
                            f"1. Explica con tus palabras qué es {tema}.\n"
                            f"2. Da un ejemplo de tu casa o tu barrio donde aparezca.\n"
                            f"3. Resuelve el ejercicio propuesto en clase y explica cada paso.\n"
                            f"4. ¿Para qué te puede servir esto fuera del colegio?\n\n"
                            "Puedes entregarlo escrito a mano y subir la foto, o escribirlo aquí mismo."),
            "duracion_min": 40, "portada": "📝", "color": COLORES[p],
        }
    metadatos.registrar_evento("CLASE_IA_GENERADA", "Docente",
                               payload={"tema": tema[:40], "temas": n, "archivos": len(archivos)})
    return {"ok": True, "propuesta": propuesta, "taller": taller,
            "msg": (f"🤖 Listo: preparé una clase de {dur} minutos sobre «{tema}» dividida en {n} temas"
                    + (f", basada en tus {len(archivos)} archivo(s)" if archivos else "")
                    + (" y un taller para evaluar." if taller else ".")
                    + " Revísala, ajústale lo que quieras y publícala.")}


# ═════════ EVALUACIONES CON CONTROL DE INTENTOS (punto 7) ═════════
from models import IntentoEvaluacion as _IntEv


@router.get("/evaluacion/estado")
def evaluacion_estado(actividad_id: int, estudiante_id: int, db: Session = Depends(get_db)):
    """¿El alumno puede presentar? ¿Ya la hizo? ¿Puede ver las respuestas?"""
    a = db.query(ActividadAula).filter(ActividadAula.id == actividad_id).first()
    if not a:
        return {"ok": False, "msg": "Evaluación no encontrada."}
    intentos = db.query(_IntEv).filter(_IntEv.actividad_id == actividad_id,
                                       _IntEv.estudiante_id == estudiante_id).order_by(
        _IntEv.intento).all()
    hechos = [i for i in intentos if i.entregado]
    max_int = 2 if a.permite_recuperacion else 1
    hoy = date.today()
    vencida = bool(a.fecha_limite and a.fecha_limite < hoy)
    ultimo = hechos[-1] if hechos else None
    aprobo = bool(ultimo and (ultimo.nota or 0) >= 3.0)
    puede = (len(hechos) < max_int and not vencida and a.estado == "publicada"
             and not (aprobo and len(hechos) >= 1))
    motivo = None
    if not puede:
        if a.estado != "publicada":
            motivo = "La evaluación está cerrada."
        elif vencida:
            motivo = f"La fecha límite era el {a.fecha_limite}. Habla con tu docente."
        elif aprobo:
            motivo = "Ya la presentaste y aprobaste. No se puede repetir."
        elif len(hechos) >= max_int:
            motivo = ("Ya usaste tu intento de recuperación." if max_int > 1
                      else "Esta evaluación es de un solo intento y ya la presentaste.")
    return {
        "ok": True, "titulo": a.titulo, "tipo": a.tipo,
        "tiempo_limite_min": a.tiempo_limite_min, "reglas": a.reglas,
        "fecha_limite": a.fecha_limite.isoformat() if a.fecha_limite else None,
        "permite_recuperacion": bool(a.permite_recuperacion),
        "intentos_hechos": len(hechos), "intentos_max": max_int,
        "puede_presentar": puede, "motivo": motivo,
        "aprobo": aprobo,
        "mi_nota": ultimo.nota if ultimo else None,
        "puede_ver_respuestas": bool(ultimo) and (not puede or aprobo),
        "historial": [{"intento": i.intento, "nota": i.nota, "puntaje": i.puntaje,
                       "minutos": i.minutos_usados, "recuperacion": bool(i.es_recuperacion),
                       "fecha": i.entregado.isoformat(sep=" ", timespec="minutes") if i.entregado else None}
                      for i in hechos],
    }


class IniciarEvalIn(BaseModel):
    actividad_id: int
    estudiante_id: int


@router.post("/evaluacion/iniciar")
def evaluacion_iniciar(payload: IniciarEvalIn, db: Session = Depends(get_db)):
    est = evaluacion_estado(payload.actividad_id, payload.estudiante_id, db)
    if not est.get("ok"):
        return est
    if not est["puede_presentar"]:
        return {"ok": False, "msg": f"⛔ {est['motivo']}"}
    n = est["intentos_hechos"] + 1
    i = _IntEv(actividad_id=payload.actividad_id, estudiante_id=payload.estudiante_id,
               intento=n, iniciado=datetime.now(), es_recuperacion=(n > 1))
    db.add(i)
    db.commit()
    a = db.query(ActividadAula).filter(ActividadAula.id == payload.actividad_id).first()
    temas = db.query(TemaClase).filter(TemaClase.actividad_id == payload.actividad_id).order_by(
        TemaClase.orden).all()
    preguntas = []
    for t in temas:
        for q in _jl(t.quiz, []):
            preguntas.append({"q": q.get("q"), "op": q.get("op", []), "tema": t.titulo})
    return {"ok": True, "intento_id": i.id, "intento": n,
            "es_recuperacion": n > 1,
            "tiempo_limite_min": a.tiempo_limite_min if a else 45,
            "preguntas": preguntas,
            "msg": (f"⏱️ Evaluación iniciada (intento {n}"
                    + (" · recuperación" if n > 1 else "")
                    + f"). Tienes {a.tiempo_limite_min if a else 45} minutos. "
                    "Al enviar no podrás volver a presentarla.")}


class EntregarEvalIn(BaseModel):
    intento_id: int
    respuestas: dict
    minutos_usados: int | None = 0


@router.post("/evaluacion/entregar")
def evaluacion_entregar(payload: EntregarEvalIn, db: Session = Depends(get_db)):
    i = db.query(_IntEv).filter(_IntEv.id == payload.intento_id).first()
    if not i:
        return {"ok": False, "msg": "Intento no encontrado."}
    if i.entregado:
        return {"ok": False, "msg": "Este intento ya fue entregado."}
    temas = db.query(TemaClase).filter(TemaClase.actividad_id == i.actividad_id).order_by(
        TemaClase.orden).all()
    correctas = []
    for t in temas:
        for q in _jl(t.quiz, []):
            correctas.append(q)
    aciertos = 0
    detalle = []
    for idx, q in enumerate(correctas):
        r = payload.respuestas.get(str(idx))
        bien = (r == q.get("correcta"))
        if bien:
            aciertos += 1
        detalle.append({"pregunta": q.get("q"), "opciones": q.get("op", []),
                        "tu_respuesta": r, "correcta": q.get("correcta"),
                        "acerto": bien, "explica": q.get("explica")})
    total = len(correctas) or 1
    pct = round(100 * aciertos / total)
    nota = round(pct / 20, 1)
    i.respuestas = json.dumps(payload.respuestas, ensure_ascii=False)
    i.puntaje = pct
    i.nota = nota
    i.entregado = datetime.now()
    i.minutos_usados = max(0, payload.minutos_usados or 0)
    en = db.query(EntregaAula).filter(EntregaAula.actividad_id == i.actividad_id,
                                      EntregaAula.estudiante_id == i.estudiante_id).first()
    if not en:
        en = EntregaAula(actividad_id=i.actividad_id, estudiante_id=i.estudiante_id)
        db.add(en)
    en.estado = "revisado"
    en.nota = max(en.nota or 0, nota)
    en.fecha_entrega = datetime.now()
    en.respuesta = f"Evaluación en línea · {aciertos}/{total} correctas ({pct}%)"
    db.commit()
    metadatos.registrar_evento("EVALUACION_ENTREGADA", "Alumno",
                               estudiante_id=i.estudiante_id,
                               payload={"nota": nota, "intento": i.intento})
    a = db.query(ActividadAula).filter(ActividadAula.id == i.actividad_id).first()
    puede_recu = bool(a and a.permite_recuperacion and i.intento < 2 and nota < 3.0)
    return {"ok": True, "nota": nota, "puntaje": pct,
            "aciertos": aciertos, "total": total, "detalle": detalle,
            "aprobo": nota >= 3.0, "puede_recuperar": puede_recu,
            "msg": (f"{'🎉' if nota >= 3.0 else '💪'} Obtuviste {nota} ({aciertos} de {total} correctas). "
                    + ("Ya puedes ver las respuestas correctas y por qué." if nota >= 3.0 else
                       "Revisa abajo cuáles fallaste y por qué. "
                       + ("Tienes derecho a recuperación." if puede_recu else
                          "Habla con tu docente sobre el plan de mejoramiento.")))}


@router.get("/evaluacion/respuestas")
def evaluacion_respuestas(actividad_id: int, estudiante_id: int, db: Session = Depends(get_db)):
    """Ver las respuestas correctas — solo después de presentar (punto 7)."""
    est = evaluacion_estado(actividad_id, estudiante_id, db)
    if not est.get("ok"):
        return est
    if not est["puede_ver_respuestas"]:
        return {"ok": False,
                "msg": "Las respuestas se muestran después de presentar la evaluación."}
    i = db.query(_IntEv).filter(_IntEv.actividad_id == actividad_id,
                                _IntEv.estudiante_id == estudiante_id,
                                _IntEv.entregado != None).order_by(  # noqa: E711
        _IntEv.intento.desc()).first()
    resp = _jl(i.respuestas, {}) if i else {}
    temas = db.query(TemaClase).filter(TemaClase.actividad_id == actividad_id).order_by(
        TemaClase.orden).all()
    out = []
    idx = 0
    for t in temas:
        for q in _jl(t.quiz, []):
            r = resp.get(str(idx))
            out.append({"n": idx + 1, "tema": t.titulo, "pregunta": q.get("q"),
                        "opciones": q.get("op", []), "correcta": q.get("correcta"),
                        "tu_respuesta": r, "acerto": r == q.get("correcta"),
                        "explica": q.get("explica")})
            idx += 1
    return {"ok": True, "nota": i.nota if i else None,
            "puntaje": i.puntaje if i else None, "preguntas": out,
            "nota_aprender": ("Revisa sobre todo las que fallaste: ahí está lo que "
                              "todavía no quedó claro. Eso es lo que hay que repasar.")}
