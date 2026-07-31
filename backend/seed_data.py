"""
Generador del conjunto de datos SIMULADO para la demo multi-perfil PRO.

Llena una base SQLite local (gyverlabs_demo.db) con un ecosistema educativo
completo y 100% sintético, SIEMPRE relativo a la fecha de HOY (así la demo
nunca se ve vieja): instituciones multi-tenant con dominio propio, personal
completo con hojas de vida, salones con horarios y temas por corte,
estudiantes con acudientes y antigüedad, asistencia de 12 semanas, notas,
observador, alertas del coordinador, WhatsApp simulado, aula virtual PRO,
contabilidad FSE + contratación SECOP 2, censo juvenil y configuración.

Ejecutar:  python seed_data.py   (determinístico, semilla fija)
"""

import json
import random
import unicodedata
from datetime import date, datetime, timedelta

from models import (
    Base, Tenant, Institucion, Personal, Salon, Estudiante, Asistencia,
    AsistenciaPersonal, Periodo, Corte, TemaPlan, NotaPeriodo,
    ObservadorEntrada, NotaPendiente, NotificacionCoord, MensajeWhatsApp,
    ActividadAula, EntregaAula, EventoCalendario,
    CuentaFSE, PlanFSE, RegistroPresupuestal, MovimientoFSE,
    Contratista, Contrato, Autorizacion, ConfigSistema, Comunicado, NotificacionPersona,
    LeccionCurso, RubroFSE, PagoContrato, SalaVirtual, MensajeSala,
    Sede, SolicitudRecurso, VotoPropuesta,
    Curso, ModuloCurso, TemaCurso, ProgresoTema, InscripcionCurso, Usuario, LogAcceso,
    TemaClase, ProgresoTemaClase, GrabacionClase, ConfigDominio, Suscripcion,
    AsignacionHorario, RevisionTema, PerfilLegal, FilaRejilla, DocumentoLegal, Correspondencia,
    PlaneacionDocente, NotaHistorica, ImportacionSIMAT, CertificadoEmitido,
    RegistroCenso, get_engine, get_sessionmaker,
)
from core.config import settings

SEED = 42
random.seed(SEED)
HOY = date.today()
AHORA = datetime.now()
PROPS = {}   # estudiante_id -> propensión de riesgo (sobrevive a los commits)

NOMBRES = ["Mariana","Santiago","Valentina","Samuel","Isabella","Mateo","Sofía","Juan","Camila","Andrés",
    "Luciana","David","Gabriela","Sebastián","Salomé","Nicolás","Danna","Emmanuel","Yuliana","Kevin",
    "Paula","Cristian","Laura","Brayan","Karen","Miguel","Daniela","Julián","Natalia","Esteban",
    "Yesenia","Yeison","Dayana","Deiby","Anderson","Leidy","Jhon","Angie","Wilmer","Yurany"]
APELLIDOS = ["Pérez","Rodríguez","Martínez","López","García","Hernández","González","Torres","Ramírez","Flórez",
    "Suárez","Ortiz","Castro","Vargas","Rueda","Mendoza","Peñaranda","Villamizar","Gómez","Cárdenas","Contreras","Rojas"]
MATERIAS = ["Matemáticas","Lenguaje","Ciencias","Sociales","Inglés"]
AREAS = ["Matemáticas","Humanidades","Ciencias Naturales","Ciencias Sociales","Inglés","Ed. Física","Tecnología"]
PARENTESCOS = ["Madre","Padre","Abuela","Abuelo","Tía","Tío","Hermana mayor","Tutor legal"]
PROFESIONES_DOC = ["Licenciatura en Matemáticas","Licenciatura en Lengua Castellana","Licenciatura en Ciencias Naturales",
    "Licenciatura en Ciencias Sociales","Licenciatura en Lenguas Extranjeras","Licenciatura en Educación Física",
    "Ingeniería de Sistemas (docente TIC)"]
BARRIOS_URB = ["El Centro","La Esperanza","Nueva Colombia","20 de Julio","El Progreso","Villa del Sol"]
VEREDAS = ["Cañabraval","El Carmen","Buenavista","La Floresta","San Juan","El Diamante"]

ECOSISTEMA = {
    ("San Pablo", "Bolívar"): [
        ("I.E. Técnico San Pablo", "113670000101", "oficial urbana", ["6","7","8","9","10","11"]),
        ("I.E. Rural La Esperanza", "213670000202", "oficial rural", ["6","7","8","9"]),
        ("I.E. Simón Bolívar", "113670000303", "oficial urbana", ["6","7","8","9","10","11"]),
    ],
    ("Santa Rosa del Sur", "Bolívar"): [
        ("I.E. Santa Rosa del Sur", "116880000101", "oficial urbana", ["6","7","8","9","10","11"]),
        ("I.E. Rural El Paraíso", "216880000202", "oficial rural", ["6","7","8","9"]),
    ],
}

TEMAS_BANCO = {
    "Matemáticas": ["Números enteros y racionales","Ecuaciones lineales","Proporcionalidad","Geometría: áreas y volúmenes","Estadística descriptiva","Funciones y gráficas"],
    "Lenguaje": ["Comprensión lectora crítica","El texto narrativo","Ortografía y gramática","Producción de textos argumentativos","Literatura colombiana","Medios y comunicación"],
    "Ciencias": ["La célula y sus funciones","Ecosistemas del Magdalena Medio","Materia y energía","El cuerpo humano","Mezclas y soluciones","Electricidad básica"],
    "Sociales": ["Mi municipio y mi región","Historia de Colombia s. XX","Democracia y participación","Geografía de Colombia","Derechos humanos","Economía campesina"],
    "Inglés": ["Greetings and introductions","Present simple","My daily routine","Food and health","Past simple","My community"],
}


def nombre_aleatorio():
    return f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)} {random.choice(APELLIDOS)}"


def slug(texto):
    t = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode()
    return "".join(c for c in t.lower() if c.isalnum())


def tel():
    return "3" + "".join(random.choice("0123456789") for _ in range(9))


def cc():
    return "".join(random.choice("0123456789") for _ in range(9))


def propension_riesgo(zona, nivel):
    p = random.betavariate(2, 6)
    if zona == "rural": p = min(1.0, p + 0.12)
    if nivel in ("A1", "A2"): p = min(1.0, p + 0.08)
    return p


def hv_json(profesion, exp):
    estudios = [profesion]
    if random.random() < 0.45:
        estudios.append("Especialización en " + random.choice(["Pedagogía","Evaluación Educativa","Gerencia Educativa","TIC en el aula"]))
    if random.random() < 0.12:
        estudios.append("Maestría en Educación")
    exp_list = []
    resto = exp
    while resto > 0:
        d = min(resto, random.randint(2, 6))
        exp_list.append(f"Docente de aula — I.E. {random.choice(['El Retorno','Camilo Torres','La Unión','San José'])} ({d} años)")
        resto -= d
    certs = random.sample(["Curso MEN: Evaluación formativa","Diplomado en convivencia escolar",
                           "Formación 'Computadores para Educar'","Primeros auxilios","Inglés B1"], k=random.randint(0, 3))
    return {"estudios": estudios, "experiencia": exp_list, "certificaciones": certs, "archivo": None}


def hv_score(hv, exp):
    return min(100, 35 + 8 * len(hv["estudios"]) + min(30, 2 * exp) + 5 * len(hv["certificaciones"]))


def _seed_curso_contabilidad(s):
    """Curso interactivo de contabilidad para alumnos: inventarios con foto,
    arqueos de caja, facturas, cotizaciones, declaración DIAN, balances y
    auditorías. Cada lección trae secciones, quiz y a veces práctica interactiva."""
    if s.query(LeccionCurso).count() > 0:
        return
    L = []

    def lec(nivel, orden, titulo, icono, resumen, secciones, quiz, practica="none"):
        L.append(LeccionCurso(curso="contabilidad", nivel=nivel, orden=orden,
                              titulo=titulo, icono=icono, resumen=resumen,
                              contenido=json.dumps({"secciones": secciones, "quiz": quiz},
                                                   ensure_ascii=False),
                              tipo_practica=practica))

    lec("basico", 1, "¿Qué es la contabilidad?", "🧮",
        "La contabilidad es el lenguaje de los negocios: registra todo lo que entra y sale de dinero.",
        [{"h": "Una historia de más de 500 años",
          "p": "Desde que existe el comercio, las personas necesitaron anotar deudas y ganancias. En 1494 el fraile italiano Luca Pacioli escribió el primer libro de partida doble: por cada registro hay un origen y un destino."},
         {"h": "¿Para qué le sirve a una empresa?",
          "p": "Para saber si gana o pierde, cuánto debe, cuánto le deben, cuánto vale y para pagar bien sus impuestos. Sin contabilidad, un negocio va a ciegas."},
         {"h": "Palabras clave",
          "p": "Ingreso = dinero que entra. Egreso/Gasto = dinero que sale. Activo = lo que tienes. Pasivo = lo que debes. Patrimonio = lo tuyo (Activo − Pasivo)."}],
        [{"q": "Si Activo = $10.000 y Pasivo = $4.000, ¿el Patrimonio es?",
          "op": ["$14.000", "$6.000", "$4.000"], "correcta": 1},
         {"q": "El dinero que ENTRA a la empresa se llama:",
          "op": ["Egreso", "Pasivo", "Ingreso"], "correcta": 2}])

    lec("basico", 2, "Registro de ventas", "🧾",
        "Toda venta se registra: qué vendiste, cuánto, a qué precio y cuándo.",
        [{"h": "El corazón del negocio",
          "p": "Cada venta anota producto, cantidad y precio. La suma de tus ventas del día es tu ingreso diario."},
         {"h": "Costo vs venta",
          "p": "Si compras un cuaderno en $2.000 y lo vendes en $3.000, tu utilidad es $1.000. El precio de venta siempre cubre el costo más la ganancia."}],
        [{"q": "Compras en $5.000 y vendes en $8.000. ¿Utilidad?",
          "op": ["$8.000", "$3.000", "$5.000"], "correcta": 1}])

    lec("basico", 3, "Inventario: lo que tienes para vender", "📦",
        "El inventario es la lista de productos con su cantidad. Aquí cargarás productos con foto.",
        [{"h": "¿Por qué importa?",
          "p": "Si no sabes qué tienes, no sabes qué vender ni cuándo pedir más. Un buen inventario evita quiebres de stock y pérdidas."},
         {"h": "Ficha de producto",
          "p": "Nombre, foto, cantidad, precio de costo y precio de venta. En la práctica cargas tu propio inventario."}],
        [{"q": "¿Qué NO va en la ficha de un producto?",
          "op": ["Cantidad", "El clima de hoy", "Precio de venta"], "correcta": 1}],
        practica="inventario")

    lec("moderado", 1, "Arqueo de caja", "💵",
        "El arqueo compara el dinero que DEBERÍA haber con el que REALMENTE hay. Detecta faltantes.",
        [{"h": "¿Qué es?",
          "p": "Al cerrar el día cuentas el efectivo y lo comparas con tu registro de ventas. Si no cuadra, hay faltante o sobrante que explicar."},
         {"h": "Fórmula",
          "p": "Efectivo esperado = saldo inicial + ventas en efectivo − retiros. Diferencia = contado − esperado."}],
        [{"q": "Esperabas $100.000 pero contaste $92.000. Hay:",
          "op": ["Sobrante $8.000", "Faltante $8.000", "Cuadra"], "correcta": 1}],
        practica="arqueo")

    lec("moderado", 2, "Cotizaciones y facturas", "📄",
        "La cotización es una oferta de precio; la factura es el documento legal de la venta.",
        [{"h": "Cotización primero, factura después",
          "p": "El cliente pide cotización. Si acepta, se emite la factura: soporte legal y base para la DIAN."},
         {"h": "Qué lleva una factura",
          "p": "Datos de vendedor y cliente, fecha, número, detalle, subtotal, IVA (19% en Colombia) y total. En la práctica armas una."}],
        [{"q": "El IVA general en Colombia es:",
          "op": ["10%", "19%", "5%"], "correcta": 1}],
        practica="factura")

    lec("moderado", 3, "Balance general", "⚖️",
        "El balance es la foto de la empresa: activos, pasivos y patrimonio.",
        [{"h": "La ecuación de oro",
          "p": "Activo = Pasivo + Patrimonio. Los dos lados SIEMPRE deben ser iguales."},
         {"h": "Ejemplo",
          "p": "$10M en activos, debes $3M → patrimonio $7M. Cuadra: 10 = 3 + 7."}],
        [{"q": "Activo $20M, Patrimonio $12M. ¿Pasivos?",
          "op": ["$32M", "$8M", "$12M"], "correcta": 1}],
        practica="balance")

    lec("avanzado", 1, "Declaración ante la DIAN", "🏛️",
        "Toda empresa declara impuestos ante la DIAN. Practicas una declaración simple.",
        [{"h": "¿Qué es la DIAN?",
          "p": "La Dirección de Impuestos y Aduanas Nacionales administra los impuestos. Las empresas declaran renta e IVA según su actividad."},
         {"h": "IVA a pagar",
          "p": "IVA a pagar = IVA cobrado en ventas − IVA pagado en compras. El saldo se le paga a la DIAN."}],
        [{"q": "Cobraste $190.000 de IVA y pagaste $70.000. ¿Declaras a pagar?",
          "op": ["$260.000", "$120.000", "$70.000"], "correcta": 1}],
        practica="declaracion")

    lec("avanzado", 2, "Estados financieros", "📊",
        "El estado de resultados muestra si ganaste o perdiste. Utilidad = Ingresos − Costos − Gastos.",
        [{"h": "Estado de resultados (P&G)",
          "p": "Ingresos menos costos de lo vendido, menos gastos (arriendo, servicios, sueldos). Lo que queda es la utilidad neta."},
         {"h": "¿Por qué importa?",
          "p": "Se puede vender mucho y perder si los gastos son altos. El P&G dice la verdad."}],
        [{"q": "Ingresos $500, costos $200, gastos $150. ¿Utilidad?",
          "op": ["$150", "$350", "$500"], "correcta": 0}])

    lec("avanzado", 3, "Auditoría y control", "🔍",
        "Auditar es revisar que todo esté registrado y soportado. Protege de errores y fraudes.",
        [{"h": "¿Qué revisa?",
          "p": "Que cada movimiento tenga soporte (factura, comprobante), que cuadre y cumpla normas. Una empresa ordenada pasa cualquier auditoría."},
         {"h": "Trazabilidad",
          "p": "Cada peso se rastrea: de dónde vino y a dónde fue. Justo lo que hace este sistema con el FSE del colegio."}],
        [{"q": "El mejor soporte de una venta en auditoría es:",
          "op": ["La palabra del vendedor", "La factura", "Un audio"], "correcta": 1}])

    for x in L:
        s.add(x)


def _seed_sedes(s):
    """Cada institucion con sus sedes: una principal y varias satelite en
    veredas. Reparte salones, personal y estudiantes entre ellas."""
    if s.query(Sede).count() > 0:
        return
    VEREDAS = ["Cerro Azul", "La Esperanza", "Villa Nueva", "El Progreso", "Santa Rita",
               "Bajo Grande", "La Palma", "Buenos Aires", "El Diamante", "Cañabraval"]
    for ie in s.query(Institucion).all():
        principal = Sede(institucion_id=ie.id, nombre=f"Sede Principal - {ie.nombre.replace('I.E. ','')[:28]}",
                         codigo_dane=ie.codigo_dane, tipo="principal",
                         zona="urbana" if "urbana" in (ie.sector or "") else "rural",
                         direccion=f"Calle {random.randint(1,20)} # {random.randint(1,30)}-{random.randint(10,80)}",
                         barrio_vereda="Centro", telefono=tel(),
                         niveles="Preescolar,Primaria,Secundaria,Media",
                         tiene_internet=True, tiene_pae=True, distancia_km=0)
        s.add(principal)
        s.flush()
        n_sat = random.randint(2, 4)
        sats = []
        for i in range(n_sat):
            v = random.choice(VEREDAS)
            VEREDAS.remove(v) if v in VEREDAS and len(VEREDAS) > 4 else None
            sat = Sede(institucion_id=ie.id, nombre=f"Sede {v}",
                       codigo_dane=f"{ie.codigo_dane}{i+1}" if ie.codigo_dane else None,
                       tipo="satelite", zona="rural",
                       direccion=f"Vereda {v}", barrio_vereda=v, telefono=tel(),
                       niveles=random.choice(["Preescolar,Primaria", "Primaria",
                                              "Preescolar,Primaria,Secundaria"]),
                       tiene_internet=random.random() < 0.55,
                       tiene_pae=random.random() < 0.8,
                       distancia_km=round(random.uniform(4, 38), 1))
            s.add(sat)
            sats.append(sat)
        s.flush()
        todas = [principal] + sats

        # Repartir salones: la mayoria en la principal
        for sal in s.query(Salon).filter(Salon.institucion_id == ie.id).all():
            sal.sede_id = principal.id if random.random() < 0.68 else random.choice(sats).id
        s.flush()

        # Personal: directivos en la principal, docentes segun su salon
        for p in s.query(Personal).filter(Personal.institucion_id == ie.id).all():
            if p.rol in ("rector", "coordinador", "contador", "abogado", "auxiliar", "secretaria"):
                p.sede_id = principal.id
            else:
                mi_salon = s.query(Salon).filter(Salon.director_id == p.id).first()
                p.sede_id = mi_salon.sede_id if mi_salon and mi_salon.sede_id else random.choice(todas).id

        # Coordinador de cada sede satelite: un docente de esa sede
        for sat in sats:
            cand = s.query(Personal).filter(Personal.sede_id == sat.id,
                                            Personal.rol == "docente").first()
            if cand:
                sat.coordinador_id = cand.id

        # Estudiantes heredan la sede de su salon
        for e in s.query(Estudiante).filter(Estudiante.institucion_id == ie.id).all():
            if e.salon_id:
                sal = s.query(Salon).filter(Salon.id == e.salon_id).first()
                e.sede_id = sal.sede_id if sal else principal.id
            else:
                e.sede_id = principal.id
    s.commit()


def _seed_solicitudes_recurso(s, ie):
    """Buzon de necesidades de los docentes (punto 10)."""
    if s.query(SolicitudRecurso).count() > 0:
        return
    docentes = s.query(Personal).filter(Personal.institucion_id == ie.id,
                                        Personal.rol == "docente").all()
    if not docentes:
        return
    PEDIDOS = [
        ("material", "Marcadores y borradores para tablero", "Se acabaron los marcadores del salon. Llevamos dos semanas usando los personales.", 30, "alta", 180000),
        ("tecnologia", "Video beam para el aula de sexto", "Necesito proyectar los videos de ciencias. El unico video beam esta en rectoria.", 1, "media", 1800000),
        ("infraestructura", "Reparacion de goteras en el salon 702", "Cuando llueve se moja el piso y toca sacar a los ninos.", 1, "alta", 900000),
        ("material", "Resmas de papel para guias", "Las guias de refuerzo las estoy sacando de mi bolsillo.", 20, "media", 420000),
        ("pae", "Refrigerios para la sede rural", "Los ninos de la vereda llegan sin desayunar y rinden menos.", 60, "alta", 0),
        ("tecnologia", "Internet para la sede satelite", "Sin internet no puedo usar el aula virtual con ellos.", 1, "alta", 2400000),
        ("material", "Kit de laboratorio de ciencias", "Para las practicas de octavo y noveno.", 1, "baja", 1500000),
        ("personal", "Apoyo de psicoorientacion medio tiempo", "Tengo tres casos de riesgo que no puedo manejar solo.", 1, "media", 0),
    ]
    ESTADOS = ["pendiente", "pendiente", "pendiente", "aprobada", "en_compra", "resuelta", "rechazada", "pendiente"]
    for i, (cat, tit, det, cant, urg, val) in enumerate(PEDIDOS):
        d = random.choice(docentes)
        est = ESTADOS[i % len(ESTADOS)]
        f = AHORA - timedelta(days=random.randint(1, 25))
        s.add(SolicitudRecurso(
            institucion_id=ie.id, sede_id=d.sede_id, solicitante_id=d.id,
            categoria=cat, titulo=tit, detalle=det, cantidad=cant,
            urgencia=urg, valor_estimado=val, estado=est,
            respuesta=("Aprobado, se incluye en el plan de compras." if est == "aprobada" else
                       "Ya se hizo el pedido al proveedor." if est == "en_compra" else
                       "Entregado al docente." if est == "resuelta" else
                       "No hay disponibilidad presupuestal este trimestre." if est == "rechazada" else None),
            resuelto_por=("Rectoria" if est != "pendiente" else None),
            fecha=f,
            fecha_respuesta=(f + timedelta(days=random.randint(1, 5))) if est != "pendiente" else None))
    s.commit()


def _seed_propuestas(s):
    """Propuestas que los contratistas ya subieron por su portal (punto 16)."""
    import secrets as _sec
    PROPS = {
        0: [("Suministro de papeleria y utiles escolares para la vigencia 2026, incluye entrega en las 4 sedes.",
             4850000, ["propuesta_tecnica.pdf", "lista_precios.xlsx", "certificado_experiencia.pdf"])],
        1: [("Prestacion del servicio de alimentacion escolar PAE para 320 estudiantes, 40 dias calendario.",
             11200000, ["propuesta_pae.pdf", "minutas_nutricionista.pdf", "concepto_sanitario.pdf"])],
        2: [("Mantenimiento y adecuacion de baterias sanitarias, incluye materiales y mano de obra.",
             5900000, ["propuesta_obra.pdf", "cronograma.pdf"])],
    }
    contratistas = s.query(Contratista).all()
    for i, c in enumerate(contratistas):
        if i not in PROPS:
            continue
        props = []
        for desc, val, archivos in PROPS[i]:
            props.append({"fecha": (HOY - timedelta(days=random.randint(3, 14))).isoformat(),
                          "valor": val, "descripcion": desc, "archivos": archivos,
                          "estado": "recibida"})
        c.propuestas = json.dumps(props, ensure_ascii=False)
        if not c.portal_token:
            c.portal_token = _sec.token_urlsafe(12)
    s.commit()


def _seed_junta(s, ie):
    """Junta directiva que aprueba o rechaza propuestas (punto 16)."""
    if s.query(VotoPropuesta).count() > 0:
        return
    rector = s.query(Personal).filter(Personal.institucion_id == ie.id,
                                      Personal.rol == "rector").first()
    docente = s.query(Personal).filter(Personal.institucion_id == ie.id,
                                       Personal.rol == "docente").first()
    JUNTA = [
        (rector.nombre if rector else "Rector(a)", "Rector - preside"),
        (docente.nombre if docente else "Docente", "Representante de docentes"),
        ("Yolanda Meza Pabon", "Representante de padres de familia"),
        ("Kevin Andres Solano", "Representante de estudiantes"),
        ("Hernan Dario Pineda", "Representante sector productivo"),
    ]
    contratistas = s.query(Contratista).all()
    for c in contratistas[:2]:
        try:
            props = json.loads(c.propuestas) if c.propuestas else []
        except Exception:
            props = []
        if not props:
            continue
        for miembro, rol in JUNTA:
            v = random.choice(["aprueba", "aprueba", "aprueba", "rechaza", "pendiente"])
            s.add(VotoPropuesta(institucion_id=ie.id, contratista_id=c.id, propuesta_idx=0,
                                miembro=miembro, rol_junta=rol, voto=v,
                                observacion=("Precio por debajo del mercado, cumple requisitos." if v == "aprueba"
                                             else "Falta soporte de experiencia especifica." if v == "rechaza" else None),
                                fecha=AHORA - timedelta(days=random.randint(1, 8)) if v != "pendiente" else None))
    s.commit()


def _seed_cursos(s):
    """Instala los cursos preinstalados: curso -> modulos -> temas."""
    if s.query(Curso).count() > 0:
        return
    from contenido_cursos import CURSOS_PREINSTALADOS
    for orden_c, cdef in enumerate(CURSOS_PREINSTALADOS, start=1):
        c = Curso(slug=cdef["slug"], titulo=cdef["titulo"], descripcion=cdef["descripcion"],
                  categoria=cdef.get("categoria"), icono=cdef.get("icono"),
                  color=cdef.get("color", "#0E7C86"),
                  duracion_texto=cdef.get("duracion_texto"),
                  grado_sugerido=cdef.get("grado_sugerido"),
                  nivel="todos", estado="publicado", orden=orden_c, preinstalado=True)
        s.add(c)
        s.flush()
        for orden_m, mdef in enumerate(cdef["modulos"], start=1):
            m = ModuloCurso(curso_id=c.id, titulo=mdef["titulo"],
                            descripcion=mdef.get("descripcion"),
                            nivel=mdef.get("nivel", "basico"), icono=mdef.get("icono"),
                            orden=orden_m)
            s.add(m)
            s.flush()
            for orden_t, tdef in enumerate(mdef["temas"], start=1):
                s.add(TemaCurso(
                    modulo_id=m.id, titulo=tdef["titulo"], resumen=tdef.get("resumen"),
                    contenido=json.dumps(tdef.get("contenido", []), ensure_ascii=False),
                    duracion_min=tdef.get("duracion_min", 12),
                    tipo_practica=tdef.get("tipo_practica"),
                    quiz=json.dumps(tdef.get("quiz", []), ensure_ascii=False),
                    recursos=json.dumps(tdef.get("recursos", []), ensure_ascii=False),
                    orden=orden_t))
    s.commit()

    # Inscribir a TODOS los estudiantes en todos los cursos preinstalados
    cursos = s.query(Curso).all()
    for e in s.query(Estudiante).all():
        for c in cursos:
            s.add(InscripcionCurso(estudiante_id=e.id, curso_id=c.id,
                                   inscrito_por="Sistema (preinstalado)", fecha=AHORA))
    s.commit()

    # Progreso simulado: unos alumnos ya avanzaron
    temas_all = s.query(TemaCurso).all()
    por_curso = {}
    for t in temas_all:
        mod = s.query(ModuloCurso).filter(ModuloCurso.id == t.modulo_id).first()
        por_curso.setdefault(mod.curso_id, []).append(t)
    ests = s.query(Estudiante).all()
    for e in random.sample(ests, k=min(120, len(ests))):
        cid = random.choice(list(por_curso.keys()))
        temas = sorted(por_curso[cid], key=lambda x: x.id)
        n = random.randint(1, max(1, len(temas) // 2))
        for t in temas[:n]:
            s.add(ProgresoTema(estudiante_id=e.id, tema_id=t.id, curso_id=cid,
                               completado=True, quiz_puntaje=random.choice([60, 80, 100, 100]),
                               quiz_intentos=random.randint(1, 2),
                               minutos=random.randint(8, 25),
                               fecha=AHORA - timedelta(days=random.randint(1, 30))))
    s.commit()


def _seed_usuarios(s):
    """Crea las cuentas de acceso: todo el personal y los estudiantes.
    Incluye registros PENDIENTES de aprobacion y un historial de auditoria."""
    if s.query(Usuario).count() > 0:
        return
    hoy = AHORA

    def _usr(nombre):
        base = slug(nombre.lower()).split()
        return (base[0][0] + base[-1])[:20] if len(base) > 1 else base[0][:20]

    usados = set()
    for p in s.query(Personal).all():
        u = _usr(p.nombre)
        n = 1
        while u in usados:
            n += 1
            u = f"{_usr(p.nombre)}{n}"
        usados.add(u)
        activo = bool(p.activo)
        s.add(Usuario(
            institucion_id=p.institucion_id, sede_id=p.sede_id, personal_id=p.id,
            usuario=u, nombre=p.nombre, email=p.email or f"{u}@institucion.edu.co",
            telefono=p.telefono, documento=p.documento, rol=p.rol,
            estado="activo" if activo else "suspendido",
            foto=p.foto, creado_por="Rectoría",
            fecha_registro=hoy - timedelta(days=random.randint(30, 400)),
            ultimo_acceso=hoy - timedelta(hours=random.randint(1, 200)) if activo else None,
            n_accesos=random.randint(3, 260) if activo else 0,
            debe_cambiar_clave=False))
    s.commit()

    # Cuentas de estudiantes (las que ya tienen codigo de acceso)
    for e in s.query(Estudiante).limit(200).all():
        s.add(Usuario(
            institucion_id=e.institucion_id, sede_id=e.sede_id, estudiante_id=e.id,
            usuario=(e.codigo_acceso or f"AL{e.id:04d}"), nombre=e.nombre,
            email=None, telefono=e.telefono, rol="alumno", estado="activo",
            creado_por="Sistema (matrícula)",
            fecha_registro=hoy - timedelta(days=random.randint(10, 300)),
            ultimo_acceso=hoy - timedelta(hours=random.randint(2, 400)) if random.random() < 0.6 else None,
            n_accesos=random.randint(0, 90), debe_cambiar_clave=False))
    s.commit()

    # Registros PENDIENTES de aprobacion (lo que el rector debe revisar)
    ie = s.query(Institucion).first()
    sede_p = s.query(Sede).filter(Sede.institucion_id == ie.id,
                                  Sede.tipo == "principal").first()
    PEND = [
        ("Diego Armando Cuesta", "docente", "Lic. en Educación Física", "3105567788", "1.098.334.221"),
        ("Luz Marina Prada Ortiz", "docente", "Normalista Superior", "3117788990", "63.556.112"),
        ("Sandra Milena Ruiz", "psicoorientacion", "Psicóloga", "3009988776", "1.102.556.334"),
        ("Wilmer Alexis Pabón", "vigilante", "Bachiller", "3126677554", "91.556.223"),
    ]
    for nom, rol, prof, tel_, doc in PEND:
        s.add(Usuario(
            institucion_id=ie.id, sede_id=sede_p.id if sede_p else None,
            usuario=slug(nom.split()[0].lower()) + slug(nom.split()[-1].lower())[:8],
            nombre=nom, email=f"{slug(nom.split()[0].lower())}@correo.com",
            telefono=tel_, documento=doc, rol=rol, estado="pendiente",
            creado_por="Registro público",
            fecha_registro=hoy - timedelta(days=random.randint(1, 9)),
            nota_admin=f"Se registró en el portal. Profesión declarada: {prof}.",
            debe_cambiar_clave=True))
    s.commit()

    # Log de auditoria
    usuarios = s.query(Usuario).filter(Usuario.estado == "activo").all()
    IPS = ["190.85.44.", "181.49.120.", "186.30.77.", "200.118.62."]
    for _ in range(140):
        u = random.choice(usuarios)
        acc = random.choices(["login", "login", "login", "logout", "cambio_perfil", "login_fallido"],
                             weights=[40, 40, 40, 20, 8, 6])[0]
        s.add(LogAcceso(
            usuario_id=u.id, institucion_id=u.institucion_id, usuario_nombre=u.nombre,
            accion="login" if acc == "login_fallido" else acc,
            resultado="fallido" if acc == "login_fallido" else "ok",
            detalle="Contraseña incorrecta" if acc == "login_fallido" else None,
            ip=random.choice(IPS) + str(random.randint(2, 250)),
            fecha=hoy - timedelta(hours=random.randint(1, 720))))
    # eventos administrativos
    for accion, det in [("aprobacion", "Aprobó el registro de un docente"),
                        ("cambio_rol", "Cambió rol de auxiliar a contador"),
                        ("suspension", "Suspendió una cuenta por retiro"),
                        ("registro", "Creó cuenta de docente nuevo")]:
        s.add(LogAcceso(usuario_id=None, institucion_id=ie.id, usuario_nombre="Rectoría",
                        accion=accion, detalle=det,
                        ip=random.choice(IPS) + str(random.randint(2, 250)),
                        fecha=hoy - timedelta(days=random.randint(1, 20))))
    s.commit()


def _seed_clases_ricas(s, ie):
    """Convierte algunas clases planas en clases con TEMAS, video y materiales
    (asi es como el docente las va a crear de ahora en adelante)."""
    if s.query(TemaClase).count() > 0:
        return
    PLANTILLAS = {
        "Matemáticas": {
            "titulo": "Fracciones en la vida real",
            "color": "#0E7C86", "portada": "➗",
            "objetivos": ["Reconocer fracciones en situaciones cotidianas",
                          "Sumar y restar fracciones con el mismo denominador",
                          "Resolver problemas de reparto con fracciones"],
            "video": "https://www.youtube.com/watch?v=nGWPZjnbBcs",
            "temas": [
                ("¿Qué es una fracción?", "Partir algo en pedazos iguales y nombrarlos.",
                 [{"t": "texto", "h": "La idea de repartir",
                   "p": "Cuando partes una arepa en 4 pedazos iguales y te comes 1, te comiste 1/4. El número de abajo (denominador) dice en cuántos pedazos partiste; el de arriba (numerador) dice cuántos tomaste."},
                  {"t": "ejemplo", "h": "En la tienda",
                   "p": "Media libra de queso es 1/2 libra. Un cuarto de pollo es 1/4 del pollo. Ya usas fracciones todos los días sin darte cuenta."},
                  {"t": "tip", "h": "Truco para recordar",
                   "p": "El DENOMINADOR es el que DENOMINA (le pone nombre): medios, tercios, cuartos. El numerador solo cuenta cuántos hay."}],
                 [{"q": "Si partes una torta en 8 y te comes 3 pedazos, ¿qué fracción comiste?",
                   "op": ["3/8", "8/3", "3/5"], "correcta": 0,
                   "explica": "Comiste 3 de los 8 pedazos: 3/8."}], 12),
                ("Sumar y restar fracciones", "Cuando el denominador es igual, es más fácil de lo que parece.",
                 [{"t": "texto", "h": "Denominadores iguales",
                   "p": "Si los pedazos son del mismo tamaño, solo sumas cuántos tienes. 2/5 + 1/5 = 3/5. El denominador NO se suma: sigue diciendo el tamaño del pedazo."},
                  {"t": "ojo", "h": "El error clásico",
                   "p": "2/5 + 1/5 NO es 3/10. Si sumas los denominadores estás cambiando el tamaño de los pedazos, y eso no pasó."}],
                 [{"q": "¿Cuánto es 3/7 + 2/7?",
                   "op": ["5/14", "5/7", "6/7"], "correcta": 1,
                   "explica": "Se suman los numeradores y el denominador queda igual: 5/7."}], 15),
                ("Problemas de reparto", "Usar fracciones para resolver situaciones reales.",
                 [{"t": "texto", "h": "De la vida al cuaderno",
                   "p": "La mayoría de problemas de fracciones son de repartir: comida, dinero, tiempo o trabajo. Identifica primero el entero y luego en cuántas partes se divide."},
                  {"t": "ejemplo", "h": "Un caso real",
                   "p": "Tres amigos compran un mercado de $60.000 y lo pagan por partes iguales. Cada uno pone 1/3, es decir $20.000. Si uno pone $30.000, puso 1/2 y le deben la diferencia."}],
                 [{"q": "Cuatro personas se reparten $80.000 por partes iguales. ¿Cuánto le toca a cada una?",
                   "op": ["$20.000", "$40.000", "$16.000"], "correcta": 0,
                   "explica": "1/4 de $80.000 = $20.000."}], 18),
            ],
        },
        "Ciencias Naturales": {
            "titulo": "El ciclo del agua y nuestro río",
            "color": "#0EA5E9", "portada": "💧",
            "objetivos": ["Explicar las etapas del ciclo del agua",
                          "Relacionar el ciclo con el río de nuestro municipio",
                          "Proponer acciones para cuidar el agua"],
            "video": "https://www.youtube.com/watch?v=Bs3JsIsVLnk",
            "temas": [
                ("Las cuatro etapas", "Evaporación, condensación, precipitación e infiltración.",
                 [{"t": "texto", "h": "Un viaje que nunca termina",
                   "p": "El sol calienta el agua del río y la convierte en vapor (evaporación). El vapor sube, se enfría y forma nubes (condensación). Cuando las gotas pesan, cae la lluvia (precipitación). Parte del agua se mete en la tierra (infiltración) y vuelve al río."},
                  {"t": "tabla", "h": "Cada etapa",
                   "filas": [["Evaporación", "El agua se vuelve vapor por el calor del sol"],
                             ["Condensación", "El vapor se enfría y forma nubes"],
                             ["Precipitación", "Cae como lluvia, granizo o nieve"],
                             ["Infiltración", "El agua entra al suelo y alimenta pozos y quebradas"]]}],
                 [{"q": "¿Qué etapa forma las nubes?",
                   "op": ["Evaporación", "Condensación", "Infiltración"], "correcta": 1,
                   "explica": "El vapor sube, se enfría y se condensa en gotitas: eso son las nubes."}], 14),
                ("El río Magdalena y nosotros", "Cómo nos afecta el ciclo del agua aquí.",
                 [{"t": "texto", "h": "Nuestro territorio",
                   "p": "En el Sur de Bolívar vivimos del río. En temporada de lluvias sube y puede inundar; en verano baja y escasea el agua. Entender el ciclo ayuda a prepararnos."},
                  {"t": "tip", "h": "Lo que sí podemos hacer",
                   "p": "Sembrar árboles cerca de las quebradas, no botar basura al agua y cuidar los nacimientos. El agua que cuidas hoy es la que tomas mañana."}],
                 [{"q": "¿Por qué se seca una quebrada si talan los árboles alrededor?",
                   "op": ["Porque los árboles dan sombra", "Porque sin raíces el agua no se infiltra y se va rápido", "No tiene relación"],
                   "correcta": 1,
                   "explica": "Las raíces ayudan a que el agua entre al suelo. Sin ellas, escurre y la quebrada se seca."}], 16),
            ],
        },
        "Lenguaje": {
            "titulo": "Escribir para que te lean",
            "color": "#7C3AED", "portada": "✍️",
            "objetivos": ["Organizar ideas antes de escribir",
                          "Escribir párrafos con una idea principal clara",
                          "Revisar y corregir el propio texto"],
            "video": "",
            "temas": [
                ("Antes de escribir: pensar", "El error es empezar por la primera frase.",
                 [{"t": "texto", "h": "Primero la idea, después las palabras",
                   "p": "Antes de escribir, responde tres preguntas: ¿de qué voy a hablar?, ¿a quién le escribo?, ¿qué quiero que entienda o haga? Con eso claro, escribir es mucho más fácil."},
                  {"t": "tip", "h": "La lluvia de ideas",
                   "p": "Escribe en desorden todo lo que se te ocurra del tema, sin juzgar. Después escoges lo mejor y lo ordenas. Nunca empieces por la hoja en blanco esperando la frase perfecta."}],
                 [{"q": "¿Qué se debe hacer primero al escribir un texto?",
                   "op": ["La introducción", "Definir tema, destinatario y propósito", "El título"],
                   "correcta": 1,
                   "explica": "Sin saber para quién y para qué escribes, el texto sale sin rumbo."}], 12),
                ("El párrafo: una idea a la vez", "Cada párrafo defiende una sola idea.",
                 [{"t": "texto", "h": "La regla de oro",
                   "p": "Un párrafo = una idea principal + las frases que la explican o la ejemplifican. Cuando cambias de idea, cambias de párrafo. Así el lector no se pierde."},
                  {"t": "ojo", "h": "Párrafos de una página",
                   "p": "Si tu párrafo tiene diez líneas seguidas sin punto aparte, seguramente metiste tres ideas juntas. Sepáralas."}],
                 [{"q": "¿Cuántas ideas principales debe tener un párrafo?",
                   "op": ["Una", "Tres", "Las que quepan"], "correcta": 0,
                   "explica": "Una idea por párrafo: es lo que hace que un texto se entienda."}], 14),
            ],
        },
    }
    salones = s.query(Salon).filter(Salon.institucion_id == ie.id).limit(6).all()
    creadas = 0
    for i, sal in enumerate(salones):
        materia = list(PLANTILLAS.keys())[i % len(PLANTILLAS)]
        P = PLANTILLAS[materia]
        a = ActividadAula(
            salon_id=sal.id, titulo=P["titulo"], tipo="clase", materia=materia,
            descripcion=f"Clase completa de {materia} organizada por temas. "
                        "Avanza a tu ritmo: cada tema tiene su explicación, su material y su quiz.",
            periodo_numero=3, corte="Corte 1",
            duracion_min=sum(t[4] for t in P["temas"]),
            portada=P["portada"], color=P["color"], video_url=P["video"] or None,
            objetivos=json.dumps(P["objetivos"], ensure_ascii=False),
            materiales=json.dumps([
                {"tipo": "pdf", "nombre": f"guia_{slug(materia)}.pdf", "url": None, "tamano": "820 KB"},
                {"tipo": "presentacion", "nombre": f"diapositivas_{slug(materia)}.pptx", "url": None, "tamano": "2.1 MB"},
            ], ensure_ascii=False),
            estado="publicada", creado_por="Docente", generado_ia=(i % 3 == 0),
            fecha_limite=HOY + timedelta(days=random.randint(4, 15)))
        s.add(a)
        s.flush()
        for orden, (tit, res, cont, quiz, dur) in enumerate(P["temas"], start=1):
            s.add(TemaClase(
                actividad_id=a.id, titulo=tit, resumen=res,
                contenido=json.dumps(cont, ensure_ascii=False),
                video_url=(P["video"] if orden == 1 and P["video"] else None),
                duracion_min=dur,
                materiales=json.dumps([{"tipo": "pdf", "nombre": f"taller_tema{orden}.pdf",
                                        "url": None, "tamano": "340 KB"}], ensure_ascii=False),
                quiz=json.dumps(quiz, ensure_ascii=False), orden=orden))
        for e in s.query(Estudiante).filter(Estudiante.salon_id == sal.id).all():
            ya = s.query(EntregaAula).filter(EntregaAula.actividad_id == a.id,
                                             EntregaAula.estudiante_id == e.id).first()
            if not ya:
                estado = random.choices(["pendiente", "entregado", "revisado"], weights=[45, 30, 25])[0]
                s.add(EntregaAula(
                    actividad_id=a.id, estudiante_id=e.id, estado=estado,
                    respuesta=("Profe, aquí está mi taller. Resolví los ejercicios del 1 al 5 "
                               "y me quedó duda en el último punto." if estado != "pendiente" else None),
                    archivo=(f"taller_{slug(e.nombre.split()[0])}.pdf" if estado != "pendiente" and random.random() < 0.6 else None),
                    nota=round(random.uniform(2.8, 5.0), 1) if estado == "revisado" else None,
                    retro=("Buen trabajo, revisa la ortografía." if estado == "revisado" else None),
                    fecha_entrega=AHORA - timedelta(days=random.randint(0, 6)) if estado != "pendiente" else None))
        creadas += 1
    s.commit()

    # progreso de algunos alumnos en los temas
    temas_all = s.query(TemaClase).all()
    for t in temas_all:
        ests = s.query(Estudiante).join(ActividadAula, ActividadAula.id == t.actividad_id).filter(
            Estudiante.salon_id == ActividadAula.salon_id).limit(12).all()
        for e in ests:
            if random.random() < 0.45:
                s.add(ProgresoTemaClase(estudiante_id=e.id, tema_id=t.id,
                                        actividad_id=t.actividad_id, completado=True,
                                        quiz_puntaje=random.choice([60, 80, 100]),
                                        minutos=random.randint(6, 20),
                                        fecha=AHORA - timedelta(days=random.randint(1, 12))))
    s.commit()


def _seed_grabaciones(s, ie):
    """Biblioteca de clases en vivo ya grabadas (punto 17)."""
    if s.query(GrabacionClase).count() > 0:
        return
    salones = s.query(Salon).filter(Salon.institucion_id == ie.id).limit(5).all()
    CLASES = [
        ("Ecuaciones de primer grado", "Matemáticas", 52,
         "Repaso completo de despeje con ejercicios en el tablero. Minuto 12: el método de la balanza."),
        ("La célula y sus partes", "Ciencias Naturales", 45,
         "Explicación con el microscopio del laboratorio. Incluye la práctica de la cebolla."),
        ("Comprensión lectora: el cuento", "Lenguaje", 48,
         "Lectura guiada y análisis de personajes. Al final, taller en grupo."),
        ("Historia de Colombia: la Independencia", "Sociales", 50,
         "Línea de tiempo desde 1810. Se resolvieron las dudas del quiz anterior."),
        ("Present simple vs present continuous", "Inglés", 44,
         "Explicación con ejemplos del día a día y práctica oral."),
    ]
    for i, (tit, mat, dur, res) in enumerate(CLASES):
        sal = salones[i % len(salones)] if salones else None
        if not sal:
            break
        doc = s.query(Personal).filter(Personal.id == sal.director_id).first()
        s.add(GrabacionClase(
            salon_id=sal.id, institucion_id=ie.id, titulo=tit, materia=mat,
            docente=doc.nombre if doc else "Docente",
            fecha=AHORA - timedelta(days=random.randint(2, 40)),
            duracion_min=dur, video_url=None, resumen=res,
            transcripcion=None, n_vistas=random.randint(3, 48)))
    s.commit()


def _seed_dominios(s):
    """Configuracion de dominio y contrato comercial de cada tenant (puntos 1 y 2)."""
    if s.query(ConfigDominio).count() > 0:
        return
    PROVS = ["hostinger", "godaddy", "cloudflare", "namecheap"]
    ESTADOS = ["activo", "propagando", "pendiente", "activo", "sin_configurar"]
    PLANES = [("institucional", 4800000, 300), ("piloto", 1200000, 100),
              ("municipal", 18000000, 2000)]
    for i, t in enumerate(s.query(Tenant).all()):
        base = (t.dominio or "institucion.edu.co").replace("https://", "")
        partes = base.split(".")
        sub = partes[0] if len(partes) > 2 else "sistema"
        raiz = ".".join(partes[1:]) if len(partes) > 2 else base
        est = ESTADOS[i % len(ESTADOS)]
        s.add(ConfigDominio(
            tenant_id=t.id, dominio=raiz, subdominio=sub,
            proveedor=PROVS[i % len(PROVS)], modo_montaje="subdominio",
            ip_servidor="203.0.113.45", estado_dns=est,
            ssl_estado="activo" if est == "activo" else "pendiente",
            wordpress_url=f"https://{raiz}" if i % 2 == 0 else None,
            integracion_wp="enlace" if i % 2 == 0 else "ninguna",
            verificado=(est == "activo"),
            ultima_verificacion=AHORA - timedelta(days=random.randint(1, 20)) if est != "sin_configurar" else None,
            notas="La página institucional está en WordPress; el sistema va en el subdominio." if i % 2 == 0 else None))
        plan, valor, usuarios = PLANES[i % len(PLANES)]
        ini = HOY - timedelta(days=random.randint(30, 330))
        fin = ini + timedelta(days=365)
        dias = (fin - HOY).days
        pagos = []
        n_cuotas = random.randint(1, 3)
        for c in range(n_cuotas):
            pagos.append({"fecha": (ini + timedelta(days=c * 120)).isoformat(),
                          "valor": round(valor / 3),
                          "concepto": f"Cuota {c + 1} de 3 · suscripción anual"})
        s.add(Suscripcion(
            tenant_id=t.id, plan=plan, fecha_inicio=ini, fecha_fin=fin,
            valor_anual=valor, n_usuarios_incluidos=usuarios,
            estado="vencida" if dias < 0 else ("por_vencer" if dias <= 45 else "activa"),
            facturas=json.dumps(pagos, ensure_ascii=False)))
    s.commit()


def _seed_horarios_asignados(s, ie):
    """Convierte los horarios JSON en asignaciones reales con docente."""
    if s.query(AsignacionHorario).count() > 0:
        return
    docentes = s.query(Personal).filter(Personal.institucion_id == ie.id,
                                        Personal.rol == "docente").all()
    if not docentes:
        return
    por_area = {}
    for d in docentes:
        if d.area:
            por_area.setdefault(d.area, []).append(d)
    for sal in s.query(Salon).filter(Salon.institucion_id == ie.id).all():
        try:
            hs = json.loads(sal.horarios) if sal.horarios else []
        except Exception:
            hs = []
        for h in hs:
            mat = h.get("materia")
            hora = h.get("hora") or "06:45-07:35"
            ini, fin = (hora.split("-") + ["", ""])[:2]
            cand = por_area.get(mat) or docentes
            doc = random.choice(cand)
            s.add(AsignacionHorario(
                institucion_id=ie.id, sede_id=sal.sede_id, salon_id=sal.id,
                personal_id=doc.id, materia=mat or "General",
                dia=h.get("dia") or "Lunes", hora_inicio=ini.strip(),
                hora_fin=fin.strip(), asignado_por="Coordinación", estado="activo"))
    s.commit()


def _seed_revisiones(s, ie):
    """Algunas clases ya revisadas por coordinación."""
    if s.query(RevisionTema).count() > 0:
        return
    salones = [x.id for x in s.query(Salon).filter(Salon.institucion_id == ie.id).all()]
    acts = s.query(ActividadAula).filter(ActividadAula.salon_id.in_(salones)).limit(6).all()
    OBS = [("aprobado", "Material completo y bien organizado. Buen uso de ejemplos del contexto."),
           ("ajustes", "Falta anexar la guía de trabajo. Por favor súbela antes del viernes."),
           ("aprobado", "Los temas corresponden al plan de área. Aprobado."),
           ("ajustes", "El quiz solo tiene una pregunta; agrega al menos tres.")]
    for i, a in enumerate(acts[:4]):
        est, obs = OBS[i % len(OBS)]
        s.add(RevisionTema(actividad_id=a.id, institucion_id=ie.id,
                           revisor="Coordinación académica", estado=est,
                           observacion=obs,
                           fecha=AHORA - timedelta(days=random.randint(1, 12))))
    s.commit()


def _seed_legal(s, ie):
    """Perfil legal y rejilla, con la estructura de los documentos reales."""
    if s.query(PerfilLegal).count() > 0:
        return
    rector = s.query(Personal).filter(Personal.institucion_id == ie.id,
                                      Personal.rol == "rector").first()
    pl = PerfilLegal(
        institucion_id=ie.id,
        nombre_oficial="INSTITUCIÓN EDUCATIVA TÉCNICA AGROPECUARIA Y EMPRESARIAL",
        sigla="IETAE",
        ordenanza="020 de Noviembre 29 de 2002",
        decreto="773 del 10 de octubre de 2003",
        licencia="Resolución 149 del 25 de Febrero de 2011",
        nit="829003637", nit_dv="2", dane=ie.codigo_dane,
        direccion="Sede principal, zona urbana",
        municipio=ie.municipio, departamento=ie.departamento,
        telefono="3145567788", email="contacto@institucion.edu.co",
        rector_nombre=(rector.nombre if rector else ie.rector),
        rector_cc="8828174", rector_cc_lugar=ie.municipio,
        rector_acta_posesion="331",
        rector_fecha_posesion=date(2021, 3, 3),
        contador_nombre="Contaduría institucional", contador_tp="TP-98765-T",
        logo_izq=ie.logo,
        pie_pagina="Fondo de Servicios Educativos — Decreto 1075 de 2015",
        consec_cdp="04", consec_rp="05", vigencia=HOY.year,
        es_demo=True, configurado_por="Datos de demostración",
        consejo_acta_vigente="001", consejo_fecha=date(HOY.year, 2, 15),
        consejo_miembros=json.dumps([
            {"rol": "Rector(a)", "nombre": (rector.nombre if rector else ie.rector)},
            {"rol": "Representante de los docentes", "nombre": "Por designar"},
            {"rol": "Representante de los padres", "nombre": "Por designar"},
            {"rol": "Representante de los estudiantes", "nombre": "Por designar"},
            {"rol": "Representante del sector productivo", "nombre": "Por designar"},
        ], ensure_ascii=False))
    s.add(pl)
    s.commit()

    # Rejilla con la estructura real: rubro → CDP → invitación → contrato → RP
    PROCESOS = [
        ("2.1.2.1.14", "Suministro de alimentos", "Otras transferencias",
         19470325, "SUMINISTRO DE VÍVERES PARA EL PROGRAMA DE ALIMENTACIÓN ESCOLAR",
         date(HOY.year, 1, 22), 30, "50190000"),
        ("2.2.1.2.01", "Fortalecimiento Gestión Administrativa", "Recurso de gratuidad",
         7599998, "APOYO LOGÍSTICO PARA EL PROCESO DE MATRÍCULAS Y ARCHIVO",
         date(HOY.year, 4, 23), 20, "80101500"),
        ("2.1.3.1.3.02", "C-Dotaciones pedagógicas", "Recurso de gratuidad",
         6845000, "SUMINISTRO DE MATERIALES DIDÁCTICOS PARA LAS SEDES",
         date(HOY.year, 4, 24), 15, "60105000"),
        ("2.1.2.1.02", "Materiales y suministros", "Recurso de gratuidad",
         10142887, "SUMINISTRO DE MATERIALES DE ASEO PARA LA INSTITUCIÓN",
         date(HOY.year, 5, 6), 10, "47131500"),
        ("2.1.3.2.02", "Mantenimiento de mobiliario", "Recurso de gratuidad",
         7250000, "MANTENIMIENTO DE VENTILADORES DE TECHO DE LAS AULAS",
         date(HOY.year, 7, 9), 5, "72154100"),
        ("2.1.3.2.01", "Mantenimiento de infraestructura", "Recurso de gratuidad",
         32754650, "DESMONTE Y MONTAJE DE CUBIERTA DEL BLOQUE ADMINISTRATIVO",
         date(HOY.year, 7, 9), 30, "72131600"),
    ]
    provs = s.query(Contratista).all()
    for i, (rc, rn, fu, val, desc, fcdp, plazo, uns) in enumerate(PROCESOS, start=1):
        prov = provs[(i - 1) % len(provs)] if provs else None
        f = FilaRejilla(
            institucion_id=ie.id, vigencia=HOY.year, consecutivo=i,
            rubro_codigo=rc, rubro_nombre=rn, fuente=fu, valor=val,
            unspsc=uns, descripcion=desc, plazo_dias=plazo,
            cdp_num=f"04-{i}", cdp_fecha=fcdp,
            cotizacion_fecha=fcdp - timedelta(days=7),
            proyecto_fecha=fcdp - timedelta(days=2),
            invitacion_num=f"{HOY.year}{i:02d}",
            invitacion_fecha=fcdp + timedelta(days=5),
            cierre_fecha=fcdp + timedelta(days=6),
            evaluacion_fecha=fcdp + timedelta(days=7),
            aceptacion_fecha=fcdp + timedelta(days=8),
            contrato_num=f"{HOY.year}{i:02d}",
            contrato_fecha=fcdp + timedelta(days=8),
            contratista_id=prov.id if prov else None,
            contratista_nombre=prov.nombre if prov else None,
            contratista_doc=prov.nit if prov else None,
            rp_num=f"05-{i}", rp_fecha=fcdp + timedelta(days=8),
            acta_inicio_fecha=fcdp + timedelta(days=8),
            acta_final_fecha=fcdp + timedelta(days=8 + plazo),
            liquidacion_fecha=fcdp + timedelta(days=8 + plazo + 14),
            estado="ejecutado" if i <= 4 else "en_proceso")
        s.add(f)
    s.commit()

    # Documentos generados de los primeros procesos
    for f in s.query(FilaRejilla).filter(FilaRejilla.consecutivo <= 4).all():
        for t, lbl, fecha in [
                ("solicitud_cotizacion", "📨 Solicitud de cotización", f.cotizacion_fecha),
                ("estudios_previos", "📋 Estudios previos", f.proyecto_fecha),
                ("invitacion", "📢 Invitación pública", f.invitacion_fecha),
                ("contrato", "📜 Contrato", f.contrato_fecha),
                ("acta_inicio", "🚀 Acta de inicio", f.acta_inicio_fecha)]:
            s.add(DocumentoLegal(
                institucion_id=ie.id, rejilla_id=f.id, tipo=t,
                numero=f.contrato_num if t == "contrato" else f"{t}-{f.consecutivo}",
                titulo=lbl, fecha=fecha, contenido=json.dumps({}, ensure_ascii=False),
                generado_por="Contratación", estado="firmado", version=1,
                creado=AHORA))
    s.commit()

    # Correspondencia de ejemplo
    CARTAS = [
        ("derecho_peticion", "Solicitud de información sobre asignación de recursos PAE",
         "Secretaría de Educación Departamental", "Secretario de Educación",
         "Gobernación de Bolívar", "enviado", 6),
        ("oficio", "Remisión de informe de ejecución presupuestal primer semestre",
         "Secretaría de Educación Departamental", "Jefe de Cobertura",
         "Gobernación de Bolívar", "enviado", 20),
        ("respuesta_dp", "Respuesta a derecho de petición sobre cupos escolares",
         "María Fernanda Ospina", "Acudiente", None, "respondido", 12),
        ("circular", "Convocatoria a reunión de padres de familia — cierre de período",
         "Padres de familia", None, None, "enviado", 3),
    ]
    for i, (tipo, asunto, dest, cargo, ent, est, dias) in enumerate(CARTAS, 1):
        f0 = HOY - timedelta(days=dias)
        s.add(Correspondencia(
            institucion_id=ie.id, tipo=tipo, radicado=f"{HOY.year}-{i:04d}",
            asunto=asunto, destinatario=dest, destinatario_cargo=cargo,
            destinatario_entidad=ent,
            remitente=(rector.nombre if rector else ie.rector),
            cuerpo=("En atención a lo dispuesto en la normativa vigente, me permito "
                    "presentar la presente comunicación para su trámite correspondiente."),
            anexos=json.dumps([], ensure_ascii=False),
            fecha=f0,
            fecha_limite=(f0 + timedelta(days=21)) if tipo == "derecho_peticion" else None,
            estado=est, creado_por="Rectoría", creado=AHORA))
    s.commit()


def _seed_secretaria(s, ie):
    """Planeaciones, notas historicas y certificados de ejemplo."""
    if s.query(PlaneacionDocente).count() > 0:
        return
    docentes = s.query(Personal).filter(Personal.institucion_id == ie.id,
                                        Personal.rol == "docente").limit(6).all()
    salones = s.query(Salon).filter(Salon.institucion_id == ie.id).limit(6).all()
    PLANES = [
        ("Plan semanal — Fracciones y decimales", "Matemáticas", "semanal", "aprobada",
         "Excelente secuencia. Los ejemplos del contexto son muy buenos.", True),
        ("Plan mensual — El ciclo del agua y el río", "Ciencias Naturales", "mensual", "enviada", None, False),
        ("Plan de período — Comprensión lectora", "Lenguaje", "periodo", "ajustes",
         "Falta anexar las guías de trabajo y detallar la evaluación de la semana 3.", False),
        ("Plan semanal — La Independencia", "Sociales", "semanal", "borrador", None, False),
        ("Plan semanal — Present simple", "Inglés", "semanal", "aprobada",
         "Aprobado. Buen uso de material audiovisual.", True),
    ]
    for i, (tit, mat, tipo, est, obs, ia) in enumerate(PLANES):
        d = docentes[i % len(docentes)] if docentes else None
        sal = salones[i % len(salones)] if salones else None
        if not d:
            break
        dias = {"semanal": 7, "mensual": 30, "periodo": 60}[tipo]
        d0 = HOY - timedelta(days=random.randint(2, 15))
        s.add(PlaneacionDocente(
            institucion_id=ie.id, personal_id=d.id, salon_id=sal.id if sal else None,
            materia=mat, periodo_numero=3, corte="Corte 1", tipo=tipo, titulo=tit,
            desde=d0, hasta=d0 + timedelta(days=dias),
            objetivos=json.dumps([
                f"Comprender los conceptos centrales de {mat.lower()}",
                "Aplicar lo aprendido en situaciones del contexto",
                "Desarrollar el trabajo colaborativo"], ensure_ascii=False),
            contenidos=json.dumps([
                {"semana": 1, "tema": "Introducción y conceptos base",
                 "actividades": "Exploración de saberes previos, explicación magistral, taller en parejas",
                 "recursos": "Tablero, guía impresa, video"},
                {"semana": 2, "tema": "Desarrollo y aplicación",
                 "actividades": "Ejercicios guiados, trabajo en grupo, socialización",
                 "recursos": "Guía de ejercicios, material concreto"},
                {"semana": 3, "tema": "Profundización",
                 "actividades": "Resolución de casos del contexto local, exposiciones",
                 "recursos": "Casos impresos, cartelera"},
                {"semana": 4, "tema": "Evaluación y refuerzo",
                 "actividades": "Evaluación escrita, plan de refuerzo para quien lo necesite",
                 "recursos": "Evaluación impresa"}], ensure_ascii=False),
            metodologia=("Aprendizaje basado en problemas del contexto rural, con trabajo "
                         "colaborativo y uso de material concreto disponible en la institución."),
            evaluacion=("Evaluación continua: participación (20%), talleres (30%), "
                        "evaluación escrita (40%), autoevaluación (10%)."),
            materiales=json.dumps([{"tipo": "pdf", "nombre": f"guia_{slug(mat)}.pdf"},
                                   {"tipo": "documento", "nombre": "taller_semana1.docx"}],
                                  ensure_ascii=False),
            generado_ia=ia, estado=est,
            revisor=("Coordinación académica" if est in ("aprobada", "ajustes") else None),
            observacion_revisor=obs,
            fecha_envio=(AHORA - timedelta(days=random.randint(1, 8))
                         if est != "borrador" else None),
            fecha_revision=(AHORA - timedelta(days=random.randint(0, 3))
                            if est in ("aprobada", "ajustes") else None),
            creado=AHORA - timedelta(days=random.randint(5, 20))))
    s.commit()

    # Notas historicas importadas
    ests = s.query(Estudiante).filter(Estudiante.institucion_id == ie.id).limit(120).all()
    MATS = ["MATEMATICAS", "LENGUAJE", "CIENCIAS NATURALES", "SOCIALES", "INGLES",
            "EDUCACION FISICA", "ARTISTICA", "ETICA"]
    lote = "SIM" + str(HOY.year)[-2:] + "01"
    n = 0
    for e in ests:
        doc = str(getattr(e, "documento", None) or e.codigo_acceso or "")
        if not doc:
            continue
        for anio in (HOY.year - 2, HOY.year - 1):
            for per in (1, 2, 3, 4):
                for mat in random.sample(MATS, 5):
                    s.add(NotaHistorica(
                        institucion_id=ie.id, estudiante_id=e.id, documento=doc,
                        nombre_origen=e.nombre, anio=anio,
                        grado=str(max(1, int(e.grado or 6) - (HOY.year - anio))),
                        periodo=per, materia=mat,
                        nota=round(random.uniform(2.5, 4.8), 1),
                        fallas=random.randint(0, 4), origen="simat", lote=lote,
                        conciliado=True))
                    n += 1
    s.add(ImportacionSIMAT(
        institucion_id=ie.id, lote=lote, archivo="notas_simat_historico.csv",
        origen="simat", n_filas=n + 14, n_cruzadas=n, n_sin_cruce=14, n_notas=n,
        detalle=json.dumps([{"documento": f"10987654{i:02d}", "nombre": f"ESTUDIANTE RETIRADO {i}"}
                            for i in range(1, 15)], ensure_ascii=False),
        estado="procesado", fecha=AHORA - timedelta(days=12), hecho_por="Secretaría académica"))
    s.commit()

    # Certificados
    TIPOS = [("estudio", "emitido"), ("notas", "emitido"), ("matricula", "solicitado"),
             ("asistencia", "solicitado"), ("recuperacion", "emitido"), ("paz_salvo", "emitido")]
    for i, (t, est) in enumerate(TIPOS, 1):
        e = ests[i % len(ests)] if ests else None
        if not e:
            break
        s.add(CertificadoEmitido(
            institucion_id=ie.id, estudiante_id=e.id, tipo=t,
            numero=f"CERT-{HOY.year}-{i:04d}",
            periodo="Período 3" if t == "notas" else None,
            datos=json.dumps({"materia": "Matemáticas", "nota": "3.5"} if t == "recuperacion" else {},
                             ensure_ascii=False),
            solicitado=AHORA - timedelta(days=random.randint(1, 10)),
            emitido=(AHORA - timedelta(days=random.randint(0, 3)) if est == "emitido" else None),
            emitido_por=("Secretaría académica" if est == "emitido" else None),
            estado=est,
            codigo_verificacion=("".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=10))
                                 if est == "emitido" else None),
            n_descargas=random.randint(0, 4) if est == "emitido" else 0))
    s.commit()


def main():
    engine = get_engine(settings.DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_sessionmaker(engine)
    s = Session()

    # ── Períodos 2026 (P1 y P2 CERRADOS, P3 activo/abierto) ─────────
    periodos = []
    for i, (nom, ini, fin, act, cer) in enumerate([
        ("Primer período", "2026-01-27", "2026-04-03", False, True),
        ("Segundo período", "2026-04-06", "2026-06-12", False, True),
        ("Tercer período", "2026-07-06", "2026-09-11", True, False),
        ("Cuarto período", "2026-09-14", "2026-11-27", False, False),
    ], start=1):
        p = Periodo(nombre=nom, numero=i, peso=25.0, activo=act, cerrado=cer,
                    fecha_inicio=date.fromisoformat(ini), fecha_fin=date.fromisoformat(fin))
        s.add(p); periodos.append(p)
    s.flush()

    # ── Config del sistema ──────────────────────────────────────────
    s.add(ConfigSistema(clave="smmlv", valor="1623500"))       # SMMLV 2026 (parametrizable)
    s.add(ConfigSistema(clave="tope_fse_smmlv", valor="20"))   # Decreto 4791/2008 art. 17

    print("Generando instituciones, tenants, personal, salones y estudiantes...")
    total_est = 0
    ie_demo = None
    for (municipio, depto), instituciones in ECOSISTEMA.items():
        s.add(Tenant(tipo="secretaria", nombre=f"Secretaría de Educación de {municipio}",
                     dominio=f"{slug(municipio)}.gyverlabs.co", color="#D97706",
                     municipio=municipio, departamento=depto,
                     modulos="dashboard,reportes,censo,datos", estado="activo",
                     creado=HOY - timedelta(days=random.randint(120, 300))))
        for nombre_ie, dane, sector, grados in instituciones:
            rector_nom = nombre_aleatorio()
            zona_ie = "rural" if "rural" in sector else "urbana"
            ie = Institucion(nombre=nombre_ie, codigo_dane=dane, municipio=municipio,
                             departamento=depto, sector=sector, rector=rector_nom,
                             direccion=(f"Cra {random.randint(2,15)} # {random.randint(1,30)}-{random.randint(2,90)}"
                                        if zona_ie == "urbana" else f"Vereda {random.choice(VEREDAS)}"),
                             telefono=tel())
            s.add(ie); s.flush()
            if ie_demo is None:
                ie_demo = ie

            s.add(Tenant(tipo="colegio", nombre=nombre_ie,
                         dominio=f"sistema.{slug(nombre_ie.replace('I.E.',''))}.edu.co",
                         color="#0E7C86" if zona_ie == "urbana" else "#1A7A4A",
                         institucion_id=ie.id, municipio=municipio, departamento=depto,
                         modulos="asistencia,aula,srd,fse" + (",contratos" if ie.id == 1 else ""),
                         estado="activo", creado=HOY - timedelta(days=random.randint(60, 240))))

            def alta(nombre, rol, area, prof, exp, email=None):
                hv = hv_json(prof, exp)
                p = Personal(institucion_id=ie.id, nombre=nombre, rol=rol, area=area,
                             email=email, telefono=tel(), documento=cc(), profesion=prof,
                             experiencia_anios=exp,
                             fecha_vinculacion=HOY - timedelta(days=int(exp * 365 * random.uniform(0.3, 0.8))),
                             hoja_vida=json.dumps(hv, ensure_ascii=False), hv_score=hv_score(hv, exp))
                s.add(p)
                return p

            alta(rector_nom, "rector", "Directivo", "Licenciatura + Especialización en Gerencia Educativa",
                 random.randint(12, 25), "rector@" + dane + ".edu.co")
            n_coord = 2 if len(grados) > 4 else 1
            for _ in range(n_coord):
                alta(nombre_aleatorio(), "coordinador", "Coordinación",
                     "Licenciatura + Especialización en Coordinación Académica", random.randint(8, 18))
            docentes = []
            for a in AREAS[: (7 if len(grados) > 4 else 4)]:
                d = alta(nombre_aleatorio(), "docente", a,
                         random.choice(PROFESIONES_DOC), random.randint(2, 20))
                docentes.append(d)
            alta(nombre_aleatorio(), "psicoorientacion", "Psicoorientación",
                 "Psicología — Universidad de Cartagena", random.randint(3, 12))
            alta(nombre_aleatorio(), "vigilante", "Seguridad", "Bachiller + curso de vigilancia", random.randint(2, 15))
            alta(nombre_aleatorio(), "servicios", "Servicios Generales", "Bachiller", random.randint(1, 20))
            s.flush()

            for per in periodos:
                if not per.fecha_inicio:
                    continue
                mitad = per.fecha_inicio + (per.fecha_fin - per.fecha_inicio) / 2
                s.add(Corte(institucion_id=ie.id, periodo_numero=per.numero, nombre="Corte 1",
                            fecha_inicio=per.fecha_inicio, fecha_fin=mitad))
                s.add(Corte(institucion_id=ie.id, periodo_numero=per.numero, nombre="Corte 2",
                            fecha_inicio=mitad + timedelta(days=1), fecha_fin=per.fecha_fin))

            _nuevos_est = []
            DIAS = ["Lunes","Martes","Miércoles","Jueves","Viernes"]
            HORAS = ["6:45-8:15","8:15-9:45","10:15-11:45"]
            for g in grados:
                grupos = ["01"]
                if zona_ie == "urbana" and g in ("6", "9"):
                    grupos.append("02")
                for grp in grupos:
                    director = random.choice(docentes)
                    horario = []
                    for dia in DIAS:
                        mats = random.sample(MATERIAS, k=3)
                        for h_i, hh in enumerate(HORAS):
                            horario.append({"dia": dia, "hora": hh, "materia": mats[h_i]})
                    sal = Salon(institucion_id=ie.id, nombre=f"{g}{grp}", grado=g,
                                jornada="Mañana" if zona_ie == "urbana" else "Única",
                                director_id=director.id,
                                horarios=json.dumps(horario, ensure_ascii=False))
                    s.add(sal); s.flush()

                    for per_num in (1, 2, 3):
                        for corte_n, mitad in (("Corte 1", 0), ("Corte 2", 1)):
                            for mat in random.sample(MATERIAS, k=2):
                                banco = TEMAS_BANCO[mat]
                                s.add(TemaPlan(salon_id=sal.id, periodo_numero=per_num, corte=corte_n,
                                               materia=mat, tema=banco[(per_num * 2 + mitad) % len(banco)],
                                               detalle="Guías + trabajo en clase + evaluación de corte"))

                    n_est = random.randint(16, 30) if zona_ie == "urbana" else random.randint(10, 20)
                    for _ in range(n_est):
                        nivel = random.choices(["A1","A2","B1","B2","C1"],
                            weights=[0.32,0.28,0.20,0.13,0.07] if zona_ie=="rural" else [0.10,0.18,0.27,0.25,0.20])[0]
                        anos_atras = random.choices([0, 1, 2, 3, 4, 5], weights=[0.18,0.22,0.2,0.16,0.14,0.10])[0]
                        est = Estudiante(
                            institucion_id=ie.id, salon_id=sal.id,
                            nombre=nombre_aleatorio(), grado=g, nivel_sisben=nivel, zona=zona_ie,
                            acudiente=nombre_aleatorio(), parentesco=random.choice(PARENTESCOS),
                            telefono=tel(),
                            direccion=(f"Cll {random.randint(1,20)} # {random.randint(1,25)}-{random.randint(2,80)}"
                                       if zona_ie == "urbana" else "Finca " + random.choice(["La Ilusión","El Porvenir","Villa Luz","Los Naranjos"])),
                            barrio_vereda=random.choice(BARRIOS_URB if zona_ie == "urbana" else VEREDAS),
                            fecha_ingreso=date(HOY.year - anos_atras, random.randint(1, 2), random.randint(15, 28)),
                        )
                        est._prop = propension_riesgo(zona_ie, nivel)
                        s.add(est); _nuevos_est.append(est); total_est += 1
            s.flush()
            for _e in _nuevos_est:
                PROPS[_e.id] = _e._prop
            _seed_fse(s, ie, zona_ie)

    s.commit()
    print(f"  {total_est} estudiantes en {sum(len(v) for v in ECOSISTEMA.values())} instituciones.")

    print("Generando asistencia (12 semanas hasta HOY) y notas...")
    _seed_asistencia_notas(s, periodos)

    print("Generando asistencia del personal docente...")
    _seed_asistencia_personal(s)

    print("Generando observador, pendientes, alertas y WhatsApp...")
    _seed_observador_alertas(s)

    print("Generando aula virtual PRO y calendario docente...")
    _seed_aula(s)
    _seed_calendario(s)

    print("Generando contratistas y contratos (SECOP 2 simulado)...")
    _seed_contratos(s, ie_demo)

    # ── Códigos de acceso para el login de alumnos (demo) ──
    print("Asignando códigos de acceso a estudiantes...")
    for e in s.query(Estudiante).all():
        e.codigo_acceso = f"AL{e.id:04d}"
    s.commit()

    # ── Rubros presupuestales del FSE ──
    for ie in s.query(Institucion).all():
        rubros = [("Funcionamiento y servicios", "1-FUNC", 18000000),
                  ("Mantenimiento de infraestructura", "2-MANT", 9000000),
                  ("Material didáctico y textos", "3-DIDA", 7000000),
                  ("Alimentación escolar (PAE)", "4-PAE", 14000000),
                  ("Conectividad y tecnología", "5-TEC", 6000000)]
        for nom, cod, pres in rubros:
            s.add(RubroFSE(institucion_id=ie.id, nombre=nom, codigo=cod, presupuesto=pres))
    s.commit()

    # ── Asignar los movimientos FSE existentes a un rubro (trazabilidad) ──
    for ie in s.query(Institucion).all():
        rubros_ie = s.query(RubroFSE).filter(RubroFSE.institucion_id == ie.id).all()
        if not rubros_ie:
            continue
        por_cod = {r.codigo: r for r in rubros_ie}
        mapa = {"1510": "3-DIDA", "1520": "4-PAE", "1524": "3-DIDA",
                "1655": "2-MANT", "2435": "5-TEC", "1512": "1-FUNC"}
        for m in s.query(MovimientoFSE).filter(MovimientoFSE.institucion_id == ie.id).all():
            cod = mapa.get(m.cuenta_codigo or "", "1-FUNC")
            r = por_cod.get(cod) or rubros_ie[0]
            m.rubro_id = r.id
            if m.tipo == "egreso" and not m.soporte:
                m.soporte = f"comprobante_{m.id}.pdf"
    s.commit()

    # ── Salas virtuales de ejemplo (clase en vivo presencial + virtual) ──
    for sal in s.query(Salon).filter(Salon.institucion_id == ie_demo.id).limit(3).all():
        sv = SalaVirtual(salon_id=sal.id, titulo=f"Clase en vivo · {sal.nombre}",
                         docente_id=sal.director_id,
                         estado=random.choice(["en_vivo", "programada", "finalizada"]),
                         fecha=AHORA - timedelta(hours=random.randint(1, 30)))
        s.add(sv)
        s.flush()
        ests = s.query(Estudiante).filter(Estudiante.salon_id == sal.id).limit(4).all()
        base = AHORA - timedelta(minutes=40)
        msgs = ["Profe, ¿ya subió la guía?", "Sí, está en materiales 👍",
                "Yo estoy conectado desde la vereda, se escucha bien",
                "¿La entrega es el viernes?", "Correcto, viernes a las 5pm.",
                "Gracias profe 🙌"]
        dire = s.query(Personal).filter(Personal.id == sal.director_id).first()
        for i, m in enumerate(msgs):
            es_doc = i in (1, 4)
            s.add(MensajeSala(sala_id=sv.id,
                              autor_tipo="docente" if es_doc else "alumno",
                              autor_id=(dire.id if es_doc and dire else (ests[i % len(ests)].id if ests else None)),
                              autor_nombre=(dire.nombre if es_doc and dire else
                                            (ests[i % len(ests)].nombre if ests else "Estudiante")),
                              texto=m, fecha=base + timedelta(minutes=i * 5)))

    # ── Curso preinstalado de CONTABILIDAD (básica/moderada/avanzada) ──
    print("Instalando curso de Contabilidad para alumnos...")
    _seed_curso_contabilidad(s)
    s.commit()

    print("Creando sedes de cada institucion...")
    _seed_sedes(s)

    print("Generando buzon de necesidades docentes...")
    _seed_solicitudes_recurso(s, ie_demo)
    _seed_propuestas(s)
    _seed_junta(s, ie_demo)

    print("Creando clases con estructura de temas...")
    _seed_clases_ricas(s, ie_demo)
    _seed_grabaciones(s, ie_demo)

    print("Asignando horarios y revisiones...")
    _seed_horarios_asignados(s, ie_demo)
    _seed_revisiones(s, ie_demo)

    print("Creando planeaciones, historico SIMAT y certificados...")
    _seed_secretaria(s, ie_demo)

    print("Creando perfil legal y rejilla de contratacion...")
    _seed_legal(s, ie_demo)

    print("Configurando dominios y suscripciones...")
    _seed_dominios(s)

    print("Instalando cursos del sistema...")
    _seed_cursos(s)

    print("Creando cuentas de usuario y log de auditoria...")
    _seed_usuarios(s)

    print("Generando censo juvenil territorial...")
    _seed_censo(s)

    s.commit()
    print("Base de datos de demostración creada en:", settings.DATABASE_URL)
    s.close()


def _seed_asistencia_notas(s, periodos):
    estudiantes = s.query(Estudiante).all()
    lunes_inicial = HOY - timedelta(weeks=12, days=HOY.weekday())
    for est in estudiantes:
        prop = PROPS.get(est.id)
        if prop is None:
            prop = random.betavariate(2, 6)
        prob_aus = 0.02 + prop * 0.30
        for semana in range(13):
            for dia in range(5):
                fecha = lunes_inicial + timedelta(weeks=semana, days=dia)
                if fecha > HOY:
                    continue
                r = random.random()
                factor = 1.6 if (dia == 0 and prop > 0.5) else 1.0
                if r < prob_aus * factor:
                    estado = "absent"
                elif r < prob_aus * factor + 0.04:
                    estado = "late" if random.random() < 0.5 else "excused"
                else:
                    estado = "present"
                s.add(Asistencia(estudiante_id=est.id, salon_id=est.salon_id, fecha=fecha, estado=estado))
        # Rendimiento académico correlacionado con la asistencia. Los alumnos con
        # alta propensión a faltar arrastran materias (patrón "va a perder el año"),
        # que es justo lo que el sistema debe detectar y alertar a tiempo.
        base = 4.7 - prop * 2.5
        materias_dificiles = random.sample(MATERIAS, k=random.randint(1, 3)) if prop > 0.45 else []
        for pi, per in enumerate(periodos[:3]):
            for m in MATERIAS:
                penal = 0.75 if m in materias_dificiles else 0.0
                nota = base - penal - pi * prop * 0.45 + random.uniform(-0.35, 0.35)
                nota = max(1.0, min(5.0, nota))
                s.add(NotaPeriodo(estudiante_id=est.id, periodo_id=per.id, materia=m, nota=round(nota, 1)))
    s.commit()


def _seed_asistencia_personal(s):
    docentes = s.query(Personal).filter(Personal.rol == "docente").all()
    lunes_inicial = HOY - timedelta(weeks=4, days=HOY.weekday())
    for d in docentes:
        prob_aus = random.choice([0.01, 0.02, 0.02, 0.03, 0.10, 0.16])
        for semana in range(5):
            for dia in range(5):
                fecha = lunes_inicial + timedelta(weeks=semana, days=dia)
                if fecha > HOY:
                    continue
                r = random.random()
                estado = "absent" if r < prob_aus else ("late" if r < prob_aus + 0.03 else "present")
                s.add(AsistenciaPersonal(personal_id=d.id, fecha=fecha, estado=estado,
                                         observacion="Incapacidad médica" if estado == "absent" and random.random() < 0.5 else ""))
    s.commit()


def _seed_observador_alertas(s):
    estudiantes = s.query(Estudiante).all()
    tipos_obs = ["comportamiento", "academico", "compromiso", "felicitacion"]
    desc_obs = {
        "comportamiento": ["Interrumpe la clase de forma reiterada","Conflicto con compañero en el descanso","Uso de celular en evaluación"],
        "academico": ["No presenta tareas de la semana","Bajo desempeño en evaluación de corte","No trae materiales de trabajo"],
        "compromiso": ["Acudiente firma compromiso de acompañamiento en casa","Estudiante se compromete a asistir puntualmente"],
        "felicitacion": ["Excelente participación en izada de bandera","Mejor promedio del salón en el corte"],
    }
    riesgosos = [e for e in estudiantes if PROPS.get(e.id, 0) > 0.45]
    for est in riesgosos:
        for _ in range(random.randint(1, 3)):
            t = random.choices(tipos_obs, weights=[0.4, 0.35, 0.15, 0.10])[0]
            firmado = random.random() < 0.5
            f = AHORA - timedelta(days=random.randint(3, 70))
            s.add(ObservadorEntrada(
                estudiante_id=est.id, fecha=f, tipo=t,
                descripcion=random.choice(desc_obs[t]),
                registrado_por="Coordinación" if t != "felicitacion" else "Docente titular",
                firmado_acudiente=firmado,
                firma_metodo="OTP WhatsApp (simulado)" if firmado else None,
                fecha_firma=f + timedelta(days=1) if firmado else None))
        if random.random() < 0.5:
            s.add(NotaPendiente(estudiante_id=est.id,
                                texto=random.choice(["Citar acudiente esta semana","Remitir a psicoorientación",
                                                     "Visita domiciliaria pendiente","Verificar transporte escolar"]),
                                creado_por="Coordinación", fecha=AHORA - timedelta(days=random.randint(1, 10)),
                                done=random.random() < 0.3))
    s.commit()

    dias_habiles = []
    f = HOY
    while len(dias_habiles) < 5:
        if f.weekday() < 5:
            dias_habiles.append(f)
        f -= timedelta(days=1)
    aus = s.query(Asistencia).filter(Asistencia.fecha.in_(dias_habiles), Asistencia.estado == "absent").all()
    est_map = {e.id: e for e in estudiantes}
    vistos = set()
    for a in aus:
        key = (a.estudiante_id, a.fecha)
        if key in vistos:
            continue
        vistos.add(key)
        e = est_map.get(a.estudiante_id)
        if not e:
            continue
        s.add(NotificacionCoord(
            institucion_id=e.institucion_id, estudiante_id=e.id, tipo="ausencia",
            titulo=f"Ausencia de {e.nombre.split()[0]} {e.nombre.split()[1]}",
            detalle=f"No asistió el {a.fecha.isoformat()} · Grado {e.grado} · Acudiente: {e.acudiente} ({e.parentesco}) · Tel {e.telefono}",
            fecha=datetime.combine(a.fecha, datetime.min.time()) + timedelta(hours=8),
            estado="abierta"))
        if random.random() < 0.6:
            s.add(MensajeWhatsApp(
                estudiante_id=e.id, destinatario=f"{e.acudiente} ({e.parentesco})", telefono=e.telefono,
                contenido=(f"Buen día. Le informamos que {e.nombre.split()[0]} no asistió hoy "
                           f"({a.fecha.strftime('%d/%m')}) a la institución. Si existe una causa justificada, "
                           "responda este mensaje o comuníquese con coordinación. — GyverLabs"),
                fecha=datetime.combine(a.fecha, datetime.min.time()) + timedelta(hours=8, minutes=5),
                estado="ENVIADO (simulado)", contexto="ausencia"))
    muestras = random.sample(estudiantes, k=12)
    for e in muestras:
        f = AHORA - timedelta(days=random.randint(8, 60))
        cerrada = random.random() < 0.6
        s.add(NotificacionCoord(
            institucion_id=e.institucion_id, estudiante_id=e.id,
            tipo=random.choice(["ausencia", "riesgo", "comportamiento"]),
            titulo=f"Seguimiento a {e.nombre.split()[0]} {e.nombre.split()[1]}",
            detalle="Caso gestionado por coordinación.",
            fecha=f, estado="archivada" if cerrada else "completada",
            resolucion=random.choice(["Se citó al acudiente y firmó compromiso.",
                                      "Se activó aula virtual por situación de salud.",
                                      "Remitido a psicoorientación; en acompañamiento.",
                                      "Se verificó transporte escolar; caso cerrado."]),
            fecha_cierre=f + timedelta(days=random.randint(1, 6))))
    s.commit()


def _seed_aula(s):
    salones = s.query(Salon).all()
    est_por_salon = {}
    for e in s.query(Estudiante).all():
        est_por_salon.setdefault(e.salon_id, []).append(e)
    plantillas = [
        ("Clase: Fracciones en la vida real", "Explicación guiada + ejemplos con precios del mercado local.", "clase", "Matemáticas",
         [{"tipo":"pdf","nombre":"Guia_fracciones.pdf"},{"tipo":"video","nombre":"Video explicativo (12 min)"}]),
        ("Taller de comprensión lectora", "Lee el texto y responde las preguntas de análisis.", "taller", "Lenguaje",
         [{"tipo":"pdf","nombre":"Lectura_El_rio.pdf"}]),
        ("Video: el ciclo del agua", "Observa el video y elabora un resumen de una página.", "video", "Ciencias",
         [{"tipo":"video","nombre":"Ciclo_del_agua.mp4"}]),
        ("Evaluación de corte — Sociales", "Evaluación en línea del Corte 1. Lee las reglas antes de iniciar.", "evaluacion", "Sociales",
         [{"tipo":"enlace","nombre":"Formulario de evaluación"}]),
        ("Curso corto: Inglés para la vereda", "Módulo autoguiado de 4 lecciones con audios.", "curso", "Inglés",
         [{"tipo":"pdf","nombre":"Modulo_1.pdf"},{"tipo":"enlace","nombre":"Audios de práctica"}]),
        ("Recuperación: Ecuaciones lineales", "Plan de recuperación con guía + sustentación.", "recuperacion", "Matemáticas",
         [{"tipo":"pdf","nombre":"Plan_recuperacion.pdf"}]),
    ]
    for sal in salones:
        for (tit, desc, tipo, mat, mats) in random.sample(plantillas, k=random.randint(2, 4)):
            fl = HOY + timedelta(days=random.randint(2, 15))
            act = ActividadAula(
                salon_id=sal.id, titulo=tit, descripcion=desc, tipo=tipo, materia=mat,
                periodo_numero=3, fecha_limite=fl,
                tiempo_limite_min=45 if tipo == "evaluacion" else None,
                reglas="Individual · Un solo intento · Cámara de honestidad activa (simulada)" if tipo == "evaluacion" else None,
                permite_recuperacion=(tipo in ("evaluacion", "taller")),
                materiales=json.dumps(mats, ensure_ascii=False),
                estado="publicada", creado_por="Docente titular",
                generado_ia=random.random() < 0.25)
            s.add(act); s.flush()
            for est in est_por_salon.get(sal.id, []):
                estado = random.choices(["pendiente","entregado","revisado"], weights=[0.4,0.4,0.2])[0]
                nota = round(random.uniform(3.0, 5.0), 1) if estado == "revisado" else None
                s.add(EntregaAula(
                    actividad_id=act.id, estudiante_id=est.id, estado=estado, nota=nota,
                    retro="Buen trabajo, revisa el punto 3." if estado == "revisado" and random.random() < 0.5 else None,
                    fecha_entrega=(AHORA - timedelta(days=random.randint(0, 6))) if estado != "pendiente" else None))
    s.commit()


def _seed_calendario(s):
    docentes = s.query(Personal).filter(Personal.rol == "docente").all()
    obligaciones = ["Consejo académico","Entrega de planillas a coordinación","Reunión de área",
                    "Comisión de evaluación","Atención a padres de familia","Formación en TIC (Secretaría)"]
    pendientes = ["Calificar taller de comprensión","Actualizar observador de 3 estudiantes",
                  "Preparar guía del Corte 2","Subir notas del corte al sistema"]
    for d in docentes:
        for _ in range(random.randint(2, 3)):
            s.add(EventoCalendario(personal_id=d.id, fecha=HOY + timedelta(days=random.randint(0, 9)),
                                   hora=random.choice(["7:00","10:30","14:00","16:00"]),
                                   titulo=random.choice(obligaciones), tipo="obligacion"))
        for _ in range(random.randint(1, 2)):
            s.add(EventoCalendario(personal_id=d.id, fecha=HOY + timedelta(days=random.randint(0, 5)),
                                   hora=None, titulo=random.choice(pendientes), tipo="pendiente"))
    s.commit()


def _seed_fse(s, ie, zona_ie):
    cuentas = [
        ("4110","Transferencias SGP — Gratuidad","ingreso"),
        ("4295","Recursos propios (certificados, cafetería)","ingreso"),
        ("4805","Donaciones","ingreso"),
        ("1510","Suministros y materiales","gasto"),
        ("1520","Bienestar estudiantil (PAE)","gasto"),
        ("1524","Material didáctico","gasto"),
        ("1655","Mantenimiento planta física","gasto"),
        ("2435","Servicios públicos","gasto"),
        ("1512","Formación y capacitación docente","gasto"),
    ]
    for c in cuentas:
        s.add(CuentaFSE(institucion_id=ie.id, codigo=c[0], nombre=c[1], tipo=c[2]))

    escala = 1.0 if zona_ie == "urbana" else 0.55
    plan = [
        ("Dotación de material didáctico grados 6-11","1524",1,2,int(8500000*escala),"comprado"),
        ("Complemento alimentario PAE primer semestre","1520",1,1,int(12000000*escala),"parcial"),
        ("Mantenimiento de baterías sanitarias","1655",1,3,int(6200000*escala),"pendiente"),
        ("Pago servicios públicos (agua, energía)","2435",1,1,int(9800000*escala),"parcial"),
        ("Compra de resmas y papelería","1510",2,4,int(1800000*escala),"comprado"),
        ("Capacitación docente en TIC","1512",2,6,int(3500000*escala),"pendiente"),
        ("Reparación de pupitres y sillas","1655",3,7,int(2400000*escala),"pendiente"),
        ("Insumos de aseo y bioseguridad","1510",2,3,int(2100000*escala),"parcial"),
    ]
    for p in plan:
        s.add(PlanFSE(institucion_id=ie.id, anio=2026, concepto=p[0], cuenta_codigo=p[1],
                      prioridad=p[2], mes_planeado=p[3], valor_presupuestado=p[4], estado=p[5]))

    rps = [
        ("CDP-2026-001","cdp","2026-02-03","Adquisición de material didáctico","Distribuidora Escolar del Norte SAS","900123456-1",int(8500000*escala),int(8320000*escala)),
        ("RP-2026-014","rp","2026-02-10","Adquisición de material didáctico","Distribuidora Escolar del Norte SAS","900123456-1",int(8500000*escala),int(8320000*escala)),
        ("RP-2026-021","rp","2026-03-05","Compra de papelería y resmas","Papelería Central Ltda","800987654-2",int(1800000*escala),int(1650000*escala)),
        ("RP-2026-033","rp","2026-04-12","Insumos de aseo y bioseguridad","Suministros Higiénicos SAS","901222333-4",int(2100000*escala),int(2380000*escala)),
    ]
    for r in rps:
        s.add(RegistroPresupuestal(institucion_id=ie.id, consecutivo=r[0], tipo=r[1], fecha=date.fromisoformat(r[2]),
                                   objeto=r[3], proveedor=r[4], nit=r[5], valor=r[6], valor_secop=r[7],
                                   secop_url="https://community.secop.gov.co/", estado="vigente"))

    ingresos = [
        ("2026-01-30","4110","Giro SGP Gratuidad primer semestre",int(38500000*escala),"ING-001"),
        ("2026-02-15","4295","Recursos propios — certificados",int(1250000*escala),"ING-002"),
    ]
    for i in ingresos:
        s.add(MovimientoFSE(institucion_id=ie.id, fecha=date.fromisoformat(i[0]), tipo="ingreso",
                            cuenta_codigo=i[1], concepto=i[2], valor=i[3], metodo="Transferencia",
                            comprobante=i[4], estado="registrado"))
    egresos = [
        ("2026-02-12","1524","Compra material didáctico","Distribuidora Escolar del Norte SAS","900123456-1",int(8320000*escala),"EGR-001"),
        ("2026-03-08","1510","Papelería y resmas","Papelería Central Ltda","800987654-2",int(1650000*escala),"EGR-002"),
        ("2026-03-20","2435","Pago energía eléctrica febrero","Electrificadora S.A.","899999999-1",int(2180000*escala),"EGR-003"),
        ("2026-04-14","1510","Insumos de aseo y bioseguridad","Suministros Higiénicos SAS","901222333-4",int(2380000*escala),"EGR-004"),
        ("2026-05-02","1520","Complemento alimentario PAE abril","Alimentos del Sur SAS","830111222-3",int(5600000*escala),"EGR-005"),
    ]
    for e in egresos:
        s.add(MovimientoFSE(institucion_id=ie.id, fecha=date.fromisoformat(e[0]), tipo="egreso",
                            cuenta_codigo=e[1], concepto=e[2], proveedor=e[3], nit=e[4], valor=e[5],
                            metodo="Transferencia", comprobante=e[6], estado="pagado"))


def _seed_contratos(s, ie_demo):
    def _doc(ok, nombre):
        if not ok:
            return {"ok": False, "archivo": None, "fecha": None}
        return {"ok": True, "archivo": nombre,
                "fecha": (HOY - timedelta(days=random.randint(5, 60))).isoformat()}
    def _docs_full(**overrides):
        base = {"cedula": _doc(True, "cedula_rep_legal.pdf"),
                "contraloria": _doc(True, "cert_contraloria.pdf"),
                "procuraduria": _doc(True, "cert_procuraduria.pdf"),
                "redam": _doc(True, "cert_redam.pdf"),
                "camara_comercio": _doc(True, "camara_comercio.pdf"),
                "rut": _doc(True, "rut_2026.pdf"),
                "seguridad_social": _doc(True, "planilla_ss_mes.pdf")}
        for k, v in overrides.items():
            base[k] = _doc(False, None) if v is False else base[k]
        return base
    docs_ok = _docs_full()
    contratistas_def = [
        ("Distribuidora Escolar del Norte SAS", "900123456-1", "juridica", docs_ok, 88, 20.0, 8320000,
         "Proveedor histórico de material didáctico. Cumplido."),
        ("Alimentos del Sur SAS", "830111222-3", "juridica", docs_ok, 82, 20.0, 5600000,
         "Operador PAE. Entregas puntuales."),
        ("Papelería Central Ltda", "800987654-2", "juridica",
         _docs_full(seguridad_social=False), 71, 15.0, 1650000,
         "Falta planilla de seguridad social del mes."),
        ("Construcciones El Progreso", "901555777-9", "juridica",
         _docs_full(contraloria=False, redam=False), 55, 12.0, 0,
         "Contratista nuevo — expediente en recolección."),
        ("María Fernanda Ayala (persona natural)", "1.095.334.221", "natural",
         _docs_full(camara_comercio=False), 76, 10.0, 0,
         "Servicios de mantenimiento menor. Persona natural (no requiere cámara)."),
    ]
    objs = {}
    for (nom, nit, tipo, docs, conf, cap, acum, notas) in contratistas_def:
        c = Contratista(nombre=nom, nit=nit, tipo=tipo, documentos=json.dumps(docs),
                        confianza=conf, capacidad_smmlv=cap, contratado_anio=acum, notas=notas)
        s.add(c); s.flush()
        objs[nom] = c

    if not ie_demo:
        s.commit(); return
    plan_items = s.query(PlanFSE).filter(PlanFSE.institucion_id == ie_demo.id).all()
    plan_por_concepto = {p.concepto: p for p in plan_items}

    def firmas(*estados):
        roles = [("Rector(a)", ie_demo.rector), ("Contratista", None), ("Jurídica", "Diana Guzmán Prada")]
        out = []
        for (rol, nom), fdo in zip(roles, estados):
            out.append({"rol": rol, "nombre": nom or "Representante legal", "firmado": fdo,
                        "fecha": (AHORA - timedelta(days=random.randint(1, 9))).isoformat(timespec="minutes") if fdo else None,
                        "metodo": "Firma electrónica + OTP (simulado)" if fdo else None})
        return json.dumps(out, ensure_ascii=False)

    contratos_def = [
        ("CT-2026-001", "Distribuidora Escolar del Norte SAS", "Suministro de material didáctico grados 6-11",
         8320000, "CDP-2026-001", "RP-2026-014", "ejecucion", firmas(True, True, True),
         plan_por_concepto.get("Dotación de material didáctico grados 6-11"), "Revisado. Sin observaciones."),
        ("CT-2026-002", "Alimentos del Sur SAS", "Complemento alimentario PAE — primer semestre",
         5600000, "CDP-2026-002", "RP-2026-018", "firmado", firmas(True, True, True),
         plan_por_concepto.get("Complemento alimentario PAE primer semestre"), "Cumple minuta MEN."),
        ("CT-2026-003", "Construcciones El Progreso", "Mantenimiento de baterías sanitarias",
         6200000, "CDP-2026-003", None, "documentos", firmas(False, False, False),
         plan_por_concepto.get("Mantenimiento de baterías sanitarias"), None),
        ("CT-2026-004", "María Fernanda Ayala (persona natural)", "Reparación de pupitres y sillas",
         2400000, "CDP-2026-004", "RP-2026-041", "firma", firmas(True, False, True),
         plan_por_concepto.get("Reparación de pupitres y sillas"), "Vo.Bo. jurídico emitido."),
    ]
    PIPE = ["borrador", "documentos", "juridica", "firma", "firmado", "ejecucion", "liquidado"]
    TIPO_X_OBJ = {"CT-2026-001": "suministro", "CT-2026-002": "pae",
                  "CT-2026-003": "obra", "CT-2026-004": "servicio"}
    # Datos ricos del expediente (CIIU, banco, representante legal) — punto 24
    CIIU_MAP = {"Papelería Central Ltda": "4761", "Distribuciones del Magdalena S.A.S.": "4630",
                "Construcciones El Progreso": "4290",
                "María Fernanda Ayala (persona natural)": "9511"}
    BANCOS = ["Bancolombia", "Banco Agrario", "Davivienda", "BBVA"]
    for nom, o in objs.items():
        o.ciiu = CIIU_MAP.get(nom, "4690")
        o.ciudad = "San Pablo"
        o.direccion = f"Calle {random.randint(1,30)} # {random.randint(1,25)}-{random.randint(10,90)}"
        o.rep_legal = nom if o.tipo == "natural" else f"{random.choice(['Carlos','Luz','Jorge','Marta'])} {random.choice(['Rueda','Ortiz','Salas','Pinto'])}"
        o.rep_legal_cc = f"{random.randint(9,99)}.{random.randint(100,999)}.{random.randint(100,999)}"
        o.banco = random.choice(BANCOS)
        o.cuenta_banco = f"{random.randint(100,999)}-{random.randint(100000,999999)}-{random.randint(10,99)}"
        o.tipo_cuenta = random.choice(["Ahorros", "Corriente"])
    s.flush()

    for (num, prov, obj, val, cdp, rp, estado, fms, plan, nota_j) in contratos_def:
        f0 = HOY - timedelta(days=random.randint(20, 60))
        idx = PIPE.index(estado) if estado in PIPE else 0
        etapas = {}
        fx = f0
        for e in PIPE[: idx + 1]:
            etapas[e] = fx.isoformat()
            fx = fx + timedelta(days=random.randint(2, 6))
        cotiz = [{"proveedor": prov, "valor": val, "fecha": (f0 - timedelta(days=3)).isoformat(),
                  "archivo": "cotizacion_1.pdf"},
                 {"proveedor": "Proveedor alterno SAS", "valor": int(val * random.uniform(1.04, 1.18)),
                  "fecha": (f0 - timedelta(days=3)).isoformat(), "archivo": "cotizacion_2.pdf"}]
        ccobro = None
        if estado in ("ejecucion", "liquidado"):
            ccobro = {"numero": f"CC-{num[-3:]}", "fecha": HOY.isoformat(), "valor": val,
                      "archivo": "cuenta_cobro.pdf", "estado": "pendiente"}
        s.add(Contrato(institucion_id=ie_demo.id, contratista_id=objs[prov].id, numero=num,
                       objeto=obj, valor=val, cdp_num=cdp, rp_num=rp,
                       fecha=f0, estado=estado,
                       secop_url="https://community.secop.gov.co/", firmas=fms,
                       plan_id=plan.id if plan else None, nota_juridica=nota_j,
                       tipo_contrato=TIPO_X_OBJ.get(num, "suministro"),
                       etapas_fechas=json.dumps(etapas),
                       cotizaciones=json.dumps(cotiz, ensure_ascii=False),
                       cuenta_cobro=json.dumps(ccobro, ensure_ascii=False) if ccobro else None))

    def alta_admin(nombre, rol, area, prof, exp):
        hv = hv_json(prof, exp)
        p = Personal(institucion_id=ie_demo.id, nombre=nombre, rol=rol, area=area,
                     telefono=tel(), documento=cc(), profesion=prof, experiencia_anios=exp,
                     fecha_vinculacion=HOY - timedelta(days=exp * 300),
                     hoja_vida=json.dumps(hv, ensure_ascii=False), hv_score=hv_score(hv, exp))
        s.add(p); s.flush()
        return p

    aux = alta_admin("Yaneth Pardo Quintero", "auxiliar", "Contratación y archivo",
                     "Técnico en Gestión Documental — SENA", 7)
    cont = alta_admin("Carlos Reyes Manosalva", "contador", "Contaduría FSE",
                      "Contaduría Pública — U. de Cartagena · TP 98765-T", 11)
    abo = alta_admin("Diana Guzmán Prada", "abogado", "Jurídica",
                     "Derecho — U. Libre · Esp. Contratación Estatal", 9)
    s.add(Autorizacion(institucion_id=ie_demo.id, personal_id=aux.id, paneles="contratos,fse"))
    s.add(Autorizacion(institucion_id=ie_demo.id, personal_id=cont.id, paneles="fse,contratos,datos"))
    # Pagos del contrato (unos pagados con evidencia, otros pendientes) — punto 27
    for ct in s.query(Contrato).filter(Contrato.institucion_id == ie_demo.id).all():
        if ct.estado in ("ejecucion", "liquidado"):
            s.add(PagoContrato(contrato_id=ct.id, institucion_id=ie_demo.id,
                               concepto=f"Pago parcial 50% · {ct.objeto[:40]}",
                               valor=round(ct.valor * 0.5), estado="pagado",
                               fecha_programada=HOY - timedelta(days=20),
                               fecha_pago=HOY - timedelta(days=18), metodo="Transferencia",
                               evidencia="transferencia_50.pdf"))
            s.add(PagoContrato(contrato_id=ct.id, institucion_id=ie_demo.id,
                               concepto=f"Saldo final 50% · {ct.objeto[:40]}",
                               valor=round(ct.valor * 0.5), estado="pendiente",
                               fecha_programada=HOY + timedelta(days=8)))
        elif ct.estado == "firmado":
            s.add(PagoContrato(contrato_id=ct.id, institucion_id=ie_demo.id,
                               concepto=f"Anticipo 30% · {ct.objeto[:40]}",
                               valor=round(ct.valor * 0.3), estado="pendiente",
                               fecha_programada=HOY + timedelta(days=3)))

    s.add(Autorizacion(institucion_id=ie_demo.id, personal_id=abo.id, paneles="contratos"))

    # Comunicados de ejemplo (rectoría → institución / docentes) con bandeja
    plantel = s.query(Personal).filter(Personal.institucion_id == ie_demo.id,
                                       Personal.activo == True).all()  # noqa: E712
    docentes_ie = [p for p in plantel if p.rol == "docente"]
    com1 = Comunicado(institucion_id=ie_demo.id, emisor="Rectoría",
                      destinatario_tipo="institucion", destinatario_id=None,
                      titulo="Jornada pedagógica este viernes",
                      mensaje="Este viernes no hay clases con estudiantes: jornada pedagógica de 7am a 1pm en la biblioteca. Asistencia obligatoria de todo el personal.",
                      fecha=AHORA - timedelta(days=2), n_destinatarios=len(plantel))
    s.add(com1); s.flush()
    for p in plantel:
        s.add(NotificacionPersona(comunicado_id=com1.id, personal_id=p.id,
                                  leida=random.random() < 0.5))
    com2 = Comunicado(institucion_id=ie_demo.id, emisor="Rectoría",
                      destinatario_tipo="docentes", destinatario_id=None,
                      titulo="Entrega de planillas del Corte 1",
                      mensaje="Recuerden subir las notas del Corte 1 al sistema antes del viernes. Coordinación revisará el lunes.",
                      fecha=AHORA - timedelta(hours=20), n_destinatarios=len(docentes_ie))
    s.add(com2); s.flush()
    for p in docentes_ie:
        s.add(NotificacionPersona(comunicado_id=com2.id, personal_id=p.id, leida=False))
    s.commit()


def _seed_censo(s):
    motivos = ["Trabajo infantil","Distancia al colegio","Embarazo adolescente","Falta de recursos",
               "Desmotivación","Problemas familiares","Situación de salud","Extraedad",
               "Cuidado de hermanos menores","Migración / desplazamiento","Discapacidad sin apoyo",
               "Falta de cupo","Consumo de sustancias"]
    alertas = ["Reclutamiento (SAT)","Minería ilegal","Cultivos ilícitos","Violencia intrafamiliar",
               "Desplazamiento","Trabajo en río","Presencia de actores armados","Explotación sexual (riesgo)",
               "Zona sin transporte escolar"]
    for (municipio, depto), instituciones in ECOSISTEMA.items():
        colegios = [i[0] for i in instituciones]
        for _ in range(random.randint(220, 300)):     # censo más poblado (punto 28)
            zona = "rural" if random.random() < 0.48 else "urbana"
            estudia = random.random() > 0.31
            zona_riesgo = random.random() < 0.28
            s.add(RegistroCenso(
                nombre=nombre_aleatorio(), edad=random.randint(10, 19),
                sexo=random.choice(["M","F"]), departamento=depto, municipio=municipio, zona=zona,
                barrio_vereda=random.choice(VEREDAS if zona == "rural" else BARRIOS_URB),
                nivel_sisben=random.choice(["A1","A2","B1","B2","C1"]),
                estudia=estudia, motivo_no_estudia=None if estudia else random.choice(motivos),
                colegio=random.choice(colegios) if estudia else None,
                zona_riesgo=zona_riesgo,
                tipo_alerta="|".join(random.sample(alertas, k=random.randint(1, 2))) if zona_riesgo else None,
                ultimo_contacto=HOY - timedelta(days=random.randint(5, 120)) if random.random() < 0.6 else None,
                estado_seguimiento=random.choice(["Sin contactar","En seguimiento","Cerrado"]),
            ))
    s.commit()


if __name__ == "__main__":
    main()
