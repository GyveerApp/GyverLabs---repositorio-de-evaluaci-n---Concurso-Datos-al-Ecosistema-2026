from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Estudiante
from ml.features import construir_features
from services.srd_service import calcular_srd_para_dataframe

router = APIRouter()


def _scores_actuales(db: Session):
    """Calcula el SRD de todos los estudiantes con el modelo demo (en memoria, sin caché)."""
    df = construir_features(db)
    if df.empty:
        raise HTTPException(500, "Base de datos vacía. Ejecuta: python seed_data.py")
    resultados = calcular_srd_para_dataframe(df)
    nombres = {e.id: (e.nombre, e.grado) for e in db.query(Estudiante).all()}
    for r in resultados:
        nombre, grado = nombres.get(r["estudiante_id"], ("Desconocido", "-"))
        r["nombre"] = nombre
        r["grado"] = grado
    return resultados


@router.get("/tablero")
def tablero(db: Session = Depends(get_db)):
    """Mapa de calor: % de estudiantes en riesgo crítico o moderado, por grado."""
    resultados = _scores_actuales(db)
    por_grado = defaultdict(list)
    for r in resultados:
        por_grado[r["grado"]].append(r)

    mapa = []
    for grado, items in sorted(por_grado.items()):
        en_riesgo = sum(1 for i in items if i["nivel"] in ("CRÍTICO", "MODERADO"))
        mapa.append({
            "grado": grado,
            "total_estudiantes": len(items),
            "pct_riesgo": round(100 * en_riesgo / len(items), 1) if items else 0,
        })

    total = len(resultados)
    criticos = sum(1 for r in resultados if r["nivel"] == "CRÍTICO")
    moderados = sum(1 for r in resultados if r["nivel"] == "MODERADO")

    return {
        "total_estudiantes": total,
        "alertas_criticas": criticos,
        "alertas_moderadas": moderados,
        "mapa_calor": mapa,
    }


@router.get("/ranking")
def ranking(limite: int = 30, db: Session = Depends(get_db)):
    """Lista de estudiantes ordenada de mayor a menor riesgo (para el panel del coordinador)."""
    resultados = _scores_actuales(db)
    resultados.sort(key=lambda r: r["score"], reverse=True)
    return resultados[:limite]


@router.get("/{estudiante_id}")
def obtener_srd(estudiante_id: int, db: Session = Depends(get_db)):
    """SRD de un estudiante puntual, con el detalle de factores para el tablero."""
    resultados = _scores_actuales(db)
    for r in resultados:
        if r["estudiante_id"] == estudiante_id:
            return r
    raise HTTPException(404, "Estudiante no encontrado")
