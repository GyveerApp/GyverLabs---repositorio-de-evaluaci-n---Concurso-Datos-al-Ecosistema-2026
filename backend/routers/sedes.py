"""Sedes, buzon de necesidades docentes y junta directiva.

Puntos 9, 10, 12 y 16 del feedback:
  - Cada institucion tiene varias sedes (principal + satelites en veredas).
  - El rector ve el estado de cada sede en tiempo real: personal, estudiantes,
    riesgo, conectividad, PAE y distancia.
  - Los docentes piden lo que necesitan; coordinacion/rectoria responde y eso
    alimenta el plan de compras.
  - La junta directiva vota las propuestas de contratacion.
"""
import json
from datetime import datetime, date
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (Sede, Salon, Personal, Estudiante, SRDScore, Institucion,
                    SolicitudRecurso, VotoPropuesta, Contratista, PlanFSE,
                    Asistencia)
import metadatos
try:
    from routers.vivo import marcar_cambio
except Exception:  # noqa: BLE001
    def marcar_cambio(*a, **k):
        pass

router = APIRouter()

CAT_LABEL = {"material": "📦 Material didáctico", "infraestructura": "🏗️ Infraestructura",
             "tecnologia": "💻 Tecnología", "personal": "👥 Personal",
             "pae": "🍽️ Alimentación", "otro": "📌 Otro"}


# ═════════════════ SEDES ═════════════════
@router.get("/")
def listar(institucion_id: int, db: Session = Depends(get_db)):
    """Mapa de sedes con su estado real: cuánta gente, cuánto riesgo, qué le falta."""
    sedes = db.query(Sede).filter(Sede.institucion_id == institucion_id).order_by(
        Sede.tipo.desc(), Sede.nombre).all()
    srd = {s.estudiante_id: s for s in db.query(SRDScore).all()}
    out = []
    for sd in sedes:
        ests = db.query(Estudiante).filter(Estudiante.sede_id == sd.id).all()
        pers = db.query(Personal).filter(Personal.sede_id == sd.id,
                                         Personal.activo == True).all()  # noqa: E712
        salones = db.query(Salon).filter(Salon.sede_id == sd.id).all()
        criticos = sum(1 for e in ests if srd.get(e.id) and srd[e.id].nivel == "CRÍTICO")
        moderados = sum(1 for e in ests if srd.get(e.id) and srd[e.id].nivel == "MODERADO")
        asis = [srd[e.id].pct_asistencia for e in ests if srd.get(e.id)]
        coord = db.query(Personal).filter(Personal.id == sd.coordinador_id).first()
        pend = db.query(SolicitudRecurso).filter(SolicitudRecurso.sede_id == sd.id,
                                                 SolicitudRecurso.estado == "pendiente").count()
        out.append({
            "id": sd.id, "nombre": sd.nombre, "tipo": sd.tipo, "zona": sd.zona,
            "codigo_dane": sd.codigo_dane, "direccion": sd.direccion,
            "barrio_vereda": sd.barrio_vereda, "telefono": sd.telefono,
            "niveles": (sd.niveles or "").split(",") if sd.niveles else [],
            "tiene_internet": bool(sd.tiene_internet), "tiene_pae": bool(sd.tiene_pae),
            "distancia_km": sd.distancia_km,
            "coordinador": coord.nombre if coord else None,
            "coordinador_id": sd.coordinador_id,
            "n_estudiantes": len(ests), "n_docentes": sum(1 for p in pers if p.rol == "docente"),
            "n_personal": len(pers), "n_salones": len(salones),
            "criticos": criticos, "moderados": moderados,
            "pct_asistencia": round(sum(asis) / len(asis), 1) if asis else None,
            "solicitudes_pendientes": pend,
            "salones": [{"id": s.id, "nombre": s.nombre, "grado": s.grado} for s in salones],
        })
    tot_est = sum(x["n_estudiantes"] for x in out)
    return {
        "sedes": out,
        "totales": {
            "n_sedes": len(out), "n_estudiantes": tot_est,
            "n_docentes": sum(x["n_docentes"] for x in out),
            "sin_internet": sum(1 for x in out if not x["tiene_internet"]),
            "sin_pae": sum(1 for x in out if not x["tiene_pae"]),
            "criticos": sum(x["criticos"] for x in out),
            "mas_lejana": max([x["distancia_km"] or 0 for x in out], default=0),
        },
    }


@router.get("/detalle")
def detalle(sede_id: int, db: Session = Depends(get_db)):
    sd = db.query(Sede).filter(Sede.id == sede_id).first()
    if not sd:
        return {"ok": False, "msg": "Sede no encontrada."}
    pers = db.query(Personal).filter(Personal.sede_id == sd.id,
                                     Personal.activo == True).all()  # noqa: E712
    salones = db.query(Salon).filter(Salon.sede_id == sd.id).all()
    srd = {s.estudiante_id: s for s in db.query(SRDScore).all()}
    filas_salon = []
    for s in salones:
        ests = db.query(Estudiante).filter(Estudiante.salon_id == s.id).all()
        dire = db.query(Personal).filter(Personal.id == s.director_id).first()
        filas_salon.append({
            "id": s.id, "nombre": s.nombre, "grado": s.grado, "jornada": s.jornada,
            "director": dire.nombre if dire else "sin director",
            "n_estudiantes": len(ests),
            "criticos": sum(1 for e in ests if srd.get(e.id) and srd[e.id].nivel == "CRÍTICO"),
        })
    return {
        "ok": True, "id": sd.id, "nombre": sd.nombre, "tipo": sd.tipo, "zona": sd.zona,
        "direccion": sd.direccion, "barrio_vereda": sd.barrio_vereda,
        "telefono": sd.telefono, "codigo_dane": sd.codigo_dane,
        "distancia_km": sd.distancia_km, "tiene_internet": bool(sd.tiene_internet),
        "tiene_pae": bool(sd.tiene_pae),
        "niveles": (sd.niveles or "").split(",") if sd.niveles else [],
        "personal": [{"id": p.id, "nombre": p.nombre, "rol": p.rol, "area": p.area,
                      "telefono": p.telefono, "email": p.email, "foto": p.foto,
                      "profesion": p.profesion, "experiencia_anios": p.experiencia_anios}
                     for p in pers],
        "salones": filas_salon,
    }


class SedeIn(BaseModel):
    id: int | None = 0
    institucion_id: int
    nombre: str
    tipo: str | None = "satelite"
    zona: str | None = "rural"
    codigo_dane: str | None = ""
    direccion: str | None = ""
    barrio_vereda: str | None = ""
    telefono: str | None = ""
    niveles: str | None = ""
    tiene_internet: bool | None = True
    tiene_pae: bool | None = True
    distancia_km: float | None = 0
    coordinador_id: int | None = None


@router.post("/guardar")
def guardar(payload: SedeIn, db: Session = Depends(get_db)):
    if not payload.nombre.strip():
        return {"ok": False, "msg": "El nombre de la sede es obligatorio."}
    if payload.id:
        sd = db.query(Sede).filter(Sede.id == payload.id).first()
        if not sd:
            return {"ok": False, "msg": "Sede no encontrada."}
    else:
        sd = Sede(institucion_id=payload.institucion_id)
        db.add(sd)
    sd.nombre = payload.nombre.strip()[:80]
    sd.tipo = payload.tipo if payload.tipo in ("principal", "satelite") else "satelite"
    sd.zona = payload.zona if payload.zona in ("urbana", "rural") else "rural"
    sd.codigo_dane = (payload.codigo_dane or "").strip()[:20] or None
    sd.direccion = (payload.direccion or "").strip()[:120]
    sd.barrio_vereda = (payload.barrio_vereda or "").strip()[:80]
    sd.telefono = (payload.telefono or "").strip()[:30]
    sd.niveles = (payload.niveles or "").strip()[:80]
    sd.tiene_internet = bool(payload.tiene_internet)
    sd.tiene_pae = bool(payload.tiene_pae)
    sd.distancia_km = max(0, payload.distancia_km or 0)
    sd.coordinador_id = payload.coordinador_id
    db.commit()
    metadatos.registrar_evento("SEDE_GUARDADA", "Rectoría", institucion_id=payload.institucion_id,
                               payload={"sede": sd.nombre})
    return {"ok": True, "id": sd.id, "msg": f"Sede «{sd.nombre}» guardada."}


class AsignarSedeIn(BaseModel):
    personal_id: int
    sede_id: int | None = None


@router.post("/asignar_personal")
def asignar_personal(payload: AsignarSedeIn, db: Session = Depends(get_db)):
    p = db.query(Personal).filter(Personal.id == payload.personal_id).first()
    if not p:
        return {"ok": False, "msg": "Persona no encontrada."}
    sd = db.query(Sede).filter(Sede.id == payload.sede_id).first() if payload.sede_id else None
    p.sede_id = sd.id if sd else None
    db.commit()
    return {"ok": True, "msg": f"{p.nombre} asignado(a) a {sd.nombre if sd else 'ninguna sede'}."}


# ═════════════════ BUZÓN DE NECESIDADES (punto 10) ═════════════════
@router.get("/solicitudes")
def solicitudes(institucion_id: int, estado: str | None = None,
                solicitante_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(SolicitudRecurso).filter(SolicitudRecurso.institucion_id == institucion_id)
    if estado:
        q = q.filter(SolicitudRecurso.estado == estado)
    if solicitante_id:
        q = q.filter(SolicitudRecurso.solicitante_id == solicitante_id)
    filas = q.order_by(SolicitudRecurso.id.desc()).limit(80).all()
    out = []
    for s in filas:
        p = db.query(Personal).filter(Personal.id == s.solicitante_id).first()
        sd = db.query(Sede).filter(Sede.id == s.sede_id).first()
        out.append({
            "id": s.id, "categoria": s.categoria, "categoria_label": CAT_LABEL.get(s.categoria, s.categoria),
            "titulo": s.titulo, "detalle": s.detalle, "cantidad": s.cantidad,
            "urgencia": s.urgencia, "valor_estimado": round(s.valor_estimado or 0),
            "estado": s.estado, "respuesta": s.respuesta, "resuelto_por": s.resuelto_por,
            "solicitante": p.nombre if p else "—", "solicitante_id": s.solicitante_id,
            "foto": p.foto if p else None,
            "sede": sd.nombre if sd else "—", "sede_id": s.sede_id,
            "fecha": s.fecha.isoformat(sep=" ", timespec="minutes") if s.fecha else "",
            "fecha_respuesta": s.fecha_respuesta.isoformat(sep=" ", timespec="minutes") if s.fecha_respuesta else None,
        })
    tot = db.query(SolicitudRecurso).filter(SolicitudRecurso.institucion_id == institucion_id).all()
    return {
        "solicitudes": out,
        "resumen": {
            "pendientes": sum(1 for x in tot if x.estado == "pendiente"),
            "aprobadas": sum(1 for x in tot if x.estado == "aprobada"),
            "en_compra": sum(1 for x in tot if x.estado == "en_compra"),
            "resueltas": sum(1 for x in tot if x.estado == "resuelta"),
            "valor_pendiente": round(sum(x.valor_estimado or 0 for x in tot if x.estado == "pendiente")),
            "urgentes": sum(1 for x in tot if x.estado == "pendiente" and x.urgencia == "alta"),
        },
    }


class SolicitudIn(BaseModel):
    institucion_id: int
    solicitante_id: int
    sede_id: int | None = None
    categoria: str | None = "material"
    titulo: str
    detalle: str | None = ""
    cantidad: int | None = 1
    urgencia: str | None = "media"
    valor_estimado: float | None = 0


@router.post("/solicitudes/crear")
def solicitud_crear(payload: SolicitudIn, db: Session = Depends(get_db)):
    if not payload.titulo.strip():
        return {"ok": False, "msg": "Escribe qué necesitas."}
    p = db.query(Personal).filter(Personal.id == payload.solicitante_id).first()
    s = SolicitudRecurso(
        institucion_id=payload.institucion_id, solicitante_id=payload.solicitante_id,
        sede_id=payload.sede_id or (p.sede_id if p else None),
        categoria=payload.categoria or "material", titulo=payload.titulo.strip()[:120],
        detalle=(payload.detalle or "").strip()[:800], cantidad=max(1, payload.cantidad or 1),
        urgencia=payload.urgencia if payload.urgencia in ("alta", "media", "baja") else "media",
        valor_estimado=max(0, payload.valor_estimado or 0),
        estado="pendiente", fecha=datetime.now())
    db.add(s)
    db.commit()
    marcar_cambio(payload.institucion_id, "solicitud", s.titulo[:40])
    metadatos.registrar_evento("SOLICITUD_RECURSO", "Docente", institucion_id=payload.institucion_id,
                               payload={"categoria": s.categoria, "urgencia": s.urgencia})
    return {"ok": True, "id": s.id,
            "msg": f"📨 Solicitud enviada a coordinación: «{s.titulo}». Te avisamos cuando respondan."}


class ResolverSolicitudIn(BaseModel):
    id: int
    estado: str            # aprobada | rechazada | en_compra | resuelta
    respuesta: str | None = ""
    resuelto_por: str | None = "Rectoría"
    agregar_al_plan: bool | None = False


@router.post("/solicitudes/resolver")
def solicitud_resolver(payload: ResolverSolicitudIn, db: Session = Depends(get_db)):
    s = db.query(SolicitudRecurso).filter(SolicitudRecurso.id == payload.id).first()
    if not s:
        return {"ok": False, "msg": "Solicitud no encontrada."}
    if payload.estado not in ("aprobada", "rechazada", "en_compra", "resuelta", "pendiente"):
        return {"ok": False, "msg": "Estado inválido."}
    s.estado = payload.estado
    s.respuesta = (payload.respuesta or "").strip()[:400] or None
    s.resuelto_por = payload.resuelto_por or "Rectoría"
    s.fecha_respuesta = datetime.now()
    extra = ""
    if payload.agregar_al_plan and payload.estado in ("aprobada", "en_compra") and not s.plan_id:
        p = PlanFSE(institucion_id=s.institucion_id, anio=date.today().year,
                    concepto=s.titulo[:150], cuenta_codigo="1510",
                    prioridad=1 if s.urgencia == "alta" else 2,
                    mes_planeado=date.today().month,
                    valor_presupuestado=s.valor_estimado or 0, estado="pendiente")
        db.add(p)
        db.flush()
        s.plan_id = p.id
        extra = " 📋 Se agregó al plan de compras del FSE."
    db.commit()
    metadatos.registrar_evento("SOLICITUD_RESUELTA", s.resuelto_por,
                               institucion_id=s.institucion_id,
                               payload={"estado": s.estado})
    return {"ok": True, "msg": f"Solicitud marcada como {payload.estado}.{extra}"}


# ═════════════════ JUNTA DIRECTIVA (punto 16) ═════════════════
@router.get("/junta/propuestas")
def junta_propuestas(institucion_id: int, db: Session = Depends(get_db)):
    """Propuestas recibidas por el portal, con el estado de votación de la junta."""
    out = []
    for c in db.query(Contratista).all():
        try:
            props = json.loads(c.propuestas) if c.propuestas else []
        except Exception:
            props = []
        for idx, p in enumerate(props):
            votos = db.query(VotoPropuesta).filter(
                VotoPropuesta.contratista_id == c.id,
                VotoPropuesta.propuesta_idx == idx,
                VotoPropuesta.institucion_id == institucion_id).all()
            aprueban = sum(1 for v in votos if v.voto == "aprueba")
            rechazan = sum(1 for v in votos if v.voto == "rechaza")
            pend = sum(1 for v in votos if v.voto == "pendiente")
            decision = ("APROBADA" if aprueban > rechazan and pend == 0 else
                        "RECHAZADA" if rechazan >= aprueban and pend == 0 else
                        "EN VOTACIÓN")
            out.append({
                "contratista": c.nombre, "contratista_id": c.id, "nit": c.nit,
                "confianza": c.confianza, "propuesta_idx": idx,
                "fecha": p.get("fecha"), "valor": round(p.get("valor") or 0),
                "descripcion": p.get("descripcion", ""), "archivos": p.get("archivos", []),
                "estado": p.get("estado", "recibida"),
                "votos": [{"id": v.id, "miembro": v.miembro, "rol": v.rol_junta,
                           "voto": v.voto, "observacion": v.observacion,
                           "fecha": v.fecha.isoformat(sep=" ", timespec="minutes") if v.fecha else None}
                          for v in votos],
                "aprueban": aprueban, "rechazan": rechazan, "pendientes": pend,
                "decision": decision,
            })
    out.sort(key=lambda x: x.get("fecha") or "", reverse=True)
    return out


class VotoIn(BaseModel):
    id: int | None = None
    institucion_id: int | None = None
    contratista_id: int | None = None
    propuesta_idx: int | None = 0
    miembro: str | None = None
    rol_junta: str | None = None
    voto: str
    observacion: str | None = ""


@router.post("/junta/votar")
def junta_votar(payload: VotoIn, db: Session = Depends(get_db)):
    if payload.voto not in ("aprueba", "rechaza", "pendiente"):
        return {"ok": False, "msg": "Voto inválido."}
    if payload.id:
        v = db.query(VotoPropuesta).filter(VotoPropuesta.id == payload.id).first()
        if not v:
            return {"ok": False, "msg": "Voto no encontrado."}
    else:
        v = VotoPropuesta(institucion_id=payload.institucion_id,
                          contratista_id=payload.contratista_id,
                          propuesta_idx=payload.propuesta_idx or 0,
                          miembro=payload.miembro or "Miembro", rol_junta=payload.rol_junta)
        db.add(v)
    v.voto = payload.voto
    v.observacion = (payload.observacion or "").strip()[:300] or None
    v.fecha = datetime.now()
    db.commit()
    metadatos.registrar_evento("VOTO_JUNTA", v.miembro, institucion_id=v.institucion_id,
                               payload={"voto": v.voto})
    return {"ok": True, "msg": f"Voto de {v.miembro} registrado: {v.voto}."}


# ═════════ BUZÓN: conversación en la solicitud (punto 27) ═════════
from models import MensajeBuzon as _MsgBuz


@router.get("/solicitudes/mensajes")
def buzon_mensajes(solicitud_id: int, db: Session = Depends(get_db)):
    filas = db.query(_MsgBuz).filter(_MsgBuz.solicitud_id == solicitud_id).order_by(_MsgBuz.id).all()
    return [{"id": m.id, "autor": m.autor, "rol": m.rol, "texto": m.texto,
             "fecha": m.fecha.isoformat(sep=" ", timespec="minutes") if m.fecha else ""}
            for m in filas]


class MsgBuzonIn(BaseModel):
    solicitud_id: int
    autor: str
    rol: str | None = ""
    texto: str
    cambiar_estado: str | None = None    # para pedir más info: "en_revision"


@router.post("/solicitudes/mensaje")
def buzon_mensaje(payload: MsgBuzonIn, db: Session = Depends(get_db)):
    """Coordinación puede repreguntar en vez de aprobar o rechazar de una."""
    s = db.query(SolicitudRecurso).filter(SolicitudRecurso.id == payload.solicitud_id).first()
    if not s:
        return {"ok": False, "msg": "Solicitud no encontrada."}
    if not payload.texto.strip():
        return {"ok": False, "msg": "Escribe el mensaje."}
    db.add(_MsgBuz(solicitud_id=payload.solicitud_id, autor=payload.autor,
                   rol=payload.rol, texto=payload.texto.strip()[:800],
                   fecha=datetime.now()))
    extra = ""
    if payload.cambiar_estado == "en_revision":
        s.estado = "pendiente"
        s.respuesta = f"Se pidió más información: {payload.texto.strip()[:150]}"
        s.resuelto_por = payload.autor
        s.fecha_respuesta = datetime.now()
        extra = " Se le notificó al docente que necesitas más detalles."
    db.commit()
    return {"ok": True, "msg": f"💬 Mensaje enviado.{extra}"}
