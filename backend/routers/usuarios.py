"""Gestion de usuarios: registro, aprobacion, roles, permisos y auditoria.

Es el panel de control que pidio el rector: ver TODAS las cuentas de su
institucion, quien entro y cuando, aprobar los registros nuevos, cambiar
roles, conceder permisos puntuales, suspender y eliminar.

Diseño tomado de un gestor de usuarios probado en produccion:
  - registro con aprobacion previa (nadie entra solo)
  - log de auditoria con IP y resultado de cada intento
  - permisos granulares ADEMAS del rol base
  - suspension reversible en vez de borrar (y borrado real solo si se exige)
"""
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (Usuario, LogAcceso, Personal, Estudiante, Institucion, Sede,
                    Autorizacion)
import metadatos

router = APIRouter()

# ── Catalogo de roles del sistema con sus capacidades base ──
ROLES = {
    "rector":          {"label": "Rectoría", "icono": "🎓", "nivel": 1,
                        "desc": "Control total de la institución",
                        "caps": ["ver_todo", "gestionar_usuarios", "gestionar_personal", "gestionar_salones",
                                 "gestionar_cortes", "ver_fse", "gestionar_fse", "ver_contratos",
                                 "gestionar_contratos", "firmar", "aprobar_pagos", "enviar_comunicados",
                                 "ver_datos_ia", "gestionar_sedes"]},
    "coordinador":     {"label": "Coordinación", "icono": "📋", "nivel": 2,
                        "desc": "Gestión académica y convivencia",
                        "caps": ["ver_academico", "gestionar_salones", "gestionar_cortes",
                                 "ver_alertas", "gestionar_alertas", "ver_personal",
                                 "enviar_comunicados", "aprobar_solicitudes"]},
    "docente":         {"label": "Docente", "icono": "👨‍🏫", "nivel": 3,
                        "desc": "Sus salones, sus clases y sus notas",
                        "caps": ["ver_mis_salones", "tomar_asistencia", "gestionar_aula",
                                 "calificar", "ver_mis_notas", "solicitar_recursos"]},
    "psicoorientacion": {"label": "Psicoorientación", "icono": "🧠", "nivel": 3,
                         "desc": "Seguimiento de casos y bienestar",
                         "caps": ["ver_academico", "ver_alertas", "gestionar_alertas", "ver_fichas"]},
    "auxiliar":        {"label": "Contratación", "icono": "🗂️", "nivel": 3,
                        "desc": "Expedientes y documentos de contratistas",
                        "caps": ["ver_contratos", "gestionar_expedientes", "ver_fse"]},
    "contador":        {"label": "Contaduría", "icono": "🧮", "nivel": 3,
                        "desc": "CDP, RP, libro del FSE y pagos",
                        "caps": ["ver_fse", "gestionar_fse", "ver_contratos", "gestionar_cdp_rp",
                                 "ver_datos_ia"]},
    "abogado":         {"label": "Jurídica", "icono": "⚖️", "nivel": 3,
                        "desc": "Revisión legal y firmas",
                        "caps": ["ver_contratos", "revisar_juridica", "firmar"]},
    "secretaria":      {"label": "Secretaría académica", "icono": "📇", "nivel": 3,
                        "desc": "Matrículas y certificados",
                        "caps": ["ver_academico", "gestionar_matriculas"]},
    "vigilante":       {"label": "Vigilancia", "icono": "🛡️", "nivel": 4,
                        "desc": "Control de acceso", "caps": ["ver_basico"]},
    "servicios":       {"label": "Servicios generales", "icono": "🧹", "nivel": 4,
                        "desc": "Apoyo operativo", "caps": ["ver_basico"]},
    "alumno":          {"label": "Estudiante", "icono": "🎒", "nivel": 5,
                        "desc": "Su portal, sus clases y sus cursos",
                        "caps": ["ver_mis_clases", "entregar_tareas", "ver_mis_notas", "tomar_cursos"]},
}

# Permisos que se pueden conceder ADEMAS del rol (lo que el rector delega)
PERMISOS_EXTRA = [
    ("ver_fse", "💰 Ver el Fondo de Servicios Educativos"),
    ("gestionar_fse", "💰 Registrar movimientos del FSE"),
    ("ver_contratos", "📜 Ver la contratación"),
    ("gestionar_contratos", "📜 Crear y editar contratos"),
    ("gestionar_expedientes", "🗂️ Administrar expedientes de contratistas"),
    ("firmar", "✍️ Firmar documentos"),
    ("aprobar_pagos", "💸 Aprobar y registrar pagos"),
    ("gestionar_usuarios", "👥 Administrar cuentas de usuario"),
    ("enviar_comunicados", "📢 Enviar comunicados institucionales"),
    ("ver_datos_ia", "🧠 Ver el panel de Datos & IA"),
    ("gestionar_sedes", "🏫 Administrar sedes"),
    ("aprobar_solicitudes", "📨 Resolver solicitudes de docentes"),
]

ESTADOS = {"pendiente": "⏳ Pendiente de aprobación", "activo": "✅ Activo",
           "suspendido": "⏸️ Suspendido", "rechazado": "❌ Rechazado"}


def _ip(request: Request):
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "—"


def _log(db, institucion_id, usuario_id, nombre, accion, detalle=None,
         ip=None, resultado="ok"):
    db.add(LogAcceso(usuario_id=usuario_id, institucion_id=institucion_id,
                     usuario_nombre=nombre, accion=accion, detalle=detalle,
                     ip=ip or "—", resultado=resultado, fecha=datetime.now()))


def _perms(u):
    try:
        extra = json.loads(u.permisos) if u.permisos else []
    except Exception:
        extra = []
    base = ROLES.get(u.rol, {}).get("caps", [])
    return base, extra


@router.get("/roles")
def roles():
    """Catalogo de roles y permisos para pintar la matriz."""
    return {
        "roles": [{"id": k, **v} for k, v in ROLES.items()],
        "permisos_extra": [{"clave": k, "label": l} for k, l in PERMISOS_EXTRA],
        "estados": ESTADOS,
    }


@router.get("/")
def listar(institucion_id: int, estado: str | None = None, rol: str | None = None,
           q: str | None = None, db: Session = Depends(get_db)):
    """Todos los usuarios de la institución, con su estado y actividad."""
    qq = db.query(Usuario).filter(Usuario.institucion_id == institucion_id)
    if estado:
        qq = qq.filter(Usuario.estado == estado)
    if rol:
        qq = qq.filter(Usuario.rol == rol)
    filas = qq.order_by(Usuario.estado, Usuario.nombre).all()
    if q:
        ql = q.strip().lower()
        filas = [u for u in filas if ql in (u.nombre or "").lower()
                 or ql in (u.usuario or "").lower() or ql in (u.email or "").lower()]
    hoy = datetime.now()
    out = []
    for u in filas[:400]:
        base, extra = _perms(u)
        sd = db.query(Sede).filter(Sede.id == u.sede_id).first()
        dias = (hoy - u.ultimo_acceso).days if u.ultimo_acceso else None
        out.append({
            "id": u.id, "usuario": u.usuario, "nombre": u.nombre, "email": u.email,
            "telefono": u.telefono, "documento": u.documento,
            "rol": u.rol, "rol_label": ROLES.get(u.rol, {}).get("label", u.rol),
            "rol_icono": ROLES.get(u.rol, {}).get("icono", "👤"),
            "estado": u.estado, "estado_label": ESTADOS.get(u.estado, u.estado),
            "foto": u.foto, "sede": sd.nombre if sd else None, "sede_id": u.sede_id,
            "personal_id": u.personal_id, "estudiante_id": u.estudiante_id,
            "permisos_base": base, "permisos_extra": extra,
            "n_accesos": u.n_accesos or 0,
            "ultimo_acceso": u.ultimo_acceso.isoformat(sep=" ", timespec="minutes") if u.ultimo_acceso else None,
            "dias_sin_entrar": dias,
            "inactivo": dias is not None and dias > 30,
            "nunca_entro": u.ultimo_acceso is None,
            "creado_por": u.creado_por, "nota_admin": u.nota_admin,
            "fecha_registro": u.fecha_registro.isoformat(sep=" ", timespec="minutes") if u.fecha_registro else None,
        })
    todos = db.query(Usuario).filter(Usuario.institucion_id == institucion_id).all()
    por_rol = {}
    for u in todos:
        por_rol[u.rol] = por_rol.get(u.rol, 0) + 1
    return {
        "usuarios": out,
        "resumen": {
            "total": len(todos),
            "activos": sum(1 for u in todos if u.estado == "activo"),
            "pendientes": sum(1 for u in todos if u.estado == "pendiente"),
            "suspendidos": sum(1 for u in todos if u.estado == "suspendido"),
            "nunca_entraron": sum(1 for u in todos if not u.ultimo_acceso),
            "inactivos_30d": sum(1 for u in todos if u.ultimo_acceso and
                                 (hoy - u.ultimo_acceso).days > 30),
            "por_rol": [{"rol": k, "label": ROLES.get(k, {}).get("label", k),
                         "icono": ROLES.get(k, {}).get("icono", "👤"), "n": v}
                        for k, v in sorted(por_rol.items(), key=lambda x: -x[1])],
        },
    }


class UsuarioIn(BaseModel):
    id: int | None = 0
    institucion_id: int
    sede_id: int | None = None
    usuario: str
    nombre: str
    email: str | None = ""
    telefono: str | None = ""
    documento: str | None = ""
    rol: str
    estado: str | None = "activo"
    foto: str | None = None
    crear_personal: bool | None = True
    nota_admin: str | None = ""


@router.post("/guardar")
def guardar(payload: UsuarioIn, request: Request, db: Session = Depends(get_db)):
    """Crea o edita una cuenta. Si es personal nuevo, tambien crea su ficha."""
    if not payload.nombre.strip() or not payload.usuario.strip():
        return {"ok": False, "msg": "El nombre y el usuario son obligatorios."}
    if payload.rol not in ROLES:
        return {"ok": False, "msg": "Rol no válido."}
    dup = db.query(Usuario).filter(Usuario.usuario == payload.usuario.strip().lower(),
                                   Usuario.id != (payload.id or 0)).first()
    if dup:
        return {"ok": False, "msg": f"El usuario «{payload.usuario}» ya existe. Elige otro."}
    nuevo = not payload.id
    if payload.id:
        u = db.query(Usuario).filter(Usuario.id == payload.id).first()
        if not u:
            return {"ok": False, "msg": "Usuario no encontrado."}
    else:
        u = Usuario(institucion_id=payload.institucion_id, fecha_registro=datetime.now(),
                    n_accesos=0, debe_cambiar_clave=True)
        db.add(u)
    u.usuario = payload.usuario.strip().lower()[:40]
    u.nombre = payload.nombre.strip()[:90]
    u.email = (payload.email or "").strip()[:90] or None
    u.telefono = (payload.telefono or "").strip()[:30] or None
    u.documento = (payload.documento or "").strip()[:30] or None
    u.rol = payload.rol
    u.sede_id = payload.sede_id
    u.nota_admin = (payload.nota_admin or "").strip()[:300] or None
    if payload.foto is not None:
        u.foto = payload.foto
    if payload.estado in ESTADOS:
        u.estado = payload.estado
    if nuevo:
        u.creado_por = "Rectoría"
    db.flush()

    # Si es personal (no alumno) y no tiene ficha, se le crea
    extra = ""
    if nuevo and payload.crear_personal and u.rol != "alumno" and not u.personal_id:
        p = Personal(institucion_id=payload.institucion_id, sede_id=payload.sede_id,
                     nombre=u.nombre, rol=u.rol, area="", telefono=u.telefono,
                     email=u.email, documento=u.documento, activo=True,
                     foto=u.foto, experiencia_anios=0,
                     fecha_vinculacion=datetime.now().date())
        db.add(p)
        db.flush()
        u.personal_id = p.id
        extra = " También se creó su ficha de personal y su hoja de vida."
    if not nuevo and u.personal_id:
        p = db.query(Personal).filter(Personal.id == u.personal_id).first()
        if p:
            p.nombre, p.rol, p.telefono, p.email = u.nombre, u.rol, u.telefono, u.email
            p.sede_id = u.sede_id
            if payload.foto is not None:
                p.foto = payload.foto
    _log(db, payload.institucion_id, u.id, "Rectoría",
         "registro" if nuevo else "edicion",
         f"{'Creó' if nuevo else 'Editó'} la cuenta de {u.nombre} ({u.rol})", _ip(request))
    db.commit()
    metadatos.registrar_evento("USUARIO_GUARDADO", "Rectoría",
                               institucion_id=payload.institucion_id,
                               payload={"rol": u.rol, "nuevo": nuevo})
    return {"ok": True, "id": u.id,
            "msg": f"Cuenta de {u.nombre} {'creada' if nuevo else 'actualizada'}.{extra}"}


class AccionIn(BaseModel):
    id: int
    motivo: str | None = ""


@router.post("/aprobar")
def aprobar(payload: AccionIn, request: Request, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.id == payload.id).first()
    if not u:
        return {"ok": False, "msg": "Usuario no encontrado."}
    if u.estado != "pendiente":
        return {"ok": False, "msg": "Esta cuenta ya fue revisada."}
    u.estado = "activo"
    extra = ""
    if not u.personal_id and u.rol != "alumno":
        p = Personal(institucion_id=u.institucion_id, sede_id=u.sede_id, nombre=u.nombre,
                     rol=u.rol, area="", telefono=u.telefono, email=u.email,
                     documento=u.documento, activo=True, experiencia_anios=0,
                     fecha_vinculacion=datetime.now().date())
        db.add(p)
        db.flush()
        u.personal_id = p.id
        extra = " Se creó su ficha de personal."
    _log(db, u.institucion_id, u.id, "Rectoría", "aprobacion",
         f"Aprobó el registro de {u.nombre} como {u.rol}", _ip(request))
    db.commit()
    metadatos.registrar_evento("USUARIO_APROBADO", "Rectoría", institucion_id=u.institucion_id)
    return {"ok": True, "msg": f"✅ {u.nombre} aprobado(a). Ya puede entrar al sistema.{extra}"}


@router.post("/rechazar")
def rechazar(payload: AccionIn, request: Request, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.id == payload.id).first()
    if not u:
        return {"ok": False, "msg": "Usuario no encontrado."}
    u.estado = "rechazado"
    u.nota_admin = (payload.motivo or "").strip()[:300] or u.nota_admin
    _log(db, u.institucion_id, u.id, "Rectoría", "rechazo",
         f"Rechazó el registro de {u.nombre}: {payload.motivo or 'sin motivo'}", _ip(request))
    db.commit()
    return {"ok": True, "msg": f"Registro de {u.nombre} rechazado."}


class RolIn(BaseModel):
    id: int
    rol: str


@router.post("/cambiar_rol")
def cambiar_rol(payload: RolIn, request: Request, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.id == payload.id).first()
    if not u:
        return {"ok": False, "msg": "Usuario no encontrado."}
    if payload.rol not in ROLES:
        return {"ok": False, "msg": "Rol no válido."}
    if u.rol == "rector" and payload.rol != "rector":
        otros = db.query(Usuario).filter(Usuario.institucion_id == u.institucion_id,
                                         Usuario.rol == "rector",
                                         Usuario.estado == "activo",
                                         Usuario.id != u.id).count()
        if otros == 0:
            return {"ok": False, "msg": "No puedes quitar el último rector de la institución. Asigna otro primero."}
    anterior = u.rol
    u.rol = payload.rol
    if u.personal_id:
        p = db.query(Personal).filter(Personal.id == u.personal_id).first()
        if p:
            p.rol = payload.rol
    _log(db, u.institucion_id, u.id, "Rectoría", "cambio_rol",
         f"{u.nombre}: {anterior} → {payload.rol}", _ip(request))
    db.commit()
    metadatos.registrar_evento("CAMBIO_ROL", "Rectoría", institucion_id=u.institucion_id,
                               payload={"de": anterior, "a": payload.rol})
    return {"ok": True,
            "msg": f"{u.nombre} pasó de {ROLES[anterior]['label']} a {ROLES[payload.rol]['label']}."}


class PermisosIn(BaseModel):
    id: int
    permisos: list


@router.post("/permisos")
def permisos(payload: PermisosIn, request: Request, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.id == payload.id).first()
    if not u:
        return {"ok": False, "msg": "Usuario no encontrado."}
    validos = {k for k, _l in PERMISOS_EXTRA}
    limpios = [p for p in payload.permisos if p in validos]
    u.permisos = json.dumps(limpios)
    # sincronizar con los paneles del sistema (autorizaciones)
    if u.personal_id:
        paneles = []
        if "ver_fse" in limpios or "gestionar_fse" in limpios:
            paneles.append("fse")
        if any(x in limpios for x in ("ver_contratos", "gestionar_contratos", "gestionar_expedientes")):
            paneles.append("contratos")
        if "ver_datos_ia" in limpios:
            paneles.append("datos")
        a = db.query(Autorizacion).filter(Autorizacion.personal_id == u.personal_id).first()
        if not a:
            a = Autorizacion(institucion_id=u.institucion_id, personal_id=u.personal_id)
            db.add(a)
        a.paneles = ",".join(paneles)
    _log(db, u.institucion_id, u.id, "Rectoría", "permisos",
         f"Actualizó permisos de {u.nombre}: {len(limpios)} concedidos", _ip(request))
    db.commit()
    return {"ok": True, "msg": f"Permisos de {u.nombre} actualizados ({len(limpios)} concedidos)."}


@router.post("/suspender")
def suspender(payload: AccionIn, request: Request, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.id == payload.id).first()
    if not u:
        return {"ok": False, "msg": "Usuario no encontrado."}
    if u.rol == "rector":
        otros = db.query(Usuario).filter(Usuario.institucion_id == u.institucion_id,
                                         Usuario.rol == "rector", Usuario.estado == "activo",
                                         Usuario.id != u.id).count()
        if otros == 0:
            return {"ok": False, "msg": "No puedes suspender al único rector activo."}
    suspender_ahora = u.estado != "suspendido"
    u.estado = "suspendido" if suspender_ahora else "activo"
    if u.personal_id:
        p = db.query(Personal).filter(Personal.id == u.personal_id).first()
        if p:
            p.activo = not suspender_ahora
    if suspender_ahora:
        u.nota_admin = (payload.motivo or "").strip()[:300] or u.nota_admin
    _log(db, u.institucion_id, u.id, "Rectoría",
         "suspension" if suspender_ahora else "reactivacion",
         f"{'Suspendió' if suspender_ahora else 'Reactivó'} a {u.nombre}. {payload.motivo or ''}".strip(),
         _ip(request))
    db.commit()
    return {"ok": True,
            "msg": (f"⏸️ {u.nombre} suspendido(a). No podrá entrar hasta que lo reactives; sus datos y su historial se conservan."
                    if suspender_ahora else f"▶️ {u.nombre} reactivado(a). Ya puede entrar de nuevo.")}


class EliminarIn(BaseModel):
    id: int
    confirmacion: str
    motivo: str | None = ""


@router.post("/eliminar")
def eliminar(payload: EliminarIn, request: Request, db: Session = Depends(get_db)):
    """Borrado definitivo. Exige confirmación escrita, igual que un corte."""
    if (payload.confirmacion or "").strip().upper() != "ELIMINAR":
        return {"ok": False,
                "msg": "Por seguridad escribe la palabra ELIMINAR para confirmar. Si solo quieres impedir el acceso, es mejor SUSPENDER: conserva el historial."}
    u = db.query(Usuario).filter(Usuario.id == payload.id).first()
    if not u:
        return {"ok": False, "msg": "Usuario no encontrado."}
    if u.rol == "rector":
        return {"ok": False, "msg": "No se puede eliminar la cuenta del rector. Cambia primero su rol."}
    nombre = u.nombre
    inst = u.institucion_id
    if u.personal_id:
        p = db.query(Personal).filter(Personal.id == u.personal_id).first()
        if p:
            p.activo = False   # la ficha queda inactiva, no se borra (histórico académico)
    _log(db, inst, None, "Rectoría", "eliminacion",
         f"Eliminó la cuenta de {nombre}. Motivo: {payload.motivo or 'no indicado'}", _ip(request))
    db.delete(u)
    db.commit()
    metadatos.registrar_evento("USUARIO_ELIMINADO", "Rectoría", institucion_id=inst)
    return {"ok": True,
            "msg": f"Cuenta de {nombre} eliminada. Su ficha de personal quedó inactiva (no se borra para conservar el histórico académico)."}


class FotoIn(BaseModel):
    id: int
    foto: str | None = None


@router.post("/foto")
def foto(payload: FotoIn, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.id == payload.id).first()
    if not u:
        return {"ok": False, "msg": "Usuario no encontrado."}
    if payload.foto and len(payload.foto) > 900_000:
        return {"ok": False, "msg": "La imagen es muy pesada. Usa uma menor a 500 KB."}
    u.foto = payload.foto
    if u.personal_id:
        p = db.query(Personal).filter(Personal.id == u.personal_id).first()
        if p:
            p.foto = payload.foto
    db.commit()
    return {"ok": True, "msg": "Foto actualizada." if payload.foto else "Foto eliminada."}


@router.get("/auditoria")
def auditoria(institucion_id: int, accion: str | None = None, dias: int = 30,
              db: Session = Depends(get_db)):
    """Quién entró, cuándo, desde dónde y qué se hizo con las cuentas."""
    desde = datetime.now() - timedelta(days=dias)
    q = db.query(LogAcceso).filter(LogAcceso.institucion_id == institucion_id,
                                   LogAcceso.fecha >= desde)
    if accion:
        q = q.filter(LogAcceso.accion == accion)
    filas = q.order_by(LogAcceso.fecha.desc()).limit(300).all()
    todos = db.query(LogAcceso).filter(LogAcceso.institucion_id == institucion_id,
                                       LogAcceso.fecha >= desde).all()
    ACC = {"login": "🔑 Inicio de sesión", "logout": "🚪 Cierre de sesión",
           "registro": "➕ Cuenta creada", "edicion": "✎ Cuenta editada",
           "aprobacion": "✅ Registro aprobado", "rechazo": "❌ Registro rechazado",
           "cambio_rol": "🔄 Cambio de rol", "permisos": "🔐 Permisos actualizados",
           "suspension": "⏸️ Cuenta suspendida", "reactivacion": "▶️ Cuenta reactivada",
           "eliminacion": "🗑️ Cuenta eliminada", "cambio_perfil": "👤 Perfil actualizado"}
    return {
        "eventos": [{
            "id": x.id, "usuario": x.usuario_nombre, "usuario_id": x.usuario_id,
            "accion": x.accion, "accion_label": ACC.get(x.accion, x.accion),
            "detalle": x.detalle, "ip": x.ip, "resultado": x.resultado,
            "fecha": x.fecha.isoformat(sep=" ", timespec="minutes") if x.fecha else "",
        } for x in filas],
        "resumen": {
            "total": len(todos),
            "logins": sum(1 for x in todos if x.accion == "login" and x.resultado == "ok"),
            "fallidos": sum(1 for x in todos if x.resultado == "fallido"),
            "administrativos": sum(1 for x in todos if x.accion in
                                   ("registro", "aprobacion", "cambio_rol", "suspension",
                                    "eliminacion", "permisos", "rechazo")),
            "dias": dias,
        },
    }


class LoginIn(BaseModel):
    usuario: str
    institucion_id: int | None = None


@router.post("/login")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    """Login de demostración: valida el usuario y registra el acceso.
    En producción aquí se verifica la contraseña con hash y el segundo factor."""
    u = db.query(Usuario).filter(Usuario.usuario == payload.usuario.strip().lower()).first()
    if not u:
        _log(db, payload.institucion_id, None, payload.usuario, "login",
             "Usuario inexistente", _ip(request), "fallido")
        db.commit()
        return {"ok": False, "msg": "Usuario no encontrado."}
    if u.estado == "pendiente":
        return {"ok": False, "msg": "⏳ Tu registro está pendiente de aprobación por rectoría."}
    if u.estado == "suspendido":
        return {"ok": False, "msg": "⏸️ Tu cuenta está suspendida. Comunícate con rectoría."}
    if u.estado == "rechazado":
        return {"ok": False, "msg": "Tu registro fue rechazado. Comunícate con la institución."}
    u.ultimo_acceso = datetime.now()
    u.n_accesos = (u.n_accesos or 0) + 1
    _log(db, u.institucion_id, u.id, u.nombre, "login", None, _ip(request))
    db.commit()
    base, extra = _perms(u)
    return {"ok": True, "id": u.id, "nombre": u.nombre, "rol": u.rol,
            "institucion_id": u.institucion_id, "personal_id": u.personal_id,
            "estudiante_id": u.estudiante_id, "permisos": base + extra,
            "debe_cambiar_clave": bool(u.debe_cambiar_clave),
            "msg": f"Bienvenido(a), {u.nombre.split()[0]}."}


class RegistroIn(BaseModel):
    institucion_id: int
    nombre: str
    usuario: str
    email: str | None = ""
    telefono: str | None = ""
    documento: str | None = ""
    rol: str | None = "docente"
    nota: str | None = ""


@router.post("/registro")
def registro(payload: RegistroIn, request: Request, db: Session = Depends(get_db)):
    """Auto-registro público: queda PENDIENTE hasta que rectoría lo apruebe."""
    if not payload.nombre.strip() or not payload.usuario.strip():
        return {"ok": False, "msg": "Nombre y usuario son obligatorios."}
    if db.query(Usuario).filter(Usuario.usuario == payload.usuario.strip().lower()).first():
        return {"ok": False, "msg": "Ese usuario ya está registrado. Elige otro."}
    if payload.rol not in ROLES or payload.rol in ("rector",):
        return {"ok": False, "msg": "Rol no válido para auto-registro."}
    u = Usuario(institucion_id=payload.institucion_id, usuario=payload.usuario.strip().lower()[:40],
                nombre=payload.nombre.strip()[:90], email=(payload.email or "").strip()[:90] or None,
                telefono=(payload.telefono or "").strip()[:30] or None,
                documento=(payload.documento or "").strip()[:30] or None,
                rol=payload.rol, estado="pendiente", creado_por="Registro público",
                fecha_registro=datetime.now(), n_accesos=0, debe_cambiar_clave=True,
                nota_admin=(payload.nota or "").strip()[:300] or None)
    db.add(u)
    db.flush()
    _log(db, payload.institucion_id, u.id, u.nombre, "registro",
         "Auto-registro desde el portal público", _ip(request))
    db.commit()
    return {"ok": True,
            "msg": "📨 Registro enviado. Rectoría debe aprobarlo antes de que puedas entrar; te avisaremos."}


# ═════════ MI PERFIL: editable por TODOS los roles (punto 16) ═════════
from models import (TokenVerificacion as _Tok, IntentoRegistro as _Int,
                    Estudiante as _EstU, Sede as _SedU)
import secrets as _sec
import re as _re


@router.get("/mi_perfil")
def mi_perfil(usuario_id: int | None = None, personal_id: int | None = None,
              estudiante_id: int | None = None, db: Session = Depends(get_db)):
    """El perfil de quien sea: docente, coordinador, contador, alumno…"""
    u = None
    if usuario_id:
        u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    elif personal_id:
        u = db.query(Usuario).filter(Usuario.personal_id == personal_id).first()
    elif estudiante_id:
        u = db.query(Usuario).filter(Usuario.estudiante_id == estudiante_id).first()
    p = db.query(Personal).filter(Personal.id == (u.personal_id if u else personal_id)).first()
    e = db.query(_EstU).filter(_EstU.id == (u.estudiante_id if u else estudiante_id)).first()
    if not u and not p and not e:
        return {"ok": False, "msg": "Perfil no encontrado."}
    sede = db.query(_SedU).filter(_SedU.id == ((u.sede_id if u else None) or
                                               (p.sede_id if p else None) or
                                               (e.sede_id if e else None))).first()
    base, extra = _perms(u) if u else ([], [])
    rol = (u.rol if u else (p.rol if p else "alumno"))
    return {
        "ok": True,
        "usuario_id": u.id if u else None,
        "personal_id": p.id if p else None,
        "estudiante_id": e.id if e else None,
        "nombre": (p.nombre if p else (e.nombre if e else (u.nombre if u else ""))),
        "usuario": u.usuario if u else None,
        "rol": rol, "rol_label": ROLES.get(rol, {}).get("label", rol),
        "rol_icono": ROLES.get(rol, {}).get("icono", "👤"),
        "email": (p.email if p else None) or (u.email if u else None),
        "telefono": (p.telefono if p else (e.telefono if e else None)) or (u.telefono if u else None),
        "documento": (p.documento if p else None) or (u.documento if u else None),
        "direccion": (getattr(p, "direccion", None) if p else (e.direccion if e else None)),
        "barrio_vereda": (e.barrio_vereda if e else None),
        "foto": (p.foto if p else None) or (u.foto if u else None),
        "profesion": p.profesion if p else None,
        "area": p.area if p else None,
        "experiencia_anios": p.experiencia_anios if p else None,
        "fecha_vinculacion": p.fecha_vinculacion.isoformat() if (p and p.fecha_vinculacion) else None,
        "sede": sede.nombre if sede else None,
        "permisos": base + extra,
        "estado": u.estado if u else "activo",
        "ultimo_acceso": u.ultimo_acceso.isoformat(sep=" ", timespec="minutes") if (u and u.ultimo_acceso) else None,
        "n_accesos": u.n_accesos if u else 0,
        "editable": ["nombre", "email", "telefono", "direccion", "foto", "profesion"],
    }


class MiPerfilIn(BaseModel):
    usuario_id: int | None = None
    personal_id: int | None = None
    estudiante_id: int | None = None
    nombre: str | None = None
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    barrio_vereda: str | None = None
    profesion: str | None = None
    foto: str | None = None


@router.post("/mi_perfil/guardar")
def mi_perfil_guardar(payload: MiPerfilIn, request: Request, db: Session = Depends(get_db)):
    """Cualquiera edita SUS datos: nombre, correo, teléfono, dirección y foto."""
    u = None
    if payload.usuario_id:
        u = db.query(Usuario).filter(Usuario.id == payload.usuario_id).first()
    elif payload.personal_id:
        u = db.query(Usuario).filter(Usuario.personal_id == payload.personal_id).first()
    elif payload.estudiante_id:
        u = db.query(Usuario).filter(Usuario.estudiante_id == payload.estudiante_id).first()
    p = db.query(Personal).filter(Personal.id == (u.personal_id if u else payload.personal_id)).first()
    e = db.query(_EstU).filter(_EstU.id == (u.estudiante_id if u else payload.estudiante_id)).first()
    if not u and not p and not e:
        return {"ok": False, "msg": "Perfil no encontrado."}
    if payload.email and not _re.match(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", payload.email.strip(), _re.I):
        return {"ok": False, "msg": "El correo no tiene un formato válido."}
    if payload.foto and len(payload.foto) > 900_000:
        return {"ok": False, "msg": "La foto es muy pesada. Usa una menor a 500 KB."}
    cambios = []
    def _set(obj, campo, valor, etiqueta):
        if obj is not None and valor is not None and hasattr(obj, campo):
            actual = getattr(obj, campo)
            nuevo = valor.strip() if isinstance(valor, str) else valor
            if nuevo != actual:
                setattr(obj, campo, nuevo)
                if etiqueta not in cambios:
                    cambios.append(etiqueta)
    for obj in (u, p, e):
        _set(obj, "nombre", payload.nombre, "nombre")
        _set(obj, "email", payload.email, "correo")
        _set(obj, "telefono", payload.telefono, "teléfono")
        _set(obj, "direccion", payload.direccion, "dirección")
        _set(obj, "barrio_vereda", payload.barrio_vereda, "barrio/vereda")
        _set(obj, "profesion", payload.profesion, "profesión")
        if payload.foto is not None and hasattr(obj, "foto"):
            obj.foto = payload.foto
            if "foto" not in cambios:
                cambios.append("foto")
    if u:
        _log(db, u.institucion_id, u.id, u.nombre, "cambio_perfil",
             f"Actualizó: {', '.join(cambios)}" if cambios else "Sin cambios", _ip(request))
    db.commit()
    return {"ok": True,
            "msg": (f"✅ Perfil actualizado: {', '.join(cambios)}." if cambios
                    else "No hubo cambios que guardar.")}


# ═════════ REGISTRO SEGURO: correo + anti-spam (punto 26) ═════════
LIMITE_IP_HORA = 3
LIMITE_EMAIL_DIA = 2
DOMINIOS_DESECHABLES = {"tempmail.com", "10minutemail.com", "guerrillamail.com",
                        "mailinator.com", "yopmail.com", "throwaway.email"}


def _anti_spam(db, ip, email):
    """Devuelve (permitido, motivo). Bloquea bots y registros masivos."""
    ahora = datetime.now()
    if not _re.match(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", (email or "").strip(), _re.I):
        return False, "El correo no tiene un formato válido."
    dominio = email.split("@")[-1].lower()
    if dominio in DOMINIOS_DESECHABLES:
        return False, "No se aceptan correos temporales. Usa tu correo personal o institucional."
    n_ip = db.query(_Int).filter(_Int.ip == ip,
                                 _Int.fecha >= ahora - timedelta(hours=1)).count()
    if n_ip >= LIMITE_IP_HORA:
        return False, f"Demasiados registros desde esta conexión ({n_ip} en una hora). Espera un momento o comunícate con la institución."
    n_mail = db.query(_Int).filter(_Int.email == email.lower(),
                                   _Int.fecha >= ahora - timedelta(days=1)).count()
    if n_mail >= LIMITE_EMAIL_DIA:
        return False, "Ya se enviaron varios registros con este correo hoy. Revisa tu bandeja de entrada."
    return True, None


class RegistroSeguroIn(BaseModel):
    institucion_id: int
    nombre: str
    usuario: str
    email: str
    telefono: str | None = ""
    documento: str | None = ""
    rol: str | None = "docente"
    nota: str | None = ""
    captcha_respuesta: int | None = None
    captcha_esperado: int | None = None


@router.get("/captcha")
def captcha():
    """Operación simple que un bot no resuelve tan fácil como un formulario vacío."""
    import random as _r
    a, b = _r.randint(2, 9), _r.randint(2, 9)
    op = _r.choice(["+", "×"])
    res = a + b if op == "+" else a * b
    return {"pregunta": f"¿Cuánto es {a} {op} {b}?", "esperado": res}


@router.post("/registro_seguro")
def registro_seguro(payload: RegistroSeguroIn, request: Request, db: Session = Depends(get_db)):
    """Auto-registro con verificación por correo y protección anti-spam."""
    ip = _ip(request)
    email = (payload.email or "").strip().lower()
    if payload.captcha_esperado is not None and payload.captcha_respuesta != payload.captcha_esperado:
        db.add(_Int(ip=ip, email=email, resultado="bloqueado",
                    motivo="Captcha incorrecto", fecha=datetime.now()))
        db.commit()
        return {"ok": False, "msg": "La respuesta a la operación no es correcta. Inténtalo de nuevo."}
    permitido, motivo = _anti_spam(db, ip, email)
    if not permitido:
        db.add(_Int(ip=ip, email=email, resultado="bloqueado", motivo=motivo,
                    fecha=datetime.now()))
        db.commit()
        return {"ok": False, "msg": f"🛡️ {motivo}"}
    if db.query(Usuario).filter(Usuario.usuario == payload.usuario.strip().lower()).first():
        db.add(_Int(ip=ip, email=email, resultado="duplicado", fecha=datetime.now()))
        db.commit()
        return {"ok": False, "msg": "Ese nombre de usuario ya está tomado. Elige otro."}
    if db.query(Usuario).filter(Usuario.email == email).first():
        db.add(_Int(ip=ip, email=email, resultado="duplicado", fecha=datetime.now()))
        db.commit()
        return {"ok": False, "msg": "Ya existe una cuenta con ese correo."}
    if payload.rol not in ROLES or payload.rol == "rector":
        return {"ok": False, "msg": "Rol no válido para registro público."}
    u = Usuario(institucion_id=payload.institucion_id,
                usuario=payload.usuario.strip().lower()[:40],
                nombre=payload.nombre.strip()[:90], email=email,
                telefono=(payload.telefono or "").strip()[:30] or None,
                documento=(payload.documento or "").strip()[:30] or None,
                rol=payload.rol, estado="pendiente", creado_por="Registro público",
                fecha_registro=datetime.now(), n_accesos=0, debe_cambiar_clave=True,
                nota_admin=(payload.nota or "").strip()[:300] or None)
    db.add(u)
    db.flush()
    token = _sec.token_urlsafe(24)
    db.add(_Tok(usuario_id=u.id, email=email, token=token, tipo="registro",
                ip_origen=ip, creado=datetime.now(),
                expira=datetime.now() + timedelta(hours=48)))
    db.add(_Int(ip=ip, email=email, resultado="ok", fecha=datetime.now()))
    _log(db, payload.institucion_id, u.id, u.nombre, "registro",
         f"Auto-registro desde {ip}, pendiente de verificar correo", ip)
    db.commit()
    return {"ok": True, "token_demo": token,
            "msg": ("📧 Te enviamos un correo para confirmar tu dirección. "
                    "Después de confirmarla, rectoría revisará tu solicitud. "
                    "Son dos pasos: primero tú confirmas que el correo es tuyo, "
                    "luego la institución aprueba tu ingreso.")}


class VerificarTokenIn(BaseModel):
    token: str


@router.post("/verificar_correo")
def verificar_correo(payload: VerificarTokenIn, db: Session = Depends(get_db)):
    t = db.query(_Tok).filter(_Tok.token == payload.token).first()
    if not t:
        return {"ok": False, "msg": "El enlace no es válido."}
    if t.usado:
        return {"ok": False, "msg": "Este enlace ya se usó."}
    if t.expira and datetime.now() > t.expira:
        return {"ok": False, "msg": "El enlace venció. Pide uno nuevo desde el registro."}
    t.usado = True
    u = db.query(Usuario).filter(Usuario.id == t.usuario_id).first()
    if u:
        u.nota_admin = ((u.nota_admin or "") + " [correo verificado]").strip()
    db.commit()
    return {"ok": True,
            "msg": "✅ Correo confirmado. Tu solicitud ya está en la lista de rectoría para aprobación."}


@router.get("/seguridad")
def seguridad(institucion_id: int, dias: int = 7, db: Session = Depends(get_db)):
    """Panel de seguridad del registro: qué se bloqueó y por qué."""
    desde = datetime.now() - timedelta(days=dias)
    filas = db.query(_Int).filter(_Int.fecha >= desde).order_by(_Int.id.desc()).limit(120).all()
    fallidos = db.query(LogAcceso).filter(LogAcceso.institucion_id == institucion_id,
                                          LogAcceso.resultado == "fallido",
                                          LogAcceso.fecha >= desde).count()
    por_ip = {}
    for x in filas:
        por_ip[x.ip] = por_ip.get(x.ip, 0) + 1
    sospechosas = [{"ip": k, "n": v} for k, v in por_ip.items() if v >= 3]
    pend_verif = db.query(_Tok).filter(_Tok.usado == False,  # noqa: E712
                                       _Tok.tipo == "registro").count()
    return {
        "intentos": [{"ip": x.ip, "email": x.email, "resultado": x.resultado,
                      "motivo": x.motivo,
                      "fecha": x.fecha.isoformat(sep=" ", timespec="minutes") if x.fecha else ""}
                     for x in filas[:60]],
        "resumen": {
            "total": len(filas),
            "bloqueados": sum(1 for x in filas if x.resultado == "bloqueado"),
            "duplicados": sum(1 for x in filas if x.resultado == "duplicado"),
            "exitosos": sum(1 for x in filas if x.resultado == "ok"),
            "logins_fallidos": fallidos,
            "correos_sin_verificar": pend_verif,
            "ips_sospechosas": sospechosas,
            "dias": dias,
        },
        "protecciones": [
            {"nombre": "Verificación por correo", "activa": True,
             "detalle": "Nadie queda registrado sin confirmar que el correo es suyo."},
            {"nombre": "Límite por IP", "activa": True,
             "detalle": f"Máximo {LIMITE_IP_HORA} registros por hora desde la misma conexión."},
            {"nombre": "Límite por correo", "activa": True,
             "detalle": f"Máximo {LIMITE_EMAIL_DIA} solicitudes diarias con el mismo correo."},
            {"nombre": "Bloqueo de correos temporales", "activa": True,
             "detalle": "Se rechazan dominios desechables tipo tempmail."},
            {"nombre": "Operación de verificación", "activa": True,
             "detalle": "Una suma simple que los formularios automáticos no resuelven."},
            {"nombre": "Aprobación humana", "activa": True,
             "detalle": "Aunque pase todo lo anterior, rectoría decide quién entra."},
            {"nombre": "Registro de intentos", "activa": True,
             "detalle": "Cada intento queda con su IP para revisarlo después."},
        ],
    }
