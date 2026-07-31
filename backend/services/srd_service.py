"""
Servicio de cálculo del Score de Riesgo de Deserción (SRD).

# ============================================================
# IMPLEMENTACIÓN PROTEGIDA — VERSIÓN PÚBLICA/DEMO A CONTINUACIÓN
# ============================================================
# La versión de producción de este servicio:
#   1. Extrae ~30 variables por estudiante (asistencia acumulada,
#      tendencia de notas, edad-grado, distancia geográfica al plantel,
#      variables socioeconómicas del cruce autorizado con SISBÉN IV/
#      SIMAT/DANE, historial de intervenciones previas, etc.).
#   2. Normaliza con el pipeline de features de producción.
#   3. Corre un modelo LightGBM entrenado y RE-CALIBRADO por institución.
#   4. Genera la explicación de factores con SHAP values.
#   5. Se re-entrena de forma incremental cada semana.
#
# Lo que SÍ hace esta versión pública: corre un LightGBM real, entrenado
# con ml/train_demo.py sobre el dataset 100% sintético de seed_data.py, y
# combina su predicción con los indicadores operativos que el equipo
# directivo necesita para actuar (faltas acumuladas, notificación a
# padres/rectoría e intervención). El contrato de datos es idéntico al de
# producción — cambian el conjunto de variables, la calibración y el origen.
# ============================================================
"""

import os
from datetime import datetime

# LightGBM es opcional: en algunos equipos Windows su instalacion falla.
# Si no esta disponible, el sistema sigue funcionando con un modelo de
# respaldo por reglas (misma escala 0-1, misma interfaz). Nada se cae.
try:
    import lightgbm as lgb
    HAY_LIGHTGBM = True
except Exception:  # noqa: BLE001
    lgb = None
    HAY_LIGHTGBM = False

from models import Estudiante, Asistencia, NotaPeriodo, Periodo, SRDScore, SRDLog
from ml.features import construir_features, NIVEL_SISBEN_NUM

_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "demo_model.txt")
_modelo = None

UMBRAL_CRITICO = 0.45
UMBRAL_MODERADO = 0.30
UMBRAL_LEVE = 0.18

# Los umbrales anteriores son los "de diseño" del producto. Como el modelo
# demo se re-entrena sobre datos sintéticos y su escala de probabilidad varía,
# el tablero calibra los cortes por PERCENTIL del lote actual (top ~8%
# crítico, siguiente ~16% moderado, siguiente ~26% leve). Así la priorización
# es estable y siempre hay casos que mostrar, sea cual sea la escala del modelo.
_CORTES = {"critico": UMBRAL_CRITICO, "moderado": UMBRAL_MODERADO, "leve": UMBRAL_LEVE}


def _calibrar_cortes(scores):
    xs = sorted(scores, reverse=True)
    n = len(xs)
    if n < 12:
        return
    # percentiles: 8% / 24% / 50%
    _CORTES["critico"] = xs[max(1, int(n * 0.08)) - 1]
    _CORTES["moderado"] = xs[max(1, int(n * 0.24)) - 1]
    _CORTES["leve"] = xs[max(1, int(n * 0.50)) - 1]

FEATURE_COLS = [
    "pct_asistencia_global", "pct_asistencia_4sem", "pct_ausencia_lunes",
    "promedio_actual", "tendencia_notas", "nivel_sisben_num", "zona_rural",
]


class _ModeloReglas:
    """Modelo de respaldo cuando LightGBM no esta instalado.

    Reproduce la lógica que el árbol aprende: el riesgo sube cuando baja la
    asistencia (sobre todo la reciente), cuando el promedio es bajo, cuando la
    tendencia de notas cae y cuando hay vulnerabilidad socioeconómica o rural.
    Devuelve una probabilidad 0-1 con la misma interfaz `.predict(df)`.
    """

    nombre = "reglas"

    def predict(self, df):
        salida = []
        for _, f in df.iterrows():
            asis_glob = float(f.get("pct_asistencia_global", 100)) / 100.0
            asis_4s = float(f.get("pct_asistencia_4sem", 100)) / 100.0
            lunes = float(f.get("pct_ausencia_lunes", 0)) / 100.0
            prom = float(f.get("promedio_actual", 5) or 5)
            tend = float(f.get("tendencia_notas", 0) or 0)
            sisben = float(f.get("nivel_sisben_num", 3) or 3)
            rural = float(f.get("zona_rural", 0) or 0)

            r = 0.0
            r += (1 - asis_4s) * 0.42          # la ausencia reciente es la señal más fuerte
            r += (1 - asis_glob) * 0.18        # la ausencia acumulada refuerza
            r += lunes * 0.08                  # patrón de faltar los lunes
            r += max(0.0, (3.5 - prom) / 3.5) * 0.22   # rendimiento bajo
            r += max(0.0, -tend) * 0.06        # notas cayendo entre períodos
            r += max(0.0, (3 - sisben)) / 3 * 0.05     # vulnerabilidad socioeconómica
            r += rural * 0.03                  # distancia/transporte
            salida.append(min(1.0, max(0.0, r)))
        return salida


def _cargar_modelo():
    global _modelo
    if _modelo is None:
        if HAY_LIGHTGBM and os.path.exists(_MODEL_PATH):
            _modelo = lgb.Booster(model_file=_MODEL_PATH)
        else:
            # Sin LightGBM (o sin modelo entrenado) usamos el respaldo por reglas.
            _modelo = _ModeloReglas()
    return _modelo


def modelo_en_uso():
    """Informa qué motor está activo (para mostrarlo en Datos & IA)."""
    m = _cargar_modelo()
    return "reglas" if isinstance(m, _ModeloReglas) else "lightgbm"


def _nivel(score: float) -> str:
    if score >= _CORTES["critico"]: return "CRÍTICO"
    if score >= _CORTES["moderado"]: return "MODERADO"
    if score >= _CORTES["leve"]: return "LEVE"
    return "SIN RIESGO"


def _factores(est, faltas_rec, pct_asist, promedio, tendencia):
    f = []
    if pct_asist < 85:
        f.append(f"Asistencia del {round(pct_asist)}% en el período reciente")
    if faltas_rec >= 3:
        f.append(f"{faltas_rec} faltas en las últimas 4 semanas")
    if promedio and promedio < 3.0:
        f.append(f"Promedio académico bajo ({promedio:.1f}/5.0)")
    if tendencia <= -0.3:
        f.append(f"Caída sostenida en el promedio ({tendencia:.1f})")
    if est.nivel_sisben in ("A1", "A2"):
        f.append("Hogar clasificado en SISBEN A1/A2")
    if est.zona == "rural":
        f.append("Zona rural con menor conectividad")
    if not f:
        f.append("Sin señales de riesgo relevantes")
    return f[:4]


def _contar_asistencia(session, est_id):
    """Cuenta faltas acumuladas, faltas recientes (4 sem) y % asistencia."""
    filas = session.query(Asistencia).filter(Asistencia.estudiante_id == est_id).all()
    if not filas:
        return 0, 0, 100.0
    filas.sort(key=lambda a: a.fecha)
    total = len(filas)
    faltas_acum = sum(1 for a in filas if a.estado == "absent")
    tard = sum(1 for a in filas if a.estado == "late")
    presente_equiv = sum(1 for a in filas if a.estado in ("present", "excused")) + tard * 0.5
    pct = round(presente_equiv / total * 100, 1)
    recientes = filas[-20:]
    faltas_rec = sum(1 for a in recientes if a.estado == "absent")
    return faltas_acum, faltas_rec, pct


def _promedio_tendencia(session, est_id, periodo_num):
    notas = session.query(NotaPeriodo).filter(NotaPeriodo.estudiante_id == est_id).all()
    if not notas:
        return 0.0, 0.0
    from collections import defaultdict
    pp = defaultdict(list)
    for n in notas:
        num = periodo_num.get(n.periodo_id)
        if num is not None:
            pp[num].append(n.nota)
    nums = sorted(pp.keys())
    prom = round(sum(sum(v) for v in pp.values()) / sum(len(v) for v in pp.values()), 2)
    tend = round(sum(pp[nums[-1]]) / len(pp[nums[-1]]) - sum(pp[nums[0]]) / len(pp[nums[0]]), 2)
    return prom, tend


def recalcular_todos(session, preservar=True):
    """Recalcula el SRD de todos los estudiantes con el modelo + indicadores.
    Preserva las banderas de notificación/intervención existentes.
    OPTIMIZADO: precarga asistencia y notas en memoria (1 query por tabla)
    en lugar de 2 queries por estudiante — pasa de ~60s a ~4s con 676
    estudiantes, clave porque cada guardado de asistencia recalcula."""
    modelo = _cargar_modelo()
    df = construir_features(session)
    if df.empty:
        return 0
    scores = modelo.predict(df[FEATURE_COLS])
    _calibrar_cortes([float(x) for x in scores])
    periodo_num = {p.id: p.numero for p in session.query(Periodo).all()}
    est_by_id = {e.id: e for e in session.query(Estudiante).all()}
    existentes = {r.estudiante_id: r for r in session.query(SRDScore).all()}

    # ── Prefetch masivo ──
    from collections import defaultdict
    asis_por_est = defaultdict(list)
    for a in session.query(Asistencia.estudiante_id, Asistencia.fecha, Asistencia.estado).all():
        asis_por_est[a.estudiante_id].append((a.fecha, a.estado))
    for lst in asis_por_est.values():
        lst.sort(key=lambda x: x[0])
    notas_por_est = defaultdict(lambda: defaultdict(list))
    for n in session.query(NotaPeriodo.estudiante_id, NotaPeriodo.periodo_id, NotaPeriodo.nota).all():
        num = periodo_num.get(n.periodo_id)
        if num is not None:
            notas_por_est[n.estudiante_id][num].append(n.nota)

    def _asis_mem(eid):
        filas = asis_por_est.get(eid, [])
        if not filas:
            return 0, 0, 100.0
        total = len(filas)
        faltas_acum = sum(1 for _, e in filas if e == "absent")
        tard = sum(1 for _, e in filas if e == "late")
        presente_equiv = sum(1 for _, e in filas if e in ("present", "excused")) + tard * 0.5
        pct = round(presente_equiv / total * 100, 1)
        faltas_rec = sum(1 for _, e in filas[-20:] if e == "absent")
        return faltas_acum, faltas_rec, pct

    def _notas_mem(eid):
        pp = notas_por_est.get(eid)
        if not pp:
            return 0.0, 0.0
        nums = sorted(pp.keys())
        prom = round(sum(sum(v) for v in pp.values()) / sum(len(v) for v in pp.values()), 2)
        tend = round(sum(pp[nums[-1]]) / len(pp[nums[-1]]) - sum(pp[nums[0]]) / len(pp[nums[0]]), 2)
        return prom, tend

    n = 0
    for i, (_, row) in enumerate(df.iterrows()):
        eid = int(row["estudiante_id"])
        est = est_by_id.get(eid)
        if not est:
            continue
        score = round(float(scores[i]), 3)
        faltas_acum, faltas_rec, pct = _asis_mem(eid)
        prom, tend = _notas_mem(eid)
        factores = _factores(est, faltas_rec, pct, prom, tend)

        rec = existentes.get(eid)
        if rec is None:
            rec = SRDScore(estudiante_id=eid)
            session.add(rec)
        rec.score = score
        rec.nivel = _nivel(score)
        rec.faltas_acumuladas = faltas_acum
        rec.faltas_recientes = faltas_rec
        rec.pct_asistencia = pct
        rec.promedio = prom
        rec.tendencia = tend
        rec.factores = " | ".join(factores)
        if not preservar or rec.notificado_padre is None:
            rec.notificado_padre = rec.notificado_padre or False
        n += 1
    session.commit()
    return n


def log(session, est_id, accion, detalle="", actor="Sistema"):
    session.add(SRDLog(estudiante_id=est_id, accion=accion, detalle=detalle,
                       actor=actor, fecha=datetime.now()))
    session.commit()
