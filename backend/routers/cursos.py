"""LMS: cursos preinstalados con avance paso a paso.

Estructura: CURSO -> MODULOS -> TEMAS. El alumno recorre los temas en orden;
cada tema tiene contenido, a veces una practica interactiva y un quiz. Al
completar un tema se desbloquea el siguiente y sube el progreso del curso.
"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (Curso, ModuloCurso, TemaCurso, ProgresoTema, InscripcionCurso,
                    Estudiante, Salon)
import metadatos

router = APIRouter()

NOTA_MINIMA_QUIZ = 60   # porcentaje para dar el tema por aprobado


def _jload(txt, por_defecto):
    try:
        return json.loads(txt) if txt else por_defecto
    except Exception:
        return por_defecto


def _temas_de_curso(db, curso_id):
    """Todos los temas del curso en orden de recorrido."""
    mods = db.query(ModuloCurso).filter(ModuloCurso.curso_id == curso_id).order_by(
        ModuloCurso.orden).all()
    out = []
    for m in mods:
        for t in db.query(TemaCurso).filter(TemaCurso.modulo_id == m.id).order_by(
                TemaCurso.orden).all():
            out.append((m, t))
    return out


@router.get("/")
def catalogo(estudiante_id: int | None = None, db: Session = Depends(get_db)):
    """Catalogo de cursos con el progreso del alumno en cada uno."""
    cursos = db.query(Curso).filter(Curso.estado == "publicado").order_by(Curso.orden).all()
    prog = {}
    if estudiante_id:
        for p in db.query(ProgresoTema).filter(ProgresoTema.estudiante_id == estudiante_id,
                                               ProgresoTema.completado == True).all():  # noqa: E712
            prog.setdefault(p.curso_id, set()).add(p.tema_id)
    out = []
    for c in cursos:
        pares = _temas_de_curso(db, c.id)
        total = len(pares)
        hechos = len(prog.get(c.id, set()))
        n_mod = db.query(ModuloCurso).filter(ModuloCurso.curso_id == c.id).count()
        minutos = sum(t.duracion_min or 0 for _m, t in pares)
        # siguiente tema pendiente
        siguiente = None
        for _m, t in pares:
            if t.id not in prog.get(c.id, set()):
                siguiente = {"id": t.id, "titulo": t.titulo}
                break
        out.append({
            "id": c.id, "slug": c.slug, "titulo": c.titulo, "descripcion": c.descripcion,
            "categoria": c.categoria, "icono": c.icono, "color": c.color,
            "duracion_texto": c.duracion_texto, "grado_sugerido": c.grado_sugerido,
            "n_modulos": n_mod, "n_temas": total, "minutos": minutos,
            "completados": hechos,
            "pct": round(100 * hechos / total) if total else 0,
            "siguiente": siguiente,
            "terminado": total > 0 and hechos >= total,
        })
    return out


@router.get("/detalle")
def detalle(curso_id: int, estudiante_id: int | None = None, db: Session = Depends(get_db)):
    """Temario completo del curso, con bloqueo progresivo de los temas."""
    c = db.query(Curso).filter(Curso.id == curso_id).first()
    if not c:
        return {"ok": False, "msg": "Curso no encontrado."}
    prog = {}
    if estudiante_id:
        for p in db.query(ProgresoTema).filter(ProgresoTema.estudiante_id == estudiante_id,
                                               ProgresoTema.curso_id == curso_id).all():
            prog[p.tema_id] = p
    mods = db.query(ModuloCurso).filter(ModuloCurso.curso_id == curso_id).order_by(
        ModuloCurso.orden).all()
    # el primer tema no completado es el "actual"; los siguientes quedan bloqueados
    orden_global = [t for _m, t in _temas_de_curso(db, curso_id)]
    idx_actual = 0
    for i, t in enumerate(orden_global):
        p = prog.get(t.id)
        if not (p and p.completado):
            idx_actual = i
            break
    else:
        idx_actual = len(orden_global)

    pos = {t.id: i for i, t in enumerate(orden_global)}
    modulos = []
    for m in mods:
        temas = db.query(TemaCurso).filter(TemaCurso.modulo_id == m.id).order_by(
            TemaCurso.orden).all()
        filas = []
        for t in temas:
            p = prog.get(t.id)
            i = pos.get(t.id, 0)
            filas.append({
                "id": t.id, "titulo": t.titulo, "resumen": t.resumen,
                "duracion_min": t.duracion_min, "tipo_practica": t.tipo_practica,
                "n_quiz": len(_jload(t.quiz, [])),
                "completado": bool(p and p.completado),
                "quiz_puntaje": p.quiz_puntaje if p else None,
                "actual": i == idx_actual,
                "bloqueado": i > idx_actual,
            })
        hechos_m = sum(1 for f in filas if f["completado"])
        modulos.append({
            "id": m.id, "titulo": m.titulo, "descripcion": m.descripcion,
            "nivel": m.nivel, "icono": m.icono, "orden": m.orden,
            "temas": filas, "n_temas": len(filas), "completados": hechos_m,
            "pct": round(100 * hechos_m / len(filas)) if filas else 0,
        })
    total = len(orden_global)
    hechos = sum(1 for t in orden_global if prog.get(t.id) and prog[t.id].completado)
    return {
        "ok": True, "id": c.id, "titulo": c.titulo, "descripcion": c.descripcion,
        "icono": c.icono, "color": c.color, "categoria": c.categoria,
        "duracion_texto": c.duracion_texto,
        "modulos": modulos, "n_temas": total, "completados": hechos,
        "pct": round(100 * hechos / total) if total else 0,
        "tema_actual": orden_global[idx_actual].id if idx_actual < total else None,
        "terminado": total > 0 and hechos >= total,
    }


@router.get("/tema")
def tema(tema_id: int, estudiante_id: int | None = None, db: Session = Depends(get_db)):
    """Un tema completo, listo para estudiarlo."""
    t = db.query(TemaCurso).filter(TemaCurso.id == tema_id).first()
    if not t:
        return {"ok": False, "msg": "Tema no encontrado."}
    m = db.query(ModuloCurso).filter(ModuloCurso.id == t.modulo_id).first()
    c = db.query(Curso).filter(Curso.id == m.curso_id).first() if m else None
    p = None
    if estudiante_id:
        p = db.query(ProgresoTema).filter(ProgresoTema.estudiante_id == estudiante_id,
                                          ProgresoTema.tema_id == tema_id).first()
    # navegacion anterior / siguiente
    orden = [x for _mm, x in _temas_de_curso(db, m.curso_id)] if m else []
    ids = [x.id for x in orden]
    i = ids.index(t.id) if t.id in ids else 0
    return {
        "ok": True, "id": t.id, "titulo": t.titulo, "resumen": t.resumen,
        "contenido": _jload(t.contenido, []), "quiz": _jload(t.quiz, []),
        "recursos": _jload(t.recursos, []),
        "duracion_min": t.duracion_min, "tipo_practica": t.tipo_practica,
        "modulo": {"id": m.id, "titulo": m.titulo, "icono": m.icono, "nivel": m.nivel} if m else None,
        "curso": {"id": c.id, "titulo": c.titulo, "icono": c.icono, "color": c.color} if c else None,
        "posicion": i + 1, "total": len(orden),
        "anterior": ids[i - 1] if i > 0 else None,
        "siguiente": ids[i + 1] if i < len(ids) - 1 else None,
        "completado": bool(p and p.completado),
        "quiz_puntaje": p.quiz_puntaje if p else None,
        "quiz_intentos": p.quiz_intentos if p else 0,
        "practica_data": _jload(p.practica_data, None) if p else None,
        "nota_minima": NOTA_MINIMA_QUIZ,
    }


class CompletarIn(BaseModel):
    tema_id: int
    estudiante_id: int
    quiz_puntaje: int | None = None
    practica_data: dict | None = None
    minutos: int | None = 0


@router.post("/tema/completar")
def completar(payload: CompletarIn, db: Session = Depends(get_db)):
    t = db.query(TemaCurso).filter(TemaCurso.id == payload.tema_id).first()
    if not t:
        return {"ok": False, "msg": "Tema no encontrado."}
    m = db.query(ModuloCurso).filter(ModuloCurso.id == t.modulo_id).first()
    curso_id = m.curso_id if m else None
    p = db.query(ProgresoTema).filter(ProgresoTema.estudiante_id == payload.estudiante_id,
                                      ProgresoTema.tema_id == payload.tema_id).first()
    if not p:
        p = ProgresoTema(estudiante_id=payload.estudiante_id, tema_id=payload.tema_id,
                         curso_id=curso_id, quiz_intentos=0)
        db.add(p)
    quiz = _jload(t.quiz, [])
    aprobado = True
    if quiz and payload.quiz_puntaje is not None:
        p.quiz_intentos = (p.quiz_intentos or 0) + 1
        p.quiz_puntaje = max(p.quiz_puntaje or 0, payload.quiz_puntaje)
        aprobado = payload.quiz_puntaje >= NOTA_MINIMA_QUIZ
    if payload.practica_data is not None:
        p.practica_data = json.dumps(payload.practica_data, ensure_ascii=False)
    p.minutos = (p.minutos or 0) + max(0, payload.minutos or 0)
    p.fecha = datetime.now()
    if aprobado:
        p.completado = True
    db.commit()
    metadatos.registrar_evento("CURSO_TEMA", "Alumno", estudiante_id=payload.estudiante_id,
                               payload={"tema": t.titulo[:40], "puntaje": payload.quiz_puntaje})
    # progreso del curso tras completar
    pares = _temas_de_curso(db, curso_id)
    total = len(pares)
    hechos = db.query(ProgresoTema).filter(ProgresoTema.estudiante_id == payload.estudiante_id,
                                           ProgresoTema.curso_id == curso_id,
                                           ProgresoTema.completado == True).count()  # noqa: E712
    ids = [x.id for _mm, x in pares]
    i = ids.index(t.id) if t.id in ids else -1
    siguiente = ids[i + 1] if 0 <= i < len(ids) - 1 else None
    if not aprobado:
        return {"ok": True, "aprobado": False,
                "msg": f"Obtuviste {payload.quiz_puntaje}%. Necesitas {NOTA_MINIMA_QUIZ}% para avanzar. Repasa el tema y vuelve a intentarlo — para eso está.",
                "siguiente": None, "pct": round(100 * hechos / total) if total else 0}
    termino = hechos >= total
    if termino:
        ins = db.query(InscripcionCurso).filter(
            InscripcionCurso.estudiante_id == payload.estudiante_id,
            InscripcionCurso.curso_id == curso_id).first()
        if ins:
            ins.certificado = True
            db.commit()
    return {
        "ok": True, "aprobado": True,
        "msg": ("🎓 ¡Terminaste el curso completo! Tu certificado quedó disponible."
                if termino else "✅ ¡Tema completado! Se desbloqueó el siguiente."),
        "siguiente": siguiente, "termino_curso": termino,
        "completados": hechos, "total": total,
        "pct": round(100 * hechos / total) if total else 0,
    }


@router.get("/mi_progreso")
def mi_progreso(estudiante_id: int, db: Session = Depends(get_db)):
    """Resumen para el tablero del alumno."""
    cursos = db.query(Curso).filter(Curso.estado == "publicado").all()
    prog = db.query(ProgresoTema).filter(ProgresoTema.estudiante_id == estudiante_id,
                                         ProgresoTema.completado == True).all()  # noqa: E712
    por_curso = {}
    for p in prog:
        por_curso[p.curso_id] = por_curso.get(p.curso_id, 0) + 1
    total_t = total_h = 0
    detalle_c = []
    for c in cursos:
        n = len(_temas_de_curso(db, c.id))
        h = por_curso.get(c.id, 0)
        total_t += n
        total_h += h
        detalle_c.append({"id": c.id, "titulo": c.titulo, "icono": c.icono,
                          "color": c.color, "completados": h, "total": n,
                          "pct": round(100 * h / n) if n else 0})
    minutos = sum(p.minutos or 0 for p in prog)
    puntajes = [p.quiz_puntaje for p in prog if p.quiz_puntaje is not None]
    return {
        "cursos": detalle_c,
        "total_temas": total_t, "completados": total_h,
        "pct": round(100 * total_h / total_t) if total_t else 0,
        "minutos_estudiados": minutos,
        "promedio_quiz": round(sum(puntajes) / len(puntajes)) if puntajes else None,
        "certificados": db.query(InscripcionCurso).filter(
            InscripcionCurso.estudiante_id == estudiante_id,
            InscripcionCurso.certificado == True).count(),  # noqa: E712
    }


@router.get("/avance_salon")
def avance_salon(salon_id: int, db: Session = Depends(get_db)):
    """Para el docente: como va su salon en los cursos del sistema."""
    ests = db.query(Estudiante).filter(Estudiante.salon_id == salon_id).all()
    cursos = db.query(Curso).filter(Curso.estado == "publicado").all()
    totales = {c.id: len(_temas_de_curso(db, c.id)) for c in cursos}
    filas = []
    for e in ests:
        prog = db.query(ProgresoTema).filter(ProgresoTema.estudiante_id == e.id,
                                             ProgresoTema.completado == True).all()  # noqa: E712
        por_c = {}
        for p in prog:
            por_c[p.curso_id] = por_c.get(p.curso_id, 0) + 1
        tot = sum(totales.values())
        hechos = sum(por_c.values())
        puntajes = [p.quiz_puntaje for p in prog if p.quiz_puntaje is not None]
        filas.append({
            "estudiante_id": e.id, "nombre": e.nombre,
            "completados": hechos, "total": tot,
            "pct": round(100 * hechos / tot) if tot else 0,
            "promedio_quiz": round(sum(puntajes) / len(puntajes)) if puntajes else None,
            "por_curso": [{"curso": c.titulo, "icono": c.icono,
                           "hechos": por_c.get(c.id, 0), "total": totales[c.id]} for c in cursos],
        })
    filas.sort(key=lambda x: -x["pct"])
    sal = db.query(Salon).filter(Salon.id == salon_id).first()
    return {"salon": sal.nombre if sal else "—", "estudiantes": filas,
            "promedio_salon": round(sum(f["pct"] for f in filas) / len(filas)) if filas else 0}
