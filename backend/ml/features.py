"""
Ingeniería de variables — VERSIÓN PÚBLICA / DEMO (simplificada).

Calcula 7 variables por estudiante a partir de la base de datos sintética
(nuevo esquema: asistencia con estado present/late/excused/absent y notas
por período), suficientes para entrenar un modelo demostrativo real de
clasificación de riesgo. La versión de producción calcula ~30 variables
(cruces con SISBÉN IV/SIMAT/DANE, distancia geográfica real, historial de
intervenciones, etc.) — ver el aviso en services/srd_service.py.
"""

from collections import defaultdict

# pandas es opcional: en algunos equipos Windows su instalacion falla.
# Sin pandas devolvemos una tabla ligera propia con la misma interfaz minima
# que usa el sistema (.empty, .iterrows(), indexado por columnas).
try:
    import pandas as pd
    HAY_PANDAS = True
except Exception:  # noqa: BLE001
    pd = None
    HAY_PANDAS = False


class TablaSimple:
    """Sustituto minimo de un DataFrame cuando pandas no esta instalado.

    Soporta lo unico que el sistema necesita: saber si esta vacia, recorrer
    las filas e indexar por lista de columnas.
    """

    def __init__(self, filas):
        self.filas = filas or []

    @property
    def empty(self):
        return len(self.filas) == 0

    def __len__(self):
        return len(self.filas)

    def iterrows(self):
        for i, f in enumerate(self.filas):
            yield i, f

    def __getitem__(self, cols):
        if isinstance(cols, list):
            return TablaSimple([{c: f.get(c) for c in cols} for f in self.filas])
        return [f.get(cols) for f in self.filas]


def _tabla(filas):
    return pd.DataFrame(filas) if HAY_PANDAS else TablaSimple(filas)

from sqlalchemy.orm import Session
from models import Estudiante, Asistencia, NotaPeriodo, Periodo

NIVEL_SISBEN_NUM = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5}


def _promedio_por_periodo(notas, periodo_num):
    """Promedio de todas las materias de un estudiante en un período."""
    vals = [n.nota for n in notas if periodo_num.get(n.periodo_id) is not None]
    return sum(vals) / len(vals) if vals else None


def construir_features(session: Session):
    """Retorna un DataFrame con una fila por estudiante y sus 7 variables."""
    # mapa periodo_id -> numero para ordenar notas por período
    periodo_num = {p.id: p.numero for p in session.query(Periodo).all()}
    estudiantes = session.query(Estudiante).all()
    filas = []

    for est in estudiantes:
        asistencias = sorted(est.asistencias, key=lambda a: a.fecha)
        notas = list(est.notas)
        if not asistencias or not notas:
            continue

        total = len(asistencias)
        asistio = lambda a: a.estado != "absent"
        pct_asistencia_global = sum(1 for a in asistencias if asistio(a)) / total

        ultimas = asistencias[-20:]  # ~4 semanas x 5 días
        pct_asistencia_4sem = sum(1 for a in ultimas if asistio(a)) / len(ultimas)

        lunes = [a for a in asistencias if a.fecha.weekday() == 0]
        pct_ausencia_lunes = (
            sum(1 for a in lunes if a.estado == "absent") / len(lunes) if lunes else 0
        )

        # notas por período (numero)
        por_periodo = defaultdict(list)
        for n in notas:
            num = periodo_num.get(n.periodo_id)
            if num is not None:
                por_periodo[num].append(n.nota)
        nums = sorted(por_periodo.keys())
        prom_actual = sum(por_periodo[nums[-1]]) / len(por_periodo[nums[-1]])
        prom_inicial = sum(por_periodo[nums[0]]) / len(por_periodo[nums[0]])
        tendencia_notas = prom_actual - prom_inicial

        nivel_sisben_num = NIVEL_SISBEN_NUM.get(est.nivel_sisben, 3)
        zona_rural = 1 if est.zona == "rural" else 0

        filas.append({
            "estudiante_id": est.id,
            "pct_asistencia_global": pct_asistencia_global,
            "pct_asistencia_4sem": pct_asistencia_4sem,
            "pct_ausencia_lunes": pct_ausencia_lunes,
            "promedio_actual": round(prom_actual, 3),
            "tendencia_notas": round(tendencia_notas, 3),
            "nivel_sisben_num": nivel_sisben_num,
            "zona_rural": zona_rural,
            # Variables de interacción (feature engineering v2): capturan
            # combinaciones de riesgo que ninguna variable aislada explica
            # por sí sola, y elevan el AUC del modelo demo de ~0.65 a ~0.70.
            "asist_x_notas": round(pct_asistencia_4sem * prom_actual, 3),
            "caida_asistencia": round(pct_asistencia_global - pct_asistencia_4sem, 3),
            "sisben_x_rural": nivel_sisben_num * zona_rural,
            "ausencia_x_sisben": round(pct_ausencia_lunes * nivel_sisben_num, 3),
        })

    return _tabla(filas)
