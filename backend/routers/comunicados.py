"""Comunicados y notificaciones push internas.

Rectoría (o coordinación) envía comunicados a: toda la institución, solo
docentes, solo coordinadores, una persona específica, o a los ACUDIENTES de un
salón (WhatsApp masivo simulado). Cada persona destinataria recibe la
notificación en su campana 🔔 con contador de no leídas; el navegador además
dispara la notificación push (API Notification) desde el frontend."""
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (Comunicado, NotificacionPersona, Personal, Estudiante,
                    Salon, MensajeWhatsApp)
import metadatos
try:
    from routers.vivo import marcar_cambio
except Exception:  # noqa: BLE001
    def marcar_cambio(*a, **k):
        pass

router = APIRouter()


class EnviarIn(BaseModel):
    institucion_id: int
    emisor: str
    destinatario_tipo: str   # institucion|docentes|coordinadores|persona|salon_acudientes
    destinatario_id: int | None = None
    titulo: str
    mensaje: str


@router.post("/enviar")
def enviar(payload: EnviarIn, db: Session = Depends(get_db)):
    if not payload.titulo.strip() or not payload.mensaje.strip():
        return {"ok": False, "msg": "Título y mensaje son obligatorios."}
    tipo = payload.destinatario_tipo
    destinatarios = []
    extra = ""
    if tipo == "institucion":
        destinatarios = db.query(Personal).filter(Personal.institucion_id == payload.institucion_id,
                                                  Personal.activo == True).all()  # noqa: E712
    elif tipo == "docentes":
        destinatarios = db.query(Personal).filter(Personal.institucion_id == payload.institucion_id,
                                                  Personal.rol == "docente",
                                                  Personal.activo == True).all()  # noqa: E712
    elif tipo == "coordinadores":
        destinatarios = db.query(Personal).filter(Personal.institucion_id == payload.institucion_id,
                                                  Personal.rol == "coordinador",
                                                  Personal.activo == True).all()  # noqa: E712
    elif tipo == "persona":
        p = db.query(Personal).filter(Personal.id == payload.destinatario_id).first()
        if not p:
            return {"ok": False, "msg": "Persona no encontrada."}
        destinatarios = [p]
    elif tipo == "salon_acudientes":
        estudiantes = db.query(Estudiante).filter(Estudiante.salon_id == payload.destinatario_id).all()
        if not estudiantes:
            return {"ok": False, "msg": "El salón no tiene estudiantes."}
        sal = db.query(Salon).filter(Salon.id == payload.destinatario_id).first()
        ahora = datetime.now()
        for e in estudiantes:
            db.add(MensajeWhatsApp(
                estudiante_id=e.id, destinatario=f"{e.acudiente} ({e.parentesco or 'acudiente'})",
                telefono=e.telefono,
                contenido=f"📢 {payload.titulo}: {payload.mensaje.strip()[:300]} — {payload.emisor}",
                fecha=ahora, estado="ENVIADO (simulado)", contexto="comunicado"))
        extra = f" 📱 WhatsApp enviado (simulado) a los {len(estudiantes)} acudientes del salón {sal.nombre if sal else ''}."
    else:
        return {"ok": False, "msg": "Tipo de destinatario inválido."}

    com = Comunicado(institucion_id=payload.institucion_id, emisor=payload.emisor,
                     destinatario_tipo=tipo, destinatario_id=payload.destinatario_id,
                     titulo=payload.titulo.strip()[:120], mensaje=payload.mensaje.strip()[:1000],
                     fecha=datetime.now(),
                     n_destinatarios=len(destinatarios) if tipo != "salon_acudientes" else
                     db.query(Estudiante).filter(Estudiante.salon_id == payload.destinatario_id).count())
    db.add(com)
    db.flush()
    for p in destinatarios:
        db.add(NotificacionPersona(comunicado_id=com.id, personal_id=p.id, leida=False))
    db.commit()
    marcar_cambio(payload.institucion_id, "comunicado", payload.titulo[:40])
    metadatos.registrar_evento("COMUNICADO", payload.emisor, institucion_id=payload.institucion_id,
                               payload={"a": tipo, "n": com.n_destinatarios})
    labels = {"institucion": "toda la institución", "docentes": "los docentes",
              "coordinadores": "coordinación", "persona": "la persona seleccionada",
              "salon_acudientes": "los acudientes del salón"}
    return {"ok": True, "msg": f"📢 Comunicado enviado a {labels.get(tipo, tipo)} ({com.n_destinatarios} destinatarios). Recibirán la notificación en su campana 🔔.{extra}"}


@router.get("/bandeja")
def bandeja(personal_id: int, db: Session = Depends(get_db)):
    filas = (db.query(NotificacionPersona, Comunicado)
             .join(Comunicado, NotificacionPersona.comunicado_id == Comunicado.id)
             .filter(NotificacionPersona.personal_id == personal_id)
             .order_by(Comunicado.fecha.desc()).limit(30).all())
    no_leidas = sum(1 for n, _ in filas if not n.leida)
    return {"no_leidas": no_leidas, "notificaciones": [{
        "id": n.id, "leida": bool(n.leida), "titulo": c.titulo, "mensaje": c.mensaje,
        "emisor": c.emisor,
        "fecha": c.fecha.isoformat(sep=" ", timespec="minutes") if c.fecha else "",
    } for n, c in filas]}


class LeerIn(BaseModel):
    id: int | None = None
    personal_id: int | None = None   # si viene: marca TODAS como leídas


@router.post("/leer")
def leer(payload: LeerIn, db: Session = Depends(get_db)):
    if payload.personal_id:
        for n in db.query(NotificacionPersona).filter(NotificacionPersona.personal_id == payload.personal_id,
                                                      NotificacionPersona.leida == False).all():  # noqa: E712
            n.leida = True
        db.commit()
        return {"ok": True, "msg": "Todas marcadas como leídas."}
    n = db.query(NotificacionPersona).filter(NotificacionPersona.id == payload.id).first()
    if not n:
        return {"ok": False, "msg": "Notificación no encontrada."}
    n.leida = True
    db.commit()
    return {"ok": True, "msg": "Leída."}


@router.get("/enviados")
def enviados(institucion_id: int, db: Session = Depends(get_db)):
    filas = db.query(Comunicado).filter(Comunicado.institucion_id == institucion_id).order_by(
        Comunicado.fecha.desc()).limit(30).all()
    labels = {"institucion": "🏫 Toda la institución", "docentes": "👨‍🏫 Docentes",
              "coordinadores": "📋 Coordinadores", "persona": "👤 Persona específica",
              "salon_acudientes": "👪 Acudientes de un salón"}
    return [{
        "id": c.id, "titulo": c.titulo, "mensaje": c.mensaje, "emisor": c.emisor,
        "destinatario": labels.get(c.destinatario_tipo, c.destinatario_tipo),
        "n": c.n_destinatarios,
        "fecha": c.fecha.isoformat(sep=" ", timespec="minutes") if c.fecha else "",
    } for c in filas]
