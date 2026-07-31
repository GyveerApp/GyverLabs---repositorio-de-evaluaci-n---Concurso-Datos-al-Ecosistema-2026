"""Centro de alertas del coordinador: ciclo de vida de los casos
(abierta → completada → archivada, con resolución e historial) y la
bandeja de WhatsApp simulado por estudiante."""
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
try:
    from routers.vivo import marcar_cambio
except Exception:  # noqa: BLE001
    def marcar_cambio(*a, **k):
        pass
from models import NotificacionCoord, Estudiante, MensajeWhatsApp
import metadatos

router = APIRouter()


@router.get("/")
def listar(institucion_id: int, estado: str | None = None, limite: int = 120,
           db: Session = Depends(get_db)):
    q = db.query(NotificacionCoord).filter(NotificacionCoord.institucion_id == institucion_id)
    if estado in ("abierta", "completada", "archivada"):
        q = q.filter(NotificacionCoord.estado == estado)
    filas = q.order_by(NotificacionCoord.fecha.desc()).limit(limite).all()
    est = {e.id: e for e in db.query(Estudiante).all()}
    hoy = datetime.now().date()
    return [{
        "id": nfc.id, "tipo": nfc.tipo, "titulo": nfc.titulo, "detalle": nfc.detalle,
        "fecha": nfc.fecha.isoformat(sep=" ", timespec="minutes") if nfc.fecha else "",
        "es_hoy": bool(nfc.fecha and nfc.fecha.date() == hoy),
        "estado": nfc.estado, "resolucion": nfc.resolucion or "",
        "fecha_cierre": nfc.fecha_cierre.isoformat(sep=" ", timespec="minutes") if nfc.fecha_cierre else None,
        "estudiante_id": nfc.estudiante_id,
        "estudiante": est[nfc.estudiante_id].nombre if nfc.estudiante_id in est else "—",
        "grado": est[nfc.estudiante_id].grado if nfc.estudiante_id in est else "",
    } for nfc in filas]


@router.get("/contador")
def contador(institucion_id: int, db: Session = Depends(get_db)):
    n = db.query(NotificacionCoord).filter(NotificacionCoord.institucion_id == institucion_id,
                                           NotificacionCoord.estado == "abierta").count()
    return {"abiertas": n}


class EstadoIn(BaseModel):
    id: int
    estado: str
    resolucion: str | None = ""


@router.post("/estado")
def cambiar_estado(payload: EstadoIn, db: Session = Depends(get_db)):
    nfc = db.query(NotificacionCoord).filter(NotificacionCoord.id == payload.id).first()
    if not nfc:
        return {"ok": False, "msg": "Alerta no encontrada."}
    if payload.estado not in ("abierta", "completada", "archivada"):
        return {"ok": False, "msg": "Estado inválido."}
    if payload.estado == "completada" and not (payload.resolucion or "").strip():
        return {"ok": False, "msg": "Para completar el caso escribe la resolución (qué se hizo)."}
    nfc.estado = payload.estado
    if payload.resolucion:
        nfc.resolucion = payload.resolucion.strip()
    if payload.estado in ("completada", "archivada"):
        nfc.fecha_cierre = datetime.now()
    db.commit()
    metadatos.registrar_evento("ALERTA_" + payload.estado.upper(), "Coordinación",
                               institucion_id=nfc.institucion_id, estudiante_id=nfc.estudiante_id,
                               payload={"tipo": nfc.tipo})
    return {"ok": True, "msg": f"Caso {payload.estado}. {'Resolución registrada en el historial.' if payload.resolucion else ''}"}


@router.get("/whatsapp")
def whatsapp(estudiante_id: int, db: Session = Depends(get_db)):
    e = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    msgs = db.query(MensajeWhatsApp).filter(MensajeWhatsApp.estudiante_id == estudiante_id).order_by(
        MensajeWhatsApp.fecha).all()
    return {
        "estudiante": e.nombre if e else "—",
        "acudiente": e.acudiente if e else "—",
        "parentesco": e.parentesco if e else "",
        "telefono": e.telefono if e else "",
        "mensajes": [{
            "id": m.id, "contenido": m.contenido, "estado": m.estado, "contexto": m.contexto,
            "fecha": m.fecha.isoformat(sep=" ", timespec="minutes") if m.fecha else "",
        } for m in msgs],
    }


class WhatsIn(BaseModel):
    estudiante_id: int
    contenido: str


@router.post("/whatsapp/enviar")
def whatsapp_enviar(payload: WhatsIn, db: Session = Depends(get_db)):
    if not payload.contenido.strip():
        return {"ok": False, "msg": "Escribe el mensaje."}
    e = db.query(Estudiante).filter(Estudiante.id == payload.estudiante_id).first()
    if not e:
        return {"ok": False, "msg": "Estudiante no encontrado."}
    db.add(MensajeWhatsApp(estudiante_id=e.id, destinatario=f"{e.acudiente} ({e.parentesco or 'acudiente'})",
                           telefono=e.telefono, contenido=payload.contenido.strip()[:500],
                           fecha=datetime.now(), estado="ENVIADO (simulado)", contexto="manual"))
    db.commit()
    metadatos.registrar_evento("WHATSAPP", "Coordinación", estudiante_id=e.id,
                               payload={"contexto": "manual"})
    return {"ok": True, "msg": f"📱 Mensaje enviado (simulado) a {e.acudiente} · {e.telefono}. En producción: Meta Cloud API / Twilio."}
