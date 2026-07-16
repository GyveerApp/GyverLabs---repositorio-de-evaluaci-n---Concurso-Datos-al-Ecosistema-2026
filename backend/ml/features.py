"""
Ingeniería de variables — VERSIÓN PÚBLICA / DEMO (simplificada).

Calcula 6 variables por estudiante a partir de la base de datos sintética,
suficientes para entrenar un modelo demostrativo real de clasificación de
riesgo. La versión de producción calcula ~30 variables (incluye variables
de cruce con fuentes externas como SISBÉN IV/SIMAT/DANE cuando la
institución lo autoriza, historial de intervenciones, distancia geográfica
real, etc.) — ver el aviso en services/srd_service.py.
"""

from collections import defaultdict
from datetime import timedelta
import pandas as pd

from sqlalchemy.orm import Session
from models import Estudiante, Asistencia, Nota

NIVEL_SISBEN_NUM = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5}


def construir_features(session: Session) -> pd.DataFrame:
    """Retorna un DataFrame con una fila por estudiante y sus variables."""
    estudiantes = session.query(Estudiante).all()
    filas = []

    for est in estudiantes:
        asistencias = sorted(est.asistencias, key=lambda a: a.fecha)
        notas = sorted(est.notas, key=lambda n: n.semana)

        if not asistencias or not notas:
            continue

        total = len(asistencias)
        presentes = sum(1 for a in asistencias if a.presente)
        pct_asistencia_global = presentes / total

        ultimas_4_semanas = asistencias[-20:]  # 4 semanas x 5 días
        presentes_4s = sum(1 for a in ultimas_4_semanas if a.presente)
        pct_asistencia_4sem = presentes_4s / len(ultimas_4_semanas)

        lunes = [a for a in asistencias if a.fecha.weekday() == 0]
        pct_ausencia_lunes = (
            1 - (sum(1 for a in lunes if a.presente) / len(lunes)) if lunes else 0
        )

        promedio_actual = notas[-1].promedio
        promedio_inicial = notas[0].promedio
        tendencia_notas = promedio_actual - promedio_inicial  # negativo = cae

        filas.append({
            "estudiante_id": est.id,
            "pct_asistencia_global": pct_asistencia_global,
            "pct_asistencia_4sem": pct_asistencia_4sem,
            "pct_ausencia_lunes": pct_ausencia_lunes,
            "promedio_actual": promedio_actual,
            "tendencia_notas": tendencia_notas,
            "nivel_sisben_num": NIVEL_SISBEN_NUM.get(est.nivel_sisben, 3),
            "zona_rural": 1 if est.zona == "rural" else 0,
        })

    return pd.DataFrame(filas)
