"""Sincronizacion en vivo (puntos 9 y 10).

El problema: un docente marca una ausencia y el coordinador no se entera hasta
que recarga. O dos coordinadores resuelven el mismo caso sin saberlo.

La solucion sin WebSocket: un contador de version por institucion. Cada vez que
algo cambia (asistencia, alerta, comunicado, entrega) sube el contador. El
navegador pregunta cada pocos segundos "¿cambio algo?" y solo recarga la tabla
si la version subio. Es barato, funciona con conexiones malas y no necesita
servidor de sockets.

Ademas avisa si OTRO usuario ya esta viendo o resolviendo el mismo caso, para
que dos coordinadores no se pisen.
"""
import json
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (NotificacionCoord, Asistencia, Estudiante, Salon,
                    Personal, Comunicado, NotificacionPersona, EntregaAula,
                    SolicitudRecurso, Institucion)

router = APIRouter()

# Estado en memoria: version por institucion y presencia de usuarios.
# En produccion esto vive en Redis; para la demo basta con el proceso.
_VERSION = {}
_PRESENCIA = {}     # {institucion_id: {usuario: {"vista":..., "caso":..., "ts":...}}}
_ULTIMO_CAMBIO = {}


def marcar_cambio(institucion_id, tipo, detalle=None):
    """Lo llaman los demas routers cuando algo cambia."""
    if not institucion_id:
        return
    _VERSION[institucion_id] = _VERSION.get(institucion_id, 0) + 1
    _ULTIMO_CAMBIO[institucion_id] = {
        "tipo": tipo, "detalle": detalle,
        "hora": datetime.now().strftime("%H:%M:%S"),
        "version": _VERSION[institucion_id],
    }


def _limpiar_presencia(inst):
    """Quita a los que llevan mas de 40 segundos sin dar señales."""
    ahora = datetime.now()
    p = _PRESENCIA.get(inst, {})
    for k in list(p.keys()):
        if (ahora - p[k]["ts"]).total_seconds() > 40:
            del p[k]


@router.get("/estado")
def estado(institucion_id: int, version: int = 0, usuario: str | None = None,
           vista: str | None = None, caso: int | None = None,
           db: Session = Depends(get_db)):
    """El navegador pregunta cada 8 segundos: ¿cambió algo desde mi versión?

    De paso registra que este usuario está mirando esta vista (presencia), para
    avisarle a los demás que no está solo.
    """
    v = _VERSION.get(institucion_id, 0)
    if usuario:
        _PRESENCIA.setdefault(institucion_id, {})[usuario] = {
            "vista": vista, "caso": caso, "ts": datetime.now()}
    _limpiar_presencia(institucion_id)
    otros = []
    for nom, info in _PRESENCIA.get(institucion_id, {}).items():
        if nom == usuario:
            continue
        otros.append({"usuario": nom, "vista": info.get("vista"), "caso": info.get("caso")})
    hay_cambio = v > version
    resumen = None
    if hay_cambio:
        hoy = date.today()
        abiertas = db.query(NotificacionCoord).filter(
            NotificacionCoord.institucion_id == institucion_id,
            NotificacionCoord.estado == "abierta").count()
        ausentes = (db.query(Asistencia).join(Estudiante, Asistencia.estudiante_id == Estudiante.id)
                    .filter(Estudiante.institucion_id == institucion_id,
                            Asistencia.fecha == hoy, Asistencia.estado == "absent").count())
        resumen = {"alertas_abiertas": abiertas, "ausentes_hoy": ausentes}
    return {
        "version": v, "hay_cambio": hay_cambio,
        "ultimo": _ULTIMO_CAMBIO.get(institucion_id),
        "resumen": resumen,
        "otros_conectados": otros,
        "n_conectados": len(_PRESENCIA.get(institucion_id, {})),
    }


class TomarCasoIn(BaseModel):
    institucion_id: int
    usuario: str
    caso_id: int
    accion: str = "tomar"     # tomar | soltar


@router.post("/caso")
def caso(payload: TomarCasoIn):
    """Un coordinador avisa que va a atender un caso, para que otro no lo repita."""
    p = _PRESENCIA.setdefault(payload.institucion_id, {})
    _limpiar_presencia(payload.institucion_id)
    if payload.accion == "tomar":
        for nom, info in p.items():
            if nom != payload.usuario and info.get("caso") == payload.caso_id:
                return {"ok": False, "ocupado_por": nom,
                        "msg": f"⚠️ {nom} ya está atendiendo este caso. Coordínense para no duplicar la gestión."}
        p[payload.usuario] = {"vista": "alertas", "caso": payload.caso_id, "ts": datetime.now()}
        return {"ok": True, "msg": "Caso tomado. Los demás verán que tú lo estás atendiendo."}
    if payload.usuario in p:
        p[payload.usuario]["caso"] = None
    return {"ok": True, "msg": "Caso liberado."}


@router.get("/feed")
def feed(institucion_id: int, minutos: int = 120, db: Session = Depends(get_db)):
    """Lo que ha pasado en la institución en los últimos minutos, en orden."""
    desde = datetime.now() - timedelta(minutes=minutos)
    hoy = date.today()
    eventos = []
    for n in db.query(NotificacionCoord).filter(
            NotificacionCoord.institucion_id == institucion_id,
            NotificacionCoord.fecha >= desde).order_by(NotificacionCoord.fecha.desc()).limit(40).all():
        e = db.query(Estudiante).filter(Estudiante.id == n.estudiante_id).first()
        eventos.append({
            "tipo": "alerta", "icono": "🔔",
            "titulo": n.titulo,
            "detalle": f"{e.nombre if e else ''} · {n.detalle or ''}".strip(" ·"),
            "estado": n.estado,
            "hora": n.fecha.strftime("%H:%M") if n.fecha else "",
            "ts": n.fecha.isoformat() if n.fecha else "",
        })
    faltas = (db.query(Asistencia, Estudiante)
              .join(Estudiante, Asistencia.estudiante_id == Estudiante.id)
              .filter(Estudiante.institucion_id == institucion_id,
                      Asistencia.fecha == hoy, Asistencia.estado == "absent").limit(25).all())
    for a, e in faltas:
        sal = db.query(Salon).filter(Salon.id == a.salon_id).first()
        eventos.append({
            "tipo": "ausencia", "icono": "❌",
            "titulo": f"{e.nombre} no llegó hoy",
            "detalle": f"Salón {sal.nombre if sal else '—'}" + (f" · {a.observacion}" if a.observacion else ""),
            "estado": "abierta", "hora": "—", "ts": hoy.isoformat(),
        })
    for c in db.query(Comunicado).filter(Comunicado.institucion_id == institucion_id,
                                         Comunicado.fecha >= desde).limit(10).all():
        eventos.append({"tipo": "comunicado", "icono": "📢", "titulo": c.titulo,
                        "detalle": f"{c.emisor} → {c.n_destinatarios} personas",
                        "estado": "info",
                        "hora": c.fecha.strftime("%H:%M") if c.fecha else "",
                        "ts": c.fecha.isoformat() if c.fecha else ""})
    for s in db.query(SolicitudRecurso).filter(
            SolicitudRecurso.institucion_id == institucion_id,
            SolicitudRecurso.fecha >= desde).limit(10).all():
        p = db.query(Personal).filter(Personal.id == s.solicitante_id).first()
        eventos.append({"tipo": "solicitud", "icono": "📬", "titulo": s.titulo,
                        "detalle": f"Pedido por {p.nombre if p else '—'}",
                        "estado": s.estado,
                        "hora": s.fecha.strftime("%H:%M") if s.fecha else "",
                        "ts": s.fecha.isoformat() if s.fecha else ""})
    eventos.sort(key=lambda x: x["ts"], reverse=True)
    return {"eventos": eventos[:50], "version": _VERSION.get(institucion_id, 0),
            "n_conectados": len(_PRESENCIA.get(institucion_id, {}))}
