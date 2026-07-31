"""Planeación docente, importación desde SIMAT y certificados de secretaría.

PLANEACIÓN: el docente arma su plan de la semana o del mes desde su propio
perfil (no en un Drive aparte), lo envía, y coordinación lo aprueba o pide
ajustes. Todo queda trazable y el docente ve la observación en su aula.

SIMAT: importa las notas históricas cruzando por documento. Lo que no cruza
queda listado para revisar a mano, sin dañar nada.

CERTIFICADOS: el alumno los pide desde su portal y los descarga cuando
secretaría los emite. Se acabó ir hasta el colegio por un papel.
"""
import json
import random
import string
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (PlaneacionDocente, NotaHistorica, ImportacionSIMAT,
                    CertificadoEmitido, Personal, Salon, Estudiante, Institucion,
                    PerfilLegal, NotaPeriodo, Periodo, Asistencia, ActividadAula,
                    EntregaAula)
import plantillas_legales as PL
import metadatos

router = APIRouter()


def _perfil_legal(db, institucion_id):
    p = db.query(PerfilLegal).filter(PerfilLegal.institucion_id == institucion_id).first()
    if p:
        return p
    ie = db.query(Institucion).filter(Institucion.id == institucion_id).first()
    return PerfilLegal(institucion_id=institucion_id,
                       nombre_oficial=(ie.nombre if ie else "INSTITUCIÓN EDUCATIVA"),
                       municipio=ie.municipio if ie else None,
                       departamento=ie.departamento if ie else None,
                       dane=ie.codigo_dane if ie else None,
                       rector_nombre=ie.rector if ie else None)


def _jl(t, d):
    try:
        return json.loads(t) if t else d
    except Exception:
        return d


# ═══════════════ PLANEACIÓN DOCENTE ═══════════════
@router.get("/planeacion")
def planeacion(institucion_id: int, personal_id: int | None = None,
               estado: str | None = None, db: Session = Depends(get_db)):
    """Las planeaciones. El docente ve las suyas; coordinación las ve todas."""
    q = db.query(PlaneacionDocente).filter(
        PlaneacionDocente.institucion_id == institucion_id)
    if personal_id:
        q = q.filter(PlaneacionDocente.personal_id == personal_id)
    if estado:
        q = q.filter(PlaneacionDocente.estado == estado)
    filas = q.order_by(PlaneacionDocente.id.desc()).limit(80).all()
    out = []
    for p in filas:
        doc = db.query(Personal).filter(Personal.id == p.personal_id).first()
        sal = db.query(Salon).filter(Salon.id == p.salon_id).first()
        cont = _jl(p.contenidos, [])
        out.append({
            "id": p.id, "titulo": p.titulo, "tipo": p.tipo,
            "docente": doc.nombre if doc else "—", "docente_id": p.personal_id,
            "foto": doc.foto if doc else None,
            "salon": sal.nombre if sal else "—", "salon_id": p.salon_id,
            "materia": p.materia, "periodo": p.periodo_numero, "corte": p.corte,
            "desde": p.desde.isoformat() if p.desde else None,
            "hasta": p.hasta.isoformat() if p.hasta else None,
            "estado": p.estado, "revisor": p.revisor,
            "observacion": p.observacion_revisor,
            "n_semanas": len(cont), "generado_ia": bool(p.generado_ia),
            "n_materiales": len(_jl(p.materiales, [])),
            "fecha_envio": p.fecha_envio.isoformat(sep=" ", timespec="minutes") if p.fecha_envio else None,
            "fecha_revision": p.fecha_revision.isoformat(sep=" ", timespec="minutes") if p.fecha_revision else None,
        })
    todas = db.query(PlaneacionDocente).filter(
        PlaneacionDocente.institucion_id == institucion_id).all()
    return {
        "planeaciones": out,
        "resumen": {
            "total": len(todas),
            "borradores": sum(1 for x in todas if x.estado == "borrador"),
            "por_revisar": sum(1 for x in todas if x.estado == "enviada"),
            "aprobadas": sum(1 for x in todas if x.estado == "aprobada"),
            "con_ajustes": sum(1 for x in todas if x.estado == "ajustes"),
        },
    }


@router.get("/planeacion/detalle")
def planeacion_detalle(id: int, db: Session = Depends(get_db)):
    p = db.query(PlaneacionDocente).filter(PlaneacionDocente.id == id).first()
    if not p:
        return {"ok": False, "msg": "Planeación no encontrada."}
    doc = db.query(Personal).filter(Personal.id == p.personal_id).first()
    sal = db.query(Salon).filter(Salon.id == p.salon_id).first()
    return {
        "ok": True, "id": p.id, "titulo": p.titulo, "tipo": p.tipo,
        "docente": doc.nombre if doc else "—", "docente_id": p.personal_id,
        "salon": sal.nombre if sal else None, "salon_id": p.salon_id,
        "materia": p.materia, "periodo_numero": p.periodo_numero, "corte": p.corte,
        "desde": p.desde.isoformat() if p.desde else None,
        "hasta": p.hasta.isoformat() if p.hasta else None,
        "objetivos": _jl(p.objetivos, []), "contenidos": _jl(p.contenidos, []),
        "metodologia": p.metodologia, "evaluacion": p.evaluacion,
        "materiales": _jl(p.materiales, []),
        "estado": p.estado, "revisor": p.revisor,
        "observacion": p.observacion_revisor, "generado_ia": bool(p.generado_ia),
        "fecha_envio": p.fecha_envio.isoformat(sep=" ", timespec="minutes") if p.fecha_envio else None,
        "fecha_revision": p.fecha_revision.isoformat(sep=" ", timespec="minutes") if p.fecha_revision else None,
        "editable": p.estado in ("borrador", "ajustes"),
    }


class PlaneacionIn(BaseModel):
    id: int | None = 0
    institucion_id: int
    personal_id: int
    salon_id: int | None = None
    materia: str | None = ""
    periodo_numero: int | None = 3
    corte: str | None = ""
    tipo: str | None = "semanal"
    titulo: str
    desde: str | None = None
    hasta: str | None = None
    objetivos: list | None = None
    contenidos: list | None = None
    metodologia: str | None = ""
    evaluacion: str | None = ""
    materiales: list | None = None
    generado_ia: bool | None = False
    enviar: bool = False


@router.post("/planeacion/guardar")
def planeacion_guardar(payload: PlaneacionIn, db: Session = Depends(get_db)):
    if not payload.titulo.strip():
        return {"ok": False, "msg": "Ponle un título a la planeación."}
    if payload.id:
        p = db.query(PlaneacionDocente).filter(PlaneacionDocente.id == payload.id).first()
        if not p:
            return {"ok": False, "msg": "Planeación no encontrada."}
        if p.estado == "aprobada":
            return {"ok": False,
                    "msg": "Esta planeación ya está aprobada. Si necesitas cambiarla, pídele a coordinación que la devuelva."}
    else:
        p = PlaneacionDocente(institucion_id=payload.institucion_id,
                              personal_id=payload.personal_id, creado=datetime.now())
        db.add(p)
    p.salon_id = payload.salon_id
    p.materia = (payload.materia or "").strip()[:60] or None
    p.periodo_numero = payload.periodo_numero or 3
    p.corte = (payload.corte or "").strip()[:40] or None
    p.tipo = payload.tipo or "semanal"
    p.titulo = payload.titulo.strip()[:150]
    p.metodologia = (payload.metodologia or "")[:2000] or None
    p.evaluacion = (payload.evaluacion or "")[:2000] or None
    p.objetivos = json.dumps([str(o)[:250] for o in (payload.objetivos or [])][:10],
                             ensure_ascii=False)
    p.contenidos = json.dumps(payload.contenidos or [], ensure_ascii=False)
    p.materiales = json.dumps(payload.materiales or [], ensure_ascii=False)
    p.generado_ia = bool(payload.generado_ia)
    for campo, val in (("desde", payload.desde), ("hasta", payload.hasta)):
        if val:
            try:
                setattr(p, campo, date.fromisoformat(val))
            except ValueError:
                pass
    if payload.enviar:
        cont = payload.contenidos or []
        if not cont:
            return {"ok": False,
                    "msg": "Antes de enviar, agrega al menos una semana con su tema y actividades."}
        p.estado = "enviada"
        p.fecha_envio = datetime.now()
    elif p.estado in (None, ""):
        p.estado = "borrador"
    db.commit()
    metadatos.registrar_evento("PLANEACION", "Docente",
                               institucion_id=payload.institucion_id,
                               payload={"estado": p.estado, "titulo": p.titulo[:40]})
    try:
        from routers.vivo import marcar_cambio
        if payload.enviar:
            marcar_cambio(payload.institucion_id, "planeacion",
                          f"Nueva planeación por revisar: {p.titulo[:40]}")
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "id": p.id, "estado": p.estado,
            "msg": ("📤 Planeación enviada a coordinación. Te avisamos apenas la revisen."
                    if payload.enviar else "💾 Guardada como borrador. Puedes seguir editándola.")}


class RevisarPlanIn(BaseModel):
    id: int
    estado: str            # aprobada | ajustes | rechazada
    observacion: str | None = ""
    revisor: str


@router.post("/planeacion/revisar")
def planeacion_revisar(payload: RevisarPlanIn, db: Session = Depends(get_db)):
    """Coordinación aprueba, pide ajustes o devuelve."""
    p = db.query(PlaneacionDocente).filter(PlaneacionDocente.id == payload.id).first()
    if not p:
        return {"ok": False, "msg": "Planeación no encontrada."}
    if payload.estado not in ("aprobada", "ajustes", "rechazada"):
        return {"ok": False, "msg": "Estado no válido."}
    if payload.estado in ("ajustes", "rechazada") and not (payload.observacion or "").strip():
        return {"ok": False,
                "msg": "Explica qué debe ajustar el docente. Sin la observación no sabe qué corregir."}
    p.estado = payload.estado
    p.revisor = payload.revisor[:90]
    p.observacion_revisor = (payload.observacion or "").strip()[:1000] or None
    p.fecha_revision = datetime.now()
    db.commit()
    doc = db.query(Personal).filter(Personal.id == p.personal_id).first()
    metadatos.registrar_evento("PLANEACION_REVISADA", payload.revisor,
                               institucion_id=p.institucion_id,
                               payload={"estado": payload.estado})
    MSG = {"aprobada": f"✅ Planeación aprobada. {doc.nombre.split()[0] if doc else 'El docente'} ya puede ejecutarla.",
           "ajustes": f"📝 Se le pidieron ajustes a {doc.nombre.split()[0] if doc else 'el docente'}. Verá tu observación en su perfil.",
           "rechazada": "❌ Planeación devuelta. El docente debe rehacerla."}
    return {"ok": True, "msg": MSG[payload.estado]}


@router.post("/planeacion/eliminar")
def planeacion_eliminar(id: int, db: Session = Depends(get_db)):
    p = db.query(PlaneacionDocente).filter(PlaneacionDocente.id == id).first()
    if not p:
        return {"ok": False, "msg": "No encontrada."}
    if p.estado == "aprobada":
        return {"ok": False, "msg": "No se puede borrar una planeación aprobada."}
    t = p.titulo
    db.delete(p)
    db.commit()
    return {"ok": True, "msg": f"«{t}» eliminada."}


@router.get("/planeacion/imprimir", response_class=HTMLResponse)
def planeacion_imprimir(id: int, db: Session = Depends(get_db)):
    """La planeación con membrete, para el archivo o para entregarla firmada."""
    p = db.query(PlaneacionDocente).filter(PlaneacionDocente.id == id).first()
    if not p:
        return HTMLResponse("<h3>No encontrada</h3>", status_code=404)
    pl = _perfil_legal(db, p.institucion_id)
    doc = db.query(Personal).filter(Personal.id == p.personal_id).first()
    sal = db.query(Salon).filter(Salon.id == p.salon_id).first()
    obj = _jl(p.objetivos, [])
    cont = _jl(p.contenidos, [])
    filas = "".join(
        f"<tr><td style='text-align:center'>{c.get('semana', i)}</td>"
        f"<td>{c.get('tema','')}</td><td>{c.get('actividades','')}</td>"
        f"<td>{c.get('recursos','')}</td></tr>"
        for i, c in enumerate(cont, 1))
    cuerpo = f"""
<h1>PLANEACIÓN {(p.tipo or 'semanal').upper()}</h1>
<div class="doc-num">{p.titulo}</div>
<table>
 <tr><td class="tk">DOCENTE</td><td>{doc.nombre if doc else ''}</td></tr>
 <tr><td class="tk">ÁREA / ASIGNATURA</td><td>{p.materia or '—'}</td></tr>
 <tr><td class="tk">GRADO / SALÓN</td><td>{sal.nombre if sal else '—'}</td></tr>
 <tr><td class="tk">PERÍODO</td><td>{p.periodo_numero}{f' · {p.corte}' if p.corte else ''}</td></tr>
 <tr><td class="tk">VIGENCIA</td><td>Del {PL.fecha_corta(p.desde)} al {PL.fecha_corta(p.hasta)}</td></tr>
 <tr><td class="tk">ESTADO</td><td>{(p.estado or '').upper()}{f' — revisó {p.revisor}' if p.revisor else ''}</td></tr>
</table>
<h2>Objetivos de aprendizaje</h2>
<ol>{''.join(f'<li>{o}</li>' for o in obj) or '<li>—</li>'}</ol>
<h2>Desarrollo</h2>
<table>
 <thead><tr><th style="width:9%">SEMANA</th><th style="width:26%">TEMA</th>
 <th>ACTIVIDADES</th><th style="width:22%">RECURSOS</th></tr></thead>
 <tbody>{filas or '<tr><td colspan="4">Sin contenidos registrados</td></tr>'}</tbody></table>
{f'<h2>Metodología</h2><p>{p.metodologia}</p>' if p.metodologia else ''}
{f'<h2>Evaluación</h2><p>{p.evaluacion}</p>' if p.evaluacion else ''}
{f'<div class="sello"><b>Observación de coordinación:</b> {p.observacion_revisor}</div>' if p.observacion_revisor else ''}
<div class="firmas">
 <div><b>{doc.nombre if doc else ''}</b><br>Docente</div>
 <div><b>{p.revisor or 'Coordinación académica'}</b><br>Coordinación académica</div>
</div>"""
    return HTMLResponse(PL.envolver("Planeación", pl, cuerpo))


# ═══════════════ TALLER IMPRIMIBLE ═══════════════
@router.get("/taller/imprimir", response_class=HTMLResponse)
def taller_imprimir(actividad_id: int, db: Session = Depends(get_db)):
    """El taller con membrete institucional, para trabajarlo en papel."""
    a = db.query(ActividadAula).filter(ActividadAula.id == actividad_id).first()
    if not a:
        return HTMLResponse("<h3>Actividad no encontrada</h3>", status_code=404)
    sal = db.query(Salon).filter(Salon.id == a.salon_id).first()
    pl = _perfil_legal(db, sal.institucion_id if sal else None)
    doc = db.query(Personal).filter(Personal.id == (sal.director_id if sal else None)).first()
    from models import TemaClase
    temas = db.query(TemaClase).filter(TemaClase.actividad_id == a.id).order_by(
        TemaClase.orden).all()
    obj = _jl(a.objetivos, [])
    secciones = ""
    n = 1
    for t in temas:
        bloques = _jl(t.contenido, [])
        txt = "".join(
            f"<p><b>{b.get('h','')}</b> {b.get('p','')}</p>"
            for b in bloques if b.get("t") in ("texto", "ejemplo", "tip"))
        secciones += f"<h2>{n}. {t.titulo}</h2>{txt}"
        quiz = _jl(t.quiz, [])
        if quiz:
            secciones += "<p><b>Responde:</b></p><ol>"
            for q in quiz:
                ops = "".join(f"<div>&nbsp;&nbsp;( ) {o}</div>" for o in q.get("op", []))
                secciones += f"<li>{q.get('q','')}{ops}</li>"
            secciones += "</ol>"
        n += 1
    if not temas:
        secciones = f"<h2>Instrucciones</h2><p style='white-space:pre-line'>{a.descripcion or ''}</p>"
    lineas = "".join('<div class="renglon"></div>' for _ in range(12))
    cuerpo = f"""
<h1>{(a.tipo or 'TALLER').upper()}: {a.titulo}</h1>
<table>
 <tr><td class="tk">ÁREA</td><td>{a.materia or '—'}</td>
     <td class="tk">GRADO</td><td>{sal.nombre if sal else '—'}</td></tr>
 <tr><td class="tk">DOCENTE</td><td>{doc.nombre if doc else '—'}</td>
     <td class="tk">PERÍODO</td><td>{a.periodo_numero or ''}{f' · {a.corte}' if a.corte else ''}</td></tr>
 <tr><td class="tk">ESTUDIANTE</td><td colspan="3" style="height:26px"></td></tr>
 <tr><td class="tk">FECHA</td><td></td><td class="tk">NOTA</td><td></td></tr>
</table>
{f'<h2>Lo que vas a lograr</h2><ol>{"".join(f"<li>{o}</li>" for o in obj)}</ol>' if obj else ''}
{f'<p style="white-space:pre-line">{a.descripcion}</p>' if a.descripcion and temas else ''}
{secciones}
<h2>Desarrollo del estudiante</h2>
{lineas}
<div class="firmas">
 <div>Firma del estudiante</div>
 <div>Firma del acudiente</div>
 <div>{doc.nombre if doc else 'Docente'}<br>Docente</div>
</div>"""
    extra = ".renglon{border-bottom:1px solid #94A3B8;height:26px;margin-bottom:2px}"
    return HTMLResponse(PL.envolver(f"Taller · {a.titulo}", pl, cuerpo, extra))


# ═══════════════ IMPORTACIÓN SIMAT ═══════════════
@router.get("/simat/formato")
def simat_formato():
    """Qué columnas debe traer el archivo."""
    return {
        "columnas": [
            {"nombre": "documento", "obligatoria": True,
             "desc": "Documento del estudiante — es lo que se usa para cruzar"},
            {"nombre": "nombre", "obligatoria": False, "desc": "Nombre completo (para verificar)"},
            {"nombre": "anio", "obligatoria": True, "desc": "Año lectivo, ej: 2024"},
            {"nombre": "grado", "obligatoria": False, "desc": "Grado que cursó"},
            {"nombre": "periodo", "obligatoria": True, "desc": "Número del período (1 a 4)"},
            {"nombre": "materia", "obligatoria": True, "desc": "Nombre de la asignatura"},
            {"nombre": "nota", "obligatoria": True, "desc": "Nota de 0.0 a 5.0"},
            {"nombre": "fallas", "obligatoria": False, "desc": "Inasistencias del período"},
        ],
        "ejemplo_csv": ("documento;nombre;anio;grado;periodo;materia;nota;fallas\\n"
                        "1098765432;PEREZ GOMEZ ANA;2024;9;1;MATEMATICAS;3.8;2\\n"
                        "1098765432;PEREZ GOMEZ ANA;2024;9;1;LENGUAJE;4.2;0"),
        "notas": [
            "El archivo puede venir separado por punto y coma (;) o por coma (,).",
            "El cruce se hace por documento. Lo que no cruce queda listado para revisar.",
            "Se puede importar varias veces: no duplica lo que ya está.",
            "Nada de esto toca las notas del año en curso.",
        ],
    }


class ImportarIn(BaseModel):
    institucion_id: int
    archivo: str | None = ""
    filas: list           # [{documento, nombre, anio, grado, periodo, materia, nota, fallas}]
    hecho_por: str | None = "Secretaría"
    origen: str | None = "simat"


@router.post("/simat/importar")
def simat_importar(payload: ImportarIn, db: Session = Depends(get_db)):
    """Cruza por documento e importa las notas históricas."""
    if not payload.filas:
        return {"ok": False, "msg": "El archivo no trae filas."}
    lote = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    ests = db.query(Estudiante).filter(
        Estudiante.institucion_id == payload.institucion_id).all()
    por_doc = {}
    for e in ests:
        d = (getattr(e, "documento", None) or e.codigo_acceso or "")
        d = str(d).replace(".", "").replace("-", "").strip()
        if d:
            por_doc[d] = e
    cruzadas, sin_cruce, n_notas = 0, [], 0
    vistos = set()
    for f in payload.filas[:5000]:
        if not isinstance(f, dict):
            continue
        doc = str(f.get("documento", "")).replace(".", "").replace("-", "").strip()
        mat = str(f.get("materia", "")).strip()[:60]
        if not doc or not mat:
            continue
        try:
            anio = int(f.get("anio") or 0)
            per = int(f.get("periodo") or 1)
            nota = float(str(f.get("nota", "")).replace(",", ".")) if f.get("nota") not in (None, "") else None
        except (ValueError, TypeError):
            continue
        if not anio:
            continue
        est = por_doc.get(doc)
        clave = (doc, anio, per, mat)
        if clave in vistos:
            continue
        vistos.add(clave)
        ya = db.query(NotaHistorica).filter(
            NotaHistorica.institucion_id == payload.institucion_id,
            NotaHistorica.documento == doc, NotaHistorica.anio == anio,
            NotaHistorica.periodo == per, NotaHistorica.materia == mat).first()
        if ya:
            continue
        db.add(NotaHistorica(
            institucion_id=payload.institucion_id,
            estudiante_id=est.id if est else None, documento=doc,
            nombre_origen=str(f.get("nombre", ""))[:120] or None,
            anio=anio, grado=str(f.get("grado", ""))[:20] or None,
            periodo=per, materia=mat, nota=nota,
            fallas=int(f.get("fallas") or 0), origen=payload.origen or "simat",
            lote=lote, conciliado=bool(est)))
        n_notas += 1
        if est:
            cruzadas += 1
        elif doc not in [x["documento"] for x in sin_cruce]:
            sin_cruce.append({"documento": doc, "nombre": str(f.get("nombre", ""))[:80]})
    imp = ImportacionSIMAT(
        institucion_id=payload.institucion_id, lote=lote,
        archivo=(payload.archivo or "")[:120] or None, origen=payload.origen or "simat",
        n_filas=len(payload.filas), n_cruzadas=cruzadas, n_sin_cruce=len(sin_cruce),
        n_notas=n_notas,
        detalle=json.dumps(sin_cruce[:60], ensure_ascii=False),
        estado="procesado", fecha=datetime.now(), hecho_por=payload.hecho_por)
    db.add(imp)
    db.commit()
    metadatos.registrar_evento("IMPORT_SIMAT", payload.hecho_por or "Secretaría",
                               institucion_id=payload.institucion_id,
                               payload={"notas": n_notas, "sin_cruce": len(sin_cruce)})
    aviso = ""
    if sin_cruce:
        aviso = (f" ⚠️ {len(sin_cruce)} documento(s) no están matriculados aquí: sus notas "
                 "quedaron guardadas y se vinculan solas cuando se matriculen.")
    return {"ok": True, "lote": lote, "n_notas": n_notas, "cruzadas": cruzadas,
            "sin_cruce": len(sin_cruce), "detalle_sin_cruce": sin_cruce[:20],
            "msg": f"📥 Importadas {n_notas} nota(s), {cruzadas} vinculadas a estudiantes.{aviso}"}


@router.get("/simat/importaciones")
def simat_importaciones(institucion_id: int, db: Session = Depends(get_db)):
    filas = db.query(ImportacionSIMAT).filter(
        ImportacionSIMAT.institucion_id == institucion_id).order_by(
        ImportacionSIMAT.id.desc()).limit(30).all()
    total = db.query(NotaHistorica).filter(
        NotaHistorica.institucion_id == institucion_id).count()
    sin_v = db.query(NotaHistorica).filter(
        NotaHistorica.institucion_id == institucion_id,
        NotaHistorica.estudiante_id == None).count()  # noqa: E711
    anios = sorted({n.anio for n in db.query(NotaHistorica).filter(
        NotaHistorica.institucion_id == institucion_id).all()}, reverse=True)
    return {
        "importaciones": [{
            "id": x.id, "lote": x.lote, "archivo": x.archivo, "origen": x.origen,
            "n_filas": x.n_filas, "n_notas": x.n_notas, "cruzadas": x.n_cruzadas,
            "sin_cruce": x.n_sin_cruce, "hecho_por": x.hecho_por,
            "sin_cruce_detalle": _jl(x.detalle, [])[:10],
            "fecha": x.fecha.isoformat(sep=" ", timespec="minutes") if x.fecha else "",
        } for x in filas],
        "resumen": {"notas_historicas": total, "sin_vincular": sin_v,
                    "anios": anios, "n_importaciones": len(filas)},
    }


@router.post("/simat/reconciliar")
def simat_reconciliar(institucion_id: int, db: Session = Depends(get_db)):
    """Vuelve a intentar vincular lo que no cruzó (útil tras matricular)."""
    huerfanas = db.query(NotaHistorica).filter(
        NotaHistorica.institucion_id == institucion_id,
        NotaHistorica.estudiante_id == None).all()  # noqa: E711
    ests = db.query(Estudiante).filter(Estudiante.institucion_id == institucion_id).all()
    por_doc = {}
    for e in ests:
        d = str(getattr(e, "documento", None) or e.codigo_acceso or "").replace(".", "").strip()
        if d:
            por_doc[d] = e
    n = 0
    for h in huerfanas:
        e = por_doc.get((h.documento or "").strip())
        if e:
            h.estudiante_id = e.id
            h.conciliado = True
            n += 1
    db.commit()
    return {"ok": True, "vinculadas": n,
            "msg": (f"🔗 Se vincularon {n} nota(s) a estudiantes matriculados."
                    if n else "No había notas nuevas para vincular.")}


@router.get("/historico")
def historico(estudiante_id: int, db: Session = Depends(get_db)):
    """El historial académico completo del alumno, año por año."""
    e = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not e:
        return {"ok": False}
    filas = db.query(NotaHistorica).filter(
        NotaHistorica.estudiante_id == estudiante_id).order_by(
        NotaHistorica.anio.desc(), NotaHistorica.periodo).all()
    por_anio = {}
    for h in filas:
        a = por_anio.setdefault(h.anio, {"anio": h.anio, "grado": h.grado,
                                         "materias": {}, "fallas": 0})
        m = a["materias"].setdefault(h.materia, {"materia": h.materia, "periodos": {}})
        m["periodos"][h.periodo] = h.nota
        a["fallas"] += h.fallas or 0
    out = []
    for a in sorted(por_anio.values(), key=lambda x: -x["anio"]):
        mats = []
        for m in a["materias"].values():
            vals = [v for v in m["periodos"].values() if v is not None]
            mats.append({"materia": m["materia"], "periodos": m["periodos"],
                         "definitiva": round(sum(vals) / len(vals), 1) if vals else None})
        mats.sort(key=lambda x: x["materia"])
        prom = [x["definitiva"] for x in mats if x["definitiva"] is not None]
        out.append({"anio": a["anio"], "grado": a["grado"], "materias": mats,
                    "promedio": round(sum(prom) / len(prom), 1) if prom else None,
                    "perdidas": sum(1 for x in mats if (x["definitiva"] or 5) < 3.0),
                    "fallas": a["fallas"]})
    return {"ok": True, "estudiante": e.nombre, "anios": out,
            "n_anios": len(out), "origen": "Importado de la plataforma anterior"}


# ═══════════════ CERTIFICADOS ═══════════════
TIPOS_CERT = {
    "estudio": {"label": "📘 Certificado de estudio",
                "desc": "Acredita que el estudiante está matriculado y cursando.",
                "requiere": []},
    "notas": {"label": "📗 Certificado de notas",
              "desc": "Las calificaciones del período o del año.",
              "requiere": ["periodo"]},
    "asistencia": {"label": "📋 Constancia de asistencia",
                   "desc": "Porcentaje de asistencia del estudiante.",
                   "requiere": []},
    "matricula": {"label": "📝 Constancia de matrícula",
                  "desc": "Para trámites de subsidios, transporte o EPS.",
                  "requiere": []},
    "recuperacion": {"label": "♻️ Certificado de recuperación",
                     "desc": "Acredita que superó las actividades de recuperación.",
                     "requiere": ["materia"]},
    "taller": {"label": "🛠️ Constancia de taller o curso",
               "desc": "Certifica la participación en un curso o taller.",
               "requiere": ["curso"]},
    "paz_salvo": {"label": "✅ Paz y salvo",
                  "desc": "Que no tiene pendientes con la institución.",
                  "requiere": []},
}


@router.get("/certificados/tipos")
def certificados_tipos():
    return {"tipos": [{"id": k, **v} for k, v in TIPOS_CERT.items()]}


@router.get("/certificados")
def certificados(institucion_id: int | None = None, estudiante_id: int | None = None,
                 estado: str | None = None, db: Session = Depends(get_db)):
    q = db.query(CertificadoEmitido)
    if estudiante_id:
        q = q.filter(CertificadoEmitido.estudiante_id == estudiante_id)
    elif institucion_id:
        q = q.filter(CertificadoEmitido.institucion_id == institucion_id)
    if estado:
        q = q.filter(CertificadoEmitido.estado == estado)
    filas = q.order_by(CertificadoEmitido.id.desc()).limit(80).all()
    out = []
    for c in filas:
        e = db.query(Estudiante).filter(Estudiante.id == c.estudiante_id).first()
        t = TIPOS_CERT.get(c.tipo, {})
        out.append({
            "id": c.id, "tipo": c.tipo, "tipo_label": t.get("label", c.tipo),
            "numero": c.numero, "estudiante": e.nombre if e else "—",
            "estudiante_id": c.estudiante_id, "periodo": c.periodo,
            "estado": c.estado, "emitido_por": c.emitido_por,
            "codigo": c.codigo_verificacion, "n_descargas": c.n_descargas or 0,
            "solicitado": c.solicitado.isoformat(sep=" ", timespec="minutes") if c.solicitado else None,
            "emitido": c.emitido.isoformat(sep=" ", timespec="minutes") if c.emitido else None,
        })
    todos = db.query(CertificadoEmitido)
    if institucion_id:
        todos = todos.filter(CertificadoEmitido.institucion_id == institucion_id)
    todos = todos.all()
    return {"certificados": out,
            "resumen": {"total": len(todos),
                        "pendientes": sum(1 for x in todos if x.estado == "solicitado"),
                        "emitidos": sum(1 for x in todos if x.estado in ("emitido", "entregado"))}}


class SolicitarCertIn(BaseModel):
    institucion_id: int
    estudiante_id: int
    tipo: str
    periodo: str | None = ""
    datos: dict | None = None


@router.post("/certificados/solicitar")
def certificados_solicitar(payload: SolicitarCertIn, db: Session = Depends(get_db)):
    """El alumno lo pide desde su portal, sin ir hasta el colegio."""
    if payload.tipo not in TIPOS_CERT:
        return {"ok": False, "msg": "Tipo de certificado no válido."}
    pend = db.query(CertificadoEmitido).filter(
        CertificadoEmitido.estudiante_id == payload.estudiante_id,
        CertificadoEmitido.tipo == payload.tipo,
        CertificadoEmitido.estado == "solicitado").first()
    if pend:
        return {"ok": False,
                "msg": "Ya tienes una solicitud pendiente de este certificado. Secretaría la está revisando."}
    n = db.query(CertificadoEmitido).filter(
        CertificadoEmitido.institucion_id == payload.institucion_id).count() + 1
    c = CertificadoEmitido(
        institucion_id=payload.institucion_id, estudiante_id=payload.estudiante_id,
        tipo=payload.tipo, numero=f"CERT-{date.today().year}-{n:04d}",
        periodo=(payload.periodo or "").strip()[:40] or None,
        datos=json.dumps(payload.datos or {}, ensure_ascii=False),
        solicitado=datetime.now(), estado="solicitado")
    db.add(c)
    db.commit()
    try:
        from routers.vivo import marcar_cambio
        marcar_cambio(payload.institucion_id, "certificado",
                      f"Nueva solicitud de {TIPOS_CERT[payload.tipo]['label']}")
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "id": c.id, "numero": c.numero,
            "msg": (f"📨 Solicitud enviada ({c.numero}). Secretaría la revisa y te avisamos "
                    "para que lo descargues desde aquí mismo.")}


class EmitirCertIn(BaseModel):
    id: int
    emitido_por: str


@router.post("/certificados/emitir")
def certificados_emitir(payload: EmitirCertIn, db: Session = Depends(get_db)):
    c = db.query(CertificadoEmitido).filter(CertificadoEmitido.id == payload.id).first()
    if not c:
        return {"ok": False, "msg": "Solicitud no encontrada."}
    if c.estado != "solicitado":
        return {"ok": False, "msg": "Este certificado ya fue emitido."}
    c.estado = "emitido"
    c.emitido = datetime.now()
    c.emitido_por = payload.emitido_por[:90]
    c.codigo_verificacion = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    db.commit()
    e = db.query(Estudiante).filter(Estudiante.id == c.estudiante_id).first()
    metadatos.registrar_evento("CERTIFICADO_EMITIDO", payload.emitido_por,
                               institucion_id=c.institucion_id,
                               estudiante_id=c.estudiante_id, payload={"tipo": c.tipo})
    return {"ok": True, "codigo": c.codigo_verificacion,
            "msg": (f"✅ {TIPOS_CERT.get(c.tipo, {}).get('label', 'Certificado')} emitido para "
                    f"{e.nombre if e else 'el estudiante'}. Ya lo puede descargar desde su portal.")}


@router.get("/certificados/ver", response_class=HTMLResponse)
def certificados_ver(id: int, db: Session = Depends(get_db)):
    c = db.query(CertificadoEmitido).filter(CertificadoEmitido.id == id).first()
    if not c:
        return HTMLResponse("<h3>No encontrado</h3>", status_code=404)
    if c.estado == "solicitado":
        return HTMLResponse(
            "<div style='font-family:system-ui;max-width:520px;margin:60px auto;text-align:center'>"
            "<h2>⏳ En trámite</h2><p>Secretaría todavía no ha emitido este certificado. "
            "Te avisamos apenas esté listo.</p></div>")
    e = db.query(Estudiante).filter(Estudiante.id == c.estudiante_id).first()
    pl = _perfil_legal(db, c.institucion_id)
    sal = db.query(Salon).filter(Salon.id == (e.salon_id if e else None)).first()
    datos = _jl(c.datos, {})
    c.n_descargas = (c.n_descargas or 0) + 1
    db.commit()
    hoy = date.today()
    doc_txt = getattr(e, "documento", None) or (e.codigo_acceso if e else "—")
    cuerpo_esp = ""
    if c.tipo == "notas":
        notas = db.query(NotaPeriodo).filter(NotaPeriodo.estudiante_id == c.estudiante_id).all()
        por_mat = {}
        for n in notas:
            por_mat.setdefault(n.materia, []).append(n.nota)
        filas = "".join(
            f"<tr><td>{m}</td><td style='text-align:center'>{round(sum(v)/len(v),1)}</td>"
            f"<td style='text-align:center'>{'APROBADA' if sum(v)/len(v) >= 3 else 'PENDIENTE'}</td></tr>"
            for m, v in sorted(por_mat.items()))
        prom = [sum(v) / len(v) for v in por_mat.values()]
        cuerpo_esp = f"""<table><thead><tr><th>ÁREA / ASIGNATURA</th>
            <th style="width:16%">DEFINITIVA</th><th style="width:22%">ESTADO</th></tr></thead>
            <tbody>{filas}<tr><td><b>PROMEDIO GENERAL</b></td>
            <td style="text-align:center"><b>{round(sum(prom)/len(prom),1) if prom else '—'}</b></td>
            <td></td></tr></tbody></table>"""
    elif c.tipo == "asistencia":
        tot = db.query(Asistencia).filter(Asistencia.estudiante_id == c.estudiante_id).count()
        fal = db.query(Asistencia).filter(Asistencia.estudiante_id == c.estudiante_id,
                                          Asistencia.estado == "absent").count()
        pct = round(100 * (tot - fal) / tot, 1) if tot else 100
        cuerpo_esp = f"""<table>
            <tr><td class="tk">DÍAS REGISTRADOS</td><td>{tot}</td></tr>
            <tr><td class="tk">INASISTENCIAS</td><td>{fal}</td></tr>
            <tr><td class="tk">PORCENTAJE DE ASISTENCIA</td><td><b>{pct}%</b></td></tr></table>"""
    elif c.tipo == "recuperacion":
        cuerpo_esp = f"""<p>Que el estudiante presentó y <b>superó satisfactoriamente</b> las
            actividades de recuperación correspondientes a la asignatura
            <b>{datos.get('materia', '____________')}</b>
            {f"del período {c.periodo}" if c.periodo else ""}, obteniendo una valoración
            de <b>{datos.get('nota', '3.0')}</b>.</p>"""
    elif c.tipo == "taller":
        cuerpo_esp = f"""<p>Que el estudiante participó y culminó satisfactoriamente
            <b>{datos.get('curso', 'el taller institucional')}</b>, con una intensidad de
            <b>{datos.get('horas', '20')} horas</b>.</p>"""
    elif c.tipo == "paz_salvo":
        cuerpo_esp = """<p>Que el estudiante <b>se encuentra a paz y salvo</b> con la
            institución por todo concepto: académico, de biblioteca, laboratorio,
            material devolutivo y compromisos de convivencia.</p>"""
    TXT = {
        "estudio": "se encuentra <b>MATRICULADO(A) Y CURSANDO</b> estudios en esta institución",
        "notas": "cursó el presente año lectivo, obteniendo las siguientes valoraciones",
        "asistencia": "presenta el siguiente registro de asistencia",
        "matricula": "se encuentra <b>DEBIDAMENTE MATRICULADO(A)</b> en esta institución",
        "recuperacion": "cursó actividades de recuperación",
        "taller": "participó en actividades de formación complementaria",
        "paz_salvo": "no presenta obligaciones pendientes con la institución",
    }
    cuerpo = f"""
<h1>{TIPOS_CERT.get(c.tipo, {}).get('label', 'CERTIFICADO').split(' ', 1)[-1].upper()}</h1>
<div class="doc-num">{c.numero}</div>
<p style="text-align:center;margin:22px 0"><b>LA SECRETARÍA ACADÉMICA</b><br>CERTIFICA QUE:</p>
<p style="text-align:center;font-size:1.15rem;margin:16px 0">
  <b>{(e.nombre if e else '').upper()}</b><br>
  <span style="font-size:.86rem;color:#475569">identificado(a) con documento {doc_txt}</span></p>
<p>{TXT.get(c.tipo, 'cumple con lo aquí certificado')}
{f', en el grado <b>{sal.nombre}</b> ({sal.jornada})' if sal else ''}
 durante el año lectivo <b>{hoy.year}</b>{f', período {c.periodo}' if c.periodo else ''}.</p>
{cuerpo_esp}
<p style="margin-top:20px">La presente constancia se expide a solicitud del interesado,
en {pl.municipio or ''}, el {PL.fecha_larga(hoy)}.</p>
<div class="firmas">
 <div><b>{c.emitido_por or 'Secretaría Académica'}</b><br>Secretaría Académica</div>
 <div>{('<img class="firma-img" src="' + pl.rector_firma + '">') if pl.rector_firma else ''}
  <b>{pl.rector_nombre or ''}</b><br>Rector(a)</div>
</div>
<div class="sello">🔐 Código de verificación: <b>{c.codigo_verificacion or '—'}</b>
 · Este documento puede validarse ante la institución citando este código.</div>"""
    return HTMLResponse(PL.envolver(f"Certificado {c.numero}", pl, cuerpo))
