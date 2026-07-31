"""Módulo legal: perfil de la institución, rejilla maestra y documentos.

La REJILLA es el corazón: una fila por contrato con el rubro, el CDP, la
invitación, el contrato y el RP, cada uno con su número y su fecha. De ahí
salen TODOS los documentos con sus fechas coherentes.

Quien puede hacer qué lo decide rectoría (ver /usuarios/permisos):
  - juridica  → redactar minuta, cláusulas, correspondencia
  - auxiliar  → armar el expediente, subir documentos
  - contador  → CDP, RP, imputación presupuestal
  - rector    → firma y aprueba todo
"""
import json
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (PerfilLegal, FilaRejilla, DocumentoLegal, Correspondencia,
                    Institucion, Contrato, Contratista, Personal, RubroFSE)
import plantillas_legales as PL
import metadatos

router = APIRouter()

# Días hábiles que la práctica deja entre cada hito (de la rejilla real)
CADENCIA = {
    "cotizacion": -7,     # antes del CDP
    "proyecto": -2,
    "cdp": 0,             # ancla
    "invitacion": 5,
    "cierre": 6,
    "evaluacion": 7,
    "aceptacion": 8,
    "contrato": 8,
    "rp": 8,
    "acta_inicio": 8,
    "liquidacion_dias": 14,   # después del acta final
}


def _perfil(db, institucion_id):
    """El perfil legal; si no existe se arma con lo que haya de la institución."""
    p = db.query(PerfilLegal).filter(PerfilLegal.institucion_id == institucion_id).first()
    if p:
        return p
    ie = db.query(Institucion).filter(Institucion.id == institucion_id).first()
    rector = db.query(Personal).filter(Personal.institucion_id == institucion_id,
                                       Personal.rol == "rector").first()
    p = PerfilLegal(
        institucion_id=institucion_id,
        nombre_oficial=(ie.nombre if ie else "INSTITUCIÓN EDUCATIVA").upper(),
        dane=ie.codigo_dane if ie else None,
        municipio=ie.municipio if ie else None,
        departamento=ie.departamento if ie else None,
        rector_nombre=(rector.nombre if rector else (ie.rector if ie else None)),
        logo_izq=ie.logo if ie else None,
        vigencia=date.today().year)
    db.add(p)
    db.commit()
    return p


# ── Lo que hay que llenar, agrupado por secciones ──
SECCIONES = [
    {"id": "identificacion", "titulo": "Identificación de la institución", "icono": "🏫",
     "ayuda": "Los datos que van en el membrete de todo documento oficial.",
     "campos": [("nombre_oficial", "Nombre oficial completo", True),
                ("nit", "NIT", True), ("nit_dv", "Dígito de verificación", False),
                ("dane", "Código DANE", True), ("municipio", "Municipio", True),
                ("departamento", "Departamento", False),
                ("direccion", "Dirección de la sede principal", False),
                ("telefono", "Teléfono", False), ("email", "Correo institucional", False)]},
    {"id": "creacion", "titulo": "Actos de creación", "icono": "📜",
     "ayuda": "Las normas que dieron origen a la institución. Van bajo el nombre en el membrete.",
     "campos": [("ordenanza", "Ordenanza o acuerdo de creación", True),
                ("decreto", "Decreto reglamentario", False),
                ("licencia", "Licencia de funcionamiento", False)]},
    {"id": "rector", "titulo": "Rector(a) y ordenación del gasto", "icono": "👤",
     "ayuda": "Sin el acta de posesión, un contrato puede ser cuestionado en auditoría.",
     "campos": [("rector_nombre", "Nombre completo", True),
                ("rector_cc", "Cédula de ciudadanía", True),
                ("rector_cc_lugar", "Lugar de expedición", False),
                ("rector_acta_posesion", "Número del acta de posesión", True),
                ("rector_fecha_posesion", "Fecha de posesión", True)]},
    {"id": "documentos", "titulo": "Documentos soporte", "icono": "📎",
     "ayuda": "Los papeles que respaldan lo anterior. Se suben una vez y quedan en el expediente institucional.",
     "campos": [("doc_acta_posesion", "Acta de posesión del rector", True),
                ("doc_cedula_rector", "Cédula del rector", False),
                ("doc_rut", "RUT de la institución", False),
                ("doc_ordenanza", "Ordenanza de creación", False),
                ("doc_licencia", "Licencia de funcionamiento", False),
                ("doc_acuerdo_contratacion", "Acuerdo de contratación del Consejo", True)]},
    {"id": "membrete", "titulo": "Imagen institucional", "icono": "🖼️",
     "ayuda": "El logo y la firma que aparecen en cada documento generado.",
     "campos": [("logo_izq", "Escudo o logo de la institución", True),
                ("rector_firma", "Firma escaneada del rector", False),
                ("pie_pagina", "Texto del pie de página", False)]},
    {"id": "consejo", "titulo": "Consejo Directivo", "icono": "🤝",
     "ayuda": "Es quien aprueba el presupuesto y los traslados entre rubros.",
     "campos": [("consejo_acta_vigente", "Acta de conformación vigente", False),
                ("consejo_fecha", "Fecha del acta", False)]},
    {"id": "firmantes", "titulo": "Otros firmantes", "icono": "🧮",
     "ayuda": "Quienes firman junto al rector en los documentos financieros.",
     "campos": [("contador_nombre", "Contador(a)", False),
                ("contador_tp", "Tarjeta profesional", False),
                ("pagador_nombre", "Pagador(a)", False)]},
    {"id": "consecutivos", "titulo": "Numeración", "icono": "🔢",
     "ayuda": "Con qué prefijo se numeran el CDP y el RP en tu institución.",
     "campos": [("consec_cdp", "Prefijo del CDP", False),
                ("consec_rp", "Prefijo del RP", False),
                ("vigencia", "Vigencia fiscal", False)]},
]


@router.get("/perfil")
def perfil(institucion_id: int, db: Session = Depends(get_db)):
    """El panel de configuración institucional, con su avance por secciones."""
    p = _perfil(db, institucion_id)
    secciones = []
    faltan_todo = []
    for s in SECCIONES:
        campos = []
        for clave, etiqueta, obligatorio in s["campos"]:
            val = getattr(p, clave, None)
            lleno = bool(val)
            campos.append({"clave": clave, "label": etiqueta, "obligatorio": obligatorio,
                           "lleno": lleno,
                           "es_archivo": clave.startswith("doc_") or clave in ("logo_izq", "logo_der", "rector_firma"),
                           "valor": (val.isoformat() if isinstance(val, (date, datetime))
                                     else (("[archivo cargado]" if lleno else None)
                                           if (clave.startswith("doc_") or clave in ("logo_izq", "logo_der", "rector_firma"))
                                           else val))})
            if obligatorio and not lleno:
                faltan_todo.append(etiqueta)
        oblig = [c for c in campos if c["obligatorio"]]
        listos = [c for c in oblig if c["lleno"]]
        secciones.append({
            **{k: v for k, v in s.items() if k != "campos"},
            "campos": campos,
            "obligatorios": len(oblig), "completos": len(listos),
            "pct": round(100 * len(listos) / len(oblig)) if oblig else 100,
            "completa": len(listos) == len(oblig),
        })
    total_ob = sum(s["obligatorios"] for s in secciones)
    total_ok = sum(s["completos"] for s in secciones)
    pct = round(100 * total_ok / total_ob) if total_ob else 100
    miembros = []
    try:
        miembros = json.loads(p.consejo_miembros) if p.consejo_miembros else []
    except Exception:
        miembros = []
    return {
        "ok": True,
        "perfil": {c.name: (getattr(p, c.name).isoformat()
                            if isinstance(getattr(p, c.name), (date, datetime))
                            else getattr(p, c.name))
                   for c in PerfilLegal.__table__.columns},
        "secciones": secciones,
        "consejo_miembros": miembros,
        "faltantes": faltan_todo,
        "completo": len(faltan_todo) == 0,
        "pct": pct,
        "es_demo": bool(p.es_demo),
        "configurado_por": p.configurado_por,
        "fecha_configuracion": (p.fecha_configuracion.isoformat(sep=" ", timespec="minutes")
                                if p.fecha_configuracion else None),
        "aviso": ("⚠️ Este perfil todavía tiene los datos de demostración. "
                  "Reemplázalos con los de tu institución antes de generar documentos reales."
                  if p.es_demo else
                  ("Sin estos datos los documentos salen incompletos y no tienen validez legal."
                   if faltan_todo else
                   "✅ Perfil completo: los documentos salen listos para firmar.")),
    }


@router.post("/perfil/limpiar_demo")
def perfil_limpiar_demo(institucion_id: int, db: Session = Depends(get_db)):
    """Borra los datos de ejemplo para empezar de cero con los reales."""
    p = _perfil(db, institucion_id)
    ie = db.query(Institucion).filter(Institucion.id == institucion_id).first()
    for c in PerfilLegal.__table__.columns:
        if c.name in ("id", "institucion_id", "consec_cdp", "consec_rp", "vigencia"):
            continue
        setattr(p, c.name, None)
    p.nombre_oficial = (ie.nombre if ie else "INSTITUCIÓN EDUCATIVA").upper()
    p.municipio = ie.municipio if ie else None
    p.departamento = ie.departamento if ie else None
    p.dane = ie.codigo_dane if ie else None
    p.es_demo = False
    p.consec_cdp = "04"
    p.consec_rp = "05"
    p.vigencia = date.today().year
    db.commit()
    return {"ok": True,
            "msg": "🧹 Datos de ejemplo borrados. Ahora carga la información real de tu institución."}


class MiembroConsejoIn(BaseModel):
    institucion_id: int
    miembros: list


@router.post("/perfil/consejo")
def perfil_consejo(payload: MiembroConsejoIn, db: Session = Depends(get_db)):
    p = _perfil(db, payload.institucion_id)
    limpios = [{"rol": str(m.get("rol", ""))[:80], "nombre": str(m.get("nombre", ""))[:90],
                "documento": str(m.get("documento", ""))[:30]}
               for m in (payload.miembros or [])[:12] if m.get("rol")]
    p.consejo_miembros = json.dumps(limpios, ensure_ascii=False)
    db.commit()
    return {"ok": True, "msg": f"Consejo Directivo actualizado ({len(limpios)} miembros)."}


class PerfilIn(BaseModel):
    institucion_id: int
    nombre_oficial: str | None = None
    sigla: str | None = None
    ordenanza: str | None = None
    decreto: str | None = None
    licencia: str | None = None
    nit: str | None = None
    nit_dv: str | None = None
    dane: str | None = None
    direccion: str | None = None
    municipio: str | None = None
    departamento: str | None = None
    telefono: str | None = None
    email: str | None = None
    web: str | None = None
    rector_nombre: str | None = None
    rector_cc: str | None = None
    rector_cc_lugar: str | None = None
    rector_acta_posesion: str | None = None
    rector_fecha_posesion: str | None = None
    rector_firma: str | None = None
    contador_nombre: str | None = None
    contador_tp: str | None = None
    pagador_nombre: str | None = None
    logo_izq: str | None = None
    logo_der: str | None = None
    pie_pagina: str | None = None
    consec_cdp: str | None = None
    consec_rp: str | None = None
    vigencia: int | None = None
    doc_acta_posesion: str | None = None
    doc_acta_nombre: str | None = None
    doc_cedula_rector: str | None = None
    doc_rut: str | None = None
    doc_ordenanza: str | None = None
    doc_licencia: str | None = None
    doc_acuerdo_contratacion: str | None = None
    doc_camara_comercio: str | None = None
    consejo_acta_vigente: str | None = None
    consejo_fecha: str | None = None
    consejo_miembros: list | None = None
    configurado_por: str | None = None
    es_demo: bool | None = None


@router.post("/perfil/guardar")
def perfil_guardar(payload: PerfilIn, db: Session = Depends(get_db)):
    p = _perfil(db, payload.institucion_id)
    for k, v in payload.model_dump(exclude_none=True).items():
        if k == "institucion_id":
            continue
        if k in ("rector_fecha_posesion", "consejo_fecha"):
            try:
                setattr(p, k, date.fromisoformat(v))
            except (ValueError, TypeError):
                pass
            continue
        if k == "consejo_miembros":
            p.consejo_miembros = json.dumps(v, ensure_ascii=False)
            continue
        if hasattr(p, k):
            setattr(p, k, v)
    if payload.configurado_por:
        p.configurado_por = payload.configurado_por
        p.fecha_configuracion = datetime.now()
        p.es_demo = False
    db.commit()
    metadatos.registrar_evento("PERFIL_LEGAL", "Rectoría", institucion_id=payload.institucion_id)
    r = perfil(payload.institucion_id, db)
    return {"ok": True, "faltantes": r["faltantes"], "completo": r["completo"],
            "pct": r["pct"],
            "msg": ("✅ Configuración institucional completa. Los documentos ya salen "
                    "con el membrete, los datos del rector y su firma."
                    if r["completo"] else
                    f"Guardado ({r['pct']}% completo). Todavía falta: {', '.join(r['faltantes'][:3])}.")}


# ═════════════════ REJILLA ═════════════════
@router.get("/rejilla")
def rejilla(institucion_id: int, vigencia: int | None = None,
            db: Session = Depends(get_db)):
    """La rejilla completa: el registro maestro de la contratación del año."""
    v = vigencia or date.today().year
    filas = db.query(FilaRejilla).filter(
        FilaRejilla.institucion_id == institucion_id,
        FilaRejilla.vigencia == v).order_by(FilaRejilla.consecutivo).all()
    hoy = date.today()
    out = []
    for f in filas:
        docs = db.query(DocumentoLegal).filter(DocumentoLegal.rejilla_id == f.id).all()
        generados = {d.tipo for d in docs}
        pendientes = [lbl for k, (lbl, _fn) in PL.PLANTILLAS.items() if k not in generados]
        out.append({
            "id": f.id, "consecutivo": f.consecutivo, "vigencia": f.vigencia,
            "rubro_codigo": f.rubro_codigo, "rubro_nombre": f.rubro_nombre,
            "fuente": f.fuente, "valor": round(f.valor or 0), "unspsc": f.unspsc,
            "descripcion": f.descripcion,
            "cdp_num": f.cdp_num, "cdp_fecha": f.cdp_fecha.isoformat() if f.cdp_fecha else None,
            "invitacion_num": f.invitacion_num,
            "invitacion_fecha": f.invitacion_fecha.isoformat() if f.invitacion_fecha else None,
            "contrato_num": f.contrato_num,
            "contrato_fecha": f.contrato_fecha.isoformat() if f.contrato_fecha else None,
            "contratista_nombre": f.contratista_nombre, "contratista_doc": f.contratista_doc,
            "contratista_id": f.contratista_id,
            "rp_num": f.rp_num, "rp_fecha": f.rp_fecha.isoformat() if f.rp_fecha else None,
            "acta_inicio_fecha": f.acta_inicio_fecha.isoformat() if f.acta_inicio_fecha else None,
            "acta_final_fecha": f.acta_final_fecha.isoformat() if f.acta_final_fecha else None,
            "liquidacion_fecha": f.liquidacion_fecha.isoformat() if f.liquidacion_fecha else None,
            "plazo_dias": f.plazo_dias, "estado": f.estado,
            "contrato_id": f.contrato_id,
            "docs_generados": sorted(generados), "n_docs": len(docs),
            "docs_pendientes": pendientes,
            "vencido": bool(f.acta_final_fecha and f.acta_final_fecha < hoy and
                            f.estado not in ("liquidado", "cerrado")),
        })
    total = sum(x["valor"] for x in out)
    return {
        "vigencia": v, "filas": out,
        "resumen": {
            "n": len(out), "valor_total": total,
            "con_contrato": sum(1 for x in out if x["contrato_num"]),
            "con_rp": sum(1 for x in out if x["rp_num"]),
            "liquidados": sum(1 for x in out if x["liquidacion_fecha"]),
            "vencidos": sum(1 for x in out if x["vencido"]),
            "docs_faltantes": sum(len(x["docs_pendientes"]) for x in out),
        },
        "por_rubro": [
            {"codigo": k, "valor": sum(x["valor"] for x in out if x["rubro_codigo"] == k),
             "n": sum(1 for x in out if x["rubro_codigo"] == k)}
            for k in sorted({x["rubro_codigo"] for x in out if x["rubro_codigo"]})
        ],
    }


class FilaIn(BaseModel):
    id: int | None = 0
    institucion_id: int
    vigencia: int | None = None
    rubro_codigo: str | None = ""
    rubro_nombre: str | None = ""
    fuente: str | None = "Recurso de gratuidad"
    valor: float = 0
    unspsc: str | None = ""
    descripcion: str
    cdp_fecha: str | None = None
    plazo_dias: int | None = 5
    contratista_id: int | None = None
    contratista_nombre: str | None = ""
    contratista_doc: str | None = ""
    auto_fechas: bool = True


@router.post("/rejilla/guardar")
def rejilla_guardar(payload: FilaIn, db: Session = Depends(get_db)):
    """Crea o edita una fila. Con auto_fechas calcula toda la cadena."""
    if not payload.descripcion.strip():
        return {"ok": False, "msg": "Escribe el objeto del proceso."}
    p = _perfil(db, payload.institucion_id)
    v = payload.vigencia or p.vigencia or date.today().year
    if payload.id:
        f = db.query(FilaRejilla).filter(FilaRejilla.id == payload.id).first()
        if not f:
            return {"ok": False, "msg": "Fila no encontrada."}
        nuevo = False
    else:
        ult = db.query(FilaRejilla).filter(
            FilaRejilla.institucion_id == payload.institucion_id,
            FilaRejilla.vigencia == v).order_by(FilaRejilla.consecutivo.desc()).first()
        cons = (ult.consecutivo + 1) if ult else 1
        f = FilaRejilla(institucion_id=payload.institucion_id, vigencia=v, consecutivo=cons)
        db.add(f)
        nuevo = True
    f.rubro_codigo = (payload.rubro_codigo or "").strip()[:30] or None
    f.rubro_nombre = (payload.rubro_nombre or "").strip()[:120] or None
    f.fuente = payload.fuente
    f.valor = max(0, payload.valor)
    f.unspsc = (payload.unspsc or "").strip()[:20] or None
    f.descripcion = payload.descripcion.strip()[:400]
    f.plazo_dias = max(1, payload.plazo_dias or 5)
    f.contratista_id = payload.contratista_id
    if payload.contratista_id:
        c = db.query(Contratista).filter(Contratista.id == payload.contratista_id).first()
        if c:
            f.contratista_nombre = c.nombre
            f.contratista_doc = c.nit
    else:
        f.contratista_nombre = (payload.contratista_nombre or "").strip()[:120] or None
        f.contratista_doc = (payload.contratista_doc or "").strip()[:40] or None

    # ── Numeración y fechas en cascada, como en la rejilla real ──
    try:
        base = date.fromisoformat(payload.cdp_fecha) if payload.cdp_fecha else date.today()
    except ValueError:
        base = date.today()
    if payload.auto_fechas or nuevo:
        f.cdp_num = f"{p.consec_cdp or '04'}-{f.consecutivo}"
        f.rp_num = f"{p.consec_rp or '05'}-{f.consecutivo}"
        f.contrato_num = f"{v}{f.consecutivo:02d}"
        f.invitacion_num = f"{v}{f.consecutivo:02d}"
        f.cdp_fecha = base
        f.cotizacion_fecha = base + timedelta(days=CADENCIA["cotizacion"])
        f.proyecto_fecha = base + timedelta(days=CADENCIA["proyecto"])
        f.invitacion_fecha = base + timedelta(days=CADENCIA["invitacion"])
        f.cierre_fecha = base + timedelta(days=CADENCIA["cierre"])
        f.evaluacion_fecha = base + timedelta(days=CADENCIA["evaluacion"])
        f.aceptacion_fecha = base + timedelta(days=CADENCIA["aceptacion"])
        f.contrato_fecha = base + timedelta(days=CADENCIA["contrato"])
        f.rp_fecha = f.contrato_fecha
        f.acta_inicio_fecha = f.contrato_fecha
        f.acta_final_fecha = f.acta_inicio_fecha + timedelta(days=f.plazo_dias)
        f.liquidacion_fecha = f.acta_final_fecha + timedelta(days=CADENCIA["liquidacion_dias"])
    db.commit()
    metadatos.registrar_evento("REJILLA", "Contratación",
                               institucion_id=payload.institucion_id,
                               payload={"consecutivo": f.consecutivo})
    return {"ok": True, "id": f.id, "consecutivo": f.consecutivo,
            "msg": (f"📋 Fila {f.consecutivo} de la rejilla lista: CDP {f.cdp_num} "
                    f"({f.cdp_fecha}) → invitación {f.invitacion_num} ({f.invitacion_fecha}) "
                    f"→ contrato {f.contrato_num} ({f.contrato_fecha}) → RP {f.rp_num}. "
                    f"El acta final va para el {f.acta_final_fecha}."
                    if (payload.auto_fechas or nuevo) else "Fila actualizada.")}


class FechasIn(BaseModel):
    id: int
    cdp_fecha: str | None = None
    invitacion_fecha: str | None = None
    cierre_fecha: str | None = None
    evaluacion_fecha: str | None = None
    aceptacion_fecha: str | None = None
    contrato_fecha: str | None = None
    rp_fecha: str | None = None
    acta_inicio_fecha: str | None = None
    acta_final_fecha: str | None = None
    liquidacion_fecha: str | None = None
    cdp_num: str | None = None
    rp_num: str | None = None
    contrato_num: str | None = None
    invitacion_num: str | None = None


@router.post("/rejilla/fechas")
def rejilla_fechas(payload: FechasIn, db: Session = Depends(get_db)):
    """Ajuste manual de fechas y números, con validación de coherencia."""
    f = db.query(FilaRejilla).filter(FilaRejilla.id == payload.id).first()
    if not f:
        return {"ok": False, "msg": "Fila no encontrada."}
    for k, v in payload.model_dump(exclude_none=True).items():
        if k == "id":
            continue
        if k.endswith("_fecha"):
            try:
                setattr(f, k, date.fromisoformat(v))
            except (ValueError, TypeError):
                pass
        else:
            setattr(f, k, v)
    # Validar el orden lógico
    orden = [("cdp_fecha", "CDP"), ("invitacion_fecha", "Invitación"),
             ("cierre_fecha", "Cierre"), ("evaluacion_fecha", "Evaluación"),
             ("contrato_fecha", "Contrato"), ("rp_fecha", "RP"),
             ("acta_inicio_fecha", "Acta de inicio"), ("acta_final_fecha", "Acta final"),
             ("liquidacion_fecha", "Liquidación")]
    problemas = []
    ant_f, ant_n = None, None
    for campo, nombre in orden:
        val = getattr(f, campo)
        if val and ant_f and val < ant_f:
            problemas.append(f"«{nombre}» ({val}) es anterior a «{ant_n}» ({ant_f})")
        if val:
            ant_f, ant_n = val, nombre
    if f.acta_inicio_fecha and f.acta_final_fecha:
        d = (f.acta_final_fecha - f.acta_inicio_fecha).days
        if d != f.plazo_dias:
            problemas.append(f"Entre acta de inicio y acta final hay {d} días, "
                             f"pero el plazo pactado es de {f.plazo_dias}")
    db.commit()
    return {"ok": True, "problemas": problemas,
            "msg": ("✅ Fechas actualizadas y coherentes." if not problemas
                    else "⚠️ Guardado, pero revisa: " + "; ".join(problemas))}


@router.post("/rejilla/eliminar")
def rejilla_eliminar(id: int, db: Session = Depends(get_db)):
    f = db.query(FilaRejilla).filter(FilaRejilla.id == id).first()
    if not f:
        return {"ok": False, "msg": "Fila no encontrada."}
    n = db.query(DocumentoLegal).filter(DocumentoLegal.rejilla_id == id).count()
    db.query(DocumentoLegal).filter(DocumentoLegal.rejilla_id == id).delete()
    c = f.consecutivo
    db.delete(f)
    db.commit()
    return {"ok": True, "msg": f"Fila {c} eliminada" + (f" junto con sus {n} documento(s)." if n else ".")}


# ═════════════════ DOCUMENTOS ═════════════════
@router.get("/documentos")
def documentos(rejilla_id: int, db: Session = Depends(get_db)):
    f = db.query(FilaRejilla).filter(FilaRejilla.id == rejilla_id).first()
    if not f:
        return {"ok": False, "msg": "Fila no encontrada."}
    docs = db.query(DocumentoLegal).filter(
        DocumentoLegal.rejilla_id == rejilla_id).order_by(DocumentoLegal.id).all()
    hechos = {d.tipo: d for d in docs}
    ORDEN = ["solicitud_cotizacion", "estudios_previos", "invitacion", "contrato",
             "acta_inicio", "acta_final", "acta_liquidacion"]
    FECHA_DE = {"solicitud_cotizacion": f.cotizacion_fecha, "estudios_previos": f.proyecto_fecha,
                "invitacion": f.invitacion_fecha, "contrato": f.contrato_fecha,
                "acta_inicio": f.acta_inicio_fecha, "acta_final": f.acta_final_fecha,
                "acta_liquidacion": f.liquidacion_fecha}
    REQUIERE = {"contrato": ("rp_num", "Necesita el RP expedido"),
                "acta_inicio": ("rp_num", "Sin RP no puede haber acta de inicio"),
                "acta_liquidacion": (None, None)}
    out = []
    for t in ORDEN:
        lbl, _fn = PL.PLANTILLAS[t]
        d = hechos.get(t)
        campo, motivo = REQUIERE.get(t, (None, None))
        bloqueado = bool(campo and not getattr(f, campo, None))
        # el acta final exige acta de inicio; la liquidación exige acta final
        if t == "acta_final" and "acta_inicio" not in hechos:
            bloqueado, motivo = True, "Primero debe existir el acta de inicio"
        if t == "acta_liquidacion" and "acta_final" not in hechos:
            bloqueado, motivo = True, "Primero debe existir el acta final"
        out.append({
            "tipo": t, "label": lbl,
            "generado": bool(d), "id": d.id if d else None,
            "numero": d.numero if d else None,
            "estado": d.estado if d else None,
            "version": d.version if d else 0,
            "fecha": FECHA_DE[t].isoformat() if FECHA_DE[t] else None,
            "bloqueado": bloqueado, "motivo": motivo,
        })
    return {"ok": True, "consecutivo": f.consecutivo, "documentos": out,
            "completos": sum(1 for x in out if x["generado"]), "total": len(out)}


class GenerarDocIn(BaseModel):
    rejilla_id: int
    tipo: str
    datos: dict | None = None
    generado_por: str | None = "Contratación"


@router.post("/documentos/generar")
def documentos_generar(payload: GenerarDocIn, db: Session = Depends(get_db)):
    if payload.tipo not in PL.PLANTILLAS:
        return {"ok": False, "msg": "Tipo de documento no válido."}
    f = db.query(FilaRejilla).filter(FilaRejilla.id == payload.rejilla_id).first()
    if not f:
        return {"ok": False, "msg": "Fila de rejilla no encontrada."}
    est = documentos(payload.rejilla_id, db)
    fila_doc = next((x for x in est["documentos"] if x["tipo"] == payload.tipo), None)
    if fila_doc and fila_doc["bloqueado"]:
        return {"ok": False, "msg": f"⛔ {fila_doc['motivo']}."}
    p = _perfil(db, f.institucion_id)
    faltan = perfil(f.institucion_id, db)["faltantes"]
    ya = db.query(DocumentoLegal).filter(DocumentoLegal.rejilla_id == payload.rejilla_id,
                                         DocumentoLegal.tipo == payload.tipo).first()
    lbl, _fn = PL.PLANTILLAS[payload.tipo]
    FECHA_DE = {"solicitud_cotizacion": f.cotizacion_fecha, "estudios_previos": f.proyecto_fecha,
                "invitacion": f.invitacion_fecha, "contrato": f.contrato_fecha,
                "acta_inicio": f.acta_inicio_fecha, "acta_final": f.acta_final_fecha,
                "acta_liquidacion": f.liquidacion_fecha}
    NUM = {"invitacion": f.invitacion_num, "contrato": f.contrato_num}
    if ya:
        ya.contenido = json.dumps(payload.datos or {}, ensure_ascii=False)
        ya.version = (ya.version or 1) + 1
        ya.estado = "borrador"
        d = ya
    else:
        d = DocumentoLegal(
            institucion_id=f.institucion_id, rejilla_id=f.id, contrato_id=f.contrato_id,
            tipo=payload.tipo, numero=NUM.get(payload.tipo, f"{payload.tipo}-{f.consecutivo}"),
            titulo=lbl, fecha=FECHA_DE.get(payload.tipo),
            contenido=json.dumps(payload.datos or {}, ensure_ascii=False),
            generado_por=payload.generado_por, estado="borrador", version=1,
            creado=datetime.now())
        db.add(d)
    db.commit()
    metadatos.registrar_evento("DOC_LEGAL", payload.generado_por or "Contratación",
                               institucion_id=f.institucion_id,
                               payload={"tipo": payload.tipo, "consec": f.consecutivo})
    aviso = ""
    if faltan:
        aviso = (f" ⚠️ El perfil legal está incompleto (falta {', '.join(faltan[:3])}), "
                 "el documento sale con espacios en blanco.")
    return {"ok": True, "id": d.id, "version": d.version,
            "url": f"/legal/documentos/ver?id={d.id}",
            "msg": f"📄 {lbl} generado con las fechas de la rejilla.{aviso}"}


@router.get("/documentos/ver", response_class=HTMLResponse)
def documentos_ver(id: int, db: Session = Depends(get_db)):
    d = db.query(DocumentoLegal).filter(DocumentoLegal.id == id).first()
    if not d:
        return HTMLResponse("<h3>Documento no encontrado</h3>", status_code=404)
    f = db.query(FilaRejilla).filter(FilaRejilla.id == d.rejilla_id).first()
    p = _perfil(db, d.institucion_id)
    datos = {}
    try:
        datos = json.loads(d.contenido) if d.contenido else {}
    except Exception:
        datos = {}
    _lbl, fn = PL.PLANTILLAS.get(d.tipo, (None, None))
    if not fn or not f:
        return HTMLResponse("<h3>No se puede generar este documento</h3>", status_code=400)
    if d.tipo == "solicitud_cotizacion":
        return HTMLResponse(fn(p, f, datos.get("items"), datos.get("proveedor")))
    if d.tipo == "contrato":
        cl = datos.get("clausulas")
        return HTMLResponse(fn(p, f, datos, cl))
    return HTMLResponse(fn(p, f, datos))


@router.get("/documentos/expediente", response_class=HTMLResponse)
def expediente(rejilla_id: int, db: Session = Depends(get_db)):
    """Todo el expediente en un solo archivo, listo para archivar o imprimir."""
    f = db.query(FilaRejilla).filter(FilaRejilla.id == rejilla_id).first()
    if not f:
        return HTMLResponse("<h3>No encontrado</h3>", status_code=404)
    p = _perfil(db, f.institucion_id)
    docs = db.query(DocumentoLegal).filter(
        DocumentoLegal.rejilla_id == rejilla_id).order_by(DocumentoLegal.id).all()
    if not docs:
        return HTMLResponse(
            "<div style='font-family:system-ui;max-width:520px;margin:60px auto;text-align:center'>"
            "<h2>Expediente vacío</h2><p>Genera primero los documentos del proceso.</p></div>")
    partes = []
    ORDEN = ["solicitud_cotizacion", "estudios_previos", "invitacion", "contrato",
             "acta_inicio", "acta_final", "acta_liquidacion"]
    hechos = {d.tipo: d for d in docs}
    for t in ORDEN:
        d = hechos.get(t)
        if not d:
            continue
        datos = {}
        try:
            datos = json.loads(d.contenido) if d.contenido else {}
        except Exception:
            pass
        _lbl, fn = PL.PLANTILLAS[t]
        if t == "solicitud_cotizacion":
            html = fn(p, f, datos.get("items"), datos.get("proveedor"))
        elif t == "contrato":
            html = fn(p, f, datos, datos.get("clausulas"))
        else:
            html = fn(p, f, datos)
        # extraer solo el cuerpo
        try:
            cuerpo = html.split("</div>\n", 1)[1].rsplit('<div class="pie">', 1)[0]
        except IndexError:
            cuerpo = html
        partes.append(f'<div class="doc-sep">{PL.membrete(p)}{cuerpo}</div>')
    cuerpo = f"""
<h1 style="font-size:1.2rem">EXPEDIENTE CONTRACTUAL</h1>
<div class="doc-num">Proceso N° {f.contrato_num or f.consecutivo} · Vigencia {f.vigencia}<br>
{(f.descripcion or '').upper()}</div>
<table>
 <tr><td class="tk">CONTRATISTA</td><td>{f.contratista_nombre or ''}</td></tr>
 <tr><td class="tk">VALOR</td><td>{PL.pesos(f.valor)}</td></tr>
 <tr><td class="tk">CDP / RP</td><td>{f.cdp_num or ''} · {f.rp_num or ''}</td></tr>
 <tr><td class="tk">RUBRO</td><td>{f.rubro_codigo or ''} — {f.rubro_nombre or ''}</td></tr>
 <tr><td class="tk">DOCUMENTOS</td><td>{len(docs)} de 7</td></tr>
</table>
<h2>Índice del expediente</h2>
<ol>{''.join(f'<li>{PL.PLANTILLAS[t][0]} — {PL.fecha_corta(hechos[t].fecha)}</li>' for t in ORDEN if t in hechos)}</ol>
{''.join(partes)}"""
    extra = ".doc-sep{page-break-before:always;padding-top:20px}"
    return HTMLResponse(PL.envolver(f"Expediente {f.contrato_num or ''}", p, cuerpo, extra))


class EstadoDocIn(BaseModel):
    id: int
    estado: str


@router.post("/documentos/estado")
def documentos_estado(payload: EstadoDocIn, db: Session = Depends(get_db)):
    d = db.query(DocumentoLegal).filter(DocumentoLegal.id == payload.id).first()
    if not d:
        return {"ok": False, "msg": "Documento no encontrado."}
    if payload.estado not in ("borrador", "revision", "firmado", "archivado"):
        return {"ok": False, "msg": "Estado no válido."}
    d.estado = payload.estado
    db.commit()
    MSG = {"revision": "Enviado a revisión jurídica.",
           "firmado": "Marcado como firmado. Ya cuenta para el expediente.",
           "archivado": "Archivado.", "borrador": "Devuelto a borrador para editarlo."}
    return {"ok": True, "msg": MSG.get(payload.estado, "Actualizado.")}


# ═════════════════ CORRESPONDENCIA ═════════════════
MODELOS_CARTA = {
    "derecho_peticion": {
        "asunto": "Derecho de petición",
        "cuerpo": ("En ejercicio del derecho fundamental de petición consagrado en el "
                   "artículo 23 de la Constitución Política y reglamentado por la Ley 1755 "
                   "de 2015, respetuosamente solicito:\n\n"
                   "1. [Escriba aquí su primera solicitud concreta]\n"
                   "2. [Escriba aquí la segunda, si aplica]\n\n"
                   "Fundamento la presente petición en los siguientes hechos:\n\n"
                   "PRIMERO: [Describa el hecho que motiva la petición]\n"
                   "SEGUNDO: [Agregue los hechos adicionales]\n\n"
                   "Solicito que la respuesta sea remitida a la dirección de notificación "
                   "que se indica al final del presente escrito.")},
    "respuesta_dp": {
        "asunto": "Respuesta a derecho de petición",
        "cuerpo": ("En atención a la petición radicada en esta institución, y dentro del "
                   "término legal, me permito dar respuesta en los siguientes términos:\n\n"
                   "FRENTE A LA PRIMERA SOLICITUD: [Respuesta concreta y de fondo]\n\n"
                   "FRENTE A LA SEGUNDA SOLICITUD: [Respuesta]\n\n"
                   "En los anteriores términos damos respuesta de fondo, clara, precisa y "
                   "congruente con lo solicitado. Si considera que la respuesta es "
                   "incompleta, puede manifestarlo dentro de los diez (10) días siguientes.")},
    "oficio": {
        "asunto": "Oficio",
        "cuerpo": ("Por medio del presente me permito informar a usted que:\n\n"
                   "[Desarrolle aquí el contenido del oficio]\n\n"
                   "Agradezco la atención prestada.")},
    "constancia": {
        "asunto": "Constancia",
        "cuerpo": ("La suscrita Rectoría de la institución hace constar que:\n\n"
                   "[Escriba aquí lo que se certifica]\n\n"
                   "La presente constancia se expide a solicitud del interesado.")},
    "circular": {
        "asunto": "Circular",
        "cuerpo": ("Para: [Docentes / Padres de familia / Comunidad educativa]\n\n"
                   "[Desarrolle aquí el contenido de la circular]\n\n"
                   "Agradecemos su atención y cumplimiento.")},
}


@router.get("/correspondencia/modelos")
def corr_modelos():
    return {"modelos": [{"tipo": k, **v} for k, v in MODELOS_CARTA.items()]}


@router.get("/correspondencia")
def corr_listar(institucion_id: int, tipo: str | None = None,
                db: Session = Depends(get_db)):
    q = db.query(Correspondencia).filter(Correspondencia.institucion_id == institucion_id)
    if tipo:
        q = q.filter(Correspondencia.tipo == tipo)
    filas = q.order_by(Correspondencia.id.desc()).limit(80).all()
    hoy = date.today()
    TIPOS = {"carta": "✉️ Carta", "oficio": "📄 Oficio",
             "derecho_peticion": "⚖️ Derecho de petición",
             "respuesta_dp": "↩️ Respuesta a DP", "circular": "📢 Circular",
             "constancia": "📜 Constancia"}
    out = []
    for c in filas:
        dias = (c.fecha_limite - hoy).days if c.fecha_limite else None
        out.append({
            "id": c.id, "tipo": c.tipo, "tipo_label": TIPOS.get(c.tipo, c.tipo),
            "radicado": c.radicado, "asunto": c.asunto,
            "destinatario": c.destinatario, "entidad": c.destinatario_entidad,
            "remitente": c.remitente, "estado": c.estado,
            "fecha": c.fecha.isoformat() if c.fecha else None,
            "fecha_limite": c.fecha_limite.isoformat() if c.fecha_limite else None,
            "dias_restantes": dias,
            "urgente": dias is not None and dias <= 3 and c.estado != "respondido",
            "vencido": dias is not None and dias < 0 and c.estado != "respondido",
        })
    return {"correspondencia": out, "tipos": [{"id": k, "label": v} for k, v in TIPOS.items()],
            "resumen": {"total": len(out),
                        "dp_pendientes": sum(1 for x in out if x["tipo"] == "derecho_peticion"
                                             and x["estado"] != "respondido"),
                        "urgentes": sum(1 for x in out if x["urgente"]),
                        "vencidos": sum(1 for x in out if x["vencido"])}}


class CorrIn(BaseModel):
    id: int | None = 0
    institucion_id: int
    tipo: str
    asunto: str
    destinatario: str | None = ""
    destinatario_cargo: str | None = ""
    destinatario_entidad: str | None = ""
    remitente: str | None = ""
    cuerpo: str | None = ""
    anexos: list | None = None
    fecha: str | None = None
    creado_por: str | None = "Rectoría"


@router.post("/correspondencia/guardar")
def corr_guardar(payload: CorrIn, db: Session = Depends(get_db)):
    if not payload.asunto.strip():
        return {"ok": False, "msg": "Escribe el asunto."}
    if payload.id:
        c = db.query(Correspondencia).filter(Correspondencia.id == payload.id).first()
        if not c:
            return {"ok": False, "msg": "No encontrado."}
    else:
        n = db.query(Correspondencia).filter(
            Correspondencia.institucion_id == payload.institucion_id).count() + 1
        c = Correspondencia(institucion_id=payload.institucion_id,
                            radicado=f"{date.today().year}-{n:04d}",
                            creado=datetime.now(), estado="borrador")
        db.add(c)
    c.tipo = payload.tipo
    c.asunto = payload.asunto.strip()[:200]
    c.destinatario = (payload.destinatario or "").strip()[:120] or None
    c.destinatario_cargo = (payload.destinatario_cargo or "").strip()[:120] or None
    c.destinatario_entidad = (payload.destinatario_entidad or "").strip()[:150] or None
    c.remitente = (payload.remitente or "").strip()[:120] or None
    c.cuerpo = (payload.cuerpo or "")[:8000]
    c.anexos = json.dumps(payload.anexos or [], ensure_ascii=False)
    c.creado_por = payload.creado_por
    try:
        c.fecha = date.fromisoformat(payload.fecha) if payload.fecha else date.today()
    except ValueError:
        c.fecha = date.today()
    if payload.tipo == "derecho_peticion":
        # 15 días hábiles ≈ 21 calendario
        c.fecha_limite = c.fecha + timedelta(days=21)
    db.commit()
    extra = ""
    if payload.tipo == "derecho_peticion":
        extra = f" ⏰ La entidad tiene hasta el {c.fecha_limite} para responder (15 días hábiles)."
    return {"ok": True, "id": c.id, "radicado": c.radicado,
            "msg": f"📝 Radicado {c.radicado} guardado.{extra}"}


@router.get("/correspondencia/ver", response_class=HTMLResponse)
def corr_ver(id: int, db: Session = Depends(get_db)):
    c = db.query(Correspondencia).filter(Correspondencia.id == id).first()
    if not c:
        return HTMLResponse("<h3>No encontrado</h3>", status_code=404)
    p = _perfil(db, c.institucion_id)
    return HTMLResponse(PL.correspondencia(p, c, {}))


@router.post("/correspondencia/estado")
def corr_estado(payload: EstadoDocIn, db: Session = Depends(get_db)):
    c = db.query(Correspondencia).filter(Correspondencia.id == payload.id).first()
    if not c:
        return {"ok": False, "msg": "No encontrado."}
    if payload.estado not in ("borrador", "enviado", "respondido", "vencido"):
        return {"ok": False, "msg": "Estado no válido."}
    c.estado = payload.estado
    db.commit()
    return {"ok": True, "msg": f"Marcado como {payload.estado}."}
