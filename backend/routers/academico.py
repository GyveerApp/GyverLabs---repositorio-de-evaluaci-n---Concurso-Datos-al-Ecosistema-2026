"""Estructura académica PRO: instituciones, salones (CRUD + horarios + temas
por corte), períodos con cierre, cortes editables, personal (CRUD + hojas de
vida con score) y notas editables por materia (bloqueadas si el período está
cerrado)."""
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (Institucion, Salon, Estudiante, Personal, Periodo, NotaPeriodo,
                    Corte, TemaPlan, SRDScore, AsistenciaPersonal, Asistencia,
                    ActividadAula, EntregaAula, EventoCalendario, Autorizacion)
import metadatos

router = APIRouter()


@router.get("/instituciones")
def instituciones(db: Session = Depends(get_db)):
    out = []
    for ie in db.query(Institucion).all():
        n_est = db.query(Estudiante).filter(Estudiante.institucion_id == ie.id).count()
        n_sal = db.query(Salon).filter(Salon.institucion_id == ie.id).count()
        out.append({
            "id": ie.id, "nombre": ie.nombre, "codigo_dane": ie.codigo_dane,
            "municipio": ie.municipio, "departamento": ie.departamento,
            "sector": ie.sector, "rector": ie.rector, "direccion": ie.direccion,
            "telefono": ie.telefono, "n_estudiantes": n_est, "n_salones": n_sal,
        })
    return out


# ═════════ SALONES ═════════
@router.get("/salones")
def salones(institucion_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Salon)
    if institucion_id:
        q = q.filter(Salon.institucion_id == institucion_id)
    dirs = {p.id: p.nombre for p in db.query(Personal).all()}
    out = []
    for sal in q.all():
        n = db.query(Estudiante).filter(Estudiante.salon_id == sal.id).count()
        en_riesgo = 0
        ids = [e.id for e in db.query(Estudiante).filter(Estudiante.salon_id == sal.id).all()]
        if ids:
            en_riesgo = db.query(SRDScore).filter(
                SRDScore.estudiante_id.in_(ids),
                SRDScore.nivel.in_(["CRÍTICO", "MODERADO"])).count()
        out.append({
            "id": sal.id, "nombre": sal.nombre, "grado": sal.grado, "jornada": sal.jornada,
            "institucion_id": sal.institucion_id, "director": dirs.get(sal.director_id, "—"),
            "director_id": sal.director_id,
            "n_estudiantes": n, "en_riesgo": en_riesgo,
        })
    out.sort(key=lambda x: x["nombre"])
    return out


class SalonIn(BaseModel):
    id: int | None = 0
    institucion_id: int
    nombre: str
    grado: str
    jornada: str | None = "Mañana"
    director_id: int | None = None


@router.post("/salones/guardar")
def salon_guardar(payload: SalonIn, db: Session = Depends(get_db)):
    if not payload.nombre.strip():
        return {"ok": False, "msg": "El nombre del salón es obligatorio."}
    if payload.id:
        sal = db.query(Salon).filter(Salon.id == payload.id).first()
        if not sal:
            return {"ok": False, "msg": "Salón no encontrado."}
    else:
        sal = Salon(institucion_id=payload.institucion_id, horarios=json.dumps([]))
        db.add(sal)
    sal.nombre = payload.nombre.strip()
    sal.grado = payload.grado or sal.nombre[:1]
    sal.jornada = payload.jornada or "Mañana"
    sal.director_id = payload.director_id
    db.commit()
    metadatos.registrar_evento("SALON_GUARDADO", "Directivo", institucion_id=payload.institucion_id,
                               payload={"salon": sal.nombre})
    return {"ok": True, "msg": f"Salón {sal.nombre} guardado.", "id": sal.id}


class IdIn(BaseModel):
    id: int


@router.post("/salones/eliminar")
def salon_eliminar(payload: IdIn, db: Session = Depends(get_db)):
    sal = db.query(Salon).filter(Salon.id == payload.id).first()
    if not sal:
        return {"ok": False, "msg": "Salón no encontrado."}
    n = db.query(Estudiante).filter(Estudiante.salon_id == sal.id).count()
    if n > 0:
        return {"ok": False, "msg": f"No se puede eliminar: el salón tiene {n} estudiantes matriculados. Reasígnalos primero."}
    db.query(TemaPlan).filter(TemaPlan.salon_id == sal.id).delete()
    db.delete(sal)
    db.commit()
    return {"ok": True, "msg": "Salón eliminado."}


@router.get("/salones/detalle")
def salon_detalle(salon_id: int, db: Session = Depends(get_db)):
    sal = db.query(Salon).filter(Salon.id == salon_id).first()
    if not sal:
        return {"ok": False, "msg": "Salón no encontrado."}
    director = db.query(Personal).filter(Personal.id == sal.director_id).first()
    n = db.query(Estudiante).filter(Estudiante.salon_id == sal.id).count()
    try:
        horarios = json.loads(sal.horarios) if sal.horarios else []
    except Exception:
        horarios = []
    temas = db.query(TemaPlan).filter(TemaPlan.salon_id == sal.id).order_by(
        TemaPlan.periodo_numero, TemaPlan.corte).all()
    cortes = db.query(Corte).filter(Corte.institucion_id == sal.institucion_id).order_by(
        Corte.periodo_numero, Corte.nombre).all()
    ests = db.query(Estudiante).filter(Estudiante.salon_id == sal.id).order_by(Estudiante.nombre).all()
    return {
        "id": sal.id, "nombre": sal.nombre, "grado": sal.grado, "jornada": sal.jornada,
        "director": director.nombre if director else "—", "director_id": sal.director_id,
        "n_estudiantes": n,
        "estudiantes": [{"id": e.id, "nombre": e.nombre, "nivel_sisben": e.nivel_sisben,
                         "acudiente": e.acudiente, "telefono": e.telefono} for e in ests],
        "horarios": horarios,
        "temas": [{"id": t.id, "periodo": t.periodo_numero, "corte": t.corte,
                   "materia": t.materia, "tema": t.tema, "detalle": t.detalle} for t in temas],
        "cortes": [{"id": c.id, "periodo": c.periodo_numero, "nombre": c.nombre,
                    "inicio": c.fecha_inicio.isoformat() if c.fecha_inicio else None,
                    "fin": c.fecha_fin.isoformat() if c.fecha_fin else None} for c in cortes],
    }


class HorariosIn(BaseModel):
    salon_id: int
    horarios: list


@router.post("/salones/horarios/guardar")
def horarios_guardar(payload: HorariosIn, db: Session = Depends(get_db)):
    sal = db.query(Salon).filter(Salon.id == payload.salon_id).first()
    if not sal:
        return {"ok": False, "msg": "Salón no encontrado."}
    limpio = []
    for h in payload.horarios[:40]:
        if isinstance(h, dict) and h.get("dia") and h.get("hora"):
            limpio.append({"dia": str(h["dia"])[:12], "hora": str(h["hora"])[:15],
                           "materia": str(h.get("materia", ""))[:30]})
    sal.horarios = json.dumps(limpio, ensure_ascii=False)
    db.commit()
    return {"ok": True, "msg": f"Horario guardado ({len(limpio)} franjas)."}


# ═════════ TEMAS POR CORTE ═════════
class TemaIn(BaseModel):
    id: int | None = 0
    salon_id: int
    periodo_numero: int
    corte: str | None = "Corte 1"
    materia: str | None = ""
    tema: str
    detalle: str | None = ""


@router.post("/temas/guardar")
def tema_guardar(payload: TemaIn, db: Session = Depends(get_db)):
    if not payload.tema.strip():
        return {"ok": False, "msg": "El tema es obligatorio."}
    if payload.id:
        t = db.query(TemaPlan).filter(TemaPlan.id == payload.id).first()
        if not t:
            return {"ok": False, "msg": "Tema no encontrado."}
    else:
        t = TemaPlan(salon_id=payload.salon_id)
        db.add(t)
    t.periodo_numero = payload.periodo_numero
    t.corte = payload.corte or "Corte 1"
    t.materia = payload.materia or ""
    t.tema = payload.tema.strip()
    t.detalle = payload.detalle or ""
    db.commit()
    return {"ok": True, "msg": "Tema guardado."}


@router.post("/temas/eliminar")
def tema_eliminar(payload: IdIn, db: Session = Depends(get_db)):
    db.query(TemaPlan).filter(TemaPlan.id == payload.id).delete()
    db.commit()
    return {"ok": True, "msg": "Tema eliminado."}


# ═════════ PERÍODOS Y CORTES ═════════
@router.get("/periodos")
def periodos(institucion_id: int | None = None, db: Session = Depends(get_db)):
    pers = db.query(Periodo).order_by(Periodo.numero).all()
    cortes = db.query(Corte)
    if institucion_id:
        cortes = cortes.filter(Corte.institucion_id == institucion_id)
    cortes = cortes.all()
    por_p = defaultdict(list)
    for c in cortes:
        por_p[c.periodo_numero].append({
            "id": c.id, "nombre": c.nombre,
            "inicio": c.fecha_inicio.isoformat() if c.fecha_inicio else None,
            "fin": c.fecha_fin.isoformat() if c.fecha_fin else None})
    return [{
        "numero": p.numero, "nombre": p.nombre, "peso": p.peso,
        "activo": bool(p.activo), "cerrado": bool(p.cerrado),
        "inicio": p.fecha_inicio.isoformat() if p.fecha_inicio else None,
        "fin": p.fecha_fin.isoformat() if p.fecha_fin else None,
        "cortes": por_p.get(p.numero, []),
    } for p in pers]


class PeriodoCerrarIn(BaseModel):
    numero: int
    cerrado: bool


@router.post("/periodos/cerrar")
def periodo_cerrar(payload: PeriodoCerrarIn, db: Session = Depends(get_db)):
    p = db.query(Periodo).filter(Periodo.numero == payload.numero).first()
    if not p:
        return {"ok": False, "msg": "Período no encontrado."}
    p.cerrado = payload.cerrado
    db.commit()
    metadatos.registrar_evento("PERIODO_" + ("CERRADO" if payload.cerrado else "ABIERTO"),
                               "Rectoría", payload={"periodo": p.numero})
    return {"ok": True, "msg": f"{p.nombre} {'cerrado 🔒' if payload.cerrado else 'abierto 🔓'}."}


class CorteIn(BaseModel):
    id: int
    inicio: str | None = None
    fin: str | None = None
    nombre: str | None = None


@router.post("/cortes/guardar")
def corte_guardar(payload: CorteIn, db: Session = Depends(get_db)):
    c = db.query(Corte).filter(Corte.id == payload.id).first()
    if not c:
        return {"ok": False, "msg": "Corte no encontrado."}
    if payload.nombre:
        c.nombre = payload.nombre
    try:
        if payload.inicio:
            c.fecha_inicio = date.fromisoformat(payload.inicio)
        if payload.fin:
            c.fecha_fin = date.fromisoformat(payload.fin)
    except ValueError:
        return {"ok": False, "msg": "Fecha inválida."}
    db.commit()
    return {"ok": True, "msg": f"{c.nombre} actualizado."}


# ═════════ ESTUDIANTES Y PERSONAL ═════════
@router.get("/estudiantes")
def estudiantes(salon_id: int | None = None, institucion_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Estudiante)
    if salon_id:
        q = q.filter(Estudiante.salon_id == salon_id)
    if institucion_id:
        q = q.filter(Estudiante.institucion_id == institucion_id)
    return [{
        "id": e.id, "nombre": e.nombre, "grado": e.grado, "zona": e.zona,
        "nivel_sisben": e.nivel_sisben, "acudiente": e.acudiente, "telefono": e.telefono,
        "parentesco": e.parentesco, "barrio_vereda": e.barrio_vereda,
    } for e in q.all()]


@router.get("/personal")
def personal(institucion_id: int | None = None, rol: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Personal).filter(Personal.activo == True)  # noqa: E712
    if institucion_id:
        q = q.filter(Personal.institucion_id == institucion_id)
    if rol:
        q = q.filter(Personal.rol == rol)
    salones_por_dir = defaultdict(int)
    for sal in db.query(Salon).all():
        if sal.director_id:
            salones_por_dir[sal.director_id] += 1
    # % asistencia docente (4 semanas)
    asis = defaultdict(lambda: [0, 0])
    for a in db.query(AsistenciaPersonal).all():
        asis[a.personal_id][1] += 1
        if a.estado in ("present", "late"):
            asis[a.personal_id][0] += 1
    aut = {a.personal_id: a.paneles for a in db.query(Autorizacion).all()}
    out = []
    for p in q.all():
        pres, tot = asis.get(p.id, [0, 0])
        out.append({
            "id": p.id, "nombre": p.nombre, "rol": p.rol, "area": p.area,
            "email": p.email, "telefono": p.telefono, "documento": p.documento,
            "profesion": p.profesion, "experiencia_anios": p.experiencia_anios,
            "hv_score": p.hv_score, "foto": p.foto,
            "n_salones": salones_por_dir.get(p.id, 0),
            "asistencia_pct": round(100 * pres / tot, 1) if tot else None,
            "paneles": aut.get(p.id, ""),
        })
    return out


class PersonalIn(BaseModel):
    id: int | None = 0
    institucion_id: int
    nombre: str
    rol: str
    area: str | None = ""
    email: str | None = ""
    telefono: str | None = ""
    documento: str | None = ""
    profesion: str | None = ""
    experiencia_anios: int | None = 0


@router.post("/personal/guardar")
def personal_guardar(payload: PersonalIn, db: Session = Depends(get_db)):
    if not payload.nombre.strip():
        return {"ok": False, "msg": "El nombre es obligatorio."}
    roles = {"docente", "coordinador", "rector", "auxiliar", "contador", "abogado",
             "psicoorientacion", "vigilante", "servicios"}
    rol = payload.rol if payload.rol in roles else "docente"
    if payload.id:
        p = db.query(Personal).filter(Personal.id == payload.id).first()
        if not p:
            return {"ok": False, "msg": "Persona no encontrada."}
    else:
        p = Personal(institucion_id=payload.institucion_id, hoja_vida=json.dumps(
            {"estudios": [], "experiencia": [], "certificaciones": [], "archivo": None}))
        db.add(p)
    p.nombre = payload.nombre.strip()
    p.rol = rol
    p.area = payload.area or ""
    p.email = payload.email or ""
    p.telefono = payload.telefono or ""
    p.documento = payload.documento or ""
    p.profesion = payload.profesion or ""
    p.experiencia_anios = payload.experiencia_anios or 0
    _recalcular_hv(p)
    db.commit()
    metadatos.registrar_evento("PERSONAL_GUARDADO", "Directivo", institucion_id=payload.institucion_id,
                               payload={"rol": rol})
    return {"ok": True, "msg": f"{p.nombre} guardado(a) como {rol}.", "id": p.id}


@router.post("/personal/eliminar")
def personal_eliminar(payload: IdIn, db: Session = Depends(get_db)):
    p = db.query(Personal).filter(Personal.id == payload.id).first()
    if not p:
        return {"ok": False, "msg": "Persona no encontrada."}
    if p.rol == "rector":
        return {"ok": False, "msg": "No se puede eliminar a la rectoría desde aquí."}
    p.activo = False
    for sal in db.query(Salon).filter(Salon.director_id == p.id).all():
        sal.director_id = None
    db.commit()
    return {"ok": True, "msg": f"{p.nombre} retirado(a) del plantel (histórico conservado)."}


def _recalcular_hv(p: Personal):
    try:
        hv = json.loads(p.hoja_vida) if p.hoja_vida else {}
    except Exception:
        hv = {}
    estudios = hv.get("estudios", []) or ([p.profesion] if p.profesion else [])
    certs = hv.get("certificaciones", [])
    p.hv_score = min(100, 35 + 8 * len(estudios) + min(30, 2 * (p.experiencia_anios or 0)) + 5 * len(certs))


@router.get("/personal/hoja_vida")
def hoja_vida(personal_id: int, db: Session = Depends(get_db)):
    p = db.query(Personal).filter(Personal.id == personal_id).first()
    if not p:
        return {"ok": False, "msg": "Persona no encontrada."}
    try:
        hv = json.loads(p.hoja_vida) if p.hoja_vida else {}
    except Exception:
        hv = {}
    return {
        "id": p.id, "nombre": p.nombre, "rol": p.rol, "area": p.area,
        "profesion": p.profesion, "experiencia_anios": p.experiencia_anios,
        "documento": p.documento, "telefono": p.telefono, "email": p.email,
        "fecha_vinculacion": p.fecha_vinculacion.isoformat() if p.fecha_vinculacion else None,
        "hv_score": p.hv_score, "foto": p.foto,
        "estudios": hv.get("estudios", []), "experiencia": hv.get("experiencia", []),
        "certificaciones": hv.get("certificaciones", []), "archivo": hv.get("archivo"),
    }


class HVIn(BaseModel):
    personal_id: int
    estudios: list[str] = []
    experiencia: list[str] = []
    certificaciones: list[str] = []
    archivo: str | None = None


@router.post("/personal/hoja_vida/guardar")
def hoja_vida_guardar(payload: HVIn, db: Session = Depends(get_db)):
    p = db.query(Personal).filter(Personal.id == payload.personal_id).first()
    if not p:
        return {"ok": False, "msg": "Persona no encontrada."}
    hv = {"estudios": [s.strip() for s in payload.estudios if s.strip()][:10],
          "experiencia": [s.strip() for s in payload.experiencia if s.strip()][:12],
          "certificaciones": [s.strip() for s in payload.certificaciones if s.strip()][:10],
          "archivo": payload.archivo}
    p.hoja_vida = json.dumps(hv, ensure_ascii=False)
    _recalcular_hv(p)
    db.commit()
    metadatos.registrar_evento("HOJA_VIDA_ACTUALIZADA", "Personal", institucion_id=p.institucion_id,
                               payload={"hv_score": p.hv_score})
    return {"ok": True, "msg": f"Hoja de vida guardada. Score recalculado: {p.hv_score}/100.",
            "hv_score": p.hv_score}


# ═════════ NOTAS (editable por materia, con candado de período) ═════════
@router.get("/notas")
def notas_matriz(salon_id: int, materia: str | None = None, db: Session = Depends(get_db)):
    """Matriz de notas. Con `materia`: la nota puntual editable por período.
    Sin materia: promedio de todas las materias por período (solo lectura)."""
    periodos = db.query(Periodo).order_by(Periodo.numero).all()
    estudiantes = db.query(Estudiante).filter(Estudiante.salon_id == salon_id).all()
    est_ids = [e.id for e in estudiantes]
    qn = db.query(NotaPeriodo).filter(NotaPeriodo.estudiante_id.in_(est_ids)) if est_ids else None
    if qn is not None and materia:
        qn = qn.filter(NotaPeriodo.materia == materia)
    notas = qn.all() if qn is not None else []
    pnum = {p.id: p.numero for p in periodos}
    idx = defaultdict(lambda: defaultdict(list))
    for n in notas:
        num = pnum.get(n.periodo_id)
        if num:
            idx[n.estudiante_id][num].append(n.nota)

    filas = []
    for e in estudiantes:
        suma_pond = 0.0
        peso_acum = 0.0
        por_p = {}
        for p in periodos:
            vals = idx[e.id].get(p.numero, [])
            prom = round(sum(vals) / len(vals), 1) if vals else None
            por_p[p.numero] = prom
            if prom is not None:
                suma_pond += prom * p.peso
                peso_acum += p.peso
        definitiva = round(suma_pond / peso_acum, 1) if peso_acum else None
        filas.append({
            "estudiante_id": e.id, "nombre": e.nombre,
            "periodos": por_p, "definitiva": definitiva,
            "estado": ("Sin notas" if definitiva is None else ("Aprobando" if definitiva >= 3.0 else "En riesgo")),
        })
    return {
        "periodos": [{"numero": p.numero, "nombre": p.nombre, "peso": p.peso,
                      "cerrado": bool(p.cerrado), "activo": bool(p.activo)} for p in periodos],
        "materias": ["Matemáticas", "Lenguaje", "Ciencias", "Sociales", "Inglés"],
        "materia": materia or "",
        "filas": filas,
    }


class NotaIn(BaseModel):
    estudiante_id: int
    periodo_numero: int
    materia: str
    nota: float


@router.post("/notas/guardar")
def guardar_nota(payload: NotaIn, db: Session = Depends(get_db)):
    if payload.nota < 0 or payload.nota > 5:
        return {"ok": False, "msg": "La nota debe estar entre 0.0 y 5.0."}
    per = db.query(Periodo).filter(Periodo.numero == payload.periodo_numero).first()
    if not per:
        return {"ok": False, "msg": "Período no encontrado."}
    if per.cerrado:
        return {"ok": False, "msg": f"🔒 {per.nombre} está CERRADO: sus notas ya no se pueden modificar. Solicita apertura a rectoría."}
    fila = db.query(NotaPeriodo).filter(
        NotaPeriodo.estudiante_id == payload.estudiante_id,
        NotaPeriodo.periodo_id == per.id,
        NotaPeriodo.materia == payload.materia).first()
    if fila:
        fila.nota = payload.nota
    else:
        db.add(NotaPeriodo(estudiante_id=payload.estudiante_id, periodo_id=per.id,
                           materia=payload.materia, nota=payload.nota))
    db.commit()
    metadatos.registrar_evento("NOTA", "Docente", estudiante_id=payload.estudiante_id,
                               payload={"periodo": payload.periodo_numero, "materia": payload.materia,
                                        "nota": payload.nota})
    return {"ok": True, "msg": f"Nota {payload.nota:.1f} guardada en {payload.materia} (P{payload.periodo_numero})."}


# ═════════ EQUIPOS DE TRABAJO (autorizaciones del rector) ═════════
class AutIn(BaseModel):
    institucion_id: int
    personal_id: int
    paneles: list[str] = []


@router.post("/autorizaciones/guardar")
def autorizacion_guardar(payload: AutIn, db: Session = Depends(get_db)):
    p = db.query(Personal).filter(Personal.id == payload.personal_id).first()
    if not p:
        return {"ok": False, "msg": "Persona no encontrada."}
    validos = [x for x in payload.paneles if x in ("fse", "contratos", "datos")]
    a = db.query(Autorizacion).filter(Autorizacion.institucion_id == payload.institucion_id,
                                      Autorizacion.personal_id == payload.personal_id).first()
    if not validos:
        if a:
            db.delete(a)
        db.commit()
        return {"ok": True, "msg": f"{p.nombre}: sin paneles autorizados."}
    if a:
        a.paneles = ",".join(validos)
    else:
        db.add(Autorizacion(institucion_id=payload.institucion_id,
                            personal_id=payload.personal_id, paneles=",".join(validos)))
    db.commit()
    metadatos.registrar_evento("AUTORIZACION", "Rectoría", institucion_id=payload.institucion_id,
                               payload={"paneles": validos})
    return {"ok": True, "msg": f"{p.nombre} autorizado(a) para: {', '.join(validos)}."}


# ═════════ GESTIÓN DE ESTUDIANTES POR SALÓN (punto 5) ═════════
class EstudianteIn(BaseModel):
    id: int | None = 0
    institucion_id: int
    salon_id: int | None = None
    nombre: str
    grado: str | None = ""
    nivel_sisben: str | None = "B1"
    zona: str | None = "urbana"
    acudiente: str | None = ""
    parentesco: str | None = ""
    telefono: str | None = ""
    direccion: str | None = ""
    barrio_vereda: str | None = ""


@router.post("/estudiantes/guardar")
def estudiante_guardar(payload: EstudianteIn, db: Session = Depends(get_db)):
    if not payload.nombre.strip():
        return {"ok": False, "msg": "El nombre del estudiante es obligatorio."}
    if payload.id:
        e = db.query(Estudiante).filter(Estudiante.id == payload.id).first()
        if not e:
            return {"ok": False, "msg": "Estudiante no encontrado."}
    else:
        from datetime import date as _d
        e = Estudiante(institucion_id=payload.institucion_id, fecha_ingreso=_d.today())
        db.add(e)
    e.nombre = payload.nombre.strip()
    e.grado = payload.grado or (db.query(Salon).filter(Salon.id == payload.salon_id).first().grado if payload.salon_id else "6")
    e.nivel_sisben = payload.nivel_sisben or "B1"
    e.zona = payload.zona or "urbana"
    e.acudiente = payload.acudiente or ""
    e.parentesco = payload.parentesco or ""
    e.telefono = payload.telefono or ""
    e.direccion = payload.direccion or ""
    e.barrio_vereda = payload.barrio_vereda or ""
    nuevo_salon = payload.salon_id != e.salon_id
    e.salon_id = payload.salon_id
    db.flush()
    if payload.salon_id and (nuevo_salon or not payload.id):
        _sincronizar_entregas(db, e.id, payload.salon_id)
    db.commit()
    metadatos.registrar_evento("ESTUDIANTE_GUARDADO", "Directivo", institucion_id=payload.institucion_id,
                               estudiante_id=e.id)
    return {"ok": True, "msg": f"{e.nombre} guardado(a)." + (" Se crearon sus entregas pendientes del aula virtual." if payload.salon_id else ""), "id": e.id}


def _sincronizar_entregas(db, estudiante_id, salon_id):
    """Al entrar un estudiante a un salón, se le crean las entregas de las
    actividades activas de ese salón (así se 'asocia a las clases sin problemas')."""
    acts = db.query(ActividadAula).filter(ActividadAula.salon_id == salon_id,
                                          ActividadAula.estado == "publicada").all()
    for a in acts:
        ya = db.query(EntregaAula).filter(EntregaAula.actividad_id == a.id,
                                          EntregaAula.estudiante_id == estudiante_id).first()
        if not ya:
            db.add(EntregaAula(actividad_id=a.id, estudiante_id=estudiante_id, estado="pendiente"))


class MoverIn(BaseModel):
    estudiante_id: int
    salon_id: int | None = None   # None = quitar del salón (queda sin asignar)


@router.post("/estudiantes/mover")
def estudiante_mover(payload: MoverIn, db: Session = Depends(get_db)):
    e = db.query(Estudiante).filter(Estudiante.id == payload.estudiante_id).first()
    if not e:
        return {"ok": False, "msg": "Estudiante no encontrado."}
    if payload.salon_id:
        sal = db.query(Salon).filter(Salon.id == payload.salon_id).first()
        if not sal:
            return {"ok": False, "msg": "Salón destino no encontrado."}
        e.salon_id = sal.id
        e.grado = sal.grado
        _sincronizar_entregas(db, e.id, sal.id)
        msg = f"{e.nombre.split()[0]} movido(a) al salón {sal.nombre}. Sus clases del aula virtual quedaron sincronizadas."
    else:
        e.salon_id = None
        msg = f"{e.nombre.split()[0]} retirado(a) del salón (matrícula y notas se conservan; queda sin salón asignado)."
    db.commit()
    metadatos.registrar_evento("ESTUDIANTE_MOVIDO", "Directivo", estudiante_id=e.id,
                               payload={"salon_id": payload.salon_id})
    return {"ok": True, "msg": msg}


@router.get("/estudiantes/sin_salon")
def estudiantes_sin_salon(institucion_id: int, db: Session = Depends(get_db)):
    filas = db.query(Estudiante).filter(Estudiante.institucion_id == institucion_id,
                                        Estudiante.salon_id == None).all()  # noqa: E711
    return [{"id": e.id, "nombre": e.nombre, "grado": e.grado} for e in filas]


# ═════════ CORTES: crear / eliminar con protección (punto 6) ═════════
class CorteNuevoIn(BaseModel):
    institucion_id: int
    periodo_numero: int
    nombre: str
    inicio: str | None = None
    fin: str | None = None


@router.post("/cortes/crear")
def corte_crear(payload: CorteNuevoIn, db: Session = Depends(get_db)):
    if not payload.nombre.strip():
        return {"ok": False, "msg": "El nombre del corte es obligatorio (ej: Corte 3)."}
    per = db.query(Periodo).filter(Periodo.numero == payload.periodo_numero).first()
    if not per:
        return {"ok": False, "msg": "Período no encontrado."}
    if per.cerrado:
        return {"ok": False, "msg": f"🔒 {per.nombre} está cerrado: no se pueden agregar cortes."}
    c = Corte(institucion_id=payload.institucion_id, periodo_numero=payload.periodo_numero,
              nombre=payload.nombre.strip()[:30])
    try:
        if payload.inicio:
            c.fecha_inicio = date.fromisoformat(payload.inicio)
        if payload.fin:
            c.fecha_fin = date.fromisoformat(payload.fin)
    except ValueError:
        return {"ok": False, "msg": "Fecha inválida."}
    db.add(c)
    db.commit()
    metadatos.registrar_evento("CORTE_CREADO", "Directivo", institucion_id=payload.institucion_id,
                               payload={"periodo": payload.periodo_numero, "corte": c.nombre})
    return {"ok": True, "msg": f"{c.nombre} creado en P{payload.periodo_numero}.", "id": c.id}


class CorteEliminarIn(BaseModel):
    id: int
    confirmacion: str


@router.post("/cortes/eliminar")
def corte_eliminar(payload: CorteEliminarIn, db: Session = Depends(get_db)):
    if (payload.confirmacion or "").strip().upper() != "ELIMINAR":
        return {"ok": False, "msg": "Por seguridad escribe la palabra ELIMINAR para confirmar. Se perderá la organización de temas ligada a este corte."}
    c = db.query(Corte).filter(Corte.id == payload.id).first()
    if not c:
        return {"ok": False, "msg": "Corte no encontrado."}
    per = db.query(Periodo).filter(Periodo.numero == c.periodo_numero).first()
    if per and per.cerrado:
        return {"ok": False, "msg": f"🔒 {per.nombre} está cerrado: sus cortes no se pueden eliminar."}
    # los temas del corte quedan sin corte (no se pierden las notas)
    n_temas = 0
    for t in db.query(TemaPlan).filter(TemaPlan.corte == c.nombre).all():
        t.corte = None
        n_temas += 1
    nombre = c.nombre
    db.delete(c)
    db.commit()
    metadatos.registrar_evento("CORTE_ELIMINADO", "Directivo", institucion_id=c.institucion_id,
                               payload={"corte": nombre})
    return {"ok": True, "msg": f"{nombre} eliminado. {n_temas} tema(s) quedaron sin corte asignado (puedes reasignarlos)."}


# ═════════ SOLICITUDES DE ASIGNACIÓN A SALÓN (punto 14) ═════════
# El docente busca su salón y pide la asignación; rector/coordinador aprueba o
# rechaza. Así los docentes NO crean salones: solo los pide.
from models import SolicitudSalon as _SolSal
from datetime import datetime as _dtsol


@router.get("/salones/buscar")
def salones_buscar(institucion_id: int, q: str | None = None, db: Session = Depends(get_db)):
    """Buscador simple de salones para que el docente encuentre el suyo."""
    qq = db.query(Salon).filter(Salon.institucion_id == institucion_id)
    filas = qq.order_by(Salon.grado, Salon.nombre).all()
    if q:
        ql = q.strip().lower()
        filas = [s for s in filas if ql in s.nombre.lower() or ql in str(s.grado).lower()]
    out = []
    for s in filas:
        dire = db.query(Personal).filter(Personal.id == s.director_id).first()
        out.append({"id": s.id, "nombre": s.nombre, "grado": s.grado, "jornada": s.jornada,
                    "director": dire.nombre if dire else None, "director_id": s.director_id,
                    "n_estudiantes": db.query(Estudiante).filter(Estudiante.salon_id == s.id).count(),
                    "libre": s.director_id is None})
    return out


class SolicitudIn(BaseModel):
    institucion_id: int
    personal_id: int
    salon_id: int
    rol_solicitado: str | None = "docente"   # docente | director
    materia: str | None = ""


@router.post("/solicitudes/crear")
def solicitud_crear(payload: SolicitudIn, db: Session = Depends(get_db)):
    ya = db.query(_SolSal).filter(_SolSal.personal_id == payload.personal_id,
                                  _SolSal.salon_id == payload.salon_id,
                                  _SolSal.estado == "pendiente").first()
    if ya:
        return {"ok": False, "msg": "Ya tienes una solicitud pendiente para ese salón."}
    sal = db.query(Salon).filter(Salon.id == payload.salon_id).first()
    if not sal:
        return {"ok": False, "msg": "Salón no encontrado."}
    if payload.rol_solicitado == "director" and sal.director_id:
        dire = db.query(Personal).filter(Personal.id == sal.director_id).first()
        return {"ok": False, "msg": f"Ese salón ya tiene director de grupo ({dire.nombre if dire else '—'}). Puedes solicitar asignación como docente de materia."}
    s = _SolSal(institucion_id=payload.institucion_id, personal_id=payload.personal_id,
                salon_id=payload.salon_id, rol_solicitado=payload.rol_solicitado or "docente",
                materia=(payload.materia or "").strip()[:40], estado="pendiente", fecha=_dtsol.now())
    db.add(s)
    db.commit()
    metadatos.registrar_evento("SOLICITUD_SALON", "Docente", institucion_id=payload.institucion_id,
                               payload={"salon": sal.nombre, "rol": s.rol_solicitado})
    return {"ok": True, "msg": f"📨 Solicitud enviada para el salón {sal.nombre}. Rectoría o coordinación la revisará; te avisamos cuando la aprueben."}


@router.get("/solicitudes")
def solicitudes(institucion_id: int, estado: str | None = None, personal_id: int | None = None,
                db: Session = Depends(get_db)):
    q = db.query(_SolSal).filter(_SolSal.institucion_id == institucion_id)
    if estado:
        q = q.filter(_SolSal.estado == estado)
    if personal_id:
        q = q.filter(_SolSal.personal_id == personal_id)
    out = []
    for s in q.order_by(_SolSal.id.desc()).limit(60).all():
        p = db.query(Personal).filter(Personal.id == s.personal_id).first()
        sal = db.query(Salon).filter(Salon.id == s.salon_id).first()
        out.append({"id": s.id, "docente": p.nombre if p else "—", "personal_id": s.personal_id,
                    "foto": p.foto if p else None,
                    "profesion": p.profesion if p else "", "experiencia": p.experiencia_anios if p else 0,
                    "salon": sal.nombre if sal else "—", "salon_id": s.salon_id,
                    "rol_solicitado": s.rol_solicitado, "materia": s.materia,
                    "estado": s.estado, "nota": s.nota,
                    "fecha": s.fecha.isoformat(sep=" ", timespec="minutes") if s.fecha else ""})
    return out


class ResolverIn(BaseModel):
    id: int
    aprobar: bool
    nota: str | None = ""


@router.post("/solicitudes/resolver")
def solicitud_resolver(payload: ResolverIn, db: Session = Depends(get_db)):
    s = db.query(_SolSal).filter(_SolSal.id == payload.id).first()
    if not s:
        return {"ok": False, "msg": "Solicitud no encontrada."}
    if s.estado != "pendiente":
        return {"ok": False, "msg": "Esta solicitud ya fue resuelta."}
    p = db.query(Personal).filter(Personal.id == s.personal_id).first()
    sal = db.query(Salon).filter(Salon.id == s.salon_id).first()
    s.nota = (payload.nota or "").strip()[:200] or None
    if payload.aprobar:
        s.estado = "aprobada"
        if s.rol_solicitado == "director" and sal and not sal.director_id:
            sal.director_id = s.personal_id
        msg = f"✅ Solicitud aprobada: {p.nombre if p else 'el docente'} quedó asignado(a) al salón {sal.nombre if sal else ''}"
        msg += " como director(a) de grupo." if s.rol_solicitado == "director" else f" como docente de {s.materia or 'su materia'}."
    else:
        s.estado = "rechazada"
        msg = f"Solicitud rechazada. Se le notificó a {p.nombre if p else 'el docente'}."
    db.commit()
    metadatos.registrar_evento("SOLICITUD_RESUELTA", "Directivo", institucion_id=s.institucion_id,
                               payload={"aprobada": payload.aprobar})
    return {"ok": True, "msg": msg}


# ═════════ CONTROL DE CORTES: abrir/cerrar para TODOS (punto 15) ═════════
class CorteEstadoIn(BaseModel):
    id: int
    cerrado: bool


@router.post("/cortes/estado")
def corte_estado(payload: CorteEstadoIn, db: Session = Depends(get_db)):
    """Rector/coordinación cierra un corte: queda cerrado para TODOS los
    docentes (no pueden modificar notas ni temas de ese corte)."""
    c = db.query(Corte).filter(Corte.id == payload.id).first()
    if not c:
        return {"ok": False, "msg": "Corte no encontrado."}
    c.cerrado = payload.cerrado
    db.commit()
    metadatos.registrar_evento("CORTE_ESTADO", "Directivo", institucion_id=c.institucion_id,
                               payload={"corte": c.nombre, "cerrado": payload.cerrado})
    if payload.cerrado:
        return {"ok": True, "msg": f"🔒 {c.nombre} CERRADO para toda la institución. Ningún docente puede modificar notas ni temas de este corte."}
    return {"ok": True, "msg": f"🔓 {c.nombre} reabierto. Los docentes pueden volver a registrar."}


# ═════════ NOTAS: AVISO A PADRES Y ALERTA DE PÉRDIDA DE AÑO (punto 11) ═════════
from models import MensajeWhatsApp as _WaN, NotaPeriodo as _NotaP, SRDScore as _SRDN
from datetime import datetime as _dtn


@router.get("/notas/riesgo_academico")
def riesgo_academico(institucion_id: int, salon_id: int | None = None,
                     db: Session = Depends(get_db)):
    """Detecta el patrón de 'va a perder el año': materias por debajo de 3.0 y
    tendencia a la baja entre períodos. El modelo aprende de estas señales."""
    q = db.query(Estudiante).filter(Estudiante.institucion_id == institucion_id)
    if salon_id:
        q = q.filter(Estudiante.salon_id == salon_id)
    periodos = {p.id: p.numero for p in db.query(Periodo).all()}
    out = []
    for e in q.all():
        notas = db.query(_NotaP).filter(_NotaP.estudiante_id == e.id).all()
        if not notas:
            continue
        por_mat = {}
        for n in notas:
            por_mat.setdefault(n.materia, {})[periodos.get(n.periodo_id, 0)] = n.nota
        perdidas, tendencias = [], []
        for mat, per in por_mat.items():
            vals = [per[k] for k in sorted(per)]
            prom = sum(vals) / len(vals)
            if prom < 3.0:
                perdidas.append({"materia": mat, "promedio": round(prom, 1)})
            if len(vals) >= 2:
                tendencias.append(vals[-1] - vals[0])
        if not perdidas:
            continue
        tend = round(sum(tendencias) / len(tendencias), 2) if tendencias else 0
        prom_gen = round(sum(n.nota for n in notas) / len(notas), 1)
        nivel = "CRÍTICO" if len(perdidas) >= 3 or (len(perdidas) >= 2 and tend < 0) else "ALERTA"
        srd = db.query(_SRDN).filter(_SRDN.estudiante_id == e.id).first()
        sal = db.query(Salon).filter(Salon.id == e.salon_id).first()
        out.append({"estudiante_id": e.id, "nombre": e.nombre,
                    "salon": sal.nombre if sal else "—",
                    "acudiente": e.acudiente, "telefono": e.telefono,
                    "promedio_general": prom_gen, "materias_perdidas": perdidas,
                    "n_perdidas": len(perdidas), "tendencia": tend,
                    "nivel": nivel,
                    "riesgo_desercion": srd.nivel if srd else None,
                    "pct_asistencia": round(srd.pct_asistencia, 1) if srd else None})
    out.sort(key=lambda x: (-x["n_perdidas"], x["promedio_general"]))
    return out


class NotificarPadreIn(BaseModel):
    estudiante_id: int
    mensaje: str | None = None


@router.post("/notas/notificar_padre")
def notificar_padre(payload: NotificarPadreIn, db: Session = Depends(get_db)):
    e = db.query(Estudiante).filter(Estudiante.id == payload.estudiante_id).first()
    if not e:
        return {"ok": False, "msg": "Estudiante no encontrado."}
    periodos = {p.id: p.numero for p in db.query(Periodo).all()}
    notas = db.query(_NotaP).filter(_NotaP.estudiante_id == e.id).all()
    por_mat = {}
    for n in notas:
        por_mat.setdefault(n.materia, []).append(n.nota)
    bajas = [m for m, v in por_mat.items() if sum(v) / len(v) < 3.0]
    txt = payload.mensaje or (
        f"Buen día {e.acudiente or 'acudiente'}. Le informamos que {e.nombre.split()[0]} presenta "
        f"dificultades académicas en: {', '.join(bajas) if bajas else 'algunas materias'}. "
        "Le invitamos a comunicarse con el director de grupo para acordar un plan de apoyo. "
        "Estamos para ayudarle. — Institución Educativa")
    db.add(_WaN(estudiante_id=e.id, destinatario=f"{e.acudiente} ({e.parentesco or 'acudiente'})",
                telefono=e.telefono, contenido=txt[:500], fecha=_dtn.now(),
                estado="ENVIADO (simulado)", contexto="notas"))
    db.commit()
    metadatos.registrar_evento("NOTIFICACION_NOTAS", "Docente", estudiante_id=e.id,
                               payload={"materias": len(bajas)})
    return {"ok": True, "msg": f"📱 Mensaje enviado (simulado) al acudiente de {e.nombre.split()[0]}: {', '.join(bajas) if bajas else 'seguimiento académico'}."}


class AlertarAlumnoIn(BaseModel):
    estudiante_id: int


@router.post("/notas/alertar_alumno")
def alertar_alumno(payload: AlertarAlumnoIn, db: Session = Depends(get_db)):
    """Alerta temprana AL ESTUDIANTE: 'vas en camino de perder el año'."""
    e = db.query(Estudiante).filter(Estudiante.id == payload.estudiante_id).first()
    if not e:
        return {"ok": False, "msg": "Estudiante no encontrado."}
    notas = db.query(_NotaP).filter(_NotaP.estudiante_id == e.id).all()
    por_mat = {}
    for n in notas:
        por_mat.setdefault(n.materia, []).append(n.nota)
    bajas = [m for m, v in por_mat.items() if sum(v) / len(v) < 3.0]
    db.add(_WaN(estudiante_id=e.id, destinatario=e.nombre, telefono=e.telefono,
                contenido=(f"Hola {e.nombre.split()[0]}: el sistema detectó que vas en riesgo de perder "
                           f"{len(bajas)} materia(s) ({', '.join(bajas[:3])}). Aún estás a tiempo: habla con tu "
                           "docente, entrega los pendientes y pide apoyo. ¡Cuentas con nosotros! — Tu colegio")[:500],
                fecha=_dtn.now(), estado="ENVIADO (simulado)", contexto="alerta_academica"))
    db.commit()
    return {"ok": True, "msg": f"🔔 Alerta enviada a {e.nombre.split()[0]}: {len(bajas)} materia(s) en riesgo. También le aparece en su portal de estudiante."}


# ═════════ HORARIOS: quién asigna y mapa general (puntos 11, 19) ═════════
from models import (AsignacionHorario as _AsigH, RevisionTema as _RevT,
                    Sede as _SedH, ActividadAula as _ActH)

FRANJAS = ["06:45-07:35", "07:35-08:25", "08:25-09:15", "09:45-10:35",
           "10:35-11:25", "11:25-12:15", "12:15-13:05"]
DIAS_SEM = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]


@router.get("/horarios/mapa")
def horarios_mapa(institucion_id: int, sede_id: int | None = None,
                  db: Session = Depends(get_db)):
    """Mapa general: qué docente da qué materia, en qué salón y a qué hora.

    Es la vista que pedía rectoría: ver TODO el colegio de un vistazo y
    detectar choques (un docente en dos salones a la misma hora).
    """
    q = db.query(_AsigH).filter(_AsigH.institucion_id == institucion_id,
                                _AsigH.estado == "activo")
    if sede_id:
        q = q.filter(_AsigH.sede_id == sede_id)
    asigs = q.all()
    salones = db.query(Salon).filter(Salon.institucion_id == institucion_id)
    if sede_id:
        salones = salones.filter(Salon.sede_id == sede_id)
    salones = salones.order_by(Salon.grado, Salon.nombre).all()
    docentes = {p.id: p for p in db.query(Personal).filter(
        Personal.institucion_id == institucion_id, Personal.rol == "docente").all()}
    # grilla por salón
    grid = {}
    for s in salones:
        grid[s.id] = {"salon": s.nombre, "grado": s.grado, "sede_id": s.sede_id,
                      "franjas": {d: {} for d in DIAS_SEM}}
    choques = []
    ocupacion = {}   # (docente, dia, franja) -> salon
    for a in asigs:
        franja = f"{a.hora_inicio}-{a.hora_fin}"
        if a.salon_id in grid and a.dia in grid[a.salon_id]["franjas"]:
            doc = docentes.get(a.personal_id)
            grid[a.salon_id]["franjas"][a.dia][franja] = {
                "id": a.id, "materia": a.materia,
                "docente": doc.nombre if doc else "Sin asignar",
                "docente_id": a.personal_id,
                "foto": doc.foto if doc else None}
        if a.personal_id:
            k = (a.personal_id, a.dia, franja)
            if k in ocupacion and ocupacion[k] != a.salon_id:
                doc = docentes.get(a.personal_id)
                s1 = next((g["salon"] for sid, g in grid.items() if sid == ocupacion[k]), "—")
                s2 = next((g["salon"] for sid, g in grid.items() if sid == a.salon_id), "—")
                choques.append({"docente": doc.nombre if doc else "—", "dia": a.dia,
                                "franja": franja, "salones": [s1, s2]})
            ocupacion[k] = a.salon_id
    # carga por docente
    carga = {}
    for a in asigs:
        if a.personal_id:
            carga[a.personal_id] = carga.get(a.personal_id, 0) + 1
    filas_carga = []
    for pid, n in sorted(carga.items(), key=lambda x: -x[1]):
        d = docentes.get(pid)
        mats = sorted({a.materia for a in asigs if a.personal_id == pid})
        sals = sorted({next((g["salon"] for sid, g in grid.items() if sid == a.salon_id), "")
                       for a in asigs if a.personal_id == pid})
        filas_carga.append({"personal_id": pid, "nombre": d.nombre if d else "—",
                            "foto": d.foto if d else None, "horas": n,
                            "materias": mats, "salones": [s for s in sals if s]})
    sin_asignar = [{"personal_id": p.id, "nombre": p.nombre, "area": p.area}
                   for p in docentes.values() if p.id not in carga]
    return {
        "franjas": FRANJAS, "dias": DIAS_SEM,
        "salones": [{"id": s.id, "nombre": s.nombre, "grado": s.grado,
                     "sede_id": s.sede_id} for s in salones],
        "grid": grid, "choques": choques, "carga_docentes": filas_carga,
        "docentes_sin_horario": sin_asignar,
        "n_asignaciones": len(asigs),
        "cobertura": round(100 * len(asigs) / (len(salones) * len(DIAS_SEM) * len(FRANJAS)), 1)
        if salones else 0,
    }


class AsignarHorarioIn(BaseModel):
    id: int | None = 0
    institucion_id: int
    salon_id: int
    personal_id: int | None = None
    materia: str
    dia: str
    hora_inicio: str
    hora_fin: str
    asignado_por: str | None = "Coordinación"
    nota: str | None = ""


@router.post("/horarios/asignar")
def horarios_asignar(payload: AsignarHorarioIn, db: Session = Depends(get_db)):
    """Solo coordinación o rectoría asigna. Avisa si hay choque de docente."""
    if payload.dia not in DIAS_SEM:
        return {"ok": False, "msg": "Día no válido."}
    if not payload.materia.strip():
        return {"ok": False, "msg": "Escribe la materia."}
    sal = db.query(Salon).filter(Salon.id == payload.salon_id).first()
    if not sal:
        return {"ok": False, "msg": "Salón no encontrado."}
    # ¿el docente ya está ocupado a esa hora en otro salón?
    if payload.personal_id:
        choque = db.query(_AsigH).filter(
            _AsigH.personal_id == payload.personal_id, _AsigH.dia == payload.dia,
            _AsigH.hora_inicio == payload.hora_inicio, _AsigH.estado == "activo",
            _AsigH.salon_id != payload.salon_id,
            _AsigH.id != (payload.id or 0)).first()
        if choque:
            otro = db.query(Salon).filter(Salon.id == choque.salon_id).first()
            p = db.query(Personal).filter(Personal.id == payload.personal_id).first()
            return {"ok": False,
                    "msg": f"⚠️ {p.nombre if p else 'Ese docente'} ya tiene clase el {payload.dia} a las {payload.hora_inicio} en el salón {otro.nombre if otro else '—'}. No puede estar en dos sitios a la vez."}
    # ¿la franja del salón ya está ocupada?
    ocupada = db.query(_AsigH).filter(
        _AsigH.salon_id == payload.salon_id, _AsigH.dia == payload.dia,
        _AsigH.hora_inicio == payload.hora_inicio, _AsigH.estado == "activo",
        _AsigH.id != (payload.id or 0)).first()
    if ocupada and not payload.id:
        db.delete(ocupada)   # reemplazar la franja
    if payload.id:
        a = db.query(_AsigH).filter(_AsigH.id == payload.id).first()
        if not a:
            return {"ok": False, "msg": "Asignación no encontrada."}
    else:
        a = _AsigH(institucion_id=payload.institucion_id)
        db.add(a)
    a.salon_id = payload.salon_id
    a.sede_id = sal.sede_id
    a.personal_id = payload.personal_id
    a.materia = payload.materia.strip()[:60]
    a.dia = payload.dia
    a.hora_inicio = payload.hora_inicio
    a.hora_fin = payload.hora_fin
    a.asignado_por = payload.asignado_por or "Coordinación"
    a.estado = "activo"
    a.nota = (payload.nota or "").strip()[:200] or None
    db.flush()
    # sincronizar el JSON de horarios del salón (lo usa el alumno)
    todas = db.query(_AsigH).filter(_AsigH.salon_id == payload.salon_id,
                                    _AsigH.estado == "activo").all()
    sal.horarios = json.dumps([{"dia": x.dia, "hora": f"{x.hora_inicio}-{x.hora_fin}",
                                "materia": x.materia} for x in todas], ensure_ascii=False)
    db.commit()
    p = db.query(Personal).filter(Personal.id == payload.personal_id).first()
    metadatos.registrar_evento("HORARIO_ASIGNADO", payload.asignado_por or "Coordinación",
                               institucion_id=payload.institucion_id,
                               payload={"salon": sal.nombre, "materia": a.materia})
    return {"ok": True, "id": a.id,
            "msg": f"✅ {payload.materia} asignada al salón {sal.nombre}, {payload.dia} {payload.hora_inicio}" +
                   (f", con {p.nombre}." if p else " (sin docente asignado todavía).")}


class QuitarHorarioIn(BaseModel):
    id: int


@router.post("/horarios/quitar")
def horarios_quitar(payload: QuitarHorarioIn, db: Session = Depends(get_db)):
    a = db.query(_AsigH).filter(_AsigH.id == payload.id).first()
    if not a:
        return {"ok": False, "msg": "Asignación no encontrada."}
    sal = db.query(Salon).filter(Salon.id == a.salon_id).first()
    mat, dia, hora = a.materia, a.dia, a.hora_inicio
    db.delete(a)
    db.flush()
    if sal:
        todas = db.query(_AsigH).filter(_AsigH.salon_id == sal.id,
                                        _AsigH.estado == "activo").all()
        sal.horarios = json.dumps([{"dia": x.dia, "hora": f"{x.hora_inicio}-{x.hora_fin}",
                                    "materia": x.materia} for x in todas], ensure_ascii=False)
    db.commit()
    return {"ok": True, "msg": f"Se quitó {mat} del {dia} {hora}."}


@router.get("/horarios/docente")
def horario_docente(personal_id: int, db: Session = Depends(get_db)):
    """El horario personal de un docente, con sus salones y materias."""
    asigs = db.query(_AsigH).filter(_AsigH.personal_id == personal_id,
                                    _AsigH.estado == "activo").all()
    grid = {d: [] for d in DIAS_SEM}
    for a in asigs:
        sal = db.query(Salon).filter(Salon.id == a.salon_id).first()
        if a.dia in grid:
            grid[a.dia].append({"id": a.id, "hora": f"{a.hora_inicio}-{a.hora_fin}",
                                "materia": a.materia,
                                "salon": sal.nombre if sal else "—",
                                "salon_id": a.salon_id})
    for d in grid:
        grid[d].sort(key=lambda x: x["hora"])
    p = db.query(Personal).filter(Personal.id == personal_id).first()
    return {"docente": p.nombre if p else "—", "horario": grid,
            "horas_semana": len(asigs),
            "materias": sorted({a.materia for a in asigs}),
            "salones": sorted({(db.query(Salon).filter(Salon.id == a.salon_id).first() or Salon()).nombre or ""
                               for a in asigs})}


# ═════════ SUPERVISIÓN DE COORDINACIÓN (puntos 20, 21, 22) ═════════
@router.get("/supervision/docente")
def supervision_docente(personal_id: int, db: Session = Depends(get_db)):
    """Lo que coordinación necesita ver de un docente: sus clases, su material,
    su asistencia y cómo va su salón."""
    p = db.query(Personal).filter(Personal.id == personal_id).first()
    if not p:
        return {"ok": False, "msg": "Docente no encontrado."}
    salones = db.query(Salon).filter(Salon.director_id == personal_id).all()
    ids_sal = [s.id for s in salones]
    asigs = db.query(_AsigH).filter(_AsigH.personal_id == personal_id,
                                    _AsigH.estado == "activo").all()
    ids_sal += [a.salon_id for a in asigs if a.salon_id not in ids_sal]
    acts = db.query(_ActH).filter(_ActH.salon_id.in_(ids_sal)).order_by(
        _ActH.id.desc()).limit(40).all() if ids_sal else []
    clases = []
    for a in acts:
        sal = db.query(Salon).filter(Salon.id == a.salon_id).first()
        try:
            mats = json.loads(a.materiales) if a.materiales else []
        except Exception:
            mats = []
        ents = db.query(EntregaAula).filter(EntregaAula.actividad_id == a.id).all()
        rev = db.query(_RevT).filter(_RevT.actividad_id == a.id).order_by(_RevT.id.desc()).first()
        clases.append({
            "id": a.id, "titulo": a.titulo, "tipo": a.tipo, "materia": a.materia,
            "salon": sal.nombre if sal else "—", "estado": a.estado,
            "corte": a.corte, "periodo": a.periodo_numero,
            "n_materiales": len(mats),
            "materiales": [{"tipo": m.get("tipo"), "nombre": m.get("nombre")} for m in mats[:6]],
            "tiene_video": bool(a.video_url),
            "n_temas": db.query(TemaClase).filter(TemaClase.actividad_id == a.id).count() if 'TemaClase' in globals() else 0,
            "entregas": sum(1 for x in ents if x.estado in ("entregado", "revisado")),
            "total": len(ents),
            "calificadas": sum(1 for x in ents if x.estado == "revisado"),
            "revision": {"estado": rev.estado, "observacion": rev.observacion,
                         "revisor": rev.revisor} if rev else None,
            "fecha_limite": a.fecha_limite.isoformat() if a.fecha_limite else None,
        })
    temas = db.query(TemaPlan).filter(TemaPlan.salon_id.in_(ids_sal)).all() if ids_sal else []
    # asistencia del docente
    from models import AsistenciaPersonal as _AP
    asis = db.query(_AP).filter(_AP.personal_id == personal_id).all()
    presente = sum(1 for x in asis if x.estado == "present")
    # cómo va su salón
    ests = db.query(Estudiante).filter(Estudiante.salon_id.in_(ids_sal)).all() if ids_sal else []
    from models import SRDScore as _S
    scores = db.query(_S).filter(_S.estudiante_id.in_([e.id for e in ests])).all() if ests else []
    return {
        "ok": True,
        "docente": {"id": p.id, "nombre": p.nombre, "area": p.area, "foto": p.foto,
                    "profesion": p.profesion, "experiencia": p.experiencia_anios,
                    "telefono": p.telefono, "email": p.email, "sede_id": p.sede_id},
        "salones": [{"id": s.id, "nombre": s.nombre, "grado": s.grado} for s in salones],
        "horas_semana": len(asigs),
        "materias": sorted({a.materia for a in asigs}),
        "clases": clases,
        "resumen_clases": {
            "total": len(clases),
            "publicadas": sum(1 for c in clases if c["estado"] == "publicada"),
            "con_material": sum(1 for c in clases if c["n_materiales"] > 0),
            "con_video": sum(1 for c in clases if c["tiene_video"]),
            "sin_calificar": sum(1 for c in clases if c["entregas"] > c["calificadas"]),
        },
        "temas_plan": [{"id": t.id, "tema": t.tema, "materia": t.materia,
                        "periodo": t.periodo_numero, "corte": t.corte,
                        "detalle": t.detalle} for t in temas],
        "asistencia": {"registros": len(asis), "presente": presente,
                       "pct": round(100 * presente / len(asis), 1) if asis else None},
        "su_salon": {
            "n_estudiantes": len(ests),
            "criticos": sum(1 for s in scores if s.nivel == "CRÍTICO"),
            "moderados": sum(1 for s in scores if s.nivel == "MODERADO"),
            "asistencia_promedio": round(sum(s.pct_asistencia for s in scores) / len(scores), 1) if scores else None,
        },
    }


class RevisarTemaIn(BaseModel):
    institucion_id: int
    actividad_id: int | None = None
    tema_plan_id: int | None = None
    revisor: str
    estado: str            # aprobado | ajustes | rechazado
    observacion: str | None = ""


@router.post("/supervision/revisar")
def supervision_revisar(payload: RevisarTemaIn, db: Session = Depends(get_db)):
    """Coordinación revisa el material del docente y deja su concepto."""
    if payload.estado not in ("aprobado", "ajustes", "rechazado", "pendiente"):
        return {"ok": False, "msg": "Estado no válido."}
    r = _RevT(institucion_id=payload.institucion_id, actividad_id=payload.actividad_id,
              tema_plan_id=payload.tema_plan_id, revisor=payload.revisor,
              estado=payload.estado,
              observacion=(payload.observacion or "").strip()[:500] or None,
              fecha=datetime.now())
    db.add(r)
    db.commit()
    MSG = {"aprobado": "✅ Material aprobado. El docente recibe la confirmación.",
           "ajustes": "📝 Se pidieron ajustes. El docente ve tu observación en su aula.",
           "rechazado": "❌ Material devuelto. El docente debe rehacerlo."}
    return {"ok": True, "msg": MSG.get(payload.estado, "Revisión guardada.")}


@router.get("/supervision/pendientes")
def supervision_pendientes(institucion_id: int, sede_id: int | None = None,
                           db: Session = Depends(get_db)):
    """Clases publicadas que coordinación todavía no ha revisado."""
    salones = db.query(Salon).filter(Salon.institucion_id == institucion_id)
    if sede_id:
        salones = salones.filter(Salon.sede_id == sede_id)
    ids = [s.id for s in salones.all()]
    acts = db.query(_ActH).filter(_ActH.salon_id.in_(ids),
                                  _ActH.estado == "publicada").order_by(
        _ActH.id.desc()).limit(60).all() if ids else []
    revisadas = {r.actividad_id for r in db.query(_RevT).filter(
        _RevT.institucion_id == institucion_id).all()}
    out = []
    for a in acts:
        if a.id in revisadas:
            continue
        sal = db.query(Salon).filter(Salon.id == a.salon_id).first()
        doc = db.query(Personal).filter(Personal.id == (sal.director_id if sal else None)).first()
        try:
            mats = json.loads(a.materiales) if a.materiales else []
        except Exception:
            mats = []
        out.append({"id": a.id, "titulo": a.titulo, "tipo": a.tipo, "materia": a.materia,
                    "salon": sal.nombre if sal else "—",
                    "docente": doc.nombre if doc else "—",
                    "docente_id": doc.id if doc else None,
                    "n_materiales": len(mats), "tiene_video": bool(a.video_url),
                    "corte": a.corte})
    return {"pendientes": out, "n": len(out)}
