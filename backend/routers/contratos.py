"""Contratación FSE — régimen especial (Decreto 4791/2008 art. 17, Ley 715/2001).

- Expediente del contratista: cédula, contraloría, procuraduría, REDAM,
  cámara de comercio, RUT, seguridad social (checklist de documentos con
  carga simulada) + score de confianza + capacidad legal en SMMLV.
- Pipeline del contrato (SECOP 2 simulado):
  borrador → documentos → jurídica → firma → firmado → ejecución → liquidado,
  con validaciones en cada paso y FIRMA EN LÍNEA con verificación de
  identidad (OTP simulado) para rector, contratista y jurídica.
- Control de topes: valor del contrato vs 20 SMMLV (régimen especial) y
  acumulado del contratista vs su capacidad — para no romper la ley.
"""
import json
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Contratista, Contrato, PlanFSE, ConfigSistema, MensajeWhatsApp, Institucion, MovimientoFSE
import metadatos

router = APIRouter()

DOCS_LABELS = [
    ("cedula", "Cédula / representante legal"),
    ("contraloria", "Certificado Contraloría"),
    ("procuraduria", "Certificado Procuraduría"),
    ("redam", "Certificado REDAM (no deudor alimentario)"),
    ("policia", "Antecedentes Policía Nacional"),
    ("camara_comercio", "Cámara de Comercio"),
    ("rut", "RUT"),
    ("seguridad_social", "Planilla seguridad social"),
    ("hoja_vida", "Hoja de vida (función pública)"),
    ("cert_bancario", "Certificación bancaria"),
]

# Vigencia legal en días de cada documento: pasado ese tiempo hay que pedirlo de
# nuevo. Es el origen de las alertas "documento por vencer" (punto 21).
DOCS_VIGENCIA = {
    "contraloria": 90, "procuraduria": 90, "redam": 90, "policia": 90,
    "camara_comercio": 90, "seguridad_social": 30, "cert_bancario": 90,
    "cedula": None, "rut": None, "hoja_vida": None,
}

# Códigos CIIU (Cámara de Comercio) por tipo de contrato: el sistema valida que
# el objeto contratado corresponda a la actividad registrada del contratista.
CIIU_POR_TIPO = {
    "suministro": ["4761", "4762", "4690", "4649"],
    "servicio": ["8130", "8121", "9511", "7490"],
    "obra": ["4100", "4290", "4330", "4390"],
    "pae": ["5621", "1084", "4630"],
}
PIPELINE = ["borrador", "documentos", "juridica", "firma", "firmado", "ejecucion", "liquidado"]

# Plazos sugeridos (días hábiles) por etapa según el tipo de contrato — así el
# pipeline "lleva los tiempos" y marca en rojo lo que se está demorando.
PLAZOS = {
    "suministro": {"borrador": 2, "documentos": 3, "juridica": 2, "firma": 2, "firmado": 1, "ejecucion": 30},
    "servicio":   {"borrador": 2, "documentos": 4, "juridica": 3, "firma": 2, "firmado": 1, "ejecucion": 60},
    "obra":       {"borrador": 3, "documentos": 6, "juridica": 4, "firma": 3, "firmado": 1, "ejecucion": 90},
    "pae":        {"borrador": 2, "documentos": 5, "juridica": 3, "firma": 2, "firmado": 1, "ejecucion": 120},
}
TIPO_LBL = {"suministro": "Suministro", "servicio": "Servicio", "obra": "Obra menor", "pae": "PAE / alimentación"}


def _smmlv(db):
    c = db.query(ConfigSistema).filter(ConfigSistema.clave == "smmlv").first()
    t = db.query(ConfigSistema).filter(ConfigSistema.clave == "tope_fse_smmlv").first()
    return (float(c.valor) if c else 1623500.0), (float(t.valor) if t else 20.0)


def _doc_norm(v):
    """Normaliza un documento: bool legado o dict {ok, archivo, fecha}."""
    if isinstance(v, dict):
        return {"ok": bool(v.get("ok")), "archivo": v.get("archivo"), "fecha": v.get("fecha")}
    return {"ok": bool(v), "archivo": None, "fecha": None}


def _docs(c):
    try:
        d = json.loads(c.documentos) if c.documentos else {}
    except Exception:
        d = {}
    req = DOCS_LABELS if c.tipo != "natural" else [x for x in DOCS_LABELS if x[0] != "camara_comercio"]
    items = []
    hoy = date.today()
    for k, lbl in req:
        nv = _doc_norm(d.get(k, False))
        vig = DOCS_VIGENCIA.get(k)
        dias_rest = None
        vencido = False
        por_vencer = False
        if nv["ok"] and nv["fecha"] and vig:
            try:
                f = date.fromisoformat(nv["fecha"][:10])
                dias_rest = vig - (hoy - f).days
                vencido = dias_rest < 0
                por_vencer = 0 <= dias_rest <= 15
            except Exception:
                pass
        items.append({"clave": k, "label": lbl, "ok": nv["ok"] and not vencido,
                      "archivo": nv["archivo"], "fecha": nv["fecha"],
                      "vigencia_dias": vig, "dias_restantes": dias_rest,
                      "vencido": vencido, "por_vencer": por_vencer})
    faltan = [i["label"] for i in items if not i["ok"]]
    return items, len(faltan) == 0, faltan


@router.get("/contratistas")
def contratistas(db: Session = Depends(get_db)):
    smmlv, _ = _smmlv(db)
    out = []
    for c in db.query(Contratista).order_by(Contratista.confianza.desc()).all():
        items, completos, faltan = _docs(c)
        cap_cop = c.capacidad_smmlv * smmlv
        out.append({
            "id": c.id, "nombre": c.nombre, "nit": c.nit, "tipo": c.tipo,
            "telefono": c.telefono, "email": c.email, "notas": c.notas,
            "documentos": items, "docs_completos": completos, "faltantes": faltan,
            "confianza": c.confianza,
            "capacidad_smmlv": c.capacidad_smmlv, "capacidad_cop": round(cap_cop),
            "contratado_anio": round(c.contratado_anio),
            "disponible_cop": round(max(0, cap_cop - c.contratado_anio)),
            "pct_usado": round(100 * c.contratado_anio / cap_cop, 1) if cap_cop else 0,
        })
    return out


class ContratistaIn(BaseModel):
    id: int | None = 0
    nombre: str
    nit: str | None = ""
    tipo: str | None = "juridica"
    telefono: str | None = ""
    email: str | None = ""
    documentos: dict | None = {}
    capacidad_smmlv: float | None = 20.0
    notas: str | None = ""


@router.post("/contratistas/guardar")
def contratista_guardar(payload: ContratistaIn, db: Session = Depends(get_db)):
    if not payload.nombre.strip():
        return {"ok": False, "msg": "El nombre / razón social es obligatorio."}
    if payload.id:
        c = db.query(Contratista).filter(Contratista.id == payload.id).first()
        if not c:
            return {"ok": False, "msg": "Contratista no encontrado."}
    else:
        c = Contratista(contratado_anio=0.0)
        db.add(c)
    c.nombre = payload.nombre.strip()
    c.nit = payload.nit or ""
    c.tipo = payload.tipo if payload.tipo in ("natural", "juridica") else "juridica"
    c.telefono = payload.telefono or ""
    c.email = payload.email or ""
    docs = {}
    for k, _lbl in DOCS_LABELS:
        v = (payload.documentos or {}).get(k, False)
        docs[k] = _doc_norm(v)
        if docs[k]["ok"] and not docs[k]["fecha"]:
            docs[k]["fecha"] = date.today().isoformat()
    c.documentos = json.dumps(docs, ensure_ascii=False)
    c.capacidad_smmlv = max(1.0, min(300.0, payload.capacidad_smmlv or 20.0))
    c.notas = payload.notas or ""
    n_ok = sum(1 for v in docs.values() if v["ok"])
    c.confianza = min(100, 30 + 8 * n_ok + (12 if c.contratado_anio > 0 else 0))
    db.commit()
    metadatos.registrar_evento("CONTRATISTA_GUARDADO", "Contratación", payload={"docs_ok": n_ok})
    return {"ok": True, "msg": f"Expediente de {c.nombre} guardado. Confianza: {c.confianza}/100.", "id": c.id}


class IdIn(BaseModel):
    id: int


@router.post("/contratistas/solicitar_docs")
def solicitar_docs(payload: IdIn, db: Session = Depends(get_db)):
    c = db.query(Contratista).filter(Contratista.id == payload.id).first()
    if not c:
        return {"ok": False, "msg": "Contratista no encontrado."}
    _, completos, faltan = _docs(c)
    if completos:
        return {"ok": False, "msg": "El expediente ya está completo. ✔"}
    db.add(MensajeWhatsApp(
        destinatario=c.nombre, telefono=c.telefono or "—",
        contenido=("Buen día. Para continuar con su proceso de contratación con la institución, "
                   "por favor cargue en el portal los siguientes documentos pendientes: "
                   + "; ".join(faltan) + ". — Oficina de Contratación (GyverLabs)"),
        fecha=datetime.now(), estado="ENVIADO (simulado)", contexto="contratos"))
    db.commit()
    metadatos.registrar_evento("CONTRATISTA_SOLICITUD_DOCS", "Contratación", payload={"faltan": len(faltan)})
    return {"ok": True, "msg": f"📱 Solicitud enviada (simulada) a {c.nombre}: {len(faltan)} documento(s) pendiente(s)."}


# ═════════ CONTRATOS (pipeline SECOP 2) ═════════
@router.get("/")
def contratos(institucion_id: int, db: Session = Depends(get_db)):
    smmlv, tope = _smmlv(db)
    cts = {c.id: c for c in db.query(Contratista).all()}
    planes = {p.id: p.concepto for p in db.query(PlanFSE).all()}
    out = []
    for ct in db.query(Contrato).filter(Contrato.institucion_id == institucion_id).order_by(
            Contrato.fecha.desc()).all():
        c = cts.get(ct.contratista_id)
        try:
            firmas = json.loads(ct.firmas) if ct.firmas else []
        except Exception:
            firmas = []
        _, docs_ok, faltan = _docs(c) if c else ([], False, ["Contratista no encontrado"])
        try:
            etapas = json.loads(ct.etapas_fechas) if ct.etapas_fechas else {}
        except Exception:
            etapas = {}
        try:
            cotiz = json.loads(ct.cotizaciones) if ct.cotizaciones else []
        except Exception:
            cotiz = []
        try:
            ccobro = json.loads(ct.cuenta_cobro) if ct.cuenta_cobro else None
        except Exception:
            ccobro = None
        tipo_c = ct.tipo_contrato or "suministro"
        plazo_etapa = PLAZOS.get(tipo_c, PLAZOS["suministro"]).get(ct.estado)
        dias_en_etapa = None
        atrasado = False
        f_ent = etapas.get(ct.estado)
        if f_ent:
            try:
                dias_en_etapa = (date.today() - date.fromisoformat(f_ent)).days
                atrasado = plazo_etapa is not None and dias_en_etapa > plazo_etapa
            except Exception:
                pass
        out.append({
            "id": ct.id, "numero": ct.numero, "objeto": ct.objeto, "valor": round(ct.valor),
            "tipo_contrato": tipo_c, "tipo_label": TIPO_LBL.get(tipo_c, tipo_c),
            "etapas_fechas": etapas, "cotizaciones": cotiz, "cuenta_cobro": ccobro,
            "plazo_etapa": plazo_etapa, "dias_en_etapa": dias_en_etapa, "atrasado": atrasado,
            "valor_smmlv": round(ct.valor / smmlv, 2),
            "excede_tope": ct.valor > tope * smmlv,
            "cdp": ct.cdp_num, "rp": ct.rp_num,
            "fecha": ct.fecha.isoformat(), "estado": ct.estado,
            "pipeline": PIPELINE, "paso": PIPELINE.index(ct.estado) if ct.estado in PIPELINE else 0,
            "secop_url": ct.secop_url, "firmas": firmas,
            "firmas_completas": bool(firmas) and all(f.get("firmado") for f in firmas),
            "nota_juridica": ct.nota_juridica,
            "contratista": c.nombre if c else "—", "contratista_id": ct.contratista_id,
            "docs_ok": docs_ok, "docs_faltantes": faltan,
            "plan": planes.get(ct.plan_id),
        })
    return out


class ContratoIn(BaseModel):
    institucion_id: int
    contratista_id: int
    objeto: str
    valor: float
    plan_id: int | None = None
    tipo_contrato: str | None = "suministro"


@router.post("/guardar")
def contrato_guardar(payload: ContratoIn, db: Session = Depends(get_db)):
    if not payload.objeto.strip():
        return {"ok": False, "msg": "El objeto del contrato es obligatorio."}
    if payload.valor <= 0:
        return {"ok": False, "msg": "El valor debe ser mayor a cero."}
    smmlv, tope = _smmlv(db)
    if payload.valor > tope * smmlv:
        return {"ok": False, "msg": (
            f"⚖️ BLOQUEADO: {round(payload.valor):,} COP supera el tope del régimen especial FSE "
            f"({tope:.0f} SMMLV = {round(tope*smmlv):,} COP — Decreto 4791/2008 art. 17). "
            "Para este monto el proceso debe ir por la Ley 80 (licitación/selección abreviada).").replace(",", ".")}
    c = db.query(Contratista).filter(Contratista.id == payload.contratista_id).first()
    if not c:
        return {"ok": False, "msg": "Selecciona un contratista."}
    cap_cop = c.capacidad_smmlv * smmlv
    if c.contratado_anio + payload.valor > cap_cop:
        return {"ok": False, "msg": (
            f"⚖️ BLOQUEADO: con este contrato {c.nombre} superaría su capacidad anual "
            f"({round(cap_cop):,} COP). Acumulado actual: {round(c.contratado_anio):,} COP.").replace(",", ".")}
    n = db.query(Contrato).count() + 1
    ie = db.query(Institucion).filter(Institucion.id == payload.institucion_id).first()
    rector = ie.rector if ie else "Rector(a)"
    firmas = [
        {"rol": "Rector(a)", "nombre": rector, "firmado": False, "fecha": None, "metodo": None},
        {"rol": "Contratista", "nombre": c.nombre, "firmado": False, "fecha": None, "metodo": None},
        {"rol": "Jurídica", "nombre": "Diana Guzmán Prada", "firmado": False, "fecha": None, "metodo": None},
    ]
    ct = Contrato(institucion_id=payload.institucion_id, contratista_id=c.id,
                  numero=f"CT-2026-{n:03d}", objeto=payload.objeto.strip()[:200],
                  valor=payload.valor, cdp_num=f"CDP-2026-{n+10:03d}", rp_num=None,
                  fecha=date.today(), estado="borrador",
                  secop_url="https://community.secop.gov.co/",
                  firmas=json.dumps(firmas, ensure_ascii=False), plan_id=payload.plan_id,
                  tipo_contrato=payload.tipo_contrato if payload.tipo_contrato in PLAZOS else "suministro",
                  etapas_fechas=json.dumps({"borrador": date.today().isoformat()}),
                  cotizaciones=json.dumps([]))
    db.add(ct)
    db.commit()
    metadatos.registrar_evento("CONTRATO_CREADO", "Contratación", institucion_id=payload.institucion_id,
                               payload={"valor": payload.valor, "smmlv": round(payload.valor / smmlv, 2)})
    return {"ok": True, "msg": f"Contrato {ct.numero} creado en BORRADOR. CDP {ct.cdp_num} expedido automáticamente.", "id": ct.id}


@router.post("/avanzar")
def contrato_avanzar(payload: IdIn, db: Session = Depends(get_db)):
    ct = db.query(Contrato).filter(Contrato.id == payload.id).first()
    if not ct:
        return {"ok": False, "msg": "Contrato no encontrado."}
    if ct.estado not in PIPELINE:
        ct.estado = "borrador"
    i = PIPELINE.index(ct.estado)
    if i >= len(PIPELINE) - 1:
        return {"ok": False, "msg": "El contrato ya está liquidado."}
    sig = PIPELINE[i + 1]
    # validaciones por paso
    if sig == "juridica":
        c = db.query(Contratista).filter(Contratista.id == ct.contratista_id).first()
        _, docs_ok, faltan = _docs(c) if c else ([], False, ["contratista"])
        if not docs_ok:
            return {"ok": False, "msg": "⛔ No puede pasar a Jurídica: faltan documentos del contratista → " + "; ".join(faltan)}
    if sig == "firma":
        if not ct.nota_juridica:
            ct.nota_juridica = "Vo.Bo. jurídico emitido (revisión de requisitos OK)."
        if not ct.rp_num:
            n = db.query(Contrato).count() + 30
            ct.rp_num = f"RP-2026-{n:03d}"
    if sig == "firmado":
        try:
            firmas = json.loads(ct.firmas) if ct.firmas else []
        except Exception:
            firmas = []
        pendientes = [f["rol"] for f in firmas if not f.get("firmado")]
        if pendientes:
            return {"ok": False, "msg": "⛔ Faltan firmas: " + ", ".join(pendientes) + ". Usa 'Firmar en línea'."}
    if sig == "ejecucion":
        c = db.query(Contratista).filter(Contratista.id == ct.contratista_id).first()
        if c:
            c.contratado_anio = (c.contratado_anio or 0) + ct.valor
    ct.estado = sig
    try:
        _et = json.loads(ct.etapas_fechas) if ct.etapas_fechas else {}
    except Exception:
        _et = {}
    _et[sig] = date.today().isoformat()
    ct.etapas_fechas = json.dumps(_et)
    db.commit()
    metadatos.registrar_evento("CONTRATO_AVANCE", "Contratación", institucion_id=ct.institucion_id,
                               payload={"contrato": ct.numero, "a": sig})
    msgs = {"documentos": "Recolección de documentos del contratista.",
            "juridica": "Enviado a revisión jurídica.",
            "firma": f"Listo para firmas. {ct.rp_num} expedido.",
            "firmado": "🎉 Contrato FIRMADO por todas las partes.",
            "ejecucion": "En ejecución. El valor se sumó al acumulado del contratista.",
            "liquidado": "Contrato liquidado y archivado."}
    return {"ok": True, "msg": f"{ct.numero} → {sig.upper()}. {msgs.get(sig,'')}"}


class FirmaIn(BaseModel):
    id: int
    rol: str
    otp: str | None = ""


@router.post("/firmar")
def contrato_firmar(payload: FirmaIn, db: Session = Depends(get_db)):
    ct = db.query(Contrato).filter(Contrato.id == payload.id).first()
    if not ct:
        return {"ok": False, "msg": "Contrato no encontrado."}
    if ct.estado not in ("firma", "juridica"):
        return {"ok": False, "msg": "El contrato aún no está en etapa de firma."}
    try:
        firmas = json.loads(ct.firmas) if ct.firmas else []
    except Exception:
        firmas = []
    encontrada = False
    for f in firmas:
        if f["rol"] == payload.rol:
            if f.get("firmado"):
                return {"ok": False, "msg": f"{payload.rol} ya firmó este contrato."}
            f["firmado"] = True
            f["fecha"] = datetime.now().isoformat(timespec="minutes")
            f["metodo"] = "Firma electrónica + OTP (simulado)"
            encontrada = True
    if not encontrada:
        return {"ok": False, "msg": "Rol de firma no válido."}
    ct.firmas = json.dumps(firmas, ensure_ascii=False)
    todas = all(f.get("firmado") for f in firmas)
    if todas and ct.estado == "firma":
        ct.estado = "firmado"
        try:
            _et = json.loads(ct.etapas_fechas) if ct.etapas_fechas else {}
        except Exception:
            _et = {}
        _et["firmado"] = date.today().isoformat()
        ct.etapas_fechas = json.dumps(_et)
    db.commit()
    metadatos.registrar_evento("CONTRATO_FIRMA", payload.rol, institucion_id=ct.institucion_id,
                               payload={"contrato": ct.numero, "completas": todas})
    return {"ok": True, "msg": ("✍️ Firma de " + payload.rol + " registrada con verificación de identidad (OTP simulado)."
                                + (" 🎉 ¡Todas las firmas completas! Contrato FIRMADO." if todas else "")),
            "todas": todas}


class JuridicaIn(BaseModel):
    id: int
    nota: str
    aprobado: bool


@router.post("/juridica")
def contrato_juridica(payload: JuridicaIn, db: Session = Depends(get_db)):
    ct = db.query(Contrato).filter(Contrato.id == payload.id).first()
    if not ct:
        return {"ok": False, "msg": "Contrato no encontrado."}
    ct.nota_juridica = (payload.nota or "").strip()[:300] or ("Aprobado sin observaciones." if payload.aprobado else "Devuelto con observaciones.")
    try:
        _et = json.loads(ct.etapas_fechas) if ct.etapas_fechas else {}
    except Exception:
        _et = {}
    if payload.aprobado and ct.estado == "juridica":
        if not ct.rp_num:
            n = db.query(Contrato).count() + 30
            ct.rp_num = f"RP-2026-{n:03d}"
        ct.estado = "firma"
        _et["firma"] = date.today().isoformat()
    elif not payload.aprobado and ct.estado == "juridica":
        ct.estado = "documentos"
        _et["documentos"] = date.today().isoformat()
    ct.etapas_fechas = json.dumps(_et)
    db.commit()
    metadatos.registrar_evento("CONTRATO_JURIDICA", "Jurídica", institucion_id=ct.institucion_id,
                               payload={"contrato": ct.numero, "aprobado": payload.aprobado})
    return {"ok": True, "msg": ("⚖️ Vo.Bo. jurídico emitido → pasa a FIRMA." if payload.aprobado
                                else "⚖️ Devuelto a DOCUMENTOS con observaciones.")}


# ═════════ TOPES Y CONTROL LEGAL ═════════
@router.get("/topes")
def topes(institucion_id: int | None = None, db: Session = Depends(get_db)):
    smmlv, tope = _smmlv(db)
    filas = []
    alertas = []
    for c in db.query(Contratista).all():
        cap = c.capacidad_smmlv * smmlv
        pct = round(100 * c.contratado_anio / cap, 1) if cap else 0
        filas.append({
            "id": c.id, "nombre": c.nombre, "capacidad_smmlv": c.capacidad_smmlv,
            "capacidad_cop": round(cap), "acumulado": round(c.contratado_anio),
            "disponible": round(max(0, cap - c.contratado_anio)), "pct": pct,
        })
        if pct >= 80:
            alertas.append(f"{c.nombre} lleva el {pct}% de su capacidad anual — planifica con otro proveedor.")
    filas.sort(key=lambda x: -x["pct"])
    return {
        "smmlv": smmlv, "tope_smmlv": tope, "tope_cop": round(tope * smmlv),
        "referencia": "Decreto 4791 de 2008, art. 17 (régimen especial FSE) · Ley 715 de 2001",
        "contratistas": filas, "alertas": alertas,
    }


class SmmlvIn(BaseModel):
    valor: float


@router.post("/topes/smmlv")
def set_smmlv(payload: SmmlvIn, db: Session = Depends(get_db)):
    if payload.valor < 500000 or payload.valor > 10000000:
        return {"ok": False, "msg": "Valor de SMMLV fuera de rango razonable."}
    c = db.query(ConfigSistema).filter(ConfigSistema.clave == "smmlv").first()
    if c:
        c.valor = str(payload.valor)
    else:
        db.add(ConfigSistema(clave="smmlv", valor=str(payload.valor)))
    db.commit()
    return {"ok": True, "msg": f"SMMLV actualizado a {round(payload.valor):,} COP.".replace(",", ".")}


# ═════════ PORTAL DEL CONTRATISTA (link de autogestión) — punto 9b ═════════
import secrets as _secrets


@router.post("/contratistas/portal_link")
def portal_link(payload: IdIn, db: Session = Depends(get_db)):
    """Genera el link único para que el CONTRATISTA suba sus propios
    documentos, y se lo envía por WhatsApp/correo (simulado)."""
    c = db.query(Contratista).filter(Contratista.id == payload.id).first()
    if not c:
        return {"ok": False, "msg": "Contratista no encontrado."}
    if not c.portal_token:
        c.portal_token = _secrets.token_urlsafe(12)
    url = f"https://portal.contratistas.gyverlabs.co/subir/{c.portal_token}"
    db.add(MensajeWhatsApp(
        destinatario=c.nombre, telefono=c.telefono or "—",
        contenido=(f"Buen día. Para agilizar su proceso de contratación, cargue sus documentos "
                   f"directamente en este enlace seguro (vence en 7 días): {url} "
                   "— Oficina de Contratación"),
        fecha=datetime.now(), estado="ENVIADO (simulado)", contexto="portal"))
    db.commit()
    metadatos.registrar_evento("PORTAL_LINK", "Contratación", payload={"contratista": c.nombre[:30]})
    return {"ok": True, "url": url,
            "msg": f"🔗 Link de autogestión generado y enviado (simulado) a {c.nombre}. Cuando el contratista suba sus documentos, aparecerán aquí automáticamente."}


@router.post("/contratistas/portal_carga")
def portal_carga(payload: IdIn, db: Session = Depends(get_db)):
    """DEMO EN VIVO: simula que el contratista entró al link y subió los
    documentos que le faltaban (con archivo y fecha de hoy)."""
    c = db.query(Contratista).filter(Contratista.id == payload.id).first()
    if not c:
        return {"ok": False, "msg": "Contratista no encontrado."}
    try:
        d = json.loads(c.documentos) if c.documentos else {}
    except Exception:
        d = {}
    req = DOCS_LABELS if c.tipo != "natural" else [x for x in DOCS_LABELS if x[0] != "camara_comercio"]
    subidos = []
    for k, lbl in req:
        nv = _doc_norm(d.get(k, False))
        if not nv["ok"]:
            d[k] = {"ok": True, "archivo": f"{k}_portal.pdf", "fecha": date.today().isoformat()}
            subidos.append(lbl)
        else:
            d[k] = nv
    if not subidos:
        return {"ok": False, "msg": "El expediente ya estaba completo."}
    c.documentos = json.dumps(d, ensure_ascii=False)
    n_ok = sum(1 for v in d.values() if _doc_norm(v)["ok"])
    c.confianza = min(100, 30 + 8 * n_ok + (12 if c.contratado_anio > 0 else 0))
    db.commit()
    metadatos.registrar_evento("PORTAL_CARGA", "Contratista", payload={"docs": len(subidos)})
    return {"ok": True, "msg": f"📥 El contratista subió {len(subidos)} documento(s) por el portal: {', '.join(subidos)}. Expediente completo ✅ — verifica las fechas y continúa el pipeline."}


# ═════════ EDITAR CONTRATO (CDP/RP/fechas/cotizaciones/cuenta de cobro) — punto 11 ═════════
class ContratoEditIn(BaseModel):
    id: int
    objeto: str | None = None
    valor: float | None = None
    tipo_contrato: str | None = None
    contratista_id: int | None = None
    cdp_num: str | None = None
    rp_num: str | None = None
    cotizaciones: list | None = None
    cuenta_cobro: dict | None = None


@router.post("/editar")
def contrato_editar(payload: ContratoEditIn, db: Session = Depends(get_db)):
    ct = db.query(Contrato).filter(Contrato.id == payload.id).first()
    if not ct:
        return {"ok": False, "msg": "Contrato no encontrado."}
    smmlv, tope = _smmlv(db)
    if payload.objeto is not None and payload.objeto.strip():
        ct.objeto = payload.objeto.strip()[:200]
    if payload.valor is not None and payload.valor > 0:
        if payload.valor > tope * smmlv:
            return {"ok": False, "msg": f"⚖️ El nuevo valor supera el tope de {tope:.0f} SMMLV del régimen especial."}
        if ct.estado not in ("borrador", "documentos"):
            return {"ok": False, "msg": "El valor solo puede modificarse en borrador o documentos (antes de jurídica)."}
        ct.valor = payload.valor
    if payload.contratista_id is not None:
        if ct.estado != "borrador":
            return {"ok": False, "msg": "El contratista solo puede cambiarse en borrador."}
        nuevo = db.query(Contratista).filter(Contratista.id == payload.contratista_id).first()
        if not nuevo:
            return {"ok": False, "msg": "Contratista no encontrado."}
        ct.contratista_id = nuevo.id
        try:
            firmas = json.loads(ct.firmas) if ct.firmas else []
            for f in firmas:
                if f.get("rol") == "Contratista":
                    f["nombre"] = nuevo.nombre
                    f["firmado"] = False
                    f["fecha"] = None
            ct.firmas = json.dumps(firmas, ensure_ascii=False)
        except Exception:
            pass
    if payload.tipo_contrato in PLAZOS:
        ct.tipo_contrato = payload.tipo_contrato
    if payload.cdp_num is not None:
        ct.cdp_num = payload.cdp_num.strip()[:30] or None
    if payload.rp_num is not None:
        ct.rp_num = payload.rp_num.strip()[:30] or None
    if payload.cotizaciones is not None:
        limpio = []
        for q in payload.cotizaciones[:8]:
            if isinstance(q, dict) and q.get("proveedor"):
                limpio.append({"proveedor": str(q["proveedor"])[:80],
                               "valor": float(q.get("valor") or 0),
                               "fecha": str(q.get("fecha") or date.today().isoformat())[:10],
                               "archivo": str(q.get("archivo") or "")[:80] or None})
        ct.cotizaciones = json.dumps(limpio, ensure_ascii=False)
    if payload.cuenta_cobro is not None:
        cc = payload.cuenta_cobro
        estado_cc = cc.get("estado", "pendiente")
        nueva = {"numero": str(cc.get("numero") or f"CC-{ct.numero[-3:]}")[:20],
                 "fecha": str(cc.get("fecha") or date.today().isoformat())[:10],
                 "valor": float(cc.get("valor") or ct.valor),
                 "archivo": str(cc.get("archivo") or "cuenta_cobro.pdf")[:80],
                 "estado": estado_cc if estado_cc in ("pendiente", "pagada") else "pendiente"}
        # Al marcar la cuenta de cobro como PAGADA se genera el egreso en el FSE
        anterior = None
        try:
            anterior = json.loads(ct.cuenta_cobro) if ct.cuenta_cobro else None
        except Exception:
            pass
        if nueva["estado"] == "pagada" and (not anterior or anterior.get("estado") != "pagada"):
            prov = db.query(Contratista).filter(Contratista.id == ct.contratista_id).first()
            db.add(MovimientoFSE(institucion_id=ct.institucion_id, fecha=date.today(), tipo="egreso",
                                 cuenta_codigo="1510", concepto=f"Pago {nueva['numero']} · {ct.numero}: {ct.objeto[:60]}",
                                 proveedor=prov.nombre if prov else "", nit=prov.nit if prov else "",
                                 valor=nueva["valor"], metodo="Transferencia",
                                 comprobante=nueva["numero"], estado="pagado"))
        ct.cuenta_cobro = json.dumps(nueva, ensure_ascii=False)
    db.commit()
    metadatos.registrar_evento("CONTRATO_EDITADO", "Contaduría/Contratación",
                               institucion_id=ct.institucion_id, payload={"contrato": ct.numero})
    return {"ok": True, "msg": f"{ct.numero} actualizado." + (" 💸 Egreso registrado en el FSE por la cuenta de cobro pagada." if payload.cuenta_cobro and payload.cuenta_cobro.get('estado') == 'pagada' else "")}


# ═════════ CRONOLOGÍA PARA AUDITORÍAS (rejilla en orden cronológico) — punto 11 ═════════
@router.get("/cronologia")
def cronologia(institucion_id: int, db: Session = Depends(get_db)):
    """Todos los hitos de la contratación de la institución, ordenados
    cronológicamente — la rejilla que piden las auditorías."""
    cts = {c.id: c.nombre for c in db.query(Contratista).all()}
    hitos = []
    ET_LBL = {"borrador": "📄 Borrador creado + CDP", "documentos": "🗂️ Recolección de documentos",
              "juridica": "⚖️ Enviado a revisión jurídica", "firma": "✍️ Habilitado para firmas + RP",
              "firmado": "✅ Contrato firmado", "ejecucion": "🚚 Inicio de ejecución",
              "liquidado": "🏁 Liquidado"}
    for ct in db.query(Contrato).filter(Contrato.institucion_id == institucion_id).all():
        nom = cts.get(ct.contratista_id, "—")
        try:
            etapas = json.loads(ct.etapas_fechas) if ct.etapas_fechas else {}
        except Exception:
            etapas = {}
        for etapa, f in etapas.items():
            hitos.append({"fecha": f, "contrato": ct.numero, "contratista": nom,
                          "hito": ET_LBL.get(etapa, etapa), "detalle": ct.objeto[:60],
                          "valor": round(ct.valor)})
        try:
            for q in (json.loads(ct.cotizaciones) if ct.cotizaciones else []):
                hitos.append({"fecha": q.get("fecha"), "contrato": ct.numero, "contratista": q.get("proveedor", nom),
                              "hito": "💬 Cotización recibida", "detalle": q.get("archivo") or "",
                              "valor": round(q.get("valor") or 0)})
        except Exception:
            pass
        try:
            firmas = json.loads(ct.firmas) if ct.firmas else []
            for f in firmas:
                if f.get("firmado") and f.get("fecha"):
                    hitos.append({"fecha": f["fecha"][:10], "contrato": ct.numero, "contratista": nom,
                                  "hito": f"✍️ Firma de {f.get('rol')}", "detalle": f.get("nombre", ""),
                                  "valor": None})
        except Exception:
            pass
        try:
            cc = json.loads(ct.cuenta_cobro) if ct.cuenta_cobro else None
            if cc:
                hitos.append({"fecha": cc.get("fecha"), "contrato": ct.numero, "contratista": nom,
                              "hito": "🧾 Cuenta de cobro " + cc.get("estado", ""), "detalle": cc.get("numero", ""),
                              "valor": round(cc.get("valor") or 0)})
        except Exception:
            pass
    hitos = [h for h in hitos if h["fecha"]]
    hitos.sort(key=lambda x: x["fecha"])
    return hitos


# ═════════ ANÁLISIS LEGAL DE PRECIOS (puntos 16 y 18) ═════════
# Precios máximos de referencia del mercado público (simulado, tipo Colombia
# Compra Eficiente). Si el contrato excede el techo, el sistema lo advierte
# ANTES de firmar — así el rector no queda expuesto en una auditoría.
PRECIOS_REFERENCIA = {
    "suministro": {"label": "Suministro de bienes", "unitario_max": 250000,
                   "nota": "Precio unitario promedio de mercado para papelería/dotación."},
    "servicio": {"label": "Prestación de servicios", "unitario_max": 4500000,
                 "nota": "Honorario mensual máximo sugerido para servicios de apoyo."},
    "obra": {"label": "Obra menor", "unitario_max": 12000000,
             "nota": "Valor máximo por frente de obra menor sin licitación."},
    "pae": {"label": "Alimentación escolar", "unitario_max": 6500,
            "nota": "Costo máximo por ración servida (referencia PAE)."},
}


class AnalisisPrecioIn(BaseModel):
    institucion_id: int
    tipo_contrato: str
    valor: float
    cantidad: int | None = 1
    objeto: str | None = ""


@router.post("/analisis_precio")
def analisis_precio(payload: AnalisisPrecioIn, db: Session = Depends(get_db)):
    """Antes de celebrar el contrato: ¿el precio está dentro de lo legalmente
    defendible? Compara contra el tope SMMLV y contra el precio de referencia."""
    smmlv, tope = _smmlv(db)
    tipo = payload.tipo_contrato if payload.tipo_contrato in PRECIOS_REFERENCIA else "suministro"
    ref = PRECIOS_REFERENCIA[tipo]
    cant = max(1, payload.cantidad or 1)
    unitario = payload.valor / cant
    tope_cop = tope * smmlv
    hallazgos = []
    nivel = "ok"
    if payload.valor > tope_cop:
        nivel = "critico"
        hallazgos.append({"tipo": "critico",
                          "texto": f"El valor ${payload.valor:,.0f} SUPERA el tope de {tope:.0f} SMMLV (${tope_cop:,.0f}) del régimen especial de los Fondos de Servicios Educativos. Requiere otro procedimiento contractual.".replace(",", ".")})
    elif payload.valor > tope_cop * 0.9:
        nivel = "alerta"
        hallazgos.append({"tipo": "alerta",
                          "texto": f"El valor está al {round(100*payload.valor/tope_cop)}% del tope legal. Documenta muy bien la justificación."})
    if unitario > ref["unitario_max"]:
        exceso = round(100 * (unitario / ref["unitario_max"] - 1))
        nivel = "critico" if exceso > 30 else ("alerta" if nivel == "ok" else nivel)
        hallazgos.append({"tipo": "critico" if exceso > 30 else "alerta",
                          "texto": f"El precio unitario (${unitario:,.0f}) está {exceso}% POR ENCIMA del precio de referencia (${ref['unitario_max']:,.0f}). {ref['nota']} Justifica con cotizaciones o ajusta el valor.".replace(",", ".")})
    n_cot = 0
    if not hallazgos:
        hallazgos.append({"tipo": "ok", "texto": "El valor está dentro de los límites legales y del precio de referencia del mercado. Contrato defendible ante auditoría."})
    return {"ok": True, "nivel": nivel, "unitario": round(unitario),
            "referencia": ref["unitario_max"], "tope_cop": round(tope_cop),
            "tope_smmlv": tope, "valor_smmlv": round(payload.valor / smmlv, 2),
            "hallazgos": hallazgos, "n_cotizaciones": n_cot,
            "recomendacion": ("Solicita al menos 3 cotizaciones y deja el estudio de mercado en el expediente."
                              if nivel != "ok" else "Adjunta las cotizaciones al expediente y continúa.")}


# ═════════ VALIDACIÓN DE LÓGICA DEL CONTRATO (punto 22 — abogado) ═════════
# Diccionario de coherencia: qué palabras deben aparecer en el objeto según el
# tipo, y qué combinaciones son incoherentes (comprar veneno con papelería).
CATEGORIAS_OBJETO = {
    "papeleria": ["papel", "resma", "lapiz", "lápiz", "cuaderno", "marcador", "tinta", "toner", "útiles", "utiles"],
    "alimentos": ["alimento", "refrigerio", "ración", "racion", "comida", "pae", "mercado", "leche"],
    "quimicos": ["veneno", "plaguicida", "insecticida", "químic", "quimic", "ácido", "acido", "pesticida"],
    "construccion": ["obra", "cemento", "ladrillo", "pintura", "baño", "bano", "techo", "reparación", "reparacion", "mantenimiento"],
    "tecnologia": ["computador", "portátil", "portatil", "internet", "software", "impresora", "tablet"],
    "servicios": ["servicio", "apoyo", "vigilancia", "aseo", "capacitación", "capacitacion", "asesoría", "asesoria"],
}
INCOMPATIBLES = [("quimicos", "alimentos"), ("quimicos", "papeleria")]


def _categorias(texto):
    t = (texto or "").lower()
    return {cat for cat, kws in CATEGORIAS_OBJETO.items() if any(k in t for k in kws)}


class ValidarLogicaIn(BaseModel):
    contrato_id: int
    items: list | None = None   # [{descripcion, cantidad, valor}] opcional


@router.post("/validar_logica")
def validar_logica(payload: ValidarLogicaIn, db: Session = Depends(get_db)):
    """Revisión jurídica automática: ¿el objeto del contrato es coherente con
    lo que se está comprando y con la actividad registrada del contratista?"""
    ct = db.query(Contrato).filter(Contrato.id == payload.contrato_id).first()
    if not ct:
        return {"ok": False, "msg": "Contrato no encontrado."}
    prov = db.query(Contratista).filter(Contratista.id == ct.contratista_id).first()
    hallazgos = []
    cats_objeto = _categorias(ct.objeto)

    # 1) coherencia objeto ↔ ítems
    items = payload.items or []
    for it in items[:20]:
        desc = str(it.get("descripcion", "")) if isinstance(it, dict) else str(it)
        cats_item = _categorias(desc)
        if not cats_item:
            continue
        for a in cats_objeto:
            for b in cats_item:
                if (a, b) in INCOMPATIBLES or (b, a) in INCOMPATIBLES:
                    hallazgos.append({"tipo": "critico",
                                      "texto": f"INCOHERENCIA GRAVE: el objeto del contrato es de «{a}» pero se está incluyendo «{desc[:50]}» ({b}). Esto es un hallazgo directo en auditoría."})
        if cats_objeto and not (cats_item & cats_objeto):
            hallazgos.append({"tipo": "alerta",
                              "texto": f"El ítem «{desc[:50]}» no parece corresponder al objeto contratado. Verifica o justifica su inclusión."})

    # 2) coherencia con actividad de Cámara de Comercio (CIIU)
    tipo_c = ct.tipo_contrato or "suministro"
    ciiu_ok = CIIU_POR_TIPO.get(tipo_c, [])
    ciiu_prov = (prov.ciiu if prov and getattr(prov, "ciiu", None) else None)
    if ciiu_prov:
        if ciiu_prov not in ciiu_ok:
            hallazgos.append({"tipo": "alerta",
                              "texto": f"El código CIIU del contratista ({ciiu_prov}) no está entre los esperados para un contrato de {tipo_c} ({', '.join(ciiu_ok)}). Verifica en Cámara de Comercio que su actividad cubra este objeto."})
        else:
            hallazgos.append({"tipo": "ok", "texto": f"CIIU {ciiu_prov} del contratista corresponde a la actividad de {tipo_c}. ✔"})
    else:
        hallazgos.append({"tipo": "alerta",
                          "texto": "El contratista no tiene registrado su código CIIU. Pídelo en la Cámara de Comercio para validar que su actividad cubra el objeto."})

    # 3) documentos vencidos
    if prov:
        docs, completos, faltan = _docs(prov)
        venc = [d["label"] for d in docs if d.get("vencido")]
        porv = [f"{d['label']} ({d['dias_restantes']}d)" for d in docs if d.get("por_vencer")]
        if venc:
            hallazgos.append({"tipo": "critico", "texto": f"Documentos VENCIDOS: {', '.join(venc)}. No se puede firmar hasta renovarlos."})
        if porv:
            hallazgos.append({"tipo": "alerta", "texto": f"Documentos por vencer: {', '.join(porv)}. Renuévalos antes de la ejecución."})
        if faltan and not venc:
            hallazgos.append({"tipo": "alerta", "texto": f"Faltan documentos: {', '.join(faltan)}."})

    # 4) soportes de precio
    try:
        cot = json.loads(ct.cotizaciones) if ct.cotizaciones else []
    except Exception:
        cot = []
    if len(cot) < 2:
        hallazgos.append({"tipo": "alerta",
                          "texto": f"Solo hay {len(cot)} cotización(es) en el expediente. La buena práctica exige mínimo 3 para soportar el estudio de mercado."})
    else:
        hallazgos.append({"tipo": "ok", "texto": f"{len(cot)} cotizaciones en el expediente para soportar el precio. ✔"})

    criticos = sum(1 for h in hallazgos if h["tipo"] == "critico")
    alertas = sum(1 for h in hallazgos if h["tipo"] == "alerta")
    concepto = ("DESFAVORABLE — debe corregirse antes de continuar" if criticos else
                ("FAVORABLE CON OBSERVACIONES" if alertas else "FAVORABLE"))
    metadatos.registrar_evento("VALIDACION_JURIDICA", "Jurídica", institucion_id=ct.institucion_id,
                               payload={"contrato": ct.numero, "criticos": criticos})
    return {"ok": True, "contrato": ct.numero, "concepto": concepto,
            "criticos": criticos, "alertas": alertas, "hallazgos": hallazgos}


# ═════════ DOCUMENTOS POR VENCER — TABLERO DE ALERTAS (punto 21) ═════════
@router.get("/documentos_alertas")
def documentos_alertas(db: Session = Depends(get_db)):
    """Qué contratistas tienen documentos vencidos o próximos a vencer."""
    out = []
    for c in db.query(Contratista).all():
        docs, completos, faltan = _docs(c)
        venc = [d for d in docs if d.get("vencido")]
        porv = [d for d in docs if d.get("por_vencer")]
        if venc or porv:
            out.append({"id": c.id, "nombre": c.nombre, "nit": c.nit,
                        "telefono": c.telefono,
                        "vencidos": [{"label": d["label"], "fecha": d["fecha"]} for d in venc],
                        "por_vencer": [{"label": d["label"], "dias": d["dias_restantes"]} for d in porv]})
    out.sort(key=lambda x: (-len(x["vencidos"]), -len(x["por_vencer"])))
    return out


class RecordarDocsIn(BaseModel):
    contratista_id: int


@router.post("/documentos_alertas/recordar")
def recordar_docs(payload: RecordarDocsIn, db: Session = Depends(get_db)):
    c = db.query(Contratista).filter(Contratista.id == payload.contratista_id).first()
    if not c:
        return {"ok": False, "msg": "Contratista no encontrado."}
    docs, _, faltan = _docs(c)
    venc = [d["label"] for d in docs if d.get("vencido") or d.get("por_vencer")]
    lista = ", ".join(venc + faltan) or "sus documentos"
    db.add(MensajeWhatsApp(
        destinatario=c.nombre, telefono=c.telefono or "—",
        contenido=(f"Buen día. Para mantener su expediente vigente ante la institución, "
                   f"por favor actualice: {lista}. Puede cargarlos en su portal. — Oficina de Contratación"),
        fecha=datetime.now(), estado="ENVIADO (simulado)", contexto="vencimiento"))
    db.commit()
    return {"ok": True, "msg": f"📱 Recordatorio enviado (simulado) a {c.nombre}: {lista}."}


# ═════════ PAGOS CON EVIDENCIA (punto 27) ═════════
from models import PagoContrato as _Pago


@router.get("/pagos")
def pagos(institucion_id: int, db: Session = Depends(get_db)):
    """Lo que el rector ve: qué está pendiente de pago y qué ya se pagó (con
    su evidencia adjunta)."""
    filas = db.query(_Pago).filter(_Pago.institucion_id == institucion_id).order_by(
        _Pago.estado.desc(), _Pago.id.desc()).all()
    cts = {c.id: c for c in db.query(Contrato).all()}
    provs = {c.id: c.nombre for c in db.query(Contratista).all()}
    out = []
    for p in filas:
        ct = cts.get(p.contrato_id)
        out.append({"id": p.id, "contrato": ct.numero if ct else "—",
                    "contrato_id": p.contrato_id,
                    "contratista": provs.get(ct.contratista_id) if ct else "—",
                    "concepto": p.concepto, "valor": round(p.valor), "estado": p.estado,
                    "fecha_programada": p.fecha_programada.isoformat() if p.fecha_programada else None,
                    "fecha_pago": p.fecha_pago.isoformat() if p.fecha_pago else None,
                    "metodo": p.metodo, "evidencia": p.evidencia, "nota": p.nota})
    pend = [p for p in out if p["estado"] == "pendiente"]
    return {"pagos": out, "n_pendientes": len(pend),
            "total_pendiente": sum(p["valor"] for p in pend),
            "total_pagado": sum(p["valor"] for p in out if p["estado"] == "pagado")}


class PagoIn(BaseModel):
    id: int | None = 0
    contrato_id: int
    institucion_id: int
    concepto: str
    valor: float
    fecha_programada: str | None = None


@router.post("/pagos/guardar")
def pago_guardar(payload: PagoIn, db: Session = Depends(get_db)):
    if payload.id:
        p = db.query(_Pago).filter(_Pago.id == payload.id).first()
        if not p:
            return {"ok": False, "msg": "Pago no encontrado."}
    else:
        p = _Pago(contrato_id=payload.contrato_id, institucion_id=payload.institucion_id)
        db.add(p)
    p.concepto = payload.concepto.strip()[:120] or "Pago de contrato"
    p.valor = max(0, payload.valor)
    if payload.fecha_programada:
        try:
            p.fecha_programada = date.fromisoformat(payload.fecha_programada)
        except ValueError:
            pass
    db.commit()
    return {"ok": True, "id": p.id, "msg": "Pago programado."}


class MarcarPagoIn(BaseModel):
    id: int
    metodo: str | None = "Transferencia"
    evidencia: str | None = None
    nota: str | None = ""


@router.post("/pagos/marcar_pagado")
def pago_marcar(payload: MarcarPagoIn, db: Session = Depends(get_db)):
    """El rector marca el pago y ANEXA la evidencia; el egreso entra al FSE."""
    p = db.query(_Pago).filter(_Pago.id == payload.id).first()
    if not p:
        return {"ok": False, "msg": "Pago no encontrado."}
    if p.estado == "pagado":
        return {"ok": False, "msg": "Este pago ya estaba marcado como pagado."}
    if not payload.evidencia:
        return {"ok": False, "msg": "📎 Debes adjuntar la evidencia del pago (comprobante o transferencia) antes de marcarlo. Sin soporte no pasa una auditoría."}
    p.estado = "pagado"
    p.fecha_pago = date.today()
    p.metodo = payload.metodo or "Transferencia"
    p.evidencia = payload.evidencia
    p.nota = (payload.nota or "").strip()[:200] or None
    ct = db.query(Contrato).filter(Contrato.id == p.contrato_id).first()
    prov = db.query(Contratista).filter(Contratista.id == ct.contratista_id).first() if ct else None
    db.add(MovimientoFSE(institucion_id=p.institucion_id, fecha=date.today(), tipo="egreso",
                         cuenta_codigo="1510",
                         concepto=f"{p.concepto} · {ct.numero if ct else ''}",
                         proveedor=prov.nombre if prov else "", nit=prov.nit if prov else "",
                         valor=p.valor, metodo=p.metodo, comprobante=p.evidencia,
                         estado="pagado", soporte=p.evidencia))
    db.commit()
    metadatos.registrar_evento("PAGO_REALIZADO", "Rectoría", institucion_id=p.institucion_id,
                               payload={"valor": p.valor, "contrato": ct.numero if ct else ""})
    return {"ok": True, "msg": f"💸 Pago marcado con evidencia «{p.evidencia}». El egreso quedó registrado en el libro del FSE con su soporte."}


# ═════════ PORTAL DEL CONTRATISTA: PROPUESTAS (punto 19) ═════════
class PropuestaIn(BaseModel):
    token: str
    valor: float | None = 0
    descripcion: str | None = ""
    archivos: list | None = None


@router.get("/portal/validar")
def portal_validar(token: str, db: Session = Depends(get_db)):
    """El contratista entra con su link único: ve qué le falta y puede subir
    documentos y su propuesta."""
    c = db.query(Contratista).filter(Contratista.portal_token == token).first()
    if not c:
        return {"ok": False, "msg": "Enlace no válido o vencido."}
    docs, completos, faltan = _docs(c)
    cts = db.query(Contrato).filter(Contrato.contratista_id == c.id).all()
    try:
        props = json.loads(c.propuestas) if c.propuestas else []
    except Exception:
        props = []
    return {"ok": True, "id": c.id, "nombre": c.nombre, "nit": c.nit, "tipo": c.tipo,
            "documentos": docs, "completos": completos, "faltantes": faltan,
            "propuestas": props,
            "contratos": [{"numero": x.numero, "objeto": x.objeto, "estado": x.estado,
                           "valor": round(x.valor)} for x in cts]}


class PortalSubirIn(BaseModel):
    token: str
    clave: str
    archivo: str


@router.post("/portal/subir_documento")
def portal_subir(payload: PortalSubirIn, db: Session = Depends(get_db)):
    c = db.query(Contratista).filter(Contratista.portal_token == payload.token).first()
    if not c:
        return {"ok": False, "msg": "Enlace no válido."}
    try:
        d = json.loads(c.documentos) if c.documentos else {}
    except Exception:
        d = {}
    d[payload.clave] = {"ok": True, "archivo": payload.archivo[:80],
                        "fecha": date.today().isoformat()}
    c.documentos = json.dumps(d, ensure_ascii=False)
    n_ok = sum(1 for v in d.values() if _doc_norm(v)["ok"])
    c.confianza = min(100, 30 + 7 * n_ok + (12 if c.contratado_anio > 0 else 0))
    db.commit()
    lbl = dict(DOCS_LABELS).get(payload.clave, payload.clave)
    return {"ok": True, "msg": f"📥 «{lbl}» recibido. La institución ya lo ve en tu expediente."}


@router.post("/portal/propuesta")
def portal_propuesta(payload: PropuestaIn, db: Session = Depends(get_db)):
    c = db.query(Contratista).filter(Contratista.portal_token == payload.token).first()
    if not c:
        return {"ok": False, "msg": "Enlace no válido."}
    try:
        props = json.loads(c.propuestas) if c.propuestas else []
    except Exception:
        props = []
    archivos = [str(a)[:80] for a in (payload.archivos or [])][:8]
    props.append({"fecha": date.today().isoformat(), "valor": round(payload.valor or 0),
                  "descripcion": (payload.descripcion or "")[:400], "archivos": archivos,
                  "estado": "recibida"})
    c.propuestas = json.dumps(props, ensure_ascii=False)
    db.commit()
    metadatos.registrar_evento("PROPUESTA_RECIBIDA", "Contratista",
                               payload={"contratista": c.nombre[:30], "valor": payload.valor})
    return {"ok": True, "msg": f"✅ Propuesta enviada por ${(payload.valor or 0):,.0f} con {len(archivos)} archivo(s). La institución la revisará.".replace(",", ".")}


@router.get("/propuestas")
def propuestas(db: Session = Depends(get_db)):
    """Bandeja de propuestas recibidas por el portal (la ve contratación)."""
    out = []
    for c in db.query(Contratista).all():
        try:
            props = json.loads(c.propuestas) if c.propuestas else []
        except Exception:
            props = []
        for p in props:
            out.append({"contratista": c.nombre, "contratista_id": c.id, "nit": c.nit, **p})
    out.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    return out


# ═════════ FIRMA: recordatorio masivo por WhatsApp (punto 23) ═════════
@router.post("/firmas/recordar")
def firmas_recordar(payload: IdIn, db: Session = Depends(get_db)):
    ct = db.query(Contrato).filter(Contrato.id == payload.id).first()
    if not ct:
        return {"ok": False, "msg": "Contrato no encontrado."}
    try:
        firmas = json.loads(ct.firmas) if ct.firmas else []
    except Exception:
        firmas = []
    pendientes = [f for f in firmas if not f.get("firmado")]
    if not pendientes:
        return {"ok": False, "msg": "Todas las firmas ya están completas ✅"}
    prov = db.query(Contratista).filter(Contratista.id == ct.contratista_id).first()
    enviados = []
    for f in pendientes:
        tel = prov.telefono if (f.get("rol") == "Contratista" and prov) else "—"
        db.add(MensajeWhatsApp(
            destinatario=f"{f.get('nombre','')} ({f.get('rol','')})", telefono=tel,
            contenido=(f"Recordatorio: el contrato {ct.numero} «{ct.objeto[:50]}» está pendiente de su "
                       "firma digital con verificación de identidad (código OTP + huella si está disponible). "
                       "Ingrese al sistema para firmarlo. — Oficina de Contratación"),
            fecha=datetime.now(), estado="ENVIADO (simulado)", contexto="firma"))
        enviados.append(f.get("rol", ""))
    db.commit()
    metadatos.registrar_evento("RECORDATORIO_FIRMA", "Contratación", institucion_id=ct.institucion_id,
                               payload={"contrato": ct.numero, "n": len(enviados)})
    return {"ok": True, "msg": f"📱 Recordatorio de firma enviado (simulado) a {len(enviados)} pendiente(s): {', '.join(enviados)}. Incluye enlace de firma con OTP y verificación biométrica."}


# ═════════ PLANILLA EXPORTABLE (punto 16) ═════════
from fastapi.responses import PlainTextResponse


@router.get("/planilla.csv", response_class=PlainTextResponse)
def planilla_csv(institucion_id: int, db: Session = Depends(get_db)):
    """Planilla de contratación en CSV: se abre en Excel y sirve de anexo
    directo para la auditoría."""
    import csv
    import io
    provs = {c.id: c for c in db.query(Contratista).all()}
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["N° Contrato", "Tipo", "Objeto", "Contratista", "NIT", "Valor",
                "SMMLV", "CDP", "RP", "Estado", "Fecha inicio", "Docs completos",
                "Cotizaciones", "Cuenta de cobro", "Estado cuenta"])
    smmlv, _ = _smmlv(db)
    for ct in db.query(Contrato).filter(Contrato.institucion_id == institucion_id).order_by(Contrato.numero).all():
        p = provs.get(ct.contratista_id)
        docs, completos, _f = _docs(p) if p else ([], False, [])
        try:
            cot = json.loads(ct.cotizaciones) if ct.cotizaciones else []
        except Exception:
            cot = []
        try:
            cc = json.loads(ct.cuenta_cobro) if ct.cuenta_cobro else None
        except Exception:
            cc = None
        w.writerow([ct.numero, TIPO_LBL.get(ct.tipo_contrato or "suministro", ""), ct.objeto,
                    p.nombre if p else "", p.nit if p else "", round(ct.valor),
                    round(ct.valor / smmlv, 2), ct.cdp_num or "", ct.rp_num or "",
                    ct.estado, ct.fecha.isoformat() if ct.fecha else "",
                    "SÍ" if completos else "NO", len(cot),
                    (cc or {}).get("numero", ""), (cc or {}).get("estado", "")])
    return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=planilla_contratacion.csv"})


# ═════════ SECOP I y II: publicar el contrato (punto 33) ═════════
from models import (PublicacionSECOP as _Secop, FirmaObservador as _FirmaObs,
                    ObservadorEntrada, Personal, Estudiante)

MODALIDADES = {
    "minima_cuantia": "Mínima cuantía (hasta 10% de la menor cuantía)",
    "seleccion_abreviada": "Selección abreviada",
    "contratacion_directa": "Contratación directa",
    "regimen_especial": "Régimen especial FSE (Decreto 4791/2008)",
}


@router.get("/secop")
def secop_listar(institucion_id: int, db: Session = Depends(get_db)):
    """Estado de publicación en SECOP de cada contrato."""
    cts = db.query(Contrato).filter(Contrato.institucion_id == institucion_id).all()
    provs = {c.id: c.nombre for c in db.query(Contratista).all()}
    out = []
    for ct in cts:
        pubs = db.query(_Secop).filter(_Secop.contrato_id == ct.id).all()
        docs, completos, faltan = ([], False, [])
        p = db.query(Contratista).filter(Contratista.id == ct.contratista_id).first()
        if p:
            docs, completos, faltan = _docs(p)
        out.append({
            "id": ct.id, "numero": ct.numero, "objeto": ct.objeto,
            "valor": round(ct.valor), "estado": ct.estado,
            "contratista": provs.get(ct.contratista_id, "—"),
            "docs_completos": completos, "faltantes": faltan,
            "publicaciones": [{"id": x.id, "plataforma": x.plataforma,
                               "numero_proceso": x.numero_proceso, "estado": x.estado,
                               "modalidad": x.modalidad, "url": x.url,
                               "fecha": x.fecha_publicacion.isoformat(sep=" ", timespec="minutes") if x.fecha_publicacion else None}
                              for x in pubs],
            "publicable": ct.estado in ("firmado", "ejecucion", "liquidado") and completos,
        })
    return {"contratos": out, "modalidades": [{"id": k, "label": v} for k, v in MODALIDADES.items()]}


class PublicarIn(BaseModel):
    contrato_id: int
    plataforma: str = "secop2"       # secop1 | secop2 | ambos
    modalidad: str | None = "regimen_especial"


@router.post("/secop/publicar")
def secop_publicar(payload: PublicarIn, db: Session = Depends(get_db)):
    """Publica el contrato en SECOP (simulado). Valida antes de dejar publicar."""
    ct = db.query(Contrato).filter(Contrato.id == payload.contrato_id).first()
    if not ct:
        return {"ok": False, "msg": "Contrato no encontrado."}
    p = db.query(Contratista).filter(Contratista.id == ct.contratista_id).first()
    if not p:
        return {"ok": False, "msg": "El contrato no tiene contratista asignado."}
    docs, completos, faltan = _docs(p)
    venc = [d["label"] for d in docs if d.get("vencido")]
    if venc:
        return {"ok": False, "msg": f"⛔ No se puede publicar: documentos VENCIDOS ({', '.join(venc)}). Renuévalos primero."}
    if not completos:
        return {"ok": False, "msg": f"⛔ Faltan documentos del contratista: {', '.join(faltan)}."}
    if ct.estado not in ("firmado", "ejecucion", "liquidado"):
        return {"ok": False, "msg": f"El contrato está en «{ct.estado}». Se publica en SECOP una vez firmado."}
    if not ct.cdp_num or not ct.rp_num:
        return {"ok": False, "msg": "⛔ SECOP exige CDP y RP. Complétalos antes de publicar."}

    plataformas = ["secop1", "secop2"] if payload.plataforma == "ambos" else [payload.plataforma]
    creadas = []
    for plat in plataformas:
        ya = db.query(_Secop).filter(_Secop.contrato_id == ct.id,
                                     _Secop.plataforma == plat,
                                     _Secop.estado == "publicado").first()
        if ya:
            continue
        n = db.query(_Secop).count() + 1
        anio = date.today().year
        num = f"{'SI' if plat == 'secop1' else 'SII'}-{anio}-{n:05d}"
        anexos = [d["archivo"] for d in docs if d.get("archivo")]
        anexos += ["minuta_contrato.pdf", "estudios_previos.pdf",
                   f"cdp_{ct.cdp_num}.pdf", f"rp_{ct.rp_num}.pdf"]
        pub = _Secop(
            contrato_id=ct.id, plataforma=plat, numero_proceso=num,
            modalidad=payload.modalidad or "regimen_especial",
            url=(f"https://www.contratos.gov.co/consultas/detalleProceso.do?numConstancia={num}"
                 if plat == "secop1" else
                 f"https://community.secop.gov.co/Public/Tendering/OpportunityDetail/Index?noticeUID={num}"),
            estado="publicado", fecha_publicacion=datetime.now(),
            documentos=json.dumps(anexos, ensure_ascii=False),
            respuesta=json.dumps({"recibido": True, "constancia": num,
                                  "anexos": len(anexos)}, ensure_ascii=False))
        db.add(pub)
        creadas.append((plat, num))
    if not creadas:
        return {"ok": False, "msg": "Este contrato ya está publicado en esa plataforma."}
    db.commit()
    metadatos.registrar_evento("SECOP_PUBLICADO", "Contratación",
                               institucion_id=ct.institucion_id,
                               payload={"contrato": ct.numero, "n": len(creadas)})
    lbl = ", ".join(f"{'SECOP I' if p == 'secop1' else 'SECOP II'} ({n})" for p, n in creadas)
    return {"ok": True, "msg": f"📤 Publicado en {lbl}. Se enviaron los documentos del expediente y los soportes presupuestales."}


# ═════════ PIPELINE DETALLADO: qué se cumplió en cada etapa (punto 34) ═════════
REQUISITOS_ETAPA = {
    "borrador": [("objeto", "Objeto del contrato definido"),
                 ("valor", "Valor establecido"),
                 ("cdp", "CDP expedido"),
                 ("tipo", "Tipo de contrato seleccionado")],
    "documentos": [("contratista", "Contratista asignado"),
                   ("docs", "Expediente documental completo"),
                   ("vigencia", "Documentos vigentes (no vencidos)"),
                   ("cotizaciones", "Mínimo 2 cotizaciones")],
    "juridica": [("revision", "Revisión jurídica realizada"),
                 ("concepto", "Concepto emitido"),
                 ("ciiu", "Actividad del contratista verificada")],
    "firma": [("rp", "RP expedido"),
              ("minuta", "Minuta elaborada")],
    "firmado": [("firmas", "Todas las firmas recogidas")],
    "ejecucion": [("secop", "Publicado en SECOP"),
                  ("supervisor", "Supervisor designado")],
    "liquidado": [("pagos", "Pagos al día"),
                  ("acta", "Acta de liquidación"),
                  ("paz_salvo", "Paz y salvo del contratista")],
}


@router.get("/pipeline_detalle")
def pipeline_detalle(contrato_id: int, db: Session = Depends(get_db)):
    """Qué requisito de cada etapa está cumplido y cuál falta."""
    ct = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not ct:
        return {"ok": False, "msg": "Contrato no encontrado."}
    p = db.query(Contratista).filter(Contratista.id == ct.contratista_id).first()
    docs, completos, faltan = _docs(p) if p else ([], False, ["contratista"])
    venc = [d for d in docs if d.get("vencido")]
    try:
        cot = json.loads(ct.cotizaciones) if ct.cotizaciones else []
    except Exception:
        cot = []
    try:
        firmas = json.loads(ct.firmas) if ct.firmas else []
    except Exception:
        firmas = []
    try:
        etapas_f = json.loads(ct.etapas_fechas) if ct.etapas_fechas else {}
    except Exception:
        etapas_f = {}
    pubs = db.query(_Secop).filter(_Secop.contrato_id == ct.id,
                                   _Secop.estado == "publicado").count()
    pagos = db.query(_Pago).filter(_Pago.contrato_id == ct.id).all()
    CUMPLE = {
        "objeto": bool(ct.objeto), "valor": ct.valor > 0, "cdp": bool(ct.cdp_num),
        "tipo": bool(ct.tipo_contrato),
        "contratista": bool(p), "docs": completos, "vigencia": len(venc) == 0,
        "cotizaciones": len(cot) >= 2,
        "revision": bool(ct.nota_juridica), "concepto": bool(ct.nota_juridica),
        "ciiu": bool(getattr(p, "ciiu", None)) if p else False,
        "rp": bool(ct.rp_num), "minuta": True,
        "firmas": bool(firmas) and all(f.get("firmado") for f in firmas),
        "secop": pubs > 0, "supervisor": True,
        "pagos": bool(pagos) and all(x.estado == "pagado" for x in pagos),
        "acta": ct.estado == "liquidado", "paz_salvo": ct.estado == "liquidado",
    }
    idx_actual = PIPELINE.index(ct.estado) if ct.estado in PIPELINE else 0
    etapas = []
    for i, et in enumerate(PIPELINE):
        reqs = REQUISITOS_ETAPA.get(et, [])
        filas = [{"clave": k, "label": l, "cumple": bool(CUMPLE.get(k))} for k, l in reqs]
        pendientes = [f["label"] for f in filas if not f["cumple"]]
        etapas.append({
            "etapa": et, "orden": i + 1,
            "estado": "completada" if i < idx_actual else "actual" if i == idx_actual else "pendiente",
            "fecha": etapas_f.get(et),
            "requisitos": filas,
            "n_cumplidos": sum(1 for f in filas if f["cumple"]),
            "n_total": len(filas),
            "pendientes": pendientes,
            "bloqueada": bool(pendientes) and i == idx_actual,
        })
    # ¿puede avanzar? (punto 36)
    actual = etapas[idx_actual] if idx_actual < len(etapas) else None
    bloqueos = actual["pendientes"] if actual else []
    criticos = [b for b in bloqueos if "vigente" in b.lower() or "vencid" in b.lower()
                or "expediente" in b.lower() or "RP" in b or "CDP" in b]
    return {
        "ok": True, "contrato": ct.numero, "estado": ct.estado,
        "etapas": etapas, "etapa_actual": ct.estado,
        "puede_avanzar": len(bloqueos) == 0,
        "bloqueos": bloqueos, "bloqueos_criticos": criticos,
        "requiere_autorizacion": len(bloqueos) > 0 and len(criticos) == 0,
        "documentos_vencidos": [d["label"] for d in venc],
    }


class AvanzarForzadoIn(BaseModel):
    id: int
    acepto_riesgo: bool = False
    justificacion: str | None = ""


@router.post("/avanzar_validado")
def avanzar_validado(payload: AvanzarForzadoIn, db: Session = Depends(get_db)):
    """Avanza de etapa solo si se cumplen los requisitos.

    Si falta algo NO crítico, deja avanzar con autorización expresa y deja la
    justificación registrada. Si hay documentos vencidos o falta CDP/RP, no
    deja pasar de ninguna forma (punto 36).
    """
    det = pipeline_detalle(payload.id, db)
    if not det.get("ok"):
        return det
    ct = db.query(Contrato).filter(Contrato.id == payload.id).first()
    if det["bloqueos_criticos"]:
        return {"ok": False,
                "msg": f"⛔ No se puede avanzar: {'; '.join(det['bloqueos_criticos'])}. Esto no se puede saltar: es lo que revisa la Contraloría."}
    if det["bloqueos"] and not payload.acepto_riesgo:
        return {"ok": False, "requiere_autorizacion": True,
                "bloqueos": det["bloqueos"],
                "msg": f"⚠️ Falta: {'; '.join(det['bloqueos'])}. Puedes avanzar bajo tu responsabilidad, dejando la justificación por escrito."}
    i = PIPELINE.index(ct.estado) if ct.estado in PIPELINE else 0
    if i >= len(PIPELINE) - 1:
        return {"ok": False, "msg": "El contrato ya está liquidado."}
    sig = PIPELINE[i + 1]
    ct.estado = sig
    try:
        et = json.loads(ct.etapas_fechas) if ct.etapas_fechas else {}
    except Exception:
        et = {}
    et[sig] = date.today().isoformat()
    ct.etapas_fechas = json.dumps(et)
    nota = ""
    if payload.acepto_riesgo and det["bloqueos"]:
        nota = f" [AVANCE AUTORIZADO con pendientes: {'; '.join(det['bloqueos'])}. Justificación: {payload.justificacion or 'no indicada'}]"
        ct.nota_juridica = ((ct.nota_juridica or "") + nota)[:500]
    db.commit()
    metadatos.registrar_evento("CONTRATO_AVANCE_VALIDADO", "Contratación",
                               institucion_id=ct.institucion_id,
                               payload={"contrato": ct.numero, "a": sig,
                                        "forzado": bool(payload.acepto_riesgo)})
    return {"ok": True, "estado": sig,
            "msg": f"{ct.numero} avanzó a «{sig}»." + (" Quedó registrada tu autorización con la justificación." if nota else "")}


# ═════════ CREACIÓN COMPLETA DE CONTRATOS (puntos 35, 37) ═════════
@router.get("/plantillas")
def plantillas(db: Session = Depends(get_db)):
    """Plantillas de contrato con sus requisitos y plazos por tipo."""
    smmlv, tope = _smmlv(db)
    P = [
        {"id": "suministro", "label": "📦 Suministro de bienes",
         "objeto_ejemplo": "Suministro de material didáctico y papelería para la vigencia 2026",
         "obligaciones": ["Entregar los bienes en las fechas pactadas",
                          "Garantizar calidad y reposición por defectos",
                          "Entregar factura electrónica"],
         "plazo_sugerido": 30, "requiere_poliza": False},
        {"id": "servicio", "label": "🛠️ Prestación de servicios",
         "objeto_ejemplo": "Prestación del servicio de aseo y mantenimiento de la planta física",
         "obligaciones": ["Prestar el servicio con personal idóneo",
                          "Aportar planilla de seguridad social mensual",
                          "Cumplir el horario acordado"],
         "plazo_sugerido": 60, "requiere_poliza": True},
        {"id": "obra", "label": "🏗️ Obra menor",
         "objeto_ejemplo": "Mantenimiento y adecuación de baterías sanitarias de la sede principal",
         "obligaciones": ["Ejecutar la obra según especificaciones técnicas",
                          "Aportar materiales de la calidad ofertada",
                          "Entregar la obra a satisfacción del supervisor"],
         "plazo_sugerido": 90, "requiere_poliza": True},
        {"id": "pae", "label": "🍽️ Alimentación escolar",
         "objeto_ejemplo": "Suministro de complemento alimentario para los estudiantes",
         "obligaciones": ["Cumplir las minutas avaladas por nutricionista",
                          "Mantener concepto sanitario vigente",
                          "Entregar en cada sede según cronograma"],
         "plazo_sugerido": 120, "requiere_poliza": True},
    ]
    for x in P:
        x["plazos_etapas"] = PLAZOS.get(x["id"], {})
    return {"plantillas": P, "smmlv": smmlv, "tope_smmlv": tope,
            "tope_cop": round(tope * smmlv),
            "documentos_exigidos": [{"clave": k, "label": l,
                                     "vigencia_dias": DOCS_VIGENCIA.get(k)}
                                    for k, l in DOCS_LABELS]}


class ContratoCompletoIn(BaseModel):
    institucion_id: int
    contratista_id: int | None = None
    tipo_contrato: str = "suministro"
    objeto: str
    valor: float
    plazo_dias: int | None = 30
    obligaciones: list | None = None
    items: list | None = None          # [{descripcion, cantidad, valor_unitario}]
    supervisor: str | None = ""
    plan_id: int | None = None
    cotizaciones: list | None = None
    modalidad: str | None = "regimen_especial"
    fecha_inicio: str | None = None


@router.post("/crear_completo")
def crear_completo(payload: ContratoCompletoIn, db: Session = Depends(get_db)):
    """Crea el contrato con todo: objeto, ítems, plazos, obligaciones y CDP."""
    if not payload.objeto.strip():
        return {"ok": False, "msg": "Escribe el objeto del contrato."}
    if payload.valor <= 0:
        return {"ok": False, "msg": "El valor debe ser mayor a cero."}
    smmlv, tope = _smmlv(db)
    if payload.valor > tope * smmlv:
        return {"ok": False,
                "msg": f"⚖️ El valor supera el tope de {tope:.0f} SMMLV (${tope * smmlv:,.0f}) del régimen especial del FSE.".replace(",", ".")}
    # validar coherencia objeto ↔ ítems antes de crear
    items = []
    total_items = 0
    for it in (payload.items or [])[:40]:
        if not isinstance(it, dict) or not (it.get("descripcion") or "").strip():
            continue
        cant = max(1, int(it.get("cantidad") or 1))
        vu = float(it.get("valor_unitario") or 0)
        items.append({"descripcion": str(it["descripcion"])[:150], "cantidad": cant,
                      "valor_unitario": round(vu), "total": round(cant * vu)})
        total_items += cant * vu
    if items and abs(total_items - payload.valor) > max(1000, payload.valor * 0.02):
        return {"ok": False,
                "msg": f"Los ítems suman ${total_items:,.0f} pero el contrato dice ${payload.valor:,.0f}. Deben coincidir.".replace(",", ".")}
    n = db.query(Contrato).count() + 1
    numero = f"CT-{date.today().year}-{n:03d}"
    cdp = f"CDP-{date.today().year}-{n:03d}"
    prov = db.query(Contratista).filter(Contratista.id == payload.contratista_id).first() if payload.contratista_id else None
    rector = db.query(Personal).filter(Personal.institucion_id == payload.institucion_id,
                                       Personal.rol == "rector").first()
    abogado = db.query(Personal).filter(Personal.institucion_id == payload.institucion_id,
                                        Personal.rol == "abogado").first()
    firmas = [
        {"rol": "Rector(a)", "nombre": rector.nombre if rector else "Rector(a)", "firmado": False, "fecha": None},
        {"rol": "Contratista", "nombre": prov.nombre if prov else "Por asignar", "firmado": False, "fecha": None},
        {"rol": "Jurídica", "nombre": abogado.nombre if abogado else "Jurídica", "firmado": False, "fecha": None},
    ]
    try:
        f0 = date.fromisoformat(payload.fecha_inicio) if payload.fecha_inicio else date.today()
    except ValueError:
        f0 = date.today()
    cot = []
    for q in (payload.cotizaciones or [])[:8]:
        if isinstance(q, dict) and q.get("proveedor"):
            cot.append({"proveedor": str(q["proveedor"])[:80], "valor": float(q.get("valor") or 0),
                        "fecha": str(q.get("fecha") or f0.isoformat())[:10],
                        "archivo": str(q.get("archivo") or "")[:80] or None})
    ct = Contrato(
        institucion_id=payload.institucion_id, contratista_id=payload.contratista_id,
        numero=numero, objeto=payload.objeto.strip()[:200], valor=payload.valor,
        cdp_num=cdp, rp_num=None, fecha=f0, estado="borrador",
        secop_url="https://community.secop.gov.co/",
        firmas=json.dumps(firmas, ensure_ascii=False),
        plan_id=payload.plan_id, tipo_contrato=payload.tipo_contrato,
        etapas_fechas=json.dumps({"borrador": f0.isoformat()}),
        cotizaciones=json.dumps(cot, ensure_ascii=False),
        nota_juridica=None)
    db.add(ct)
    db.flush()
    # guardar items y obligaciones en la nota del contrato (JSON en cuenta_cobro es para pagos)
    detalle = {"items": items, "obligaciones": [str(o)[:200] for o in (payload.obligaciones or [])][:10],
               "plazo_dias": payload.plazo_dias or 30, "supervisor": payload.supervisor or "",
               "modalidad": payload.modalidad or "regimen_especial",
               "fecha_fin_estimada": (f0 + timedelta(days=payload.plazo_dias or 30)).isoformat()}
    ct.objeto = ct.objeto  # sin cambio
    ct.cuenta_cobro = None
    ct.etapas_fechas = json.dumps({"borrador": f0.isoformat(), "_detalle": detalle},
                                  ensure_ascii=False)
    db.commit()
    metadatos.registrar_evento("CONTRATO_CREADO_COMPLETO", "Contratación",
                               institucion_id=payload.institucion_id,
                               payload={"numero": numero, "valor": payload.valor})
    avisos = []
    if not payload.contratista_id:
        avisos.append("Falta asignar el contratista.")
    if len(cot) < 2:
        avisos.append("Se recomiendan mínimo 2 cotizaciones para soportar el precio.")
    return {"ok": True, "id": ct.id, "numero": numero, "cdp": cdp,
            "msg": f"📄 {numero} creado con CDP {cdp} por ${payload.valor:,.0f}.".replace(",", ".")
                   + (" ⚠️ " + " ".join(avisos) if avisos else ""),
            "avisos": avisos}


# ═════════ FIRMA EN LÍNEA DEL OBSERVADOR (punto 23) ═════════
class FirmaObsIn(BaseModel):
    observacion_id: int
    estudiante_id: int
    firmante: str = "alumno"       # alumno | acudiente
    nombre: str | None = ""
    documento: str | None = ""
    comentario: str | None = ""


@router.post("/observador/solicitar_firma")
def obs_solicitar_firma(payload: FirmaObsIn, db: Session = Depends(get_db)):
    """El docente manda a firmar: se genera el código y se envía por WhatsApp."""
    import random as _r
    e = db.query(Estudiante).filter(Estudiante.id == payload.estudiante_id).first()
    if not e:
        return {"ok": False, "msg": "Estudiante no encontrado."}
    codigo = f"{_r.randint(100000, 999999)}"
    f = _FirmaObs(observacion_id=payload.observacion_id, estudiante_id=payload.estudiante_id,
                  firmante=payload.firmante, codigo_otp=codigo, firmado=False)
    db.add(f)
    dest = e.acudiente if payload.firmante == "acudiente" else e.nombre
    db.add(MensajeWhatsApp(
        estudiante_id=e.id, destinatario=dest, telefono=e.telefono,
        contenido=(f"Su código para firmar la anotación del observador de {e.nombre.split()[0]} "
                   f"es: {codigo}. Válido por 24 horas. — Institución Educativa"),
        fecha=datetime.now(), estado="ENVIADO (simulado)", contexto="firma_observador"))
    db.commit()
    return {"ok": True, "firma_id": f.id, "codigo_demo": codigo,
            "msg": f"📱 Código de firma enviado a {dest}. En la demo el código es {codigo}."}


class ConfirmarFirmaIn(BaseModel):
    firma_id: int
    codigo: str
    nombre: str | None = ""
    documento: str | None = ""
    comentario: str | None = ""


@router.post("/observador/firmar")
def obs_firmar(payload: ConfirmarFirmaIn, db: Session = Depends(get_db)):
    f = db.query(_FirmaObs).filter(_FirmaObs.id == payload.firma_id).first()
    if not f:
        return {"ok": False, "msg": "Solicitud de firma no encontrada."}
    if f.firmado:
        return {"ok": False, "msg": "Esta anotación ya fue firmada."}
    if (payload.codigo or "").strip() != f.codigo_otp:
        return {"ok": False, "msg": "El código no coincide. Revísalo e intenta de nuevo."}
    f.firmado = True
    f.fecha = datetime.now()
    f.nombre = (payload.nombre or "").strip()[:90] or None
    f.documento = (payload.documento or "").strip()[:30] or None
    f.comentario = (payload.comentario or "").strip()[:300] or None
    obs = db.query(ObservadorEntrada).filter(ObservadorEntrada.id == f.observacion_id).first()
    if obs and f.firmante == "acudiente":
        obs.firmado_acudiente = True
        obs.firma_metodo = "OTP en línea"
        obs.fecha_firma = datetime.now()
    db.commit()
    metadatos.registrar_evento("OBSERVADOR_FIRMADO", f.firmante,
                               estudiante_id=f.estudiante_id)
    return {"ok": True,
            "msg": f"✍️ Firmado por {f.nombre or f.firmante} con verificación de identidad. Queda con fecha y hora como evidencia."}


@router.get("/observador/firmas")
def obs_firmas(estudiante_id: int, db: Session = Depends(get_db)):
    filas = db.query(_FirmaObs).filter(_FirmaObs.estudiante_id == estudiante_id).all()
    return [{"id": f.id, "observacion_id": f.observacion_id, "firmante": f.firmante,
             "nombre": f.nombre, "documento": f.documento, "firmado": bool(f.firmado),
             "comentario": f.comentario,
             "fecha": f.fecha.isoformat(sep=" ", timespec="minutes") if f.fecha else None}
            for f in filas]


# ═════════ PORTAL DEL CONTRATISTA: ingreso por cédula (punto 29) ═════════
class IngresoPortalIn(BaseModel):
    documento: str


@router.post("/portal/ingresar")
def portal_ingresar(payload: IngresoPortalIn, db: Session = Depends(get_db)):
    """El contratista entra con su cédula o NIT, sin necesitar el link."""
    doc = (payload.documento or "").strip().replace(".", "").replace("-", "").replace(" ", "")
    if len(doc) < 5:
        return {"ok": False, "msg": "Escribe tu número de cédula o NIT completo."}
    encontrado = None
    for c in db.query(Contratista).all():
        limpio = (c.nit or "").replace(".", "").replace("-", "").replace(" ", "")
        if limpio and (limpio.startswith(doc) or doc.startswith(limpio[:8])):
            encontrado = c
            break
        rl = (getattr(c, "rep_legal_cc", None) or "").replace(".", "").replace("-", "")
        if rl and rl == doc:
            encontrado = c
            break
    if not encontrado:
        return {"ok": False,
                "msg": "No encontramos ese documento en la base de contratistas de la institución. Comunícate con la oficina de contratación para que te registren primero."}
    if not encontrado.portal_token:
        encontrado.portal_token = _secrets.token_urlsafe(12)
        db.commit()
    metadatos.registrar_evento("PORTAL_INGRESO", "Contratista",
                               payload={"contratista": encontrado.nombre[:30]})
    return {"ok": True, "token": encontrado.portal_token, "nombre": encontrado.nombre,
            "msg": f"Bienvenido(a), {encontrado.nombre}."}


@router.get("/portal/vista_previa")
def portal_vista_previa(contratista_id: int, base_url: str | None = None,
                        db: Session = Depends(get_db)):
    """Lo que verá el contratista, para que contratación lo revise antes de enviar."""
    c = db.query(Contratista).filter(Contratista.id == contratista_id).first()
    if not c:
        return {"ok": False, "msg": "Contratista no encontrado."}
    if not c.portal_token:
        c.portal_token = _secrets.token_urlsafe(12)
        db.commit()
    docs, completos, faltan = _docs(c)
    cts = db.query(Contrato).filter(Contrato.contratista_id == c.id).all()
    try:
        props = json.loads(c.propuestas) if c.propuestas else []
    except Exception:
        props = []
    dominio = (base_url or "").strip().rstrip("/")
    if not dominio:
        dominio = "https://portal.contratistas.gyverlabs.co"
    return {
        "ok": True,
        "contratista": {"id": c.id, "nombre": c.nombre, "nit": c.nit, "tipo": c.tipo,
                        "telefono": c.telefono, "email": c.email},
        "url_token": f"{dominio}/subir/{c.portal_token}",
        "url_cedula": f"{dominio}/ingresar",
        "instrucciones": [
            "El contratista entra con su cédula o NIT (no necesita recordar ningún enlace).",
            "Ve exactamente qué documentos le faltan y cuáles están por vencer.",
            "Sube cada documento y queda al instante en el expediente de la institución.",
            "Puede presentar su propuesta con archivos adjuntos.",
            "Ve el estado de sus contratos y sus pagos.",
        ],
        "vista": {
            "documentos": docs, "completos": completos, "faltantes": faltan,
            "contratos": [{"numero": x.numero, "objeto": x.objeto, "estado": x.estado,
                           "valor": round(x.valor)} for x in cts],
            "propuestas": props,
        },
        "nota_produccion": ("En producción este enlace usa el dominio real de la institución "
                            "(por ejemplo contratistas.ietac.edu.co) y se configura en "
                            "Súper Admin → Dominios. El sistema reemplaza la dirección "
                            "automáticamente sin tocar el código."),
    }


# ═════════ CERTIFICADO DE CURSO con documento y horas (punto 15) ═════════
from fastapi.responses import HTMLResponse as _HTMLResp


@router.get("/certificado", response_class=_HTMLResp)
def certificado(estudiante_id: int, curso_id: int, db: Session = Depends(get_db)):
    """Certificado imprimible con nombre, documento, horas y código de verificación."""
    from models import (Estudiante as _E, Curso as _C, ModuloCurso as _M,
                        TemaCurso as _T, ProgresoTema as _P, Institucion as _I)
    e = db.query(_E).filter(_E.id == estudiante_id).first()
    c = db.query(_C).filter(_C.id == curso_id).first()
    if not e or not c:
        return _HTMLResp("<h3>No encontrado</h3>", status_code=404)
    mods = db.query(_M).filter(_M.curso_id == curso_id).order_by(_M.orden).all()
    temas = []
    for m in mods:
        temas += db.query(_T).filter(_T.modulo_id == m.id).all()
    prog = db.query(_P).filter(_P.estudiante_id == estudiante_id,
                               _P.curso_id == curso_id, _P.completado == True).all()  # noqa: E712
    if len(prog) < len(temas):
        return _HTMLResp(
            f"<div style='font-family:system-ui;max-width:520px;margin:60px auto;text-align:center'>"
            f"<h2>Todavía no</h2><p>Completaste {len(prog)} de {len(temas)} temas de "
            f"«{c.titulo}». Termina el curso y vuelve por tu certificado.</p></div>",
            status_code=200)
    minutos = sum(t.duracion_min or 0 for t in temas)
    estudiadas = sum(p.minutos or 0 for p in prog)
    horas = max(1, round(max(minutos, estudiadas) / 60))
    puntajes = [p.quiz_puntaje for p in prog if p.quiz_puntaje is not None]
    prom = round(sum(puntajes) / len(puntajes)) if puntajes else None
    ie = db.query(_I).filter(_I.id == e.institucion_id).first()
    ult = max([p.fecha for p in prog if p.fecha], default=datetime.now())
    codigo = f"GV-{curso_id:03d}-{estudiante_id:05d}-{ult.strftime('%y%m%d')}"
    logo = (ie.logo if ie and ie.logo else None)
    MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    fecha_txt = f"{ult.day} de {MESES[ult.month]} de {ult.year}"
    _doc = getattr(e, "documento", None)
    doc_txt = f"documento {_doc}" if _doc else f"código estudiantil {e.codigo_acceso or '—'}"
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>Certificado · {e.nombre}</title>
<style>
 @page{{size:landscape}}
 body{{font-family:Georgia,'Times New Roman',serif;margin:0;padding:26px;background:#F1F5F9}}
 .cert{{max-width:940px;margin:0 auto;background:#fff;border:16px solid {c.color or '#0E7C86'};
   padding:44px 56px;position:relative}}
 .cert::after{{content:"";position:absolute;inset:10px;border:1px solid #CBD5E1;pointer-events:none}}
 .head{{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:8px}}
 .inst{{font-size:.82rem;color:#475569;line-height:1.4}}
 .logo img{{max-height:56px;max-width:150px;object-fit:contain}}
 h1{{font-size:2.1rem;color:{c.color or '#0E7C86'};margin:14px 0 4px;letter-spacing:.14em;text-align:center}}
 .sub{{text-align:center;color:#64748B;letter-spacing:.24em;font-size:.72rem;text-transform:uppercase}}
 .nom{{text-align:center;font-size:2rem;margin:26px 0 4px;color:#0F2138}}
 .doc{{text-align:center;color:#475569;font-size:.92rem;margin-bottom:20px}}
 .txt{{text-align:center;color:#334155;font-size:1rem;line-height:1.7}}
 .curso{{text-align:center;font-size:1.35rem;color:{c.color or '#0E7C86'};font-weight:bold;margin:12px 0}}
 .datos{{display:flex;justify-content:center;gap:34px;margin:22px 0;flex-wrap:wrap}}
 .dato{{text-align:center}}
 .dato b{{display:block;font-size:1.25rem;color:#0F2138}}
 .dato span{{font-size:.72rem;color:#64748B;text-transform:uppercase;letter-spacing:.06em}}
 .temario{{font-size:.74rem;color:#64748B;margin-top:16px;line-height:1.6;text-align:center}}
 .firmas{{display:flex;justify-content:space-around;margin-top:40px;gap:44px}}
 .firmas div{{flex:1;border-top:1px solid #94A3B8;padding-top:6px;font-size:.78rem;color:#475569;text-align:center}}
 .cod{{margin-top:22px;text-align:center;font-size:.68rem;color:#94A3B8;font-family:ui-monospace,monospace}}
 .noprint{{max-width:940px;margin:0 auto 14px;background:#FEF3C7;border:1px solid #FCD34D;
   border-radius:8px;padding:10px 14px;font-family:system-ui;font-size:.85rem}}
 @media print{{body{{background:#fff;padding:0}} .noprint{{display:none}}}}
</style></head><body onload="setTimeout(()=>window.print(),500)">
<div class="noprint">💡 En el diálogo de impresión elige <b>«Guardar como PDF»</b> y orientación horizontal.
 <button onclick="window.print()" style="margin-left:10px">🖨️ Imprimir</button></div>
<div class="cert">
  <div class="head">
    <div class="inst"><b>{(ie.nombre if ie else 'Institución Educativa')}</b><br>
      {(ie.municipio + ', ' + ie.departamento) if ie else ''}<br>
      {('DANE ' + ie.codigo_dane) if ie and ie.codigo_dane else ''}</div>
    <div class="logo">{f'<img src="{logo}">' if logo else ''}</div>
  </div>
  <div class="sub">Constancia de formación complementaria</div>
  <h1>CERTIFICADO</h1>
  <div class="txt">La institución hace constar que</div>
  <div class="nom">{e.nombre}</div>
  <div class="doc">identificado(a) con <b>{doc_txt}</b>
    · estudiante de grado {e.grado or '—'}</div>
  <div class="txt">cursó y aprobó satisfactoriamente el programa</div>
  <div class="curso">{c.titulo}</div>
  <div class="datos">
    <div class="dato"><b>{horas}</b><span>horas certificadas</span></div>
    <div class="dato"><b>{len(temas)}</b><span>temas completados</span></div>
    <div class="dato"><b>{len(mods)}</b><span>módulos</span></div>
    {f'<div class="dato"><b>{prom}%</b><span>promedio en evaluaciones</span></div>' if prom is not None else ''}
  </div>
  <div class="txt" style="font-size:.9rem">Expedido el {fecha_txt}</div>
  <div class="temario"><b>Contenido cursado:</b> {' · '.join(m.titulo for m in mods)}</div>
  <div class="firmas">
    <div>Rectoría<br><span style="font-size:.7rem">{(ie.rector if ie else '')}</span></div>
    <div>Coordinación académica</div>
  </div>
  <div class="cod">Código de verificación: {codigo} · Este documento puede validarse ante la institución</div>
</div></body></html>"""
    return _HTMLResp(html)
