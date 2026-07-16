from datetime import date
from collections import defaultdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Asistencia

router = APIRouter()


class AsistenciaRegistrar(BaseModel):
    estudiante_id: int
    fecha: date
    presente: bool
    observacion: str | None = None


@router.post("/registrar")
def registrar_asistencia(payload: AsistenciaRegistrar):
    """
    Registra la asistencia diaria de un estudiante.
    Este endpoint es el disparador del pipeline de cálculo del SRD:
    cada registro alimenta las features que consume el motor de IA
    en el job semanal (ver core/scheduler.py en la versión de producción).
    En esta demo no persiste el registro nuevo (la base sintética es de
    solo lectura para mantener resultados reproducibles) — confirma el
    contrato de la API tal como lo usaría el frontend en producción.
    """
    return {"status": "registrado", "estudiante_id": payload.estudiante_id}


@router.get("/resumen")
def resumen_asistencia(db: Session = Depends(get_db)):
    """Asistencia global por semana, para el gráfico de tendencia del dashboard."""
    registros = db.query(Asistencia).all()
    por_semana = defaultdict(lambda: [0, 0])  # semana ISO -> [presentes, total]
    for r in registros:
        semana = r.fecha.isocalendar()[1]
        por_semana[semana][1] += 1
        if r.presente:
            por_semana[semana][0] += 1

    puntos = [
        {"semana": s, "pct_asistencia": round(100 * p / t, 1)}
        for s, (p, t) in sorted(por_semana.items())
    ]
    total = len(registros)
    presentes = sum(1 for r in registros if r.presente)
    return {
        "pct_asistencia_global": round(100 * presentes / total, 1) if total else 0,
        "tendencia_semanal": puntos,
    }
