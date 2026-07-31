"""Súper Admin GyverLabs (Nivel 1) — gestión de tenants.

Internamente todo vive interconectado en una sola plataforma; externamente
cada colegio y cada secretaría tiene su PROPIO dominio, color y marca
('percepción a la medida'). Aquí el súper admin crea nuevas secretarías y
nuevos colegios: al crear un tenant se genera su institución, su rector
inicial, sus cuentas FSE y su dominio — igual que en producción se generaría
el schema y la config JSON.
"""
import json
import unicodedata
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (Tenant, Institucion, Personal, Salon, Estudiante, CuentaFSE,
                    SRDScore, MovimientoFSE)
import metadatos

router = APIRouter()


def _slug(t):
    t = unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode()
    return "".join(c for c in t.lower() if c.isalnum())


@router.get("/resumen")
def resumen(db: Session = Depends(get_db)):
    tenants = db.query(Tenant).all()
    n_col = sum(1 for t in tenants if t.tipo == "colegio")
    n_sec = sum(1 for t in tenants if t.tipo == "secretaria")
    n_est = db.query(Estudiante).count()
    n_per = db.query(Personal).count()
    riesgo = db.query(SRDScore).filter(SRDScore.nivel.in_(["CRÍTICO", "MODERADO"])).count()
    fse = sum(m.valor for m in db.query(MovimientoFSE).filter(MovimientoFSE.tipo == "egreso",
                                                              MovimientoFSE.estado != "anulado").all())
    return {"colegios": n_col, "secretarias": n_sec, "dominios": len(tenants),
            "estudiantes": n_est, "personal": n_per, "en_riesgo": riesgo,
            "fse_ejecutado": round(fse)}


@router.get("/tenants")
def tenants(db: Session = Depends(get_db)):
    inst = {i.id: i for i in db.query(Institucion).all()}
    est_por_ie = {}
    for e in db.query(Estudiante).all():
        est_por_ie[e.institucion_id] = est_por_ie.get(e.institucion_id, 0) + 1
    out = []
    for t in db.query(Tenant).order_by(Tenant.tipo.desc(), Tenant.id).all():
        ie = inst.get(t.institucion_id)
        out.append({
            "id": t.id, "tipo": t.tipo, "nombre": t.nombre, "dominio": t.dominio,
            "color": t.color, "municipio": t.municipio, "departamento": t.departamento,
            "modulos": (t.modulos or "").split(","), "estado": t.estado,
            "creado": t.creado.isoformat() if t.creado else None,
            "institucion_id": t.institucion_id,
            "logo": t.logo or (ie.logo if ie else None),
            "n_estudiantes": est_por_ie.get(t.institucion_id, 0) if ie else None,
            "dane": ie.codigo_dane if ie else None,
        })
    return out


class InstitucionIn(BaseModel):
    nombre: str
    dane: str | None = ""
    municipio: str
    departamento: str
    sector: str | None = "oficial urbana"
    rector: str | None = ""
    color: str | None = "#0E7C86"
    modulos: str | None = "asistencia,aula,srd,fse"
    crear_salones: bool | None = True
    logo: str | None = None      # dataURL del logo institucional (marca del colegio)
    dominio: str | None = None   # dominio propio marca blanca (ej: ietac.edu.co) — sin rastro de la plataforma


@router.post("/tenants/institucion")
def crear_institucion(payload: InstitucionIn, db: Session = Depends(get_db)):
    if not payload.nombre.strip() or not payload.municipio.strip():
        return {"ok": False, "msg": "Nombre y municipio son obligatorios."}
    ie = Institucion(nombre=payload.nombre.strip(), codigo_dane=payload.dane or "0000000000",
                     municipio=payload.municipio.strip(), departamento=payload.departamento.strip() or "Bolívar",
                     sector=payload.sector or "oficial urbana",
                     rector=payload.rector or "Por designar", telefono="", direccion="",
                     logo=payload.logo)
    db.add(ie); db.flush()
    dominio = (payload.dominio or "").strip().lower() or f"sistema.{_slug(payload.nombre.replace('I.E.',''))}.edu.co"
    db.add(Tenant(tipo="colegio", nombre=ie.nombre, dominio=dominio, color=payload.color or "#0E7C86",
                  logo=payload.logo,
                  institucion_id=ie.id, municipio=ie.municipio, departamento=ie.departamento,
                  modulos=payload.modulos or "asistencia,aula,srd,fse", estado="activo", creado=date.today()))
    # rector inicial + cuentas FSE base (igual que el bootstrap de un schema real)
    if payload.rector:
        db.add(Personal(institucion_id=ie.id, nombre=payload.rector, rol="rector",
                        area="Directivo", email=f"rector@{_slug(payload.nombre)}.edu.co",
                        experiencia_anios=10, hv_score=70, activo=True))
    for c in [("4110", "Transferencias SGP — Gratuidad", "ingreso"), ("1510", "Suministros y materiales", "gasto"),
              ("1524", "Material didáctico", "gasto"), ("1655", "Mantenimiento planta física", "gasto")]:
        db.add(CuentaFSE(institucion_id=ie.id, codigo=c[0], nombre=c[1], tipo=c[2]))
    if payload.crear_salones:
        for g in ["6", "7", "8", "9"]:
            db.add(Salon(institucion_id=ie.id, nombre=f"{g}01", grado=g, jornada="Mañana",
                         horarios=json.dumps([])))
    db.commit()
    metadatos.registrar_evento("TENANT_CREADO", "Súper Admin", institucion_id=ie.id,
                               payload={"tipo": "colegio", "dominio": dominio})
    return {"ok": True, "msg": f"Institución creada. Dominio: {dominio}" + (" (marca blanca — sin rastro de GyverLabs)" if payload.dominio else ""), "institucion_id": ie.id}


class SecretariaIn(BaseModel):
    municipio: str
    departamento: str


@router.post("/tenants/secretaria")
def crear_secretaria(payload: SecretariaIn, db: Session = Depends(get_db)):
    if not payload.municipio.strip():
        return {"ok": False, "msg": "El municipio es obligatorio."}
    existe = db.query(Tenant).filter(Tenant.tipo == "secretaria",
                                     Tenant.municipio == payload.municipio.strip()).first()
    if existe:
        return {"ok": False, "msg": "Ya existe una Secretaría para ese municipio."}
    dominio = f"{_slug(payload.municipio)}.gyverlabs.co"
    db.add(Tenant(tipo="secretaria", nombre=f"Secretaría de Educación de {payload.municipio.strip()}",
                  dominio=dominio, color="#D97706", municipio=payload.municipio.strip(),
                  departamento=payload.departamento.strip() or "Bolívar",
                  modulos="dashboard,reportes,censo,datos", estado="activo", creado=date.today()))
    db.commit()
    metadatos.registrar_evento("TENANT_CREADO", "Súper Admin",
                               payload={"tipo": "secretaria", "dominio": dominio})
    return {"ok": True, "msg": f"Secretaría creada. Dominio: {dominio}"}


class EstadoIn(BaseModel):
    tenant_id: int
    estado: str


@router.post("/tenants/estado")
def cambiar_estado(payload: EstadoIn, db: Session = Depends(get_db)):
    t = db.query(Tenant).filter(Tenant.id == payload.tenant_id).first()
    if not t:
        return {"ok": False, "msg": "Tenant no encontrado."}
    t.estado = payload.estado if payload.estado in ("activo", "suspendido") else "activo"
    db.commit()
    return {"ok": True, "msg": f"Tenant {t.nombre}: {t.estado}."}


# ═════════ BRANDING POR INSTITUCIÓN (punto 25) ═════════
class BrandingIn(BaseModel):
    tenant_id: int
    logo: str | None = None       # dataURL; None = quitar
    color: str | None = None
    nombre: str | None = None
    dominio: str | None = None


@router.post("/tenants/branding")
def tenant_branding(payload: BrandingIn, db: Session = Depends(get_db)):
    """El súper admin sube el logo de la institución: ese logo reemplaza la
    marca en TODO el sistema de ese tenant (sidebar, encabezados, guías PDF)."""
    t = db.query(Tenant).filter(Tenant.id == payload.tenant_id).first()
    if not t:
        return {"ok": False, "msg": "Tenant no encontrado."}
    if payload.logo and len(payload.logo) > 900_000:
        return {"ok": False, "msg": "El logo es muy pesado. Usa una imagen más pequeña (recomendado < 500 KB)."}
    if payload.logo is not None:
        t.logo = payload.logo or None
        ie = db.query(Institucion).filter(Institucion.id == t.institucion_id).first()
        if ie:
            ie.logo = t.logo
    if payload.color:
        t.color = payload.color
    if payload.nombre and payload.nombre.strip():
        t.nombre = payload.nombre.strip()
        ie = db.query(Institucion).filter(Institucion.id == t.institucion_id).first()
        if ie:
            ie.nombre = t.nombre
    if payload.dominio is not None and payload.dominio.strip():
        t.dominio = payload.dominio.strip().lower()
    db.commit()
    return {"ok": True, "msg": f"🎨 Marca de «{t.nombre}» actualizada. El logo aparecerá en todo el sistema de esta institución."}
