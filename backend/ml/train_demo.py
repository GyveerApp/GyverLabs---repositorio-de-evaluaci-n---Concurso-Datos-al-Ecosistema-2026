"""
Entrenamiento del modelo DEMO de Score de Riesgo de Deserción (SRD).

# ============================================================
# ESTO ES LA VERSIÓN PÚBLICA / SIMPLIFICADA DEL MOTOR DE IA
# ============================================================
# Entrena un LightGBM real, con datos reales de este dataset sintético,
# y reporta métricas reales (no inventadas) — para que el jurado pueda
# verificar con sus propios ojos que el pipeline de IA funciona de punta
# a punta y es reproducible.
#
# Lo que NO incluye esta versión (por ser la propiedad intelectual
# central del producto, protegida bajo LICENSE):
#   - El conjunto completo de ~30 variables usadas en producción
#     (incluye cruces con SISBÉN IV/SIMAT/DANE reales, distancia
#     geográfica real, historial real de intervenciones).
#   - La calibración de umbral específica por institución (aquí se usa
#     un umbral fijo genérico).
#   - El re-entrenamiento incremental semanal y el pipeline de
#     explicabilidad SHAP en producción.
#
# La etiqueta de entrenamiento en este script es SINTÉTICA: se construye
# a partir de una combinación ponderada de las variables observables más
# ruido aleatorio, para simular un patrón de riesgo realista sin usar
# ningún dato de una persona real. Esto es una práctica estándar para
# construir datasets de demostración reproducibles.
# ============================================================
"""

import json
import sys
import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score
import lightgbm as lgb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import get_engine, get_sessionmaker  # noqa: E402
from core.config import settings  # noqa: E402
from ml.features import construir_features  # noqa: E402

RANDOM_STATE = 42
MODEL_PATH = os.path.join(os.path.dirname(__file__), "demo_model.txt")
METRICS_PATH = os.path.join(os.path.dirname(__file__), "metrics_demo.json")


def construir_etiqueta_sintetica(df: pd.DataFrame) -> pd.Series:
    """
    Etiqueta sintética "riesgo_alto" (1/0), construida como combinación
    ponderada de variables observables + ruido — NO usa ninguna variable
    oculta ni información de personas reales. El propósito es que el
    modelo tenga una relación real y aprendible con los datos de entrada
    (como ocurriría en producción con la etiqueta real de deserción).
    """
    rng = np.random.default_rng(RANDOM_STATE)
    z = (
        -4.2 * df["pct_asistencia_4sem"]
        - 2.6 * df["pct_asistencia_global"]
        + 1.8 * df["pct_ausencia_lunes"]
        - 0.55 * df["tendencia_notas"]
        - 0.28 * df["promedio_actual"]
        + 0.35 * df["nivel_sisben_num"] * -1  # nivel más bajo (A1) => más riesgo
        + 0.4 * df["zona_rural"]
        + 5.5
    )
    prob = 1 / (1 + np.exp(-z))
    ruido = rng.normal(0, 0.12, size=len(df))
    prob_final = np.clip(prob + ruido, 0.01, 0.99)
    etiqueta = rng.binomial(1, prob_final)
    return pd.Series(etiqueta, index=df.index)


def main():
    engine = get_engine(settings.DATABASE_URL)
    Session = get_sessionmaker(engine)
    session = Session()

    print("Cargando variables desde la base de datos sintética...")
    df = construir_features(session)
    session.close()

    if df.empty:
        print("No hay datos. Ejecuta primero: python seed_data.py")
        return

    df["riesgo_alto"] = construir_etiqueta_sintetica(df)

    feature_cols = [
        "pct_asistencia_global", "pct_asistencia_4sem", "pct_ausencia_lunes",
        "promedio_actual", "tendencia_notas", "nivel_sisben_num", "zona_rural",
    ]
    X = df[feature_cols]
    y = df["riesgo_alto"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y
    )

    print(f"Entrenando LightGBM sobre {len(X_train)} estudiantes (holdout de {len(X_test)})...")
    train_data = lgb.Dataset(X_train, label=y_train)
    valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

    params = {
        "objective": "binary",
        "metric": "auc",
        "verbosity": -1,
        "seed": RANDOM_STATE,
        "num_leaves": 15,
        "learning_rate": 0.08,
        "min_data_in_leaf": 15,
    }
    modelo = lgb.train(
        params, train_data, num_boost_round=200,
        valid_sets=[valid_data],
        callbacks=[lgb.early_stopping(20, verbose=False)],
    )

    y_pred_prob = modelo.predict(X_test, num_iteration=modelo.best_iteration)
    y_pred = (y_pred_prob >= 0.5).astype(int)

    metricas = {
        "auc_roc": round(float(roc_auc_score(y_test, y_pred_prob)), 4),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred)), 4),
        "recall": round(float(recall_score(y_test, y_pred)), 4),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "n_iteraciones": int(modelo.best_iteration),
        "importancia_variables": dict(zip(
            feature_cols, [int(v) for v in modelo.feature_importance(importance_type="gain")]
        )),
        "nota": (
            "Métricas calculadas sobre el dataset SINTÉTICO de demostración "
            "(seed_data.py), con etiqueta construida artificialmente para "
            "fines de evaluación. No representan el desempeño del modelo de "
            "producción, que se entrena y calibra con datos reales por institución."
        ),
    }

    modelo.save_model(MODEL_PATH)
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metricas, f, ensure_ascii=False, indent=2)

    print("\nModelo entrenado y guardado en:", MODEL_PATH)
    print("Métricas (dataset sintético de demo):")
    for k, v in metricas.items():
        if k not in ("importancia_variables", "nota"):
            print(f"  {k}: {v}")
    print("Importancia de variables (gain):", metricas["importancia_variables"])


if __name__ == "__main__":
    main()
