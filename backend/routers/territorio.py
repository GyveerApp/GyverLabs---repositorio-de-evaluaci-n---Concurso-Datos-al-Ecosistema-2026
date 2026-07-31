"""Vistas agregadas para Secretaría (municipio) y Ministerio (nacional):
cruce de datos entre instituciones."""
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Tenant as _TenantSec
from models import (Institucion, Estudiante, Salon, Personal, SRDScore,
                    MovimientoFSE, RegistroCenso)

router = APIRouter()


def _riesgo_por_institucion(db):
    est_ie = {e.id: e.institucion_id for e in db.query(Estudiante).all()}
    agg = defaultdict(lambda: {"total": 0, "criticos": 0, "moderados": 0})
    for s in db.query(SRDScore).all():
        iid = est_ie.get(s.estudiante_id)
        if iid is None:
            continue
        agg[iid]["total"] += 1
        if s.nivel == "CRÍTICO":
            agg[iid]["criticos"] += 1
        elif s.nivel == "MODERADO":
            agg[iid]["moderados"] += 1
    return agg


def _fse_por_institucion(db):
    agg = defaultdict(lambda: {"ingresos": 0.0, "egresos": 0.0})
    for m in db.query(MovimientoFSE).filter(MovimientoFSE.estado != "anulado").all():
        if m.tipo == "ingreso":
            agg[m.institucion_id]["ingresos"] += m.valor
        else:
            agg[m.institucion_id]["egresos"] += m.valor
    return agg


@router.get("/secretaria")
def secretaria(municipio: str | None = None, db: Session = Depends(get_db)):
    """Consolidado de todos los colegios de un municipio."""
    q = db.query(Institucion)
    if municipio:
        q = q.filter(Institucion.municipio == municipio)
    instituciones = q.all()
    if not municipio and instituciones:
        municipio = instituciones[0].municipio
        instituciones = [i for i in instituciones if i.municipio == municipio]

    riesgo = _riesgo_por_institucion(db)
    fse = _fse_por_institucion(db)
    colegios = []
    tot_est = tot_crit = tot_mod = 0
    tot_ing = tot_egr = 0.0
    for ie in instituciones:
        n_est = db.query(Estudiante).filter(Estudiante.institucion_id == ie.id).count()
        n_doc = db.query(Personal).filter(Personal.institucion_id == ie.id, Personal.rol == "docente").count()
        r = riesgo.get(ie.id, {"total": 0, "criticos": 0, "moderados": 0})
        f = fse.get(ie.id, {"ingresos": 0, "egresos": 0})
        tot_est += n_est
        tot_crit += r["criticos"]
        tot_mod += r["moderados"]
        tot_ing += f["ingresos"]
        tot_egr += f["egresos"]
        tn = db.query(_TenantSec).filter(_TenantSec.institucion_id == ie.id).first()
        colegios.append({
            "id": ie.id, "institucion_id": ie.id,
            "nombre": ie.nombre, "sector": ie.sector, "codigo_dane": ie.codigo_dane,
            "dominio": tn.dominio if tn else None, "color": (tn.color if tn else "#0E7C86"),
            "n_estudiantes": n_est, "n_docentes": n_doc,
            "criticos": r["criticos"], "moderados": r["moderados"],
            "pct_riesgo": round(100 * (r["criticos"] + r["moderados"]) / r["total"], 1) if r["total"] else 0,
            "ingresos": round(f["ingresos"]), "egresos": round(f["egresos"]),
        })
    colegios.sort(key=lambda x: x["pct_riesgo"], reverse=True)

    # censo del municipio
    censo = db.query(RegistroCenso).filter(RegistroCenso.municipio == municipio).all()
    no_estudian = sum(1 for c in censo if not c.estudia)
    en_riesgo_zona = sum(1 for c in censo if c.zona_riesgo)

    depto = instituciones[0].departamento if instituciones else "Bolívar"
    tot_doc = sum(c["n_docentes"] for c in colegios)
    return {
        "municipio": municipio, "departamento": depto,
        "kpis": {
            "n_colegios": len(instituciones), "n_estudiantes": tot_est,
            "criticos": tot_crit, "moderados": tot_mod,
            "en_riesgo": tot_crit + tot_mod, "n_docentes": tot_doc,
            "ingresos": round(tot_ing), "egresos": round(tot_egr),
            "censo_total": len(censo), "censo_no_estudian": no_estudian, "censo_riesgo_zona": en_riesgo_zona,
        },
        "censo": {"total": len(censo), "fuera_sistema": no_estudian, "zonas_riesgo": en_riesgo_zona},
        "colegios": colegios,
    }


@router.get("/ministerio")
def ministerio(db: Session = Depends(get_db)):
    """Consolidado nacional por departamento y municipio."""
    riesgo = _riesgo_por_institucion(db)
    fse = _fse_por_institucion(db)
    instituciones = db.query(Institucion).all()

    por_muni = defaultdict(lambda: {"colegios": 0, "estudiantes": 0, "criticos": 0, "moderados": 0,
                                    "ingresos": 0.0, "egresos": 0.0, "departamento": ""})
    for ie in instituciones:
        key = ie.municipio
        n_est = db.query(Estudiante).filter(Estudiante.institucion_id == ie.id).count()
        r = riesgo.get(ie.id, {"criticos": 0, "moderados": 0})
        f = fse.get(ie.id, {"ingresos": 0, "egresos": 0})
        d = por_muni[key]
        d["departamento"] = ie.departamento
        d["colegios"] += 1
        d["estudiantes"] += n_est
        d["criticos"] += r["criticos"]
        d["moderados"] += r["moderados"]
        d["ingresos"] += f["ingresos"]
        d["egresos"] += f["egresos"]

    municipios = []
    for muni, d in por_muni.items():
        municipios.append({
            "municipio": muni, "departamento": d["departamento"],
            "colegios": d["colegios"], "estudiantes": d["estudiantes"],
            "criticos": d["criticos"], "moderados": d["moderados"],
            "pct_riesgo": round(100 * (d["criticos"] + d["moderados"]) / d["estudiantes"], 1) if d["estudiantes"] else 0,
            "ingresos": round(d["ingresos"]), "egresos": round(d["egresos"]),
        })
    municipios.sort(key=lambda x: x["pct_riesgo"], reverse=True)

    # censo nacional
    censo = db.query(RegistroCenso).all()
    return {
        "kpis": {
            "n_departamentos": len(set(m["departamento"] for m in municipios)),
            "n_municipios": len(municipios),
            "n_colegios": len(instituciones),
            "n_estudiantes": sum(m["estudiantes"] for m in municipios),
            "criticos": sum(m["criticos"] for m in municipios),
            "moderados": sum(m["moderados"] for m in municipios),
            "ingresos": round(sum(m["ingresos"] for m in municipios)),
            "egresos": round(sum(m["egresos"] for m in municipios)),
            "censo_total": len(censo),
            "censo_no_estudian": sum(1 for c in censo if not c.estudia),
        },
        "municipios": municipios,
    }


# ═════════ PRO: drill-down de institución para la Secretaría ═════════
import json as _json
from datetime import datetime as _dt
from pydantic import BaseModel as _BM
from models import (Personal as _Per, Tenant as _Ten, Contrato as _Con,
                    Contratista as _Ctr, MensajeWhatsApp as _Wa, Salon as _Sal)


@router.get("/institucion_detalle")
def institucion_detalle(institucion_id: int, db: Session = Depends(get_db)):
    """Todo lo que la Secretaría ve al entrar a un colegio: personal completo
    (de rectoría a vigilancia), hojas de vida con score, compras/contratos,
    FSE, riesgo y el dominio propio del tenant."""
    ie = db.query(Institucion).filter(Institucion.id == institucion_id).first()
    if not ie:
        return {"ok": False, "msg": "Institución no encontrada."}
    tenant = db.query(_Ten).filter(_Ten.institucion_id == ie.id).first()
    personal = db.query(_Per).filter(_Per.institucion_id == ie.id, _Per.activo == True).all()  # noqa: E712
    orden_rol = {"rector": 0, "coordinador": 1, "docente": 2, "psicoorientacion": 3,
                 "auxiliar": 4, "contador": 5, "abogado": 6, "vigilante": 7, "servicios": 8}
    personal_out = sorted([{
        "id": p.id, "nombre": p.nombre, "rol": p.rol, "area": p.area,
        "profesion": p.profesion, "experiencia_anios": p.experiencia_anios,
        "hv_score": p.hv_score, "telefono": p.telefono, "email": p.email, "foto": p.foto,
    } for p in personal], key=lambda x: (orden_rol.get(x["rol"], 9), -(x["hv_score"] or 0)))

    n_est = db.query(Estudiante).filter(Estudiante.institucion_id == ie.id).count()
    n_sal = db.query(_Sal).filter(_Sal.institucion_id == ie.id).count()
    riesgo = _riesgo_por_institucion(db).get(ie.id, {"total": 0, "criticos": 0, "moderados": 0})
    fse = _fse_por_institucion(db).get(ie.id, {"ingresos": 0, "egresos": 0})

    movs = db.query(MovimientoFSE).filter(MovimientoFSE.institucion_id == ie.id,
                                          MovimientoFSE.tipo == "egreso").order_by(
        MovimientoFSE.fecha.desc()).limit(8).all()
    cts = {c.id: c.nombre for c in db.query(_Ctr).all()}
    contratos = db.query(_Con).filter(_Con.institucion_id == ie.id).all()

    top_hv = sorted([p for p in personal_out if p["rol"] in ("docente", "coordinador", "rector")],
                    key=lambda x: -(x["hv_score"] or 0))[:5]
    return {
        "id": ie.id, "nombre": ie.nombre, "dane": ie.codigo_dane, "sector": ie.sector,
        "municipio": ie.municipio, "departamento": ie.departamento,
        "direccion": ie.direccion, "telefono": ie.telefono, "rector": ie.rector,
        "dominio": tenant.dominio if tenant else None,
        "color": tenant.color if tenant else "#0E7C86",
        "modulos": (tenant.modulos or "").split(",") if tenant else [],
        "kpis": {"estudiantes": n_est, "salones": n_sal, "personal": len(personal),
                 "criticos": riesgo["criticos"], "moderados": riesgo["moderados"],
                 "pct_riesgo": round(100 * (riesgo["criticos"] + riesgo["moderados"]) / riesgo["total"], 1) if riesgo["total"] else 0,
                 "fse_ingresos": round(fse["ingresos"]), "fse_egresos": round(fse["egresos"])},
        "personal": personal_out,
        "top_hojas_vida": top_hv,
        "compras": [{"fecha": m.fecha.isoformat(), "concepto": m.concepto,
                     "proveedor": m.proveedor, "valor": round(m.valor)} for m in movs],
        "contratos": [{"numero": c.numero, "objeto": c.objeto, "valor": round(c.valor),
                       "estado": c.estado, "contratista": cts.get(c.contratista_id, "—")}
                      for c in contratos],
    }


class _MsgIn(_BM):
    personal_id: int
    contenido: str
    asunto: str | None = ""


@router.post("/mensaje")
def mensaje_personal(payload: _MsgIn, db: Session = Depends(get_db)):
    """La Secretaría contacta directamente a un docente/directivo (p.ej. para
    una vacante u oferta de formación) — WhatsApp simulado."""
    p = db.query(_Per).filter(_Per.id == payload.personal_id).first()
    if not p:
        return {"ok": False, "msg": "Persona no encontrada."}
    if not payload.contenido.strip():
        return {"ok": False, "msg": "Escribe el mensaje."}
    db.add(_Wa(personal_id=p.id, destinatario=p.nombre, telefono=p.telefono or "—",
               contenido=((payload.asunto + " — ") if payload.asunto else "") + payload.contenido.strip()[:400],
               fecha=_dt.now(), estado="ENVIADO (simulado)", contexto="secretaria"))
    db.commit()
    try:
        import metadatos as _m
        _m.registrar_evento("MENSAJE_SECRETARIA", "Secretaría", institucion_id=p.institucion_id)
    except Exception:
        pass
    return {"ok": True, "msg": f"📱 Mensaje enviado (simulado) a {p.nombre} · {p.telefono}."}


@router.get("/ministerio_tendencia")
def ministerio_tendencia(db: Session = Depends(get_db)):
    """Tendencia nacional de asistencia por semana + comparativo departamental."""
    from collections import defaultdict as _dd
    from models import Asistencia as _As
    est_depto = {}
    for e in db.query(Estudiante).all():
        est_depto[e.id] = e.institucion_id
    ie_depto = {i.id: i.departamento for i in db.query(Institucion).all()}
    por_sem = _dd(lambda: [0, 0])
    por_depto = _dd(lambda: [0, 0])
    for a in db.query(_As).all():
        sem = a.fecha.isocalendar()[1]
        ok = a.estado in ("present", "late", "excused")
        por_sem[sem][1] += 1
        if ok:
            por_sem[sem][0] += 1
        d = ie_depto.get(est_depto.get(a.estudiante_id))
        if d:
            por_depto[d][1] += 1
            if ok:
                por_depto[d][0] += 1
    tendencia = [{"semana": s, "pct": round(100 * p / t, 1) if t else 0}
                 for s, (p, t) in sorted(por_sem.items())][-10:]
    departamentos = [{"departamento": d, "pct": round(100 * p / t, 1) if t else 0, "registros": t}
                     for d, (p, t) in sorted(por_depto.items())]
    return {"tendencia": tendencia, "departamentos": departamentos}
