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

# Debe reflejar las mismas llaves que GEOGRAFIA_CENSO en seed_data.py
_GEOGRAFIA = {
    "Santander": ["Bucaramanga", "Barrancabermeja", "Puerto Wilches", "Floridablanca"],
    "Bolívar": ["San Pablo", "Santa Rosa del Sur", "Simití", "Cartagena"],
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
