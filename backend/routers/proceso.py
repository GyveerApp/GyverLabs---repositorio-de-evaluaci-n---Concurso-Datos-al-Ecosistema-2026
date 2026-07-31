"""Proceso de contratacion completo (puntos 11, 17, 18, 25).

Sigue la rejilla real que se usa en las instituciones educativas:

  1.   Reciben los papeles
  1.1  Solicitud de cotizaciones y papeles habilitantes
  1.2  Se monta a la rejilla + solicitud de CDP
  1.3  Redaccion del proceso (minuta con clausulas)
  1.4  Impresion
  1.5  Pasa a firma
  1.4.1 Acta de inicio
  1.6  Montar al SECOP
  1.7  Pasa a archivo
  +    Acta final / liquidacion

Cada etapa pide SUS documentos y no deja avanzar sin ellos. Juridica puede
crear el contrato desde cero, redactar la minuta y descargarla.
"""
import json
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (Contrato, Contratista, EtapaContrato, ActaContrato,
                    ClausulaContrato, Institucion, Personal, ConfigSistema,
                    PlanFSE, RubroFSE, MovimientoFSE, PagoContrato)
import metadatos

router = APIRouter()

# ── La rejilla: cada etapa con lo que exige ──
REJILLA = [
    {"codigo": "1", "nombre": "Recepción de documentos", "orden": 1,
     "responsable": "Contratación", "dias": 2,
     "docs": [("solicitud", "Solicitud de la necesidad firmada"),
              ("estudio_previo", "Estudio previo / justificación")],
     "ayuda": "Aquí llega la necesidad: quién la pide, para qué y por qué es necesaria."},
    {"codigo": "1.1", "nombre": "Cotizaciones y habilitantes", "orden": 2,
     "responsable": "Contratación", "dias": 5,
     "docs": [("cotizacion_1", "Cotización 1"), ("cotizacion_2", "Cotización 2"),
              ("cotizacion_3", "Cotización 3 (recomendada)"),
              ("habilitantes", "Documentos habilitantes del proveedor")],
     "ayuda": "Se piden mínimo 2 cotizaciones (3 es la buena práctica) y los papeles del contratista."},
    {"codigo": "1.2", "nombre": "Rejilla y solicitud de CDP", "orden": 3,
     "responsable": "Contaduría", "dias": 2,
     "docs": [("rejilla", "Rejilla comparativa de precios"),
              ("solicitud_cdp", "Solicitud de CDP"),
              ("cdp", "CDP expedido")],
     "ayuda": "Se compara precio por precio y se pide el certificado de disponibilidad presupuestal."},
    {"codigo": "1.3", "nombre": "Redacción del proceso", "orden": 4,
     "responsable": "Jurídica", "dias": 3,
     "docs": [("minuta", "Minuta del contrato"),
              ("clausulas", "Clausulado revisado")],
     "ayuda": "Jurídica redacta la minuta con las cláusulas que aplican al tipo de contrato."},
    {"codigo": "1.4", "nombre": "Impresión", "orden": 5,
     "responsable": "Contratación", "dias": 1,
     "docs": [("impreso", "Contrato impreso para firma")],
     "ayuda": "Se imprime el documento definitivo para recoger las firmas físicas o digitales."},
    {"codigo": "1.5", "nombre": "Firmas", "orden": 6,
     "responsable": "Rectoría", "dias": 3,
     "docs": [("firmado", "Contrato firmado por las partes"),
              ("rp", "RP expedido"),
              ("poliza", "Póliza (si aplica)")],
     "ayuda": "Firman rector, contratista y jurídica. Con el contrato firmado se expide el RP."},
    {"codigo": "1.4.1", "nombre": "Acta de inicio", "orden": 7,
     "responsable": "Supervisor", "dias": 2,
     "docs": [("acta_inicio", "Acta de inicio suscrita")],
     "ayuda": "Marca el arranque del plazo de ejecución. Desde aquí corren los días del contrato."},
    {"codigo": "1.6", "nombre": "Publicación en SECOP", "orden": 8,
     "responsable": "Contratación", "dias": 3,
     "docs": [("constancia_secop", "Constancia de publicación")],
     "ayuda": "La ley exige publicar el proceso. Sin esto hay hallazgo seguro."},
    {"codigo": "1.7", "nombre": "Archivo del expediente", "orden": 9,
     "responsable": "Contratación", "dias": 5,
     "docs": [("acta_final", "Acta final / de liquidación"),
              ("paz_salvo", "Paz y salvo del contratista"),
              ("informe_supervision", "Informe final de supervisión")],
     "ayuda": "El expediente completo se archiva. Es lo que revisa la Contraloría años después."},
]

# ── Cláusulas por tipo de contrato ──
CLAUSULAS_BASE = [
    ("Objeto", "El CONTRATISTA se obliga con la INSTITUCIÓN EDUCATIVA a {objeto}."),
    ("Valor y forma de pago",
     "El valor del presente contrato es la suma de {valor_letras} (${valor}) M/CTE, "
     "que la INSTITUCIÓN pagará al CONTRATISTA previa presentación de la factura o cuenta de cobro, "
     "informe de supervisión y paz y salvo de aportes al Sistema de Seguridad Social."),
    ("Plazo de ejecución",
     "El plazo de ejecución será de {plazo} días calendario contados a partir de la suscripción "
     "del acta de inicio, sin exceder el 31 de diciembre de la vigencia fiscal."),
    ("Obligaciones del contratista",
     "Además de las derivadas de la naturaleza del contrato, el CONTRATISTA se obliga a: {obligaciones}"),
    ("Obligaciones de la institución",
     "1) Pagar el valor pactado en la forma acordada. 2) Suministrar la información necesaria "
     "para la ejecución. 3) Ejercer la supervisión del contrato."),
    ("Supervisión",
     "La supervisión será ejercida por {supervisor}, quien velará por el cumplimiento y "
     "suscribirá los informes y actas correspondientes."),
    ("Imputación presupuestal",
     "El presente contrato se imputa al CDP N° {cdp} del rubro {rubro} del presupuesto "
     "del Fondo de Servicios Educativos de la vigencia {anio}."),
    ("Régimen legal aplicable",
     "El presente contrato se rige por el régimen especial de contratación de los Fondos de "
     "Servicios Educativos previsto en el Decreto 1075 de 2015 (que compiló el Decreto 4791 de 2008), "
     "y en lo no previsto por las normas del derecho privado."),
    ("Inhabilidades e incompatibilidades",
     "El CONTRATISTA declara bajo la gravedad del juramento que no se encuentra incurso en "
     "causal alguna de inhabilidad o incompatibilidad consagrada en la Constitución y la ley."),
    ("Terminación",
     "El contrato terminará por: vencimiento del plazo, cumplimiento del objeto, mutuo acuerdo, "
     "o incumplimiento de cualquiera de las obligaciones pactadas."),
    ("Liquidación",
     "El contrato se liquidará de común acuerdo dentro de los cuatro (4) meses siguientes "
     "a su terminación, mediante acta suscrita por las partes."),
    ("Perfeccionamiento y ejecución",
     "El contrato se perfecciona con la firma de las partes y para su ejecución requiere "
     "el registro presupuestal y la suscripción del acta de inicio."),
]

CLAUSULAS_EXTRA = {
    "obra": [("Garantías",
              "El CONTRATISTA constituirá a favor de la INSTITUCIÓN póliza de cumplimiento "
              "por el 20% del valor del contrato, y de estabilidad de la obra por el 30% "
              "con vigencia de cinco (5) años."),
             ("Seguridad industrial",
              "El CONTRATISTA responderá por la seguridad de su personal, dotación de elementos "
              "de protección y afiliación al Sistema de Riesgos Laborales.")],
    "servicio": [("Garantías",
                  "El CONTRATISTA constituirá póliza de cumplimiento por el 20% del valor "
                  "y de pago de salarios y prestaciones por el 10%."),
                 ("Independencia laboral",
                  "El presente contrato no genera relación laboral ni prestaciones sociales "
                  "entre la INSTITUCIÓN y el CONTRATISTA o su personal.")],
    "suministro": [("Calidad y garantía de los bienes",
                    "Los bienes suministrados deberán ser nuevos, de primera calidad y contar "
                    "con garantía mínima de un (1) año contado desde la entrega a satisfacción.")],
    "pae": [("Calidad e inocuidad",
             "El CONTRATISTA garantizará el cumplimiento de las minutas avaladas por nutricionista, "
             "las condiciones sanitarias vigentes y la trazabilidad de los alimentos."),
            ("Manipulación de alimentos",
             "Todo el personal contará con certificado vigente de manipulación de alimentos "
             "y examen médico ocupacional.")],
}

MODELOS_ACTA = {
    "inicio": {
        "titulo": "ACTA DE INICIO",
        "plantilla": ("En {municipio}, a los {dia} días del mes de {mes} de {anio}, se reunieron "
                      "{rector}, en calidad de Rector(a) de {institucion}, y {contratista}, "
                      "en calidad de CONTRATISTA, con el fin de suscribir el acta de inicio del "
                      "contrato N° {numero}, cuyo objeto es: {objeto}.\n\n"
                      "Verificados los requisitos de perfeccionamiento y ejecución (registro "
                      "presupuestal N° {rp} y garantías aprobadas), las partes acuerdan dar inicio "
                      "a la ejecución a partir de la fecha, por un plazo de {plazo} días calendario, "
                      "venciendo el {fecha_fin}.\n\n"
                      "El supervisor designado es {supervisor}, quien velará por el cumplimiento.")},
    "parcial": {
        "titulo": "ACTA PARCIAL DE AVANCE",
        "plantilla": ("Siendo el {dia} de {mes} de {anio}, el supervisor {supervisor} deja constancia "
                      "del avance del contrato N° {numero}, con un porcentaje de ejecución del "
                      "{pct}% y un valor ejecutado de ${valor_ejecutado}.\n\n"
                      "Se deja constancia de que el CONTRATISTA ha cumplido con las obligaciones "
                      "correspondientes a este período.")},
    "suspension": {
        "titulo": "ACTA DE SUSPENSIÓN",
        "plantilla": ("En {municipio}, el {dia} de {mes} de {anio}, las partes del contrato N° {numero} "
                      "acuerdan suspender su ejecución por las siguientes razones: {motivo}.\n\n"
                      "El plazo suspendido se reanudará mediante acta de reinicio.")},
    "final": {
        "titulo": "ACTA FINAL DE RECIBO A SATISFACCIÓN",
        "plantilla": ("En {municipio}, a los {dia} días del mes de {mes} de {anio}, se reunieron "
                      "{rector}, Rector(a) de {institucion}, {supervisor}, supervisor del contrato, "
                      "y {contratista}, CONTRATISTA, para suscribir el acta final del contrato "
                      "N° {numero}.\n\n"
                      "El supervisor deja constancia de que el CONTRATISTA cumplió a satisfacción "
                      "con el objeto contratado, ejecutando el 100% por valor de ${valor_ejecutado}.\n\n"
                      "Se deja constancia de que no existen obligaciones pendientes entre las partes "
                      "y que el contratista se encuentra a paz y salvo por concepto de aportes "
                      "al Sistema de Seguridad Social.")},
    "liquidacion": {
        "titulo": "ACTA DE LIQUIDACIÓN",
        "plantilla": ("En {municipio}, el {dia} de {mes} de {anio}, las partes proceden a liquidar "
                      "el contrato N° {numero}.\n\n"
                      "Valor inicial: ${valor}. Valor ejecutado: ${valor_ejecutado}. "
                      "Saldo a favor de la institución: ${saldo}.\n\n"
                      "Las partes se declaran a paz y salvo y renuncian a cualquier reclamación "
                      "futura derivada del presente contrato.")},
}

MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _jl(t, d):
    try:
        return json.loads(t) if t else d
    except Exception:
        return d


def _numero_letras(n):
    """Convierte a letras el valor del contrato (para la minuta)."""
    UNI = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE",
           "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS", "DIECISIETE",
           "DIECIOCHO", "DIECINUEVE", "VEINTE"]
    DEC = ["", "", "VEINTI", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA",
           "OCHENTA", "NOVENTA"]
    CEN = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
           "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]

    def _hasta999(x):
        if x == 0:
            return ""
        if x == 100:
            return "CIEN"
        c, r = divmod(x, 100)
        out = CEN[c]
        if r:
            if r <= 20:
                out += (" " if out else "") + UNI[r]
            else:
                d, u = divmod(r, 10)
                if d == 2:
                    out += (" " if out else "") + "VEINTI" + UNI[u].lower().upper() if u else (" " if out else "") + "VEINTE"
                else:
                    out += (" " if out else "") + DEC[d] + (" Y " + UNI[u] if u else "")
        return out.strip()

    n = int(round(n))
    if n == 0:
        return "CERO PESOS"
    millones, resto = divmod(n, 1_000_000)
    miles, unidades = divmod(resto, 1000)
    partes = []
    if millones:
        partes.append(("UN MILLÓN" if millones == 1 else _hasta999(millones) + " MILLONES"))
    if miles:
        partes.append(("MIL" if miles == 1 else _hasta999(miles) + " MIL"))
    if unidades:
        partes.append(_hasta999(unidades))
    return " ".join(partes) + " PESOS"


@router.get("/rejilla")
def rejilla():
    """La estructura del proceso, para pintarla en el frontend."""
    return {"etapas": REJILLA,
            "tipos_acta": [{"id": k, "titulo": v["titulo"]} for k, v in MODELOS_ACTA.items()]}


@router.post("/iniciar")
def iniciar(contrato_id: int, db: Session = Depends(get_db)):
    """Crea la rejilla de etapas para un contrato que no la tenga."""
    ct = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not ct:
        return {"ok": False, "msg": "Contrato no encontrado."}
    if db.query(EtapaContrato).filter(EtapaContrato.contrato_id == contrato_id).count():
        return {"ok": False, "msg": "Este contrato ya tiene su rejilla creada."}
    base = ct.fecha or date.today()
    acum = 0
    for e in REJILLA:
        acum += e["dias"]
        db.add(EtapaContrato(
            contrato_id=contrato_id, codigo=e["codigo"], nombre=e["nombre"],
            orden=e["orden"], responsable=e["responsable"],
            fecha_limite=base + timedelta(days=acum),
            estado="en_proceso" if e["orden"] == 1 else "pendiente",
            documentos=json.dumps({k: None for k, _l in e["docs"]}, ensure_ascii=False)))
    db.commit()
    return {"ok": True, "msg": f"📋 Rejilla creada con {len(REJILLA)} etapas y sus fechas límite."}


@router.get("/proceso")
def proceso(contrato_id: int, db: Session = Depends(get_db)):
    """Estado completo del proceso: etapas, documentos, actas y cláusulas."""
    ct = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not ct:
        return {"ok": False, "msg": "Contrato no encontrado."}
    etapas = db.query(EtapaContrato).filter(
        EtapaContrato.contrato_id == contrato_id).order_by(EtapaContrato.orden).all()
    if not etapas:
        iniciar(contrato_id, db)
        etapas = db.query(EtapaContrato).filter(
            EtapaContrato.contrato_id == contrato_id).order_by(EtapaContrato.orden).all()
    hoy = date.today()
    ref = {e["codigo"]: e for e in REJILLA}
    filas = []
    for e in etapas:
        r = ref.get(e.codigo, {})
        docs_guardados = _jl(e.documentos, {})
        docs = []
        for k, lbl in r.get("docs", []):
            v = docs_guardados.get(k)
            docs.append({"clave": k, "label": lbl, "archivo": v,
                         "subido": bool(v),
                         "opcional": "recomendada" in lbl.lower() or "si aplica" in lbl.lower()})
        faltan = [d["label"] for d in docs if not d["subido"] and not d["opcional"]]
        atrasada = (e.estado != "completada" and e.fecha_limite and e.fecha_limite < hoy)
        filas.append({
            "id": e.id, "codigo": e.codigo, "nombre": e.nombre, "orden": e.orden,
            "responsable": e.responsable, "estado": e.estado,
            "ayuda": r.get("ayuda"),
            "fecha_limite": e.fecha_limite.isoformat() if e.fecha_limite else None,
            "fecha_completada": e.fecha_completada.isoformat() if e.fecha_completada else None,
            "dias_restantes": (e.fecha_limite - hoy).days if e.fecha_limite else None,
            "atrasada": bool(atrasada),
            "documentos": docs, "faltantes": faltan,
            "completable": len(faltan) == 0,
            "nota": e.nota,
        })
    actas = db.query(ActaContrato).filter(ActaContrato.contrato_id == contrato_id).all()
    claus = db.query(ClausulaContrato).filter(
        ClausulaContrato.contrato_id == contrato_id).order_by(ClausulaContrato.numero).all()
    prov = db.query(Contratista).filter(Contratista.id == ct.contratista_id).first()
    actual = next((f for f in filas if f["estado"] in ("en_proceso", "pendiente")), None)
    return {
        "ok": True,
        "contrato": {"id": ct.id, "numero": ct.numero, "objeto": ct.objeto,
                     "valor": round(ct.valor), "tipo": ct.tipo_contrato,
                     "estado": ct.estado, "cdp": ct.cdp_num, "rp": ct.rp_num,
                     "contratista": prov.nombre if prov else None,
                     "contratista_id": ct.contratista_id},
        "etapas": filas,
        "etapa_actual": actual["codigo"] if actual else None,
        "avance": round(100 * sum(1 for f in filas if f["estado"] == "completada") / len(filas)) if filas else 0,
        "atrasadas": [f["nombre"] for f in filas if f["atrasada"]],
        "actas": [{"id": a.id, "tipo": a.tipo, "numero": a.numero,
                   "fecha": a.fecha.isoformat() if a.fecha else None,
                   "estado": a.estado, "pct_avance": a.pct_avance,
                   "valor_ejecutado": round(a.valor_ejecutado or 0),
                   "titulo": MODELOS_ACTA.get(a.tipo, {}).get("titulo", a.tipo)} for a in actas],
        "clausulas": [{"id": c.id, "numero": c.numero, "titulo": c.titulo,
                       "texto": c.texto, "editada": bool(c.editada)} for c in claus],
        "tiene_minuta": len(claus) > 0,
    }


class SubirDocEtapaIn(BaseModel):
    etapa_id: int
    clave: str
    archivo: str


@router.post("/etapa/documento")
def etapa_documento(payload: SubirDocEtapaIn, db: Session = Depends(get_db)):
    """Anexa un documento a SU etapa (punto 18: dónde subir cada cosa)."""
    e = db.query(EtapaContrato).filter(EtapaContrato.id == payload.etapa_id).first()
    if not e:
        return {"ok": False, "msg": "Etapa no encontrada."}
    docs = _jl(e.documentos, {})
    docs[payload.clave] = payload.archivo[:120]
    e.documentos = json.dumps(docs, ensure_ascii=False)
    if e.estado == "pendiente":
        e.estado = "en_proceso"
    # si es una cotización, también va al contrato
    if payload.clave.startswith("cotizacion"):
        ct = db.query(Contrato).filter(Contrato.id == e.contrato_id).first()
        if ct:
            cot = _jl(ct.cotizaciones, [])
            if not any(x.get("archivo") == payload.archivo for x in cot):
                cot.append({"proveedor": f"Cotización {len(cot) + 1}", "valor": 0,
                            "fecha": date.today().isoformat(), "archivo": payload.archivo[:80]})
                ct.cotizaciones = json.dumps(cot, ensure_ascii=False)
    ref = next((x for x in REJILLA if x["codigo"] == e.codigo), {})
    lbl = dict(ref.get("docs", [])).get(payload.clave, payload.clave)
    db.commit()
    return {"ok": True, "msg": f"📎 «{lbl}» anexado a la etapa {e.codigo}."}


class CompletarEtapaIn(BaseModel):
    etapa_id: int
    nota: str | None = ""
    forzar: bool = False


@router.post("/etapa/completar")
def etapa_completar(payload: CompletarEtapaIn, db: Session = Depends(get_db)):
    """Cierra la etapa y abre la siguiente. No deja si faltan documentos."""
    e = db.query(EtapaContrato).filter(EtapaContrato.id == payload.etapa_id).first()
    if not e:
        return {"ok": False, "msg": "Etapa no encontrada."}
    ref = next((x for x in REJILLA if x["codigo"] == e.codigo), {})
    docs = _jl(e.documentos, {})
    faltan = [lbl for k, lbl in ref.get("docs", [])
              if not docs.get(k) and "recomendada" not in lbl.lower() and "si aplica" not in lbl.lower()]
    if faltan and not payload.forzar:
        return {"ok": False, "faltantes": faltan,
                "msg": f"⛔ Faltan documentos de esta etapa: {', '.join(faltan)}. Súbelos en la lista de arriba."}
    e.estado = "completada"
    e.fecha_completada = date.today()
    if payload.nota:
        e.nota = payload.nota[:400]
    sig = db.query(EtapaContrato).filter(EtapaContrato.contrato_id == e.contrato_id,
                                         EtapaContrato.orden == e.orden + 1).first()
    if sig:
        sig.estado = "en_proceso"
    # sincronizar el estado del contrato con la rejilla
    ct = db.query(Contrato).filter(Contrato.id == e.contrato_id).first()
    MAPA = {"1": "borrador", "1.1": "documentos", "1.2": "documentos", "1.3": "juridica",
            "1.4": "firma", "1.5": "firmado", "1.4.1": "ejecucion", "1.6": "ejecucion",
            "1.7": "liquidado"}
    if ct and e.codigo in MAPA:
        ct.estado = MAPA[e.codigo]
        et = _jl(ct.etapas_fechas, {})
        et[MAPA[e.codigo]] = date.today().isoformat()
        ct.etapas_fechas = json.dumps(et, ensure_ascii=False)
    db.commit()
    metadatos.registrar_evento("ETAPA_CONTRATO", e.responsable or "Contratación",
                               payload={"etapa": e.codigo, "forzada": payload.forzar})
    extra = f" Sigue: {sig.codigo} {sig.nombre} (responsable: {sig.responsable})." if sig else " ¡Proceso terminado!"
    aviso = " ⚠️ Se cerró con documentos pendientes, quedó registrado." if (faltan and payload.forzar) else ""
    return {"ok": True, "msg": f"✅ Etapa {e.codigo} completada.{extra}{aviso}"}


# ═════════ MINUTA Y CLÁUSULAS (punto 25) ═════════
class GenerarMinutaIn(BaseModel):
    contrato_id: int
    supervisor: str | None = ""
    rubro: str | None = ""
    obligaciones: list | None = None


@router.post("/minuta/generar")
def minuta_generar(payload: GenerarMinutaIn, db: Session = Depends(get_db)):
    """Jurídica genera la minuta completa con las cláusulas del tipo de contrato."""
    ct = db.query(Contrato).filter(Contrato.id == payload.contrato_id).first()
    if not ct:
        return {"ok": False, "msg": "Contrato no encontrado."}
    db.query(ClausulaContrato).filter(
        ClausulaContrato.contrato_id == payload.contrato_id).delete()
    det = _jl(ct.etapas_fechas, {}).get("_detalle", {})
    obligaciones = payload.obligaciones or det.get("obligaciones") or [
        "Ejecutar el objeto contratado con calidad y oportunidad",
        "Presentar los informes que requiera el supervisor",
        "Mantener vigentes los aportes al Sistema de Seguridad Social"]
    ctx = {
        "objeto": ct.objeto,
        "valor": f"{round(ct.valor):,}".replace(",", "."),
        "valor_letras": _numero_letras(ct.valor),
        "plazo": det.get("plazo_dias", 30),
        "obligaciones": " ".join(f"{i}) {o}." for i, o in enumerate(obligaciones, 1)),
        "supervisor": payload.supervisor or det.get("supervisor") or "el supervisor designado por rectoría",
        "cdp": ct.cdp_num or "por expedir",
        "rubro": payload.rubro or "gastos generales del FSE",
        "anio": (ct.fecha or date.today()).year,
    }
    lista = list(CLAUSULAS_BASE)
    extra = CLAUSULAS_EXTRA.get(ct.tipo_contrato or "suministro", [])
    lista = lista[:4] + extra + lista[4:]
    for i, (tit, txt) in enumerate(lista, 1):
        try:
            texto = txt.format(**ctx)
        except (KeyError, IndexError):
            texto = txt
        db.add(ClausulaContrato(contrato_id=ct.id, numero=i, titulo=tit,
                                texto=texto, obligatoria=True))
    db.commit()
    metadatos.registrar_evento("MINUTA_GENERADA", "Jurídica",
                               institucion_id=ct.institucion_id,
                               payload={"contrato": ct.numero, "clausulas": len(lista)})
    return {"ok": True, "n": len(lista),
            "msg": f"⚖️ Minuta generada con {len(lista)} cláusulas para un contrato de {ct.tipo_contrato}. Revísala y ajusta lo que necesites."}


class EditarClausulaIn(BaseModel):
    id: int
    titulo: str | None = None
    texto: str | None = None


@router.post("/minuta/clausula")
def minuta_clausula(payload: EditarClausulaIn, db: Session = Depends(get_db)):
    c = db.query(ClausulaContrato).filter(ClausulaContrato.id == payload.id).first()
    if not c:
        return {"ok": False, "msg": "Cláusula no encontrada."}
    if payload.titulo:
        c.titulo = payload.titulo[:120]
    if payload.texto:
        c.texto = payload.texto[:4000]
    c.editada = True
    db.commit()
    return {"ok": True, "msg": f"Cláusula {c.numero} actualizada."}


class NuevaClausulaIn(BaseModel):
    contrato_id: int
    titulo: str
    texto: str


@router.post("/minuta/agregar")
def minuta_agregar(payload: NuevaClausulaIn, db: Session = Depends(get_db)):
    n = db.query(ClausulaContrato).filter(
        ClausulaContrato.contrato_id == payload.contrato_id).count()
    db.add(ClausulaContrato(contrato_id=payload.contrato_id, numero=n + 1,
                            titulo=payload.titulo[:120], texto=payload.texto[:4000],
                            obligatoria=False, editada=True))
    db.commit()
    return {"ok": True, "msg": "Cláusula agregada."}


@router.post("/minuta/eliminar")
def minuta_eliminar(id: int, db: Session = Depends(get_db)):
    c = db.query(ClausulaContrato).filter(ClausulaContrato.id == id).first()
    if not c:
        return {"ok": False, "msg": "No encontrada."}
    if c.obligatoria:
        return {"ok": False, "msg": "Esta cláusula es obligatoria por ley y no se puede eliminar."}
    db.delete(c)
    db.commit()
    return {"ok": True, "msg": "Cláusula eliminada."}


@router.get("/minuta.html", response_class=HTMLResponse)
def minuta_html(contrato_id: int, db: Session = Depends(get_db)):
    """El contrato listo para imprimir o guardar como PDF."""
    ct = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not ct:
        return HTMLResponse("<h3>Contrato no encontrado</h3>", status_code=404)
    claus = db.query(ClausulaContrato).filter(
        ClausulaContrato.contrato_id == contrato_id).order_by(ClausulaContrato.numero).all()
    if not claus:
        return HTMLResponse(
            "<div style='font-family:system-ui;max-width:520px;margin:60px auto;text-align:center'>"
            "<h2>Falta la minuta</h2><p>Jurídica debe generarla primero desde el proceso "
            "del contrato (etapa 1.3 Redacción).</p></div>")
    prov = db.query(Contratista).filter(Contratista.id == ct.contratista_id).first()
    ie = db.query(Institucion).filter(Institucion.id == ct.institucion_id).first()
    rector = db.query(Personal).filter(Personal.institucion_id == ct.institucion_id,
                                       Personal.rol == "rector").first()
    f = ct.fecha or date.today()
    ROM = ["", "PRIMERA", "SEGUNDA", "TERCERA", "CUARTA", "QUINTA", "SEXTA", "SÉPTIMA",
           "OCTAVA", "NOVENA", "DÉCIMA", "DÉCIMA PRIMERA", "DÉCIMA SEGUNDA",
           "DÉCIMA TERCERA", "DÉCIMA CUARTA", "DÉCIMA QUINTA", "DÉCIMA SEXTA"]
    cuerpo = "".join(
        f'<p class="cl"><b>{ROM[c.numero] if c.numero < len(ROM) else c.numero}. '
        f'{c.titulo.upper()}:</b> {c.texto}</p>' for c in claus)
    firmas = _jl(ct.firmas, [])
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>Contrato {ct.numero}</title><style>
 body{{font-family:'Times New Roman',Georgia,serif;max-width:800px;margin:26px auto;padding:0 26px;
   color:#1B2530;line-height:1.62;font-size:.96rem;text-align:justify}}
 .enc{{text-align:center;margin-bottom:22px;border-bottom:2px solid #0F2138;padding-bottom:12px}}
 .enc h1{{font-size:1.15rem;margin:6px 0;letter-spacing:.04em}}
 .enc .ie{{font-size:.86rem;color:#475569}}
 .partes{{background:#F8FAFC;padding:14px 18px;border-radius:8px;margin-bottom:18px;font-size:.92rem}}
 .cl{{margin-bottom:13px}}
 .firmas{{display:flex;justify-content:space-between;gap:40px;margin-top:70px}}
 .firmas div{{flex:1;border-top:1px solid #1B2530;padding-top:6px;text-align:center;font-size:.84rem}}
 .pie{{margin-top:34px;font-size:.7rem;color:#94A3B8;text-align:center}}
 .noprint{{background:#FEF3C7;border:1px solid #FCD34D;border-radius:8px;padding:10px 14px;
   margin-bottom:16px;font-family:system-ui;font-size:.85rem}}
 @media print{{.noprint{{display:none}} body{{margin:0}}}}
</style></head><body onload="setTimeout(()=>window.print(),400)">
<div class="noprint">💡 En el diálogo de impresión elige <b>«Guardar como PDF»</b>.
 <button onclick="window.print()" style="margin-left:8px">🖨️ Imprimir</button></div>
<div class="enc">
  <div class="ie">{ie.nombre if ie else ''}<br>NIT {ie.codigo_dane if ie else ''} · {ie.municipio if ie else ''}, {ie.departamento if ie else ''}</div>
  <h1>CONTRATO DE {(ct.tipo_contrato or 'SUMINISTRO').upper()} N° {ct.numero}</h1>
  <div class="ie">Fondo de Servicios Educativos · Vigencia {f.year}</div>
</div>
<div class="partes">
  Entre los suscritos, <b>{(rector.nombre if rector else (ie.rector if ie else 'EL RECTOR'))}</b>,
  mayor de edad, identificado(a) con cédula de ciudadanía, obrando en calidad de Rector(a) y
  Ordenador(a) del Gasto del Fondo de Servicios Educativos de <b>{ie.nombre if ie else 'la institución'}</b>,
  quien en adelante se denominará <b>LA INSTITUCIÓN</b>; y
  <b>{prov.nombre if prov else 'EL CONTRATISTA'}</b>, identificado(a) con
  {'NIT' if (prov and prov.tipo == 'juridica') else 'C.C.'} {prov.nit if prov else '—'},
  {f"representado(a) legalmente por {prov.rep_legal}" if (prov and getattr(prov, 'rep_legal', None)) else ""},
  quien en adelante se denominará <b>EL CONTRATISTA</b>, hemos convenido celebrar el presente
  contrato, previas las siguientes consideraciones y cláusulas:
</div>
{cuerpo}
<p style="margin-top:24px">Para constancia se firma en {ie.municipio if ie else '____'},
 a los {f.day} días del mes de {MESES[f.month]} de {f.year}.</p>
<div class="firmas">
  <div><b>{(rector.nombre if rector else 'RECTOR(A)')}</b><br>Rector(a) — LA INSTITUCIÓN</div>
  <div><b>{prov.nombre if prov else 'CONTRATISTA'}</b><br>{'NIT' if (prov and prov.tipo == 'juridica') else 'C.C.'} {prov.nit if prov else ''} — EL CONTRATISTA</div>
</div>
{'<div class="firmas"><div><b>' + next((x.get('nombre', '') for x in firmas if x.get('rol') == 'Jurídica'), 'Jurídica') + '</b><br>Revisión jurídica</div><div><b>Supervisor</b><br>Supervisión del contrato</div></div>' if firmas else ''}
<div class="pie">CDP {ct.cdp_num or '—'} · RP {ct.rp_num or '—'} · Documento generado por el sistema · Datos de demostración</div>
</body></html>"""
    return HTMLResponse(html)


# ═════════ ACTAS (punto 17) ═════════
class ActaIn(BaseModel):
    contrato_id: int
    tipo: str
    fecha: str | None = None
    pct_avance: int | None = 100
    valor_ejecutado: float | None = None
    supervisor: str | None = ""
    motivo: str | None = ""
    observaciones: str | None = ""


@router.post("/acta/generar")
def acta_generar(payload: ActaIn, db: Session = Depends(get_db)):
    """Genera el acta con su texto legal ya redactado."""
    if payload.tipo not in MODELOS_ACTA:
        return {"ok": False, "msg": "Tipo de acta no válido."}
    ct = db.query(Contrato).filter(Contrato.id == payload.contrato_id).first()
    if not ct:
        return {"ok": False, "msg": "Contrato no encontrado."}
    if payload.tipo == "inicio":
        if not ct.rp_num:
            return {"ok": False,
                    "msg": "⛔ No se puede suscribir el acta de inicio sin RP: la ley exige el registro presupuestal antes de ejecutar."}
        ya = db.query(ActaContrato).filter(ActaContrato.contrato_id == ct.id,
                                           ActaContrato.tipo == "inicio").first()
        if ya:
            return {"ok": False, "msg": "Este contrato ya tiene acta de inicio."}
    if payload.tipo in ("final", "liquidacion"):
        inicio = db.query(ActaContrato).filter(ActaContrato.contrato_id == ct.id,
                                               ActaContrato.tipo == "inicio").first()
        if not inicio:
            return {"ok": False, "msg": "⛔ No puede haber acta final sin acta de inicio."}
    try:
        f = date.fromisoformat(payload.fecha) if payload.fecha else date.today()
    except ValueError:
        f = date.today()
    ie = db.query(Institucion).filter(Institucion.id == ct.institucion_id).first()
    prov = db.query(Contratista).filter(Contratista.id == ct.contratista_id).first()
    rector = db.query(Personal).filter(Personal.institucion_id == ct.institucion_id,
                                       Personal.rol == "rector").first()
    det = _jl(ct.etapas_fechas, {}).get("_detalle", {})
    plazo = det.get("plazo_dias", 30)
    ejec = payload.valor_ejecutado if payload.valor_ejecutado is not None else ct.valor
    ctx = {
        "municipio": ie.municipio if ie else "___", "dia": f.day, "mes": MESES[f.month],
        "anio": f.year, "rector": rector.nombre if rector else (ie.rector if ie else "El Rector"),
        "institucion": ie.nombre if ie else "la institución",
        "contratista": prov.nombre if prov else "el contratista",
        "numero": ct.numero, "objeto": ct.objeto, "rp": ct.rp_num or "—",
        "plazo": plazo,
        "fecha_fin": (f + timedelta(days=plazo)).isoformat(),
        "supervisor": payload.supervisor or det.get("supervisor") or "el supervisor designado",
        "pct": payload.pct_avance or 100,
        "valor_ejecutado": f"{round(ejec):,}".replace(",", "."),
        "valor": f"{round(ct.valor):,}".replace(",", "."),
        "saldo": f"{round(ct.valor - ejec):,}".replace(",", "."),
        "motivo": payload.motivo or "las razones expuestas por las partes",
    }
    modelo = MODELOS_ACTA[payload.tipo]
    try:
        contenido = modelo["plantilla"].format(**ctx)
    except (KeyError, IndexError):
        contenido = modelo["plantilla"]
    n = db.query(ActaContrato).filter(ActaContrato.contrato_id == ct.id).count() + 1
    a = ActaContrato(
        contrato_id=ct.id, tipo=payload.tipo,
        numero=f"ACTA-{ct.numero.split('-')[-1]}-{n:02d}", fecha=f,
        contenido=contenido, valor_ejecutado=ejec,
        pct_avance=payload.pct_avance or 100, estado="borrador",
        observaciones=(payload.observaciones or "").strip()[:500] or None,
        firmantes=json.dumps([
            {"rol": "Rector(a)", "nombre": rector.nombre if rector else "", "firmado": False},
            {"rol": "Supervisor", "nombre": ctx["supervisor"], "firmado": False},
            {"rol": "Contratista", "nombre": prov.nombre if prov else "", "firmado": False},
        ], ensure_ascii=False))
    db.add(a)
    # el acta de inicio mueve el contrato a ejecución
    if payload.tipo == "inicio":
        ct.estado = "ejecucion"
        et = _jl(ct.etapas_fechas, {})
        et["ejecucion"] = f.isoformat()
        ct.etapas_fechas = json.dumps(et, ensure_ascii=False)
    if payload.tipo in ("final", "liquidacion"):
        ct.estado = "liquidado"
    db.commit()
    metadatos.registrar_evento("ACTA_GENERADA", "Contratación",
                               institucion_id=ct.institucion_id,
                               payload={"tipo": payload.tipo, "contrato": ct.numero})
    return {"ok": True, "id": a.id, "numero": a.numero,
            "msg": f"📄 {modelo['titulo']} generada ({a.numero}). Revísala, imprímela y recoge las firmas."}


@router.get("/acta.html", response_class=HTMLResponse)
def acta_html(id: int, db: Session = Depends(get_db)):
    a = db.query(ActaContrato).filter(ActaContrato.id == id).first()
    if not a:
        return HTMLResponse("<h3>Acta no encontrada</h3>", status_code=404)
    ct = db.query(Contrato).filter(Contrato.id == a.contrato_id).first()
    ie = db.query(Institucion).filter(Institucion.id == (ct.institucion_id if ct else None)).first()
    firm = _jl(a.firmantes, [])
    modelo = MODELOS_ACTA.get(a.tipo, {"titulo": a.tipo.upper()})
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>{a.numero}</title><style>
 body{{font-family:'Times New Roman',Georgia,serif;max-width:760px;margin:30px auto;padding:0 26px;
   line-height:1.7;color:#1B2530;text-align:justify}}
 .enc{{text-align:center;border-bottom:2px solid #0F2138;padding-bottom:12px;margin-bottom:20px}}
 .enc h1{{font-size:1.1rem;letter-spacing:.05em;margin:8px 0 4px}}
 .meta{{font-size:.84rem;color:#475569}}
 .cont{{white-space:pre-line;margin:20px 0}}
 .obs{{background:#F8FAFC;border-left:3px solid #0E7C86;padding:10px 14px;margin:16px 0;font-size:.9rem}}
 .firmas{{display:flex;justify-content:space-around;gap:30px;margin-top:64px}}
 .firmas div{{flex:1;border-top:1px solid #1B2530;padding-top:6px;text-align:center;font-size:.82rem}}
 .noprint{{background:#FEF3C7;border:1px solid #FCD34D;border-radius:8px;padding:10px 14px;
   margin-bottom:14px;font-family:system-ui;font-size:.85rem}}
 @media print{{.noprint{{display:none}}}}
</style></head><body onload="setTimeout(()=>window.print(),400)">
<div class="noprint">💡 Elige <b>«Guardar como PDF»</b> para descargar el acta.
 <button onclick="window.print()" style="margin-left:8px">🖨️ Imprimir</button></div>
<div class="enc">
  <div class="meta">{ie.nombre if ie else ''} · Fondo de Servicios Educativos</div>
  <h1>{modelo['titulo']}</h1>
  <div class="meta">{a.numero} · Contrato {ct.numero if ct else ''}</div>
</div>
<div class="cont">{a.contenido or ''}</div>
{f'<div class="obs"><b>Observaciones:</b> {a.observaciones}</div>' if a.observaciones else ''}
<div class="firmas">
  {''.join(f"<div><b>{x.get('nombre') or x.get('rol')}</b><br>{x.get('rol')}</div>" for x in firm)}
</div>
<div style="margin-top:30px;font-size:.7rem;color:#94A3B8;text-align:center">
  Documento generado por el sistema · Datos de demostración</div>
</body></html>"""
    return HTMLResponse(html)


class FirmarActaIn(BaseModel):
    id: int
    rol: str


@router.post("/acta/firmar")
def acta_firmar(payload: FirmarActaIn, db: Session = Depends(get_db)):
    a = db.query(ActaContrato).filter(ActaContrato.id == payload.id).first()
    if not a:
        return {"ok": False, "msg": "Acta no encontrada."}
    firm = _jl(a.firmantes, [])
    hallado = False
    for x in firm:
        if x.get("rol") == payload.rol:
            x["firmado"] = True
            x["fecha"] = datetime.now().isoformat(sep=" ", timespec="minutes")
            hallado = True
    if not hallado:
        return {"ok": False, "msg": "Ese firmante no está en el acta."}
    a.firmantes = json.dumps(firm, ensure_ascii=False)
    if all(x.get("firmado") for x in firm):
        a.estado = "firmada"
    db.commit()
    return {"ok": True,
            "msg": (f"✍️ Firmó {payload.rol}." +
                    (" El acta quedó completamente firmada." if a.estado == "firmada" else
                     f" Faltan: {', '.join(x['rol'] for x in firm if not x.get('firmado'))}."))}
