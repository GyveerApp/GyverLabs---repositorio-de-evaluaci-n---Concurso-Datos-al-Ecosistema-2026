"""
Motor de Inteligencia Artificial — cálculo del SRD por lote.

IMPLEMENTACIÓN PROTEGIDA.
En producción, este script:
  - Carga `model.pkl` (LightGBM, AUC-ROC >= 0.82, ver train.py / evaluate.py)
  - Corre `features.py` sobre todos los tenants activos
  - Escribe los scores en la tabla `srd_scores` de cada schema
  - Se ejecuta semanalmente vía cron (core/scheduler.py)

El modelo entrenado y el pipeline de features no se incluyen en este
repositorio de evaluación. Ver services/srd_service.py para una
implementación de demostración con el mismo contrato de datos.
"""

def predict_batch(tenant_schema: str):
    raise NotImplementedError(
        "Disponible en el ambiente de producción / demo institucional. "
        "Contactar al autor para evaluación técnica ampliada."
    )
