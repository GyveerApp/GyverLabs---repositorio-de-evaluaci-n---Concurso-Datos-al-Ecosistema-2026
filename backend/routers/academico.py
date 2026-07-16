from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Estudiante

router = APIRouter()


class GradoOut(BaseModel):
    id: int
    nombre: str
    grupos: list[str]


# Estructura académica de ejemplo — en producción viene del modelo
# `academico.py` (SQLAlchemy) dentro del schema de cada tenant.
_GRADOS_DEMO = [
    GradoOut(id=1, nombre="Sexto", grupos=["601"]),
    GradoOut(id=2, nombre="Séptimo", grupos=["701"]),
    GradoOut(id=3, nombre="Octavo", grupos=["801"]),
    GradoOut(id=4, nombre="Noveno", grupos=["901", "902"]),
    GradoOut(id=5, nombre="Décimo", grupos=["1001"]),
]


@router.get("/grados", response_model=list[GradoOut])
def listar_grados():
    """Lista los grados y grupos configurados para el colegio activo (tenant)."""
    return _GRADOS_DEMO


@router.get("/estudiantes")
def listar_estudiantes(grado: str | None = None, db: Session = Depends(get_db)):
    """Lista los estudiantes del colegio de demostración (base sintética)."""
    query = db.query(Estudiante)
    if grado:
        query = query.filter(Estudiante.grado == grado)
    estudiantes = query.all()
    return [
        {"id": e.id, "nombre": e.nombre, "grado": e.grado, "zona": e.zona, "nivel_sisben": e.nivel_sisben}
        for e in estudiantes
    ]
