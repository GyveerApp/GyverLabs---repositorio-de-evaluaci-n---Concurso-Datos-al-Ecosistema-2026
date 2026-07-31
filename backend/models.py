"""
Modelos de base de datos — versión de evaluación/demo (multi-perfil) PRO.

Esquema SIMPLIFICADO y público del modelo real. Soporta la demostración
del sistema completo con NUEVE perfiles (Súper Admin GyverLabs, Docente,
Coordinación, Rectoría, Contratación, Contaduría, Jurídica, Secretaría de
Educación y Ministerio) sobre una sola base SQLite local.

Multi-tenant simulado (tabla Tenant): internamente todo vive interconectado
en una sola plataforma; externamente cada colegio y cada secretaría tiene su
propio dominio, colores y marca (percepción "a la medida" — ver Guía Maestra).

Todos los datos son 100% sintéticos. La captura de metadatos para IA replica
la filosofía del log unificado de trading (un evento por acción, snapshots
semanales por estudiante) — lista para LightGBM / LSTM / Transformer.
"""

from datetime import date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime, Text, ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Tenant(Base):
    """NIVEL 1 (Súper Admin): cada secretaría y cada colegio es un tenant con
    su propio dominio, color y módulos. Un solo código, N dominios."""
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True)
    tipo = Column(String, nullable=False)          # secretaria | colegio
    nombre = Column(String, nullable=False)
    dominio = Column(String, nullable=False)       # sistema.iecc.edu.co / bolivar.gyverlabs.co
    color = Column(String, default="#0E7C86")
    logo = Column(Text, nullable=True)             # dataURL del logo (marca por institución)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"), nullable=True)
    municipio = Column(String, nullable=True)
    departamento = Column(String, nullable=True)
    modulos = Column(String, default="asistencia,aula,srd,fse")
    estado = Column(String, default="activo")      # activo | suspendido
    creado = Column(Date, nullable=True)


class Institucion(Base):
    __tablename__ = "instituciones"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    codigo_dane = Column(String, nullable=False)
    municipio = Column(String, nullable=False)
    departamento = Column(String, nullable=False)
    sector = Column(String, nullable=False)
    rector = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    logo = Column(Text, nullable=True)             # logo institucional (aparece en todo el sistema del tenant)


class Personal(Base):
    """Todo el personal: docentes, coordinadores, rector, administrativos,
    contador, abogado, psicoorientación, vigilancia, servicios generales."""
    __tablename__ = "personal"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=True)
    nombre = Column(String, nullable=False)
    rol = Column(String, nullable=False)
    area = Column(String, nullable=True)
    email = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    documento = Column(String, nullable=True)
    profesion = Column(String, nullable=True)
    experiencia_anios = Column(Integer, default=0)
    fecha_vinculacion = Column(Date, nullable=True)
    foto = Column(Text, nullable=True)              # dataURL (editable en la demo)
    hoja_vida = Column(Text, nullable=True)         # JSON {estudios[],experiencia[],certificaciones[],archivo}
    hv_score = Column(Integer, default=0)
    activo = Column(Boolean, default=True)


class Salon(Base):
    __tablename__ = "salones"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=True)
    nombre = Column(String, nullable=False)
    grado = Column(String, nullable=False)
    jornada = Column(String, nullable=False)
    director_id = Column(Integer, ForeignKey("personal.id"), nullable=True)
    horarios = Column(Text, nullable=True)          # JSON [{dia,hora,materia}]


class Estudiante(Base):
    __tablename__ = "estudiantes"
    id = Column(Integer, primary_key=True)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=True)
    codigo_acceso = Column(String, nullable=True)  # código simple para que el alumno entre (demo)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    salon_id = Column(Integer, ForeignKey("salones.id"))
    nombre = Column(String, nullable=False)
    grado = Column(String, nullable=False)
    nivel_sisben = Column(String, nullable=False)
    zona = Column(String, nullable=False)
    acudiente = Column(String, nullable=True)
    parentesco = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    barrio_vereda = Column(String, nullable=True)
    fecha_ingreso = Column(Date, nullable=True)

    asistencias = relationship("Asistencia", back_populates="estudiante")
    notas = relationship("NotaPeriodo", back_populates="estudiante")


class Asistencia(Base):
    __tablename__ = "asistencia"
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    salon_id = Column(Integer, ForeignKey("salones.id"))
    fecha = Column(Date, nullable=False)
    estado = Column(String, nullable=False, default="present")
    observacion = Column(String, nullable=True)

    estudiante = relationship("Estudiante", back_populates="asistencias")


class AsistenciaPersonal(Base):
    """Asistencia del PERSONAL (docentes) — control de coordinación/rectoría."""
    __tablename__ = "asistencia_personal"
    id = Column(Integer, primary_key=True)
    personal_id = Column(Integer, ForeignKey("personal.id"))
    fecha = Column(Date, nullable=False)
    estado = Column(String, nullable=False, default="present")
    observacion = Column(String, nullable=True)


class Periodo(Base):
    __tablename__ = "periodos"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    numero = Column(Integer, nullable=False)
    peso = Column(Float, nullable=False, default=25.0)
    activo = Column(Boolean, default=False)
    cerrado = Column(Boolean, default=False)
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)


class Corte(Base):
    """Cortes dentro de cada período (fechas editables por institución)."""
    __tablename__ = "cortes"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    periodo_numero = Column(Integer, nullable=False)
    nombre = Column(String, nullable=False)
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    cerrado = Column(Boolean, default=False)   # cerrado por rectoría → bloquea a TODOS


class TemaPlan(Base):
    """Temas que maneja el docente por salón / período / corte."""
    __tablename__ = "temas_plan"
    id = Column(Integer, primary_key=True)
    salon_id = Column(Integer, ForeignKey("salones.id"))
    periodo_numero = Column(Integer, nullable=False)
    corte = Column(String, nullable=True)
    materia = Column(String, nullable=True)
    tema = Column(String, nullable=False)
    detalle = Column(String, nullable=True)


class NotaPeriodo(Base):
    __tablename__ = "notas_periodo"
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    periodo_id = Column(Integer, ForeignKey("periodos.id"))
    materia = Column(String, nullable=False)
    nota = Column(Float, nullable=False)

    estudiante = relationship("Estudiante", back_populates="notas")


class SRDScore(Base):
    __tablename__ = "srd_scores"
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"), unique=True)
    score = Column(Float, nullable=False)
    nivel = Column(String, nullable=False)
    faltas_acumuladas = Column(Integer, default=0)
    faltas_recientes = Column(Integer, default=0)
    pct_asistencia = Column(Float, default=100.0)
    promedio = Column(Float, default=0.0)
    tendencia = Column(Float, default=0.0)
    factores = Column(String, nullable=False)
    notificado_padre = Column(Boolean, default=False)
    fecha_notif_padre = Column(DateTime, nullable=True)
    notificado_rectoria = Column(Boolean, default=False)
    fecha_notif_rectoria = Column(DateTime, nullable=True)
    intervencion_estado = Column(String, default="pendiente")
    intervencion_nota = Column(String, nullable=True)


class SRDLog(Base):
    __tablename__ = "srd_log"
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    accion = Column(String, nullable=False)
    detalle = Column(String, nullable=True)
    actor = Column(String, nullable=True)
    fecha = Column(DateTime, nullable=False)


class ObservadorEntrada(Base):
    """Observador del estudiante — con firma simulada del acudiente (OTP)."""
    __tablename__ = "observador"
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    fecha = Column(DateTime, nullable=False)
    tipo = Column(String, nullable=False)     # comportamiento|academico|felicitacion|compromiso
    descripcion = Column(String, nullable=False)
    registrado_por = Column(String, nullable=True)
    firmado_acudiente = Column(Boolean, default=False)
    firma_metodo = Column(String, nullable=True)
    fecha_firma = Column(DateTime, nullable=True)


class NotaPendiente(Base):
    """Bitácora de pendientes por estudiante."""
    __tablename__ = "pendientes"
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    texto = Column(String, nullable=False)
    creado_por = Column(String, nullable=True)
    fecha = Column(DateTime, nullable=False)
    done = Column(Boolean, default=False)


class NotificacionCoord(Base):
    """Alertas del coordinador: abierta → completada → archivada, con resolución."""
    __tablename__ = "notificaciones"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"), nullable=True)
    tipo = Column(String, nullable=False)      # ausencia|riesgo|comportamiento
    titulo = Column(String, nullable=False)
    detalle = Column(String, nullable=True)
    fecha = Column(DateTime, nullable=False)
    estado = Column(String, default="abierta")
    resolucion = Column(String, nullable=True)
    fecha_cierre = Column(DateTime, nullable=True)


class MensajeWhatsApp(Base):
    """Simulación de pasarela WhatsApp (producción: Meta Cloud API / Twilio)."""
    __tablename__ = "mensajes_whatsapp"
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"), nullable=True)
    personal_id = Column(Integer, ForeignKey("personal.id"), nullable=True)
    destinatario = Column(String, nullable=False)
    telefono = Column(String, nullable=True)
    contenido = Column(String, nullable=False)
    fecha = Column(DateTime, nullable=False)
    estado = Column(String, default="ENVIADO (simulado)")
    contexto = Column(String, nullable=True)


class ActividadAula(Base):
    __tablename__ = "aula_actividades"
    id = Column(Integer, primary_key=True)
    salon_id = Column(Integer, ForeignKey("salones.id"))
    padre_id = Column(Integer, ForeignKey("aula_actividades.id"), nullable=True)  # taller/evaluación ligado a una clase
    titulo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo = Column(String, default="taller")    # clase|taller|lectura|video|foro|evaluacion|curso|recuperacion
    materia = Column(String, nullable=True)
    periodo_numero = Column(Integer, nullable=True)
    fecha_limite = Column(Date, nullable=True)
    tiempo_limite_min = Column(Integer, nullable=True)
    reglas = Column(String, nullable=True)
    permite_recuperacion = Column(Boolean, default=False)
    materiales = Column(Text, nullable=True)   # JSON [{tipo,nombre,url,tamano}]
    estado = Column(String, default="publicada")
    creado_por = Column(String, nullable=True)
    generado_ia = Column(Boolean, default=False)
    # ── Estructura tipo curso (portada, duracion, objetivos) ──
    portada = Column(Text, nullable=True)          # dataURL o emoji
    color = Column(String, default="#0E7C86")
    duracion_min = Column(Integer, default=45)
    objetivos = Column(Text, nullable=True)        # JSON [texto]
    video_url = Column(String, nullable=True)      # YouTube/Vimeo principal
    corte = Column(String, nullable=True)          # a que corte pertenece
    tema_plan_id = Column(Integer, ForeignKey("temas_plan.id"), nullable=True)


class TemaClase(Base):
    """Un tema DENTRO de una clase. Igual que en los cursos: el alumno
    avanza tema por tema, con su video, su contenido y su quiz."""
    __tablename__ = "aula_temas"
    id = Column(Integer, primary_key=True)
    actividad_id = Column(Integer, ForeignKey("aula_actividades.id"))
    titulo = Column(String, nullable=False)
    resumen = Column(String, nullable=True)
    contenido = Column(Text, nullable=True)        # JSON de bloques
    video_url = Column(String, nullable=True)      # link de YouTube -> se incrusta
    duracion_min = Column(Integer, default=10)
    materiales = Column(Text, nullable=True)       # JSON de archivos del tema
    quiz = Column(Text, nullable=True)             # JSON de preguntas
    orden = Column(Integer, default=1)


class ProgresoTemaClase(Base):
    __tablename__ = "aula_progreso_tema"
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    tema_id = Column(Integer, ForeignKey("aula_temas.id"))
    actividad_id = Column(Integer, ForeignKey("aula_actividades.id"))
    completado = Column(Boolean, default=False)
    quiz_puntaje = Column(Integer, nullable=True)
    minutos = Column(Integer, default=0)
    fecha = Column(DateTime, nullable=True)


class GrabacionClase(Base):
    """Biblioteca de clases en vivo grabadas (punto 17)."""
    __tablename__ = "grabaciones"
    id = Column(Integer, primary_key=True)
    sala_id = Column(Integer, ForeignKey("salas_virtuales.id"), nullable=True)
    salon_id = Column(Integer, ForeignKey("salones.id"))
    institucion_id = Column(Integer, ForeignKey("instituciones.id"), nullable=True)
    titulo = Column(String, nullable=False)
    materia = Column(String, nullable=True)
    docente = Column(String, nullable=True)
    fecha = Column(DateTime, nullable=True)
    duracion_min = Column(Integer, default=45)
    video_url = Column(String, nullable=True)
    resumen = Column(Text, nullable=True)
    transcripcion = Column(Text, nullable=True)
    n_vistas = Column(Integer, default=0)


class ConfigDominio(Base):
    """Configuracion de dominio/DNS por tenant, para el super admin (punto 1)."""
    __tablename__ = "config_dominios"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    dominio = Column(String, nullable=False)
    subdominio = Column(String, nullable=True)      # ej: "sistema" -> sistema.ietac.edu.co
    proveedor = Column(String, nullable=True)       # hostinger|godaddy|namecheap|cloudflare|otro
    modo_montaje = Column(String, default="subdominio")  # subdominio|dominio_propio|ruta
    ip_servidor = Column(String, nullable=True)
    estado_dns = Column(String, default="pendiente")  # pendiente|propagando|activo|error
    ssl_estado = Column(String, default="pendiente")
    wordpress_url = Column(String, nullable=True)   # si la web institucional es WP
    integracion_wp = Column(String, default="ninguna")  # ninguna|plugin|iframe|enlace
    verificado = Column(Boolean, default=False)
    ultima_verificacion = Column(DateTime, nullable=True)
    notas = Column(Text, nullable=True)


class Suscripcion(Base):
    """Contrato comercial del tenant: desde cuando, hasta cuando, cuanto (punto 2)."""
    __tablename__ = "suscripciones"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    plan = Column(String, default="institucional")   # piloto|institucional|municipal|departamental
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    valor_anual = Column(Float, default=0)
    estado = Column(String, default="activa")        # activa|por_vencer|vencida|suspendida
    facturas = Column(Text, nullable=True)           # JSON de pagos recibidos
    n_usuarios_incluidos = Column(Integer, default=100)
    notas = Column(Text, nullable=True)


class EntregaAula(Base):
    __tablename__ = "aula_entregas"
    id = Column(Integer, primary_key=True)
    actividad_id = Column(Integer, ForeignKey("aula_actividades.id"))
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    estado = Column(String, default="pendiente")
    nota = Column(Float, nullable=True)
    retro = Column(String, nullable=True)
    fecha_entrega = Column(DateTime, nullable=True)
    respuesta = Column(Text, nullable=True)         # lo que el alumno entrega (texto)
    archivo = Column(String, nullable=True)         # nombre del archivo adjunto (simulado)


class EventoCalendario(Base):
    """Agenda del docente: clases, obligaciones, pendientes, evaluaciones."""
    __tablename__ = "calendario"
    id = Column(Integer, primary_key=True)
    personal_id = Column(Integer, ForeignKey("personal.id"))
    fecha = Column(Date, nullable=False)
    hora = Column(String, nullable=True)
    titulo = Column(String, nullable=False)
    tipo = Column(String, default="obligacion")
    detalle = Column(String, nullable=True)
    done = Column(Boolean, default=False)


class CuentaFSE(Base):
    __tablename__ = "fse_cuentas"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    codigo = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    tipo = Column(String, nullable=False)


class PlanFSE(Base):
    __tablename__ = "fse_plan"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    anio = Column(Integer, nullable=False)
    concepto = Column(String, nullable=False)
    cuenta_codigo = Column(String, nullable=True)
    prioridad = Column(Integer, default=2)
    mes_planeado = Column(Integer, default=1)
    valor_presupuestado = Column(Float, default=0.0)
    estado = Column(String, default="pendiente")


class RegistroPresupuestal(Base):
    __tablename__ = "fse_rp"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    consecutivo = Column(String, nullable=False)
    tipo = Column(String, default="rp")
    fecha = Column(Date, nullable=False)
    objeto = Column(String, nullable=False)
    proveedor = Column(String, nullable=True)
    nit = Column(String, nullable=True)
    valor = Column(Float, nullable=False)
    valor_secop = Column(Float, nullable=True)
    secop_url = Column(String, nullable=True)
    estado = Column(String, default="vigente")


class MovimientoFSE(Base):
    __tablename__ = "fse_movimientos"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    fecha = Column(Date, nullable=False)
    tipo = Column(String, nullable=False)
    cuenta_codigo = Column(String, nullable=True)
    concepto = Column(String, nullable=False)
    proveedor = Column(String, nullable=True)
    nit = Column(String, nullable=True)
    valor = Column(Float, nullable=False)
    metodo = Column(String, nullable=True)
    comprobante = Column(String, nullable=True)
    estado = Column(String, default="registrado")
    rubro_id = Column(Integer, ForeignKey("fse_rubros.id"), nullable=True)   # asignación a rubro
    soporte = Column(String, nullable=True)      # nombre del comprobante/evidencia adjunta


class Contratista(Base):
    """Proveedores del FSE con expediente documental (SECOP 2) y capacidad legal."""
    __tablename__ = "contratistas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    nit = Column(String, nullable=True)
    tipo = Column(String, default="juridica")
    telefono = Column(String, nullable=True)
    email = Column(String, nullable=True)
    documentos = Column(Text, nullable=True)    # JSON {clave:{ok,archivo,fecha}} (acepta bool legado)
    portal_token = Column(String, nullable=True)  # link de autogestión para subir documentos
    confianza = Column(Integer, default=60)
    capacidad_smmlv = Column(Float, default=20.0)
    contratado_anio = Column(Float, default=0.0)
    notas = Column(String, nullable=True)
    # Datos ricos del expediente (punto 24) y validación jurídica (punto 22)
    ciiu = Column(String, nullable=True)           # actividad económica registrada
    direccion = Column(String, nullable=True)
    ciudad = Column(String, nullable=True)
    rep_legal = Column(String, nullable=True)
    rep_legal_cc = Column(String, nullable=True)
    banco = Column(String, nullable=True)
    cuenta_banco = Column(String, nullable=True)
    tipo_cuenta = Column(String, nullable=True)
    propuestas = Column(Text, nullable=True)       # JSON: propuestas subidas por el portal


class Contrato(Base):
    """Pipeline régimen especial FSE (Decreto 4791/2008 art. 17):
    borrador → documentos → juridica → firma → firmado → ejecucion → liquidado."""
    __tablename__ = "contratos"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    contratista_id = Column(Integer, ForeignKey("contratistas.id"))
    numero = Column(String, nullable=False)
    objeto = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    cdp_num = Column(String, nullable=True)
    rp_num = Column(String, nullable=True)
    fecha = Column(Date, nullable=False)
    estado = Column(String, default="borrador")
    secop_url = Column(String, nullable=True)
    firmas = Column(Text, nullable=True)    # JSON [{rol,nombre,firmado,fecha,metodo}]
    plan_id = Column(Integer, ForeignKey("fse_plan.id"), nullable=True)
    nota_juridica = Column(String, nullable=True)
    tipo_contrato = Column(String, default="suministro")  # suministro|servicio|obra|pae
    etapas_fechas = Column(Text, nullable=True)   # JSON {etapa: fecha_iso} — cronología para auditoría
    cotizaciones = Column(Text, nullable=True)    # JSON [{proveedor,valor,fecha,archivo}]
    cuenta_cobro = Column(Text, nullable=True)    # JSON {numero,fecha,valor,archivo,estado}


class Autorizacion(Base):
    """Grupos de trabajo: el rector autoriza paneles (fse, contratos, datos)."""
    __tablename__ = "autorizaciones"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    personal_id = Column(Integer, ForeignKey("personal.id"))
    paneles = Column(String, nullable=False)


class PublicacionDatos(Base):
    """Historial de datasets publicados en datos.gov.co (simulado)."""
    __tablename__ = "publicaciones_datos"
    id = Column(Integer, primary_key=True)
    titulo = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
    categoria = Column(String, default="Educación")
    licencia = Column(String, default="CC-BY 4.0")
    registros = Column(Integer, default=0)
    url_simulada = Column(String, nullable=True)
    fecha = Column(DateTime, nullable=False)
    responsable = Column(String, nullable=True)


class Comunicado(Base):
    """Notificaciones push internas: rectoría (o coordinación) envía a toda la
    institución, a docentes, a coordinadores, a una persona o a los acudientes
    de un salón (WhatsApp masivo simulado)."""
    __tablename__ = "comunicados"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    emisor = Column(String, nullable=False)
    destinatario_tipo = Column(String, nullable=False)  # institucion|docentes|coordinadores|persona|salon_acudientes
    destinatario_id = Column(Integer, nullable=True)    # persona_id o salon_id según el tipo
    titulo = Column(String, nullable=False)
    mensaje = Column(Text, nullable=False)
    fecha = Column(DateTime, nullable=False)
    n_destinatarios = Column(Integer, default=0)


class NotificacionPersona(Base):
    """Bandeja individual: una fila por persona destinataria (campana 🔔)."""
    __tablename__ = "notificaciones_persona"
    id = Column(Integer, primary_key=True)
    comunicado_id = Column(Integer, ForeignKey("comunicados.id"))
    personal_id = Column(Integer, ForeignKey("personal.id"))
    leida = Column(Boolean, default=False)


class SolicitudSalon(Base):
    """Docente solicita ser asignado a un salón; rector/coordinador aprueba o rechaza."""
    __tablename__ = "solicitudes_salon"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    personal_id = Column(Integer, ForeignKey("personal.id"))
    salon_id = Column(Integer, ForeignKey("salones.id"))
    rol_solicitado = Column(String, default="docente")   # docente | director
    materia = Column(String, nullable=True)
    estado = Column(String, default="pendiente")         # pendiente | aprobada | rechazada
    nota = Column(String, nullable=True)
    fecha = Column(DateTime, nullable=True)


class SalaVirtual(Base):
    """Sala de clase en vivo / chat entre alumnos con el docente como moderador."""
    __tablename__ = "salas_virtuales"
    id = Column(Integer, primary_key=True)
    salon_id = Column(Integer, ForeignKey("salones.id"))
    actividad_id = Column(Integer, ForeignKey("aula_actividades.id"), nullable=True)
    titulo = Column(String, nullable=False)
    docente_id = Column(Integer, ForeignKey("personal.id"), nullable=True)
    estado = Column(String, default="programada")        # programada | en_vivo | finalizada
    fecha = Column(DateTime, nullable=True)


class MensajeSala(Base):
    __tablename__ = "mensajes_sala"
    id = Column(Integer, primary_key=True)
    sala_id = Column(Integer, ForeignKey("salas_virtuales.id"))
    autor_tipo = Column(String, default="alumno")        # alumno | docente
    autor_id = Column(Integer, nullable=True)
    autor_nombre = Column(String, nullable=True)
    texto = Column(Text, nullable=False)
    fecha = Column(DateTime, nullable=True)


class RubroFSE(Base):
    """Rubro presupuestal del FSE; el rector agrega/quita y ve saldo por rubro."""
    __tablename__ = "fse_rubros"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    nombre = Column(String, nullable=False)
    codigo = Column(String, nullable=True)
    presupuesto = Column(Float, default=0)


class LeccionCurso(Base):
    """Lección de un curso preinstalado (p.ej. Contabilidad básica/media/avanzada)."""
    __tablename__ = "curso_lecciones"
    id = Column(Integer, primary_key=True)
    curso = Column(String, nullable=False)               # contabilidad
    nivel = Column(String, nullable=False)               # basico | moderado | avanzado
    orden = Column(Integer, default=1)
    titulo = Column(String, nullable=False)
    icono = Column(String, nullable=True)
    resumen = Column(Text, nullable=True)
    contenido = Column(Text, nullable=True)              # JSON: secciones + quiz + práctica
    tipo_practica = Column(String, nullable=True)        # inventario | arqueo | factura | cotizacion | declaracion | balance | none


class ProgresoAlumno(Base):
    __tablename__ = "curso_progreso"
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    leccion_id = Column(Integer, ForeignKey("curso_lecciones.id"))
    completada = Column(Boolean, default=False)
    quiz_puntaje = Column(Integer, nullable=True)
    practica_data = Column(Text, nullable=True)          # JSON de la práctica del alumno
    fecha = Column(DateTime, nullable=True)


class PagoContrato(Base):
    """Pagos de un contrato: el rector marca pagado y anexa la evidencia."""
    __tablename__ = "pagos_contrato"
    id = Column(Integer, primary_key=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id"))
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    concepto = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    estado = Column(String, default="pendiente")   # pendiente | pagado
    fecha_programada = Column(Date, nullable=True)
    fecha_pago = Column(Date, nullable=True)
    metodo = Column(String, nullable=True)
    evidencia = Column(String, nullable=True)      # nombre del soporte de pago
    nota = Column(String, nullable=True)


class Sede(Base):
    """Sede o campus de una institucion. Un colegio rural tipicamente tiene
    una sede principal y varias sedes satelite en veredas."""
    __tablename__ = "sedes"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    nombre = Column(String, nullable=False)
    codigo_dane = Column(String, nullable=True)
    tipo = Column(String, default="satelite")      # principal | satelite
    zona = Column(String, default="rural")         # urbana | rural
    direccion = Column(String, nullable=True)
    barrio_vereda = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    coordinador_id = Column(Integer, ForeignKey("personal.id"), nullable=True)
    niveles = Column(String, nullable=True)        # "Preescolar,Primaria" etc
    tiene_internet = Column(Boolean, default=True)
    tiene_pae = Column(Boolean, default=True)
    distancia_km = Column(Float, default=0)        # desde la sede principal


class SolicitudRecurso(Base):
    """Buzon de necesidades: el docente pide algo y coordinacion/rectoria
    resuelve. Alimenta directamente el plan de compras y la contratacion."""
    __tablename__ = "solicitudes_recurso"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=True)
    solicitante_id = Column(Integer, ForeignKey("personal.id"))
    categoria = Column(String, default="material")  # material|infraestructura|tecnologia|personal|pae|otro
    titulo = Column(String, nullable=False)
    detalle = Column(Text, nullable=True)
    cantidad = Column(Integer, default=1)
    urgencia = Column(String, default="media")      # alta|media|baja
    valor_estimado = Column(Float, default=0)
    estado = Column(String, default="pendiente")    # pendiente|aprobada|rechazada|en_compra|resuelta
    respuesta = Column(String, nullable=True)
    resuelto_por = Column(String, nullable=True)
    fecha = Column(DateTime, nullable=True)
    fecha_respuesta = Column(DateTime, nullable=True)
    plan_id = Column(Integer, ForeignKey("fse_plan.id"), nullable=True)


class VotoPropuesta(Base):
    """Junta directiva aprueba o rechaza una propuesta de contratacion."""
    __tablename__ = "votos_propuesta"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    contratista_id = Column(Integer, ForeignKey("contratistas.id"))
    propuesta_idx = Column(Integer, default=0)      # indice dentro del JSON de propuestas
    miembro = Column(String, nullable=False)        # nombre del miembro de la junta
    rol_junta = Column(String, nullable=True)       # Rector, Docente, Padre, Estudiante, Sector productivo
    voto = Column(String, default="pendiente")      # aprueba|rechaza|pendiente
    observacion = Column(String, nullable=True)
    fecha = Column(DateTime, nullable=True)


# ═══════════════════════════════════════════════════════════════════
#  LMS: CURSOS PREINSTALADOS (curso -> modulos -> temas -> quiz)
#  Estructura inspirada en las plataformas de cursos: el alumno avanza
#  tema por tema, desbloqueando el siguiente, con progreso visible.
# ═══════════════════════════════════════════════════════════════════
class Curso(Base):
    __tablename__ = "cursos"
    id = Column(Integer, primary_key=True)
    slug = Column(String, nullable=False)
    titulo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=True)
    categoria = Column(String, nullable=True)
    icono = Column(String, nullable=True)
    color = Column(String, default="#0E7C86")
    portada = Column(Text, nullable=True)          # dataURL o emoji grande
    duracion_texto = Column(String, nullable=True)  # "8 horas"
    nivel = Column(String, default="basico")        # basico|medio|avanzado|todos
    grado_sugerido = Column(String, nullable=True)  # "6-11"
    estado = Column(String, default="publicado")
    orden = Column(Integer, default=1)
    preinstalado = Column(Boolean, default=True)


class ModuloCurso(Base):
    __tablename__ = "curso_modulos"
    id = Column(Integer, primary_key=True)
    curso_id = Column(Integer, ForeignKey("cursos.id"))
    titulo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=True)
    nivel = Column(String, default="basico")        # basico|medio|avanzado
    icono = Column(String, nullable=True)
    orden = Column(Integer, default=1)


class TemaCurso(Base):
    """Un tema = una 'clase' del curso. El alumno la abre, la estudia,
    hace su practica y su quiz, y la marca como completada para avanzar."""
    __tablename__ = "curso_temas"
    id = Column(Integer, primary_key=True)
    modulo_id = Column(Integer, ForeignKey("curso_modulos.id"))
    titulo = Column(String, nullable=False)
    resumen = Column(String, nullable=True)
    contenido = Column(Text, nullable=True)         # JSON: bloques (texto, ejemplo, tip, tabla, video)
    duracion_min = Column(Integer, default=12)
    tipo_practica = Column(String, nullable=True)   # inventario|arqueo|factura|balance|declaracion|nomina|flujo|none
    quiz = Column(Text, nullable=True)              # JSON de preguntas
    recursos = Column(Text, nullable=True)          # JSON de materiales descargables
    orden = Column(Integer, default=1)


class ProgresoTema(Base):
    __tablename__ = "curso_progreso_tema"
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    tema_id = Column(Integer, ForeignKey("curso_temas.id"))
    curso_id = Column(Integer, ForeignKey("cursos.id"))
    completado = Column(Boolean, default=False)
    quiz_puntaje = Column(Integer, nullable=True)
    quiz_intentos = Column(Integer, default=0)
    practica_data = Column(Text, nullable=True)
    minutos = Column(Integer, default=0)
    fecha = Column(DateTime, nullable=True)


class InscripcionCurso(Base):
    __tablename__ = "curso_inscripciones"
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    curso_id = Column(Integer, ForeignKey("cursos.id"))
    inscrito_por = Column(String, nullable=True)
    fecha = Column(DateTime, nullable=True)
    certificado = Column(Boolean, default=False)


# ═══════════════════════════════════════════════════════════════════
#  GESTION DE USUARIOS: registro, aprobacion, roles, permisos, auditoria
# ═══════════════════════════════════════════════════════════════════
class Usuario(Base):
    """Cuenta de acceso al sistema. Se vincula a Personal (staff) o a
    Estudiante (alumno). El rector administra todas las de su institucion."""
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"), nullable=True)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=True)
    personal_id = Column(Integer, ForeignKey("personal.id"), nullable=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"), nullable=True)
    usuario = Column(String, nullable=False)        # nombre de usuario / correo
    nombre = Column(String, nullable=False)
    email = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    documento = Column(String, nullable=True)
    rol = Column(String, default="docente")
    estado = Column(String, default="activo")       # pendiente|activo|suspendido|rechazado
    permisos = Column(Text, nullable=True)          # JSON: permisos extra concedidos
    foto = Column(Text, nullable=True)
    ultimo_acceso = Column(DateTime, nullable=True)
    n_accesos = Column(Integer, default=0)
    creado_por = Column(String, nullable=True)
    fecha_registro = Column(DateTime, nullable=True)
    nota_admin = Column(String, nullable=True)
    debe_cambiar_clave = Column(Boolean, default=True)


class LogAcceso(Base):
    """Auditoria: quien entro, que hizo, desde donde y cuando."""
    __tablename__ = "log_accesos"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"), nullable=True)
    usuario_nombre = Column(String, nullable=True)
    accion = Column(String, nullable=False)         # login|logout|registro|aprobacion|cambio_rol|suspension|eliminacion
    detalle = Column(String, nullable=True)
    ip = Column(String, nullable=True)
    resultado = Column(String, default="ok")        # ok|fallido|bloqueado
    fecha = Column(DateTime, nullable=True)


class ColaOffline(Base):
    """Acciones hechas sin internet que esperan sincronizarse (modo offline)."""
    __tablename__ = "cola_offline"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"), nullable=True)
    origen = Column(String, nullable=True)          # nombre del docente/dispositivo
    tipo = Column(String, nullable=False)           # asistencia|nota|entrega|alerta|observador
    payload = Column(Text, nullable=False)          # JSON de la accion
    creado_en = Column(DateTime, nullable=True)     # cuando ocurrio de verdad
    sincronizado = Column(Boolean, default=False)
    sincronizado_en = Column(DateTime, nullable=True)
    resultado = Column(String, nullable=True)


class FirmaObservador(Base):
    """Firma en linea del observador por el alumno y el acudiente (punto 23)."""
    __tablename__ = "firmas_observador"
    id = Column(Integer, primary_key=True)
    observacion_id = Column(Integer, ForeignKey("observador.id"), nullable=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    firmante = Column(String, nullable=False)        # alumno | acudiente | docente
    nombre = Column(String, nullable=True)
    documento = Column(String, nullable=True)
    codigo_otp = Column(String, nullable=True)
    firmado = Column(Boolean, default=False)
    fecha = Column(DateTime, nullable=True)
    ip = Column(String, nullable=True)
    comentario = Column(String, nullable=True)


class MensajeBuzon(Base):
    """Conversacion dentro de una solicitud de recurso (punto 27)."""
    __tablename__ = "buzon_mensajes"
    id = Column(Integer, primary_key=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes_recurso.id"))
    autor = Column(String, nullable=False)
    rol = Column(String, nullable=True)
    texto = Column(Text, nullable=False)
    fecha = Column(DateTime, nullable=True)


class PublicacionSECOP(Base):
    """Publicacion de un contrato en SECOP I / II (punto 33)."""
    __tablename__ = "secop_publicaciones"
    id = Column(Integer, primary_key=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id"))
    plataforma = Column(String, default="secop2")     # secop1 | secop2 | tvec
    numero_proceso = Column(String, nullable=True)
    modalidad = Column(String, nullable=True)
    url = Column(String, nullable=True)
    estado = Column(String, default="borrador")       # borrador|publicado|adjudicado|error
    fecha_publicacion = Column(DateTime, nullable=True)
    documentos = Column(Text, nullable=True)          # JSON de anexos publicados
    respuesta = Column(Text, nullable=True)           # respuesta simulada del sistema


class ExportacionDatos(Base):
    """Registro de exportaciones para portales de datos y entrenamiento (punto 32)."""
    __tablename__ = "exportaciones"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"), nullable=True)
    destino = Column(String, nullable=False)          # datos_gov|mintic|entrenamiento|portal_institucion
    formato = Column(String, default="json")          # json|csv|jsonl|parquet
    dataset = Column(String, nullable=True)
    n_registros = Column(Integer, default=0)
    tamano_kb = Column(Float, default=0)
    anonimizado = Column(Boolean, default=True)
    estado = Column(String, default="generado")
    url = Column(String, nullable=True)
    fecha = Column(DateTime, nullable=True)
    proxima_sync = Column(DateTime, nullable=True)
    frecuencia = Column(String, nullable=True)        # manual|diaria|semanal|mensual


class TokenVerificacion(Base):
    """Confirmacion por correo y proteccion anti-spam del registro (punto 26)."""
    __tablename__ = "tokens_verificacion"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    email = Column(String, nullable=False)
    token = Column(String, nullable=False)
    tipo = Column(String, default="registro")     # registro|recuperacion|cambio_email
    usado = Column(Boolean, default=False)
    intentos = Column(Integer, default=0)
    ip_origen = Column(String, nullable=True)
    creado = Column(DateTime, nullable=True)
    expira = Column(DateTime, nullable=True)


class IntentoRegistro(Base):
    """Control anti-spam: cuantos intentos por IP y por correo."""
    __tablename__ = "intentos_registro"
    id = Column(Integer, primary_key=True)
    ip = Column(String, nullable=True)
    email = Column(String, nullable=True)
    resultado = Column(String, default="ok")      # ok|bloqueado|duplicado|invalido
    motivo = Column(String, nullable=True)
    fecha = Column(DateTime, nullable=True)


class AsignacionHorario(Base):
    """Quien dicta que materia, en que salon y a que hora (puntos 19, 11)."""
    __tablename__ = "asignaciones_horario"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=True)
    salon_id = Column(Integer, ForeignKey("salones.id"))
    personal_id = Column(Integer, ForeignKey("personal.id"), nullable=True)
    materia = Column(String, nullable=False)
    dia = Column(String, nullable=False)          # Lunes..Viernes
    hora_inicio = Column(String, nullable=False)  # "06:45"
    hora_fin = Column(String, nullable=False)
    asignado_por = Column(String, nullable=True)
    estado = Column(String, default="activo")     # activo|propuesto|cancelado
    nota = Column(String, nullable=True)


class RevisionTema(Base):
    """Coordinacion revisa el tema y el material del docente (punto 20, 22)."""
    __tablename__ = "revisiones_tema"
    id = Column(Integer, primary_key=True)
    tema_plan_id = Column(Integer, ForeignKey("temas_plan.id"), nullable=True)
    actividad_id = Column(Integer, ForeignKey("aula_actividades.id"), nullable=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    revisor = Column(String, nullable=False)
    estado = Column(String, default="pendiente")  # pendiente|aprobado|ajustes|rechazado
    observacion = Column(Text, nullable=True)
    fecha = Column(DateTime, nullable=True)


class EtapaContrato(Base):
    """Rejilla real del proceso de contratacion (punto 11).

    1. Reciben papeles -> 1.1 cotizaciones y habilitantes -> 1.2 rejilla + CDP
    -> 1.3 redaccion -> 1.4 impresion -> 1.5 firma -> 1.4.1 acta inicio
    -> 1.6 SECOP -> 1.7 archivo -> acta final."""
    __tablename__ = "etapas_contrato"
    id = Column(Integer, primary_key=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id"))
    codigo = Column(String, nullable=False)          # "1.1", "1.2"...
    nombre = Column(String, nullable=False)
    orden = Column(Integer, default=1)
    estado = Column(String, default="pendiente")     # pendiente|en_proceso|completada|omitida
    responsable = Column(String, nullable=True)
    fecha_limite = Column(Date, nullable=True)
    fecha_completada = Column(Date, nullable=True)
    documentos = Column(Text, nullable=True)         # JSON de archivos de ESTA etapa
    nota = Column(Text, nullable=True)


class ActaContrato(Base):
    """Actas de inicio, parciales y final, con sus fechas legales."""
    __tablename__ = "actas_contrato"
    id = Column(Integer, primary_key=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id"))
    tipo = Column(String, nullable=False)            # inicio|parcial|suspension|reinicio|final|liquidacion
    numero = Column(String, nullable=True)
    fecha = Column(Date, nullable=True)
    contenido = Column(Text, nullable=True)
    firmantes = Column(Text, nullable=True)          # JSON
    valor_ejecutado = Column(Float, default=0)
    pct_avance = Column(Integer, default=0)
    estado = Column(String, default="borrador")      # borrador|firmada
    archivo = Column(String, nullable=True)
    observaciones = Column(Text, nullable=True)


class ClausulaContrato(Base):
    """Clausulas de la minuta, editables por juridica."""
    __tablename__ = "clausulas_contrato"
    id = Column(Integer, primary_key=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id"))
    numero = Column(Integer, default=1)
    titulo = Column(String, nullable=False)
    texto = Column(Text, nullable=False)
    obligatoria = Column(Boolean, default=True)
    editada = Column(Boolean, default=False)


class TrasladoRubro(Base):
    """Traslado presupuestal entre rubros, con control de legalidad (punto 16)."""
    __tablename__ = "traslados_rubro"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    rubro_origen_id = Column(Integer, ForeignKey("fse_rubros.id"))
    rubro_destino_id = Column(Integer, ForeignKey("fse_rubros.id"))
    valor = Column(Float, nullable=False)
    justificacion = Column(Text, nullable=False)
    riesgo = Column(String, default="bajo")          # bajo|medio|alto
    alertas = Column(Text, nullable=True)            # JSON de advertencias legales
    acepto_riesgo = Column(Boolean, default=False)
    acta_consejo = Column(String, nullable=True)     # numero del acta que lo aprueba
    solicitado_por = Column(String, nullable=True)
    estado = Column(String, default="pendiente")     # pendiente|aprobado|rechazado|ejecutado
    fecha = Column(DateTime, nullable=True)
    fecha_ejecucion = Column(DateTime, nullable=True)


class IntentoEvaluacion(Base):
    """Control de intentos de una evaluacion (punto 7)."""
    __tablename__ = "intentos_evaluacion"
    id = Column(Integer, primary_key=True)
    actividad_id = Column(Integer, ForeignKey("aula_actividades.id"))
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    intento = Column(Integer, default=1)
    respuestas = Column(Text, nullable=True)         # JSON
    puntaje = Column(Float, nullable=True)
    nota = Column(Float, nullable=True)
    iniciado = Column(DateTime, nullable=True)
    entregado = Column(DateTime, nullable=True)
    minutos_usados = Column(Integer, default=0)
    es_recuperacion = Column(Boolean, default=False)
    revisado = Column(Boolean, default=False)


class NegocioAlumno(Base):
    """Sistema contable de practica del alumno (punto 24)."""
    __tablename__ = "negocios_alumno"
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    nombre = Column(String, nullable=False)
    tipo = Column(String, default="tienda")
    capital_inicial = Column(Float, default=500000)
    caja = Column(Float, default=500000)
    banco = Column(Float, default=0)
    creado = Column(DateTime, nullable=True)


class ProductoAlumno(Base):
    __tablename__ = "productos_alumno"
    id = Column(Integer, primary_key=True)
    negocio_id = Column(Integer, ForeignKey("negocios_alumno.id"))
    nombre = Column(String, nullable=False)
    foto = Column(Text, nullable=True)
    cantidad = Column(Integer, default=0)
    costo = Column(Float, default=0)
    precio = Column(Float, default=0)
    minimo = Column(Integer, default=5)


class MovimientoAlumno(Base):
    __tablename__ = "movimientos_alumno"
    id = Column(Integer, primary_key=True)
    negocio_id = Column(Integer, ForeignKey("negocios_alumno.id"))
    tipo = Column(String, nullable=False)             # compra|venta|gasto|ingreso|arqueo
    producto_id = Column(Integer, ForeignKey("productos_alumno.id"), nullable=True)
    descripcion = Column(String, nullable=True)
    cantidad = Column(Integer, default=1)
    valor_unitario = Column(Float, default=0)
    total = Column(Float, default=0)
    iva = Column(Float, default=0)
    metodo = Column(String, default="efectivo")
    fecha = Column(DateTime, nullable=True)
    nota = Column(String, nullable=True)


class PerfilLegal(Base):
    """Datos legales de la institucion para encabezar TODOS los documentos.

    Sale de los papeles reales: ordenanza de creacion, decreto reglamentario,
    licencia de funcionamiento, NIT con digito de verificacion, DANE, y los
    datos del rector con su acta de posesion (sin eso no hay contrato valido).
    """
    __tablename__ = "perfil_legal"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    nombre_oficial = Column(String, nullable=False)
    sigla = Column(String, nullable=True)
    ordenanza = Column(String, nullable=True)          # "020 de Noviembre 29 de 2002"
    decreto = Column(String, nullable=True)            # "773 del 10 de octubre de 2003"
    licencia = Column(String, nullable=True)           # "Resolucion 149 del 25 de Febrero de 2011"
    nit = Column(String, nullable=True)
    nit_dv = Column(String, nullable=True)
    dane = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    municipio = Column(String, nullable=True)
    departamento = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    email = Column(String, nullable=True)
    web = Column(String, nullable=True)
    # Rector / ordenador del gasto
    rector_nombre = Column(String, nullable=True)
    rector_cc = Column(String, nullable=True)
    rector_cc_lugar = Column(String, nullable=True)
    rector_acta_posesion = Column(String, nullable=True)
    rector_fecha_posesion = Column(Date, nullable=True)
    rector_firma = Column(Text, nullable=True)
    # Otros firmantes
    contador_nombre = Column(String, nullable=True)
    contador_tp = Column(String, nullable=True)
    pagador_nombre = Column(String, nullable=True)
    # Documentos soporte que respaldan los datos (se suben una vez)
    doc_acta_posesion = Column(Text, nullable=True)    # el acta escaneada
    doc_acta_nombre = Column(String, nullable=True)
    doc_cedula_rector = Column(Text, nullable=True)
    doc_rut = Column(Text, nullable=True)
    doc_ordenanza = Column(Text, nullable=True)
    doc_licencia = Column(Text, nullable=True)
    doc_acuerdo_contratacion = Column(Text, nullable=True)   # reglamento del Consejo
    doc_camara_comercio = Column(Text, nullable=True)
    # Consejo Directivo (aprueba presupuesto y traslados)
    consejo_acta_vigente = Column(String, nullable=True)
    consejo_fecha = Column(Date, nullable=True)
    consejo_miembros = Column(Text, nullable=True)      # JSON
    # Control de configuracion
    configurado_por = Column(String, nullable=True)
    fecha_configuracion = Column(DateTime, nullable=True)
    es_demo = Column(Boolean, default=True)
    # Membrete
    logo_izq = Column(Text, nullable=True)
    logo_der = Column(Text, nullable=True)
    pie_pagina = Column(String, nullable=True)
    # Consecutivos
    consec_cdp = Column(String, default="04")
    consec_rp = Column(String, default="05")
    consec_contrato = Column(Integer, default=0)
    vigencia = Column(Integer, default=2026)


class FilaRejilla(Base):
    """Una fila de la rejilla: el registro maestro que amarra todo.

    RUBRO -> CDP (N + fecha) -> INVITACION (N + fecha) -> CONTRATO (N + fecha)
    -> RP (N + fecha). Las fechas de aqui son las que mandan en todos los
    documentos que se generen.
    """
    __tablename__ = "rejilla"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    contrato_id = Column(Integer, ForeignKey("contratos.id"), nullable=True)
    vigencia = Column(Integer, default=2026)
    consecutivo = Column(Integer, nullable=False)
    # Presupuesto
    rubro_codigo = Column(String, nullable=True)
    rubro_nombre = Column(String, nullable=True)
    fuente = Column(String, nullable=True)
    valor = Column(Float, default=0)
    unspsc = Column(String, nullable=True)
    # CDP
    cdp_num = Column(String, nullable=True)
    cdp_fecha = Column(Date, nullable=True)
    # Proceso
    descripcion = Column(Text, nullable=True)
    proyecto_fecha = Column(Date, nullable=True)
    cotizacion_fecha = Column(Date, nullable=True)
    invitacion_num = Column(String, nullable=True)
    invitacion_fecha = Column(Date, nullable=True)
    cierre_fecha = Column(Date, nullable=True)
    evaluacion_fecha = Column(Date, nullable=True)
    aceptacion_fecha = Column(Date, nullable=True)
    # Contrato
    contrato_num = Column(String, nullable=True)
    contrato_fecha = Column(Date, nullable=True)
    contratista_id = Column(Integer, ForeignKey("contratistas.id"), nullable=True)
    contratista_nombre = Column(String, nullable=True)
    contratista_doc = Column(String, nullable=True)
    # RP
    rp_num = Column(String, nullable=True)
    rp_fecha = Column(Date, nullable=True)
    # Ejecucion
    acta_inicio_fecha = Column(Date, nullable=True)
    plazo_dias = Column(Integer, default=5)
    acta_final_fecha = Column(Date, nullable=True)
    liquidacion_fecha = Column(Date, nullable=True)
    estado = Column(String, default="planeado")
    observaciones = Column(Text, nullable=True)


class DocumentoLegal(Base):
    """Documento generado del proceso, con su version y su archivo."""
    __tablename__ = "documentos_legales"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    rejilla_id = Column(Integer, ForeignKey("rejilla.id"), nullable=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id"), nullable=True)
    tipo = Column(String, nullable=False)
    numero = Column(String, nullable=True)
    titulo = Column(String, nullable=True)
    fecha = Column(Date, nullable=True)
    contenido = Column(Text, nullable=True)          # JSON con los campos
    generado_por = Column(String, nullable=True)
    estado = Column(String, default="borrador")      # borrador|revision|firmado|archivado
    version = Column(Integer, default=1)
    creado = Column(DateTime, nullable=True)


class Correspondencia(Base):
    """Cartas, oficios, derechos de peticion y sus respuestas."""
    __tablename__ = "correspondencia"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    tipo = Column(String, nullable=False)            # carta|oficio|derecho_peticion|respuesta_dp|circular|constancia
    radicado = Column(String, nullable=True)
    asunto = Column(String, nullable=False)
    destinatario = Column(String, nullable=True)
    destinatario_cargo = Column(String, nullable=True)
    destinatario_entidad = Column(String, nullable=True)
    remitente = Column(String, nullable=True)
    cuerpo = Column(Text, nullable=True)
    anexos = Column(Text, nullable=True)
    fecha = Column(Date, nullable=True)
    fecha_limite = Column(Date, nullable=True)       # DP: 15 dias habiles
    estado = Column(String, default="borrador")      # borrador|enviado|respondido|vencido
    respuesta_id = Column(Integer, ForeignKey("correspondencia.id"), nullable=True)
    creado_por = Column(String, nullable=True)
    creado = Column(DateTime, nullable=True)


class PlaneacionDocente(Base):
    """El plan de clases del docente. Lo sube aqui mismo, no a un Drive:
    coordinacion lo ve, lo aprueba o pide ajustes, y queda trazable."""
    __tablename__ = "planeaciones"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    personal_id = Column(Integer, ForeignKey("personal.id"))
    salon_id = Column(Integer, ForeignKey("salones.id"), nullable=True)
    materia = Column(String, nullable=True)
    periodo_numero = Column(Integer, default=3)
    corte = Column(String, nullable=True)
    tipo = Column(String, default="semanal")        # semanal|mensual|periodo
    titulo = Column(String, nullable=False)
    desde = Column(Date, nullable=True)
    hasta = Column(Date, nullable=True)
    objetivos = Column(Text, nullable=True)          # JSON
    contenidos = Column(Text, nullable=True)         # JSON [{semana, tema, actividades, recursos}]
    metodologia = Column(Text, nullable=True)
    evaluacion = Column(Text, nullable=True)
    materiales = Column(Text, nullable=True)         # JSON de archivos anexos
    generado_ia = Column(Boolean, default=False)
    estado = Column(String, default="borrador")      # borrador|enviada|aprobada|ajustes|rechazada
    revisor = Column(String, nullable=True)
    observacion_revisor = Column(Text, nullable=True)
    fecha_envio = Column(DateTime, nullable=True)
    fecha_revision = Column(DateTime, nullable=True)
    creado = Column(DateTime, nullable=True)


class NotaHistorica(Base):
    """Notas importadas de SIMAT u otra plataforma anterior."""
    __tablename__ = "notas_historicas"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"), nullable=True)
    documento = Column(String, nullable=True)
    nombre_origen = Column(String, nullable=True)
    anio = Column(Integer, nullable=False)
    grado = Column(String, nullable=True)
    periodo = Column(Integer, default=1)
    materia = Column(String, nullable=False)
    nota = Column(Float, nullable=True)
    fallas = Column(Integer, default=0)
    origen = Column(String, default="simat")
    lote = Column(String, nullable=True)
    conciliado = Column(Boolean, default=False)


class ImportacionSIMAT(Base):
    """Cada carga de archivo, con su resultado."""
    __tablename__ = "importaciones"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    lote = Column(String, nullable=False)
    archivo = Column(String, nullable=True)
    origen = Column(String, default="simat")
    n_filas = Column(Integer, default=0)
    n_cruzadas = Column(Integer, default=0)
    n_sin_cruce = Column(Integer, default=0)
    n_notas = Column(Integer, default=0)
    detalle = Column(Text, nullable=True)
    estado = Column(String, default="procesado")
    fecha = Column(DateTime, nullable=True)
    hecho_por = Column(String, nullable=True)


class CertificadoEmitido(Base):
    """Certificados que expide secretaria y el alumno descarga."""
    __tablename__ = "certificados"
    id = Column(Integer, primary_key=True)
    institucion_id = Column(Integer, ForeignKey("instituciones.id"))
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    tipo = Column(String, nullable=False)
    numero = Column(String, nullable=True)
    periodo = Column(String, nullable=True)
    datos = Column(Text, nullable=True)
    solicitado = Column(DateTime, nullable=True)
    emitido = Column(DateTime, nullable=True)
    emitido_por = Column(String, nullable=True)
    estado = Column(String, default="solicitado")   # solicitado|emitido|entregado
    codigo_verificacion = Column(String, nullable=True)
    n_descargas = Column(Integer, default=0)


class ConfigSistema(Base):
    """Parámetros del sistema (p.ej. SMMLV vigente)."""
    __tablename__ = "config_sistema"
    id = Column(Integer, primary_key=True)
    clave = Column(String, unique=True, nullable=False)
    valor = Column(String, nullable=False)


class RegistroCenso(Base):
    __tablename__ = "censo_juvenil"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    edad = Column(Integer, nullable=False)
    sexo = Column(String, nullable=False)
    departamento = Column(String, nullable=False)
    municipio = Column(String, nullable=False)
    zona = Column(String, nullable=False)
    barrio_vereda = Column(String, nullable=False)
    nivel_sisben = Column(String, nullable=False)
    estudia = Column(Boolean, nullable=False)
    motivo_no_estudia = Column(String, nullable=True)
    colegio = Column(String, nullable=True)
    zona_riesgo = Column(Boolean, nullable=False, default=False)
    tipo_alerta = Column(String, nullable=True)
    ultimo_contacto = Column(Date, nullable=True)
    estado_seguimiento = Column(String, nullable=False)


def get_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def get_sessionmaker(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
