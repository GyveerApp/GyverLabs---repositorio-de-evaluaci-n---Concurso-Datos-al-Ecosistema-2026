"""
Servicio de cálculo del Score de Riesgo de Deserción (SRD).

# ============================================================
# IMPLEMENTACIÓN PROTEGIDA — VERSIÓN PÚBLICA/DEMO A CONTINUACIÓN
# ============================================================
# La versión de producción de este servicio:
#   1. Extrae ~30 variables por estudiante (asistencia acumulada,
#      tendencia de notas, edad-grado, distancia geográfica al
#      plantel, variables socioeconómicas cuando el colegio
#      autoriza el cruce con fuentes como SISBÉN IV/SIMAT/DANE,
#      historial de intervenciones previas, entre otras).
#   2. Normaliza esas variables con el pipeline de `ml/features.py`
#      de producción (distinto del `ml/features.py` público de este
#      repositorio, que solo calcula 7 variables básicas).
#   3. Corre un modelo LightGBM entrenado y RE-CALIBRADO por institución
#      (umbral ajustado con el coordinador según su histórico real).
#   4. Genera la explicación de factores con SHAP values.
#   5. Se re-entrena de forma incremental cada semana (core/scheduler.py).
#
# Lo que SÍ hace esta versión pública: corre un LightGBM real,
# entrenado con `ml/train_demo.py` sobre el dataset 100% sintético de
# `seed_data.py`, y sirve sus predicciones reales sobre esos estudiantes
# de demostración. El contrato de datos (inputs/outputs de la API) es
# idéntico al de producción — lo que cambia es el conjunto de variables,
# la calibración y el origen de los datos.
# ============================================================
"""

import os
import lightgbm as lgb

_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "demo_model.txt")
_modelo = None

UMBRAL_CRITICO = 0.45
UMBRAL_MODERADO = 0.30
UMBRAL_LEVE = 0.18


def _cargar_modelo():
    global _modelo
    if _modelo is None:
        if not os.path.exists(_MODEL_PATH):
            raise RuntimeError(
                "No se encontró el modelo demo entrenado. Ejecuta primero: "
                "python ml/train_demo.py (después de python seed_data.py)."
            )
        _modelo = lgb.Booster(model_file=_MODEL_PATH)
    return _modelo


def _nivel_desde_score(score: float) -> str:
    if score >= UMBRAL_CRITICO:
        return "CRÍTICO"
    if score >= UMBRAL_MODERADO:
        return "MODERADO"
    if score >= UMBRAL_LEVE:
        return "LEVE"
    return "SIN RIESGO"


def _factores(row: dict) -> list[str]:
    factores = []
    if row["pct_asistencia_4sem"] < 0.85:
        factores.append(f"Asistencia del {round(row['pct_asistencia_4sem']*100)}% en las últimas 4 semanas")
    if row["pct_ausencia_lunes"] > 0.15:
        factores.append("Patrón de inasistencia concentrado los lunes")
    if row["tendencia_notas"] < -0.3:
        factores.append("Caída sostenida en el promedio académico")
    if row["nivel_sisben_num"] <= 2:
        factores.append("Hogar clasificado en SISBEN A1/A2")
    if row["zona_rural"] == 1:
        factores.append("Ubicación en zona rural con menor conectividad")
    if not factores:
        factores.append("Sin señales de riesgo relevantes esta semana")
    return factores[:3]


def calcular_srd_para_dataframe(df):
    """Corre el modelo demo sobre un DataFrame de features (ver ml/features.py)."""
    modelo = _cargar_modelo()
    cols = [
        "pct_asistencia_global", "pct_asistencia_4sem", "pct_ausencia_lunes",
        "promedio_actual", "tendencia_notas", "nivel_sisben_num", "zona_rural",
    ]
    scores = modelo.predict(df[cols])
    resultados = []
    for i, (_, row) in enumerate(df.iterrows()):
        score = float(scores[i])
        resultados.append({
            "estudiante_id": int(row["estudiante_id"]),
            "score": round(score, 3),
            "nivel": _nivel_desde_score(score),
            "factores": _factores(row.to_dict()),
        })
    return resultados
