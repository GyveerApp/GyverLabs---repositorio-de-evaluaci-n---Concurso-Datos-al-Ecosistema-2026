"""
Módulo — Censo Juvenil Territorial

A diferencia de los demás routers (que operan dentro del tenant de UN
colegio), este módulo representa la vista de Secretaría/Alcaldía: cruza
SISBEN + estado educativo + alertas de protección por departamento y
municipio, para ubicar tanto a los jóvenes que hoy no están estudiando
como a los que sí estudian pero viven en una zona con alguna alerta
activa (Sistema de Alertas Tempranas — SAT, Defensoría del Pueblo).

Datos 100% sintéticos — ver backend/seed_data.py::generar_censo_juvenil.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import RegistroCenso

router = APIRouter()

# Refleja los municipios que genera seed_data.py (ECOSISTEMA)
_GEOGRAFIA = {
    "Bolívar": ["San Pablo", "Santa Rosa del Sur"],
}


@router.get("/geografia")
def geografia():
    """Departamentos y municipios disponibles para el filtro del censo."""
    return _GEOGRAFIA


def _query_base(db: Session, departamento: str | None, municipio: str | None):
    q = db.query(RegistroCenso)
    if departamento:
        q = q.filter(RegistroCenso.departamento == departamento)
    if municipio:
        q = q.filter(RegistroCenso.municipio == municipio)
    return q


@router.get("/resumen")
def resumen(departamento: str | None = None, municipio: str | None = None, db: Session = Depends(get_db)):
    """KPIs agregados del censo para el filtro territorial seleccionado."""
    registros = _query_base(db, departamento, municipio).all()
    total = len(registros)
    if total == 0:
        raise HTTPException(404, "Sin registros para ese filtro. Ejecuta: python seed_data.py")

    fuera_sistema = sum(1 for r in registros if not r.estudia)
    en_riesgo = sum(1 for r in registros if r.zona_riesgo)
    doble_vulnerabilidad = sum(1 for r in registros if r.zona_riesgo and not r.estudia)
    sin_contactar = sum(
        1 for r in registros
        if r.estado_seguimiento == "Sin contactar" and (r.zona_riesgo or not r.estudia)
    )
    return {
        "total_jovenes": total,
        "fuera_sistema_educativo": fuera_sistema,
        "pct_fuera_sistema": round(100 * fuera_sistema / total, 1),
        "en_zona_riesgo": en_riesgo,
        "pct_zona_riesgo": round(100 * en_riesgo / total, 1),
        "doble_vulnerabilidad": doble_vulnerabilidad,
        "alertas_sin_contactar": sin_contactar,
    }


@router.get("/jovenes")
def jovenes(
    departamento: str | None = None,
    municipio: str | None = None,
    categoria: str = Query("todos", pattern="^(todos|fuera_sistema|zona_riesgo)$"),
    db: Session = Depends(get_db),
):
    """Listado de jóvenes censados, opcionalmente filtrado por categoría:
    - fuera_sistema: jóvenes en casa que no se encuentran estudiando
    - zona_riesgo: jóvenes que sí estudian pero viven en zona con alerta activa
    """
    registros = _query_base(db, departamento, municipio).all()
    if categoria == "fuera_sistema":
        registros = [r for r in registros if not r.estudia]
    elif categoria == "zona_riesgo":
        registros = [r for r in registros if r.zona_riesgo]

    return [
        {
            "id": r.id, "nombre": r.nombre, "edad": r.edad, "sexo": r.sexo,
            "departamento": r.departamento, "municipio": r.municipio, "zona": r.zona,
            "barrio_vereda": r.barrio_vereda, "nivel_sisben": r.nivel_sisben,
            "estudia": r.estudia, "motivo_no_estudia": r.motivo_no_estudia, "colegio": r.colegio,
            "zona_riesgo": r.zona_riesgo,
            "tipo_alerta": r.tipo_alerta.split("|") if r.tipo_alerta else [],
            "ultimo_contacto": r.ultimo_contacto.isoformat() if r.ultimo_contacto else None,
            "estado_seguimiento": r.estado_seguimiento,
        }
        for r in registros
    ]


@router.get("/zonas")
def zonas(departamento: str | None = None, municipio: str | None = None, db: Session = Depends(get_db)):
    """Ranking de barrios/veredas con más jóvenes FUERA del sistema educativo
    (dónde debería abrir cobertura la Secretaría) + alertas de protección."""
    from collections import defaultdict
    registros = _query_base(db, departamento, municipio).all()
    agg = defaultdict(lambda: {"total": 0, "fuera": 0, "alertas": 0, "zona": ""})
    for r in registros:
        d = agg[r.barrio_vereda]
        d["total"] += 1
        d["zona"] = r.zona
        if not r.estudia:
            d["fuera"] += 1
        if r.zona_riesgo:
            d["alertas"] += 1
    out = [{
        "barrio_vereda": k, "zona": v["zona"], "total": v["total"], "fuera": v["fuera"],
        "pct_fuera": round(100 * v["fuera"] / v["total"], 1) if v["total"] else 0,
        "alertas": v["alertas"],
    } for k, v in agg.items()]
    out.sort(key=lambda x: (-x["fuera"], -x["pct_fuera"]))
    return out


# ═════════ CENSO PRO: gestión de jóvenes + cruce con instituciones (punto 13) ═════════
from datetime import date as _dc, datetime as _dtc
from pydantic import BaseModel as _BMC
from models import (Estudiante as _EstC, Salon as _SalC, Institucion as _InsC,
                    MensajeWhatsApp as _WaC)
import metadatos as _metac


@router.get("/jovenes")
def jovenes(municipio: str | None = None, filtro: str | None = None,
            db: Session = Depends(get_db)):
    q = _query_base(db, None, municipio)
    filas = q.all()
    out = []
    for r in filas:
        if filtro == "fuera" and r.estudia:
            continue
        if filtro == "riesgo" and not r.zona_riesgo:
            continue
        if filtro == "sin_contactar" and r.estado_seguimiento != "Sin contactar":
            continue
        out.append({
            "id": r.id, "nombre": r.nombre, "edad": r.edad, "sexo": r.sexo,
            "zona": r.zona, "barrio_vereda": r.barrio_vereda, "nivel_sisben": r.nivel_sisben,
            "estudia": bool(r.estudia), "motivo": r.motivo_no_estudia, "colegio": r.colegio,
            "zona_riesgo": bool(r.zona_riesgo), "tipo_alerta": r.tipo_alerta,
            "ultimo_contacto": r.ultimo_contacto.isoformat() if r.ultimo_contacto else None,
            "estado": r.estado_seguimiento, "municipio": r.municipio,
        })
    out.sort(key=lambda x: (x["estudia"], x["estado"] != "Sin contactar", -x["edad"]))
    return out[:200]


class _JovenIn(_BMC):
    id: int | None = 0
    nombre: str
    edad: int
    sexo: str | None = "M"
    municipio: str
    departamento: str | None = "Bolívar"
    zona: str | None = "urbana"
    barrio_vereda: str | None = ""
    nivel_sisben: str | None = "B1"
    estudia: bool | None = False
    motivo_no_estudia: str | None = ""
    zona_riesgo: bool | None = False
    tipo_alerta: str | None = ""
    estado_seguimiento: str | None = "Sin contactar"


@router.post("/guardar")
def joven_guardar(payload: _JovenIn, db: Session = Depends(get_db)):
    if not payload.nombre.strip():
        return {"ok": False, "msg": "El nombre es obligatorio."}
    if payload.id:
        r = db.query(RegistroCenso).filter(RegistroCenso.id == payload.id).first()
        if not r:
            return {"ok": False, "msg": "Registro no encontrado."}
    else:
        r = RegistroCenso(departamento=payload.departamento or "Bolívar",
                          estado_seguimiento="Sin contactar")
        db.add(r)
    r.nombre = payload.nombre.strip()
    r.edad = max(10, min(19, payload.edad))
    r.sexo = payload.sexo if payload.sexo in ("M", "F") else "M"
    r.municipio = payload.municipio.strip()
    r.zona = payload.zona if payload.zona in ("urbana", "rural") else "urbana"
    r.barrio_vereda = payload.barrio_vereda or ""
    r.nivel_sisben = payload.nivel_sisben or "B1"
    r.estudia = bool(payload.estudia)
    r.motivo_no_estudia = None if r.estudia else (payload.motivo_no_estudia or "Sin información")
    r.zona_riesgo = bool(payload.zona_riesgo)
    r.tipo_alerta = payload.tipo_alerta or None
    if payload.estado_seguimiento in ("Sin contactar", "En seguimiento", "Cerrado"):
        r.estado_seguimiento = payload.estado_seguimiento
    db.commit()
    _metac.registrar_evento("CENSO_REGISTRO", "Secretaría", payload={"municipio": r.municipio})
    return {"ok": True, "msg": f"Registro de {r.nombre.split()[0]} guardado en el censo.", "id": r.id}


class _IdC(_BMC):
    id: int


@router.post("/contactar")
def joven_contactar(payload: _IdC, db: Session = Depends(get_db)):
    r = db.query(RegistroCenso).filter(RegistroCenso.id == payload.id).first()
    if not r:
        return {"ok": False, "msg": "Registro no encontrado."}
    db.add(_WaC(destinatario=f"Familia de {r.nombre}", telefono="3XX XXX XXXX",
                contenido=(f"Buen día. La Secretaría de Educación quiere ayudar a que "
                           f"{r.nombre.split()[0]} regrese al colegio: hay cupo, transporte y "
                           "apoyo disponibles. ¿Podemos visitarlos esta semana? — Secretaría de Educación"),
                fecha=_dtc.now(), estado="ENVIADO (simulado)", contexto="censo"))
    r.ultimo_contacto = _dc.today()
    if r.estado_seguimiento == "Sin contactar":
        r.estado_seguimiento = "En seguimiento"
    db.commit()
    _metac.registrar_evento("CENSO_CONTACTO", "Secretaría")
    return {"ok": True, "msg": f"📱 Mensaje de acercamiento enviado (simulado) a la familia de {r.nombre.split()[0]}. Estado → En seguimiento, contacto registrado hoy."}


class _MatricularIn(_BMC):
    id: int
    institucion_id: int


@router.post("/matricular")
def joven_matricular(payload: _MatricularIn, db: Session = Depends(get_db)):
    """El cruce en acción: un joven del censo entra al sistema escolar. Se crea
    su matrícula en la institución elegida (salón según su edad) y el registro
    del censo queda cerrado y vinculado."""
    r = db.query(RegistroCenso).filter(RegistroCenso.id == payload.id).first()
    if not r:
        return {"ok": False, "msg": "Registro no encontrado."}
    if r.estudia:
        return {"ok": False, "msg": f"{r.nombre.split()[0]} ya figura estudiando en {r.colegio or 'un colegio'}."}
    ie = db.query(_InsC).filter(_InsC.id == payload.institucion_id).first()
    if not ie:
        return {"ok": False, "msg": "Institución no encontrada."}
    grado = str(max(6, min(11, r.edad - 6)))   # 12 años→6°, 13→7°... aproximación
    sal = (db.query(_SalC).filter(_SalC.institucion_id == ie.id, _SalC.grado == grado).first()
           or db.query(_SalC).filter(_SalC.institucion_id == ie.id).first())
    est = _EstC(institucion_id=ie.id, salon_id=sal.id if sal else None,
                nombre=r.nombre, grado=grado, nivel_sisben=r.nivel_sisben,
                zona=r.zona, acudiente=f"Acudiente de {r.nombre.split()[0]}", parentesco="Acudiente",
                telefono="3XX XXX XXXX", direccion="", barrio_vereda=r.barrio_vereda,
                fecha_ingreso=_dc.today())
    db.add(est)
    r.estudia = True
    r.colegio = ie.nombre
    r.motivo_no_estudia = None
    r.estado_seguimiento = "Cerrado"
    r.ultimo_contacto = _dc.today()
    db.commit()
    _metac.registrar_evento("CENSO_MATRICULA", "Secretaría", institucion_id=ie.id,
                            payload={"grado": grado})
    return {"ok": True, "msg": f"🎒 ¡{r.nombre.split()[0]} matriculado(a) en {ie.nombre} (grado {grado}{', salón ' + sal.nombre if sal else ''})! El censo quedó cruzado con la matrícula y el caso cerrado."}


@router.get("/cruce")
def cruce(municipio: str | None = None, db: Session = Depends(get_db)):
    """Cruce censo ↔ instituciones: qué dice el censo vs la matrícula real de
    cada colegio (el detector de brechas de cobertura)."""
    registros = _query_base(db, None, municipio).all()
    if not municipio and registros:
        municipio = registros[0].municipio
        registros = [r for r in registros if r.municipio == municipio]
    por_colegio = {}
    for r in registros:
        if r.estudia and r.colegio:
            por_colegio[r.colegio] = por_colegio.get(r.colegio, 0) + 1
    out = []
    for ie in db.query(_InsC).filter(_InsC.municipio == municipio).all():
        matricula = db.query(_EstC).filter(_EstC.institucion_id == ie.id).count()
        censados = por_colegio.get(ie.nombre, 0)
        out.append({"institucion": ie.nombre, "matricula_real": matricula,
                    "censados_dicen_estudiar": censados,
                    "cobertura_censo_pct": round(100 * censados / matricula, 1) if matricula else 0})
    fuera = sum(1 for r in registros if not r.estudia)
    total = len(registros)
    return {"municipio": municipio, "total_censados": total, "fuera_sistema": fuera,
            "matriculados_via_censo": sum(1 for r in registros if r.estado_seguimiento == "Cerrado" and r.estudia),
            "colegios": out}
