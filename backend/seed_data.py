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
    Base, Estudiante, Asistencia, Nota, MovimientoFSE, RegistroCenso, get_engine, get_sessionmaker,
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

# ----------------------------------------------------------------------
# CENSO JUVENIL TERRITORIAL — datos simulados por departamento/municipio
# ----------------------------------------------------------------------
GEOGRAFIA_CENSO = {
    "Santander": {
        "Bucaramanga": {"zona_pred": "urbana", "riesgo_base": 0.16, "lugares": [
            "Comuna Nororiental", "Barrio Kennedy", "Barrio Café Madrid",
            "Barrio La Concordia", "Barrio Girardot", "Barrio La Joya"]},
        "Barrancabermeja": {"zona_pred": "urbana", "riesgo_base": 0.30, "lugares": [
            "Comuna 1 — Miraflores", "Comuna 7 — El Danubio", "Corregimiento El Llanito",
            "Comuna 5 — Torcoroma", "Barrio Provivienda"]},
        "Puerto Wilches": {"zona_pred": "rural", "riesgo_base": 0.28, "lugares": [
            "Vereda Puente Sogamoso", "Corregimiento Bocas del Rosario",
            "Vereda El Guamo", "Casco urbano Puerto Wilches"]},
        "Floridablanca": {"zona_pred": "urbana", "riesgo_base": 0.12, "lugares": [
            "Barrio Caldas", "Barrio Bucarica", "Barrio Cañaveral", "Barrio Lagos"]},
    },
    "Bolívar": {
        "San Pablo": {"zona_pred": "rural", "riesgo_base": 0.34, "lugares": [
            "Vereda La Fortuna", "Corregimiento Cerro Azul", "Vereda El Paraíso",
            "Casco urbano San Pablo", "Vereda La Ceiba"]},
        "Santa Rosa del Sur": {"zona_pred": "rural", "riesgo_base": 0.33, "lugares": [
            "Vereda Buena Vista", "Corregimiento Cerro Burgos", "Vereda La Fría",
            "Casco urbano Santa Rosa del Sur"]},
        "Simití": {"zona_pred": "rural", "riesgo_base": 0.31, "lugares": [
            "Vereda Monterrey", "Corregimiento Vallecito", "Casco urbano Simití"]},
        "Cartagena": {"zona_pred": "urbana", "riesgo_base": 0.14, "lugares": [
            "Barrio Olaya Herrera", "Barrio Nelson Mandela", "Barrio El Pozón",
            "Barrio San José de los Campanitos"]},
    },
}

# Categorías alineadas al lenguaje del Sistema de Alertas Tempranas (SAT) de la
# Defensoría del Pueblo y a los motivos de inasistencia que reporta el MEN/DANE.
MOTIVOS_NO_ESTUDIA = [
    "Trabajo agrícola o informal para aportar al hogar",
    "Cuidado de hermanos u otros familiares",
    "Embarazo o maternidad temprana",
    "Distancia o falta de transporte al establecimiento",
    "Falta de cupo escolar disponible",
    "Desmotivación tras repitencia previa",
    "Desplazamiento o cambio de residencia reciente",
    "Documentos o registro civil pendiente de trámite",
]
TIPOS_ALERTA = [
    "Riesgo de reclutamiento, uso o utilización por grupos armados",
    "Riesgo de violencia sexual",
    "Riesgo de trabajo infantil",
    "Riesgo de desplazamiento forzado",
    "Zona con restricciones de movilidad (confinamiento)",
    "Violencia intrafamiliar reportada",
    "Riesgo de unión temprana / embarazo adolescente",
    "Entorno con consumo de sustancias psicoactivas",
]
ESTADOS_SEGUIMIENTO = ["Sin contactar", "En seguimiento", "Contactado — caso cerrado"]
COLEGIOS_REF = [
    "I.E. San Pablo", "I.E. Normal Superior", "I.E. Técnica Agropecuaria",
    "I.E. La Esperanza", "I.E. Simón Bolívar", "I.E. Rural Integrada",
]
N_CENSO_POR_MUNICIPIO = 55


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


def generar_censo_juvenil(session):
    """Genera el censo juvenil territorial simulado (12 a 17 años) para
    cada municipio configurado en GEOGRAFIA_CENSO. Cruza, de forma
    plausible pero sintética, SISBEN + estado educativo + alertas de
    protección — el mismo contrato de datos que en producción vendría
    de SISBEN IV, SIMAT y el SAT de la Defensoría del Pueblo."""
    usados = set()
    total = 0
    for depto, municipios in GEOGRAFIA_CENSO.items():
        for municipio, meta in municipios.items():
            riesgo_base = meta["riesgo_base"]
            for _ in range(N_CENSO_POR_MUNICIPIO):
                edad = random.randint(12, 17)
                sexo = random.choice(["M", "F"])
                zona = meta["zona_pred"] if random.random() < 0.75 else (
                    "rural" if meta["zona_pred"] == "urbana" else "urbana"
                )
                lugar = random.choice(meta["lugares"])
                nivel = random.choices(
                    NIVELES_SISBEN,
                    weights=[0.30, 0.27, 0.20, 0.14, 0.09] if zona == "rural" else [0.14, 0.20, 0.28, 0.22, 0.16],
                )[0]

                propension = random.betavariate(2, 5)
                propension = min(1.0, propension + riesgo_base * 0.6)

                estudia = random.random() > (0.14 + propension * 0.30)
                motivo = None if estudia else random.choice(MOTIVOS_NO_ESTUDIA)
                colegio = random.choice(COLEGIOS_REF) if estudia else None

                prob_zona_riesgo = riesgo_base + (0.10 if not estudia else 0) + (propension * 0.15)
                zona_riesgo = random.random() < min(0.65, prob_zona_riesgo)
                tipo_alerta = None
                if zona_riesgo:
                    n_alertas = 1 if random.random() < 0.7 else 2
                    tipo_alerta = "|".join(random.sample(TIPOS_ALERTA, k=n_alertas))

                estado = "Sin contactar"
                fecha_contacto = None
                if zona_riesgo or not estudia:
                    estado = random.choices(ESTADOS_SEGUIMIENTO, weights=[0.45, 0.35, 0.20])[0]
                    if estado != "Sin contactar":
                        fecha_contacto = HOY - timedelta(days=random.randint(1, 60))

                session.add(RegistroCenso(
                    nombre=nombre_aleatorio(usados), edad=edad, sexo=sexo,
                    departamento=depto, municipio=municipio, zona=zona,
                    barrio_vereda=lugar, nivel_sisben=nivel,
                    estudia=estudia, motivo_no_estudia=motivo, colegio=colegio,
                    zona_riesgo=zona_riesgo, tipo_alerta=tipo_alerta,
                    ultimo_contacto=fecha_contacto, estado_seguimiento=estado,
                ))
                total += 1
    session.commit()
    return total


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

    print("Generando censo juvenil territorial (Santander y Bolívar)...")
    total_censo = generar_censo_juvenil(session)
    print(f"  {total_censo} jóvenes censados en {sum(len(m) for m in GEOGRAFIA_CENSO.values())} municipios.")

    print("Listo. Base de datos de demostración creada en:", settings.DATABASE_URL)
    session.close()


if __name__ == "__main__":
    main()
