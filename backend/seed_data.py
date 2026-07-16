"""
Generador del conjunto de datos SIMULADO para la demo de evaluación.

Este script llena una base SQLite local (`gyverlabs_demo.db`) con datos
100% sintéticos: ningún estudiante, colegio, docente o cifra corresponde
a una persona o institución real. Los nombres se generan combinando listas
de nombres y apellidos comunes en Colombia, y las variables (asistencia,
notas, SISBEN, zona) se generan con relaciones estadísticas plausibles
para que el modelo demo (ver ml/train_demo.py) tenga patrones reales que
aprender — no ruido puro.

Ejecutar:  python seed_data.py
Es determinístico (semilla fija) — genera siempre el mismo dataset.
"""

import random
from datetime import date, timedelta

from models import (
    Base, Estudiante, Asistencia, Nota, MovimientoFSE, get_engine, get_sessionmaker,
)
from core.config import settings

SEED = 42
random.seed(SEED)

NOMBRES = [
    "Mariana", "Santiago", "Valentina", "Samuel", "Isabella", "Mateo", "Sofía", "Juan",
    "Camila", "Andrés", "Luciana", "David", "Gabriela", "Sebastián", "Salomé", "Nicolás",
    "Antonella", "Emmanuel", "Danna", "Jerónimo", "Yuliana", "Kevin", "Paula", "Cristian",
    "Laura", "Brayan", "Karen", "Miguel", "Daniela", "Julián", "Natalia", "Esteban",
    "Yesenia", "Yeison", "Dayana", "Deiby", "Yuliet", "Anderson", "Leidy", "Jhon",
]
APELLIDOS = [
    "Pérez", "Rodríguez", "Martínez", "López", "García", "Hernández", "González",
    "Torres", "Ramírez", "Flórez", "Suárez", "Ortiz", "Castro", "Vargas", "Rueda",
    "Mendoza", "Peñaranda", "Villamizar", "Gómez", "Cárdenas", "Contreras", "Rojas",
]

GRADOS = ["601", "701", "801", "901", "902", "1001"]
NIVELES_SISBEN = ["A1", "A2", "B1", "B2", "C1"]
N_ESTUDIANTES = 840  # coincide con "842 estudiantes" mostrado en el panel institucional
N_SEMANAS = 12
HOY = date(2026, 7, 10)


def nombre_aleatorio(usados):
    while True:
        n = f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)} {random.choice(APELLIDOS)}"
        if n not in usados:
            usados.add(n)
            return n


def generar_estudiantes(session):
    usados = set()
    estudiantes = []
    for i in range(N_ESTUDIANTES):
        grado = GRADOS[i % len(GRADOS)]
        zona = "rural" if random.random() < 0.32 else "urbana"
        # las zonas rurales tienden a niveles SISBEN más bajos en esta simulación
        nivel = random.choices(
            NIVELES_SISBEN,
            weights=[0.32, 0.28, 0.20, 0.13, 0.07] if zona == "rural" else [0.10, 0.18, 0.27, 0.25, 0.20],
        )[0]

        # "propensión de riesgo" latente: usada solo para generar datos
        # coherentes (no se guarda ni se expone — es un truco de simulación)
        propension = random.betavariate(2, 6)
        if zona == "rural":
            propension = min(1.0, propension + 0.12)
        if nivel in ("A1", "A2"):
            propension = min(1.0, propension + 0.08)

        est = Estudiante(nombre=nombre_aleatorio(usados), grado=grado, nivel_sisben=nivel, zona=zona)
        est._propension = propension  # atributo temporal en memoria, no persistido
        estudiantes.append(est)
        session.add(est)
    session.flush()
    return estudiantes


def generar_asistencia_y_notas(session, estudiantes):
    lunes_inicial = HOY - timedelta(weeks=N_SEMANAS, days=HOY.weekday())
    for est in estudiantes:
        prop = est._propension
        prob_ausencia_base = 0.03 + prop * 0.35  # 3% a 38% según propensión

        promedio_actual = round(random.uniform(3.2, 4.8) - prop * 1.1, 2)
        for semana in range(N_SEMANAS):
            # tendencia: el promedio decae levemente en estudiantes de alta propensión
            promedio_semana = max(1.0, min(5.0, promedio_actual - (prop * semana * 0.03) + random.uniform(-0.15, 0.15)))
            session.add(Nota(estudiante_id=est.id, semana=semana + 1, promedio=round(promedio_semana, 2)))

            for dia in range(5):  # lunes a viernes
                fecha = lunes_inicial + timedelta(weeks=semana, days=dia)
                # los lunes concentran más inasistencia en estudiantes de alta propensión (patrón real observado)
                factor_dia = 1.6 if dia == 0 and prop > 0.5 else 1.0
                presente = random.random() > (prob_ausencia_base * factor_dia)
                session.add(Asistencia(estudiante_id=est.id, fecha=fecha, presente=presente))
    session.commit()


def generar_fse(session):
    conceptos_ingreso = [
        ("Giro SGP — Calidad Gratuidad Educativa", "4110 Transferencias Nación", (18_000_000, 42_000_000)),
        ("Recursos propios — arriendo cafetería escolar", "4295 Otros ingresos", (400_000, 1_200_000)),
        ("Donación empresa local", "4805 Donaciones", (500_000, 2_000_000)),
    ]
    conceptos_gasto = [
        ("Compra material didáctico", "1524 Materiales y suministros", (300_000, 2_500_000)),
        ("Mantenimiento planta física", "1655 Mantenimiento", (500_000, 4_000_000)),
        ("Servicios públicos sede principal", "2435 Servicios públicos", (600_000, 1_800_000)),
        ("Complemento alimentario PAE", "1520 Bienestar estudiantil", (800_000, 3_200_000)),
        ("Capacitación docente", "1512 Formación", (300_000, 1_500_000)),
        ("Insumos aseo y cafetería", "1510 Suministros generales", (150_000, 900_000)),
    ]
    fecha = HOY - timedelta(weeks=N_SEMANAS)
    for _ in range(14):
        c, cuenta, rango = random.choice(conceptos_ingreso)
        session.add(MovimientoFSE(
            fecha=fecha + timedelta(days=random.randint(0, N_SEMANAS * 7)),
            concepto=c, cuenta_cgn=cuenta, valor=float(random.randint(*rango)),
        ))
    for _ in range(28):
        c, cuenta, rango = random.choice(conceptos_gasto)
        session.add(MovimientoFSE(
            fecha=fecha + timedelta(days=random.randint(0, N_SEMANAS * 7)),
            concepto=c, cuenta_cgn=cuenta, valor=-float(random.randint(*rango)),
        ))
    session.commit()


def main():
    engine = get_engine(settings.DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_sessionmaker(engine)
    session = Session()

    print("Generando estudiantes sintéticos...")
    estudiantes = generar_estudiantes(session)
    print(f"  {len(estudiantes)} estudiantes creados en {len(GRADOS)} grados.")

    print("Generando historial de asistencia y notas (esto toma unos segundos)...")
    generar_asistencia_y_notas(session, estudiantes)

    print("Generando movimientos contables del FSE...")
    generar_fse(session)

    print("Listo. Base de datos de demostración creada en:", settings.DATABASE_URL)
    session.close()


if __name__ == "__main__":
    main()
