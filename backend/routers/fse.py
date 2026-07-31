"""Contabilidad del Fondo de Servicios Educativos (FSE): resumen, plan anual,
RP/CDP, ingresos/egresos e informe de auditoría con comparación SECOP."""
from datetime import date
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import CuentaFSE, PlanFSE, RegistroPresupuestal, MovimientoFSE, ConfigSistema
import metadatos

router = APIRouter()


def _default_ie(db, institucion_id):
    if institucion_id:
        return institucion_id
    from models import Institucion
    ie = db.query(Institucion).first()
    return ie.id if ie else 0


@router.get("/resumen")
def resumen(institucion_id: int | None = None, db: Session = Depends(get_db)):
    iid = _default_ie(db, institucion_id)
    movs = db.query(MovimientoFSE).filter(MovimientoFSE.institucion_id == iid,
                                          MovimientoFSE.estado != "anulado").all()
    ing = sum(m.valor for m in movs if m.tipo == "ingreso")
    egr = sum(m.valor for m in movs if m.tipo == "egreso")
    plan = db.query(PlanFSE).filter(PlanFSE.institucion_id == iid, PlanFSE.anio == 2026).all()
    plan_total = sum(p.valor_presupuestado for p in plan)
    return {"institucion_id": iid, "ingresos": round(ing), "egresos": round(egr),
            "saldo": round(ing - egr), "plan_total": round(plan_total), "n_movimientos": len(movs)}


@router.get("/cuentas")
def cuentas(institucion_id: int | None = None, db: Session = Depends(get_db)):
    iid = _default_ie(db, institucion_id)
    return [{"codigo": c.codigo, "nombre": c.nombre, "tipo": c.tipo}
            for c in db.query(CuentaFSE).filter(CuentaFSE.institucion_id == iid).order_by(CuentaFSE.codigo).all()]


@router.get("/plan")
def plan(institucion_id: int | None = None, db: Session = Depends(get_db)):
    iid = _default_ie(db, institucion_id)
    filas = db.query(PlanFSE).filter(PlanFSE.institucion_id == iid, PlanFSE.anio == 2026).all()
    filas.sort(key=lambda p: (p.prioridad, p.mes_planeado))
    return [{
        "id": p.id, "concepto": p.concepto, "cuenta": p.cuenta_codigo,
        "prioridad": p.prioridad, "mes": p.mes_planeado,
        "valor": round(p.valor_presupuestado), "estado": p.estado,
    } for p in filas]


@router.get("/rp")
def rps(institucion_id: int | None = None, db: Session = Depends(get_db)):
    iid = _default_ie(db, institucion_id)
    filas = db.query(RegistroPresupuestal).filter(RegistroPresupuestal.institucion_id == iid).order_by(
        RegistroPresupuestal.fecha.desc()).all()
    out = []
    for r in filas:
        desv = None
        if r.valor_secop and r.valor_secop > 0:
            desv = round((r.valor - r.valor_secop) / r.valor_secop * 100, 1)
        out.append({
            "id": r.id, "consecutivo": r.consecutivo, "tipo": r.tipo,
            "fecha": r.fecha.isoformat(), "objeto": r.objeto,
            "proveedor": r.proveedor, "nit": r.nit, "valor": round(r.valor),
            "valor_secop": round(r.valor_secop) if r.valor_secop else None,
            "secop_url": r.secop_url, "desviacion": desv, "estado": r.estado,
        })
    return out


@router.get("/movimientos")
def movimientos(institucion_id: int | None = None, limite: int = 100, db: Session = Depends(get_db)):
    iid = _default_ie(db, institucion_id)
    filas = db.query(MovimientoFSE).filter(MovimientoFSE.institucion_id == iid).order_by(
        MovimientoFSE.fecha.desc()).limit(limite).all()
    return [{
        "id": m.id, "fecha": m.fecha.isoformat(), "tipo": m.tipo, "cuenta": m.cuenta_codigo,
        "concepto": m.concepto, "proveedor": m.proveedor, "nit": m.nit,
        "valor": round(m.valor), "metodo": m.metodo, "comprobante": m.comprobante, "estado": m.estado,
    } for m in filas]


class MovIn(BaseModel):
    id: int | None = 0
    institucion_id: int
    fecha: str
    tipo: str
    cuenta: str | None = ""
    concepto: str
    proveedor: str | None = ""
    nit: str | None = ""
    valor: float
    metodo: str | None = ""
    comprobante: str | None = ""
    estado: str | None = "registrado"


@router.post("/movimientos/guardar")
def guardar_mov(payload: MovIn, db: Session = Depends(get_db)):
    if not payload.concepto.strip():
        return {"ok": False, "msg": "El concepto es obligatorio."}
    if payload.valor <= 0:
        return {"ok": False, "msg": "El valor debe ser mayor a cero."}
    try:
        f = date.fromisoformat(payload.fecha)
    except ValueError:
        f = date.today()
    if payload.id:
        m = db.query(MovimientoFSE).filter(MovimientoFSE.id == payload.id).first()
        if not m:
            return {"ok": False, "msg": "Movimiento no encontrado."}
    else:
        m = MovimientoFSE(institucion_id=payload.institucion_id)
        db.add(m)
    m.fecha = f
    m.tipo = payload.tipo if payload.tipo in ("ingreso", "egreso") else "egreso"
    m.cuenta_codigo = payload.cuenta or ""
    m.concepto = payload.concepto
    m.proveedor = payload.proveedor or ""
    m.nit = payload.nit or ""
    m.valor = payload.valor
    m.metodo = payload.metodo or ""
    m.comprobante = payload.comprobante or ""
    m.estado = payload.estado if payload.estado in ("registrado", "pagado", "anulado") else "registrado"
    db.commit()
    return {"ok": True, "msg": "Movimiento guardado."}


@router.get("/auditoria")
def auditoria(institucion_id: int | None = None, db: Session = Depends(get_db)):
    """Balance para auditoría: egresos con valor pagado vs precio SECOP y desviación."""
    iid = _default_ie(db, institucion_id)
    movs = db.query(MovimientoFSE).filter(MovimientoFSE.institucion_id == iid).all()
    rps = db.query(RegistroPresupuestal).filter(RegistroPresupuestal.institucion_id == iid).all()
    ing = sum(m.valor for m in movs if m.tipo == "ingreso" and m.estado != "anulado")
    egr = sum(m.valor for m in movs if m.tipo == "egreso" and m.estado != "anulado")
    filas = []
    for m in movs:
        if m.tipo != "egreso":
            continue
        secop = None
        secop_url = ""
        for r in rps:
            if r.valor_secop and (m.proveedor == r.proveedor or (r.objeto[:10].lower() in m.concepto.lower())):
                secop = r.valor_secop
                secop_url = r.secop_url
                break
        desv = round((m.valor - secop) / secop * 100, 1) if secop and secop > 0 else None
        filas.append({
            "fecha": m.fecha.isoformat(), "concepto": m.concepto, "proveedor": m.proveedor or "—",
            "nit": m.nit or "—", "cuenta": m.cuenta_codigo or "—", "comprobante": m.comprobante or "—",
            "valor": round(m.valor), "valor_secop": round(secop) if secop else None,
            "secop_url": secop_url, "desviacion": desv,
        })
    filas.sort(key=lambda x: x["fecha"])
    return {"totales": {"ingresos": round(ing), "egresos": round(egr), "saldo": round(ing - egr)}, "filas": filas}


# ═════════ PLAN DE COMPRAS: CRUD + importación PDF con IA (punto 9a) ═════════
from pydantic import BaseModel as _BMF
from models import PlanFSE as _PlanF
import metadatos as _metaf


class _PlanIn(_BMF):
    id: int | None = 0
    institucion_id: int
    concepto: str
    cuenta_codigo: str | None = ""
    prioridad: int | None = 2
    mes_planeado: int | None = 1
    valor_presupuestado: float | None = 0
    estado: str | None = "pendiente"


@router.post("/plan/guardar")
def plan_guardar(payload: _PlanIn, db: Session = Depends(get_db)):
    if not payload.concepto.strip():
        return {"ok": False, "msg": "El concepto es obligatorio."}
    if payload.id:
        p = db.query(_PlanF).filter(_PlanF.id == payload.id).first()
        if not p:
            return {"ok": False, "msg": "Ítem no encontrado."}
    else:
        p = _PlanF(institucion_id=payload.institucion_id, anio=2026)
        db.add(p)
    p.concepto = payload.concepto.strip()[:150]
    p.cuenta_codigo = payload.cuenta_codigo or ""
    p.prioridad = payload.prioridad if payload.prioridad in (1, 2, 3) else 2
    p.mes_planeado = max(1, min(12, payload.mes_planeado or 1))
    p.valor_presupuestado = max(0, payload.valor_presupuestado or 0)
    if payload.estado in ("pendiente", "parcial", "comprado"):
        p.estado = payload.estado
    db.commit()
    _metaf.registrar_evento("PLAN_COMPRAS", "Rectoría", institucion_id=payload.institucion_id,
                            payload={"concepto": p.concepto[:40]})
    return {"ok": True, "msg": f"Ítem del plan guardado: {p.concepto}.", "id": p.id}


class _PlanEstadoIn(_BMF):
    id: int
    estado: str


@router.post("/plan/estado")
def plan_estado(payload: _PlanEstadoIn, db: Session = Depends(get_db)):
    p = db.query(_PlanF).filter(_PlanF.id == payload.id).first()
    if not p:
        return {"ok": False, "msg": "Ítem no encontrado."}
    if payload.estado not in ("pendiente", "parcial", "comprado"):
        return {"ok": False, "msg": "Estado inválido."}
    p.estado = payload.estado
    db.commit()
    return {"ok": True, "msg": f"«{p.concepto[:40]}» → {payload.estado}."}


class _PlanDelIn(_BMF):
    id: int


@router.post("/plan/eliminar")
def plan_eliminar(payload: _PlanDelIn, db: Session = Depends(get_db)):
    p = db.query(_PlanF).filter(_PlanF.id == payload.id).first()
    if not p:
        return {"ok": False, "msg": "Ítem no encontrado."}
    db.delete(p)
    db.commit()
    return {"ok": True, "msg": "Ítem eliminado del plan."}


class _PlanPDFIn(_BMF):
    institucion_id: int
    archivo: str


@router.post("/plan/importar_pdf")
def plan_importar_pdf(payload: _PlanPDFIn, db: Session = Depends(get_db)):
    """Análisis del PDF del plan anual con IA (simulado): devuelve los ítems
    'detectados' en el documento para que el rector los revise y confirme.
    En producción: OCR + extracción estructurada con el motor GyverLabs."""
    base = [
        ("Dotación de textos y material bibliográfico", "1524", 1, 2, 7800000),
        ("Complemento alimentario PAE segundo semestre", "1520", 1, 7, 11500000),
        ("Mantenimiento eléctrico y luminarias", "1655", 2, 8, 4200000),
        ("Insumos de laboratorio de ciencias", "1510", 2, 9, 2900000),
        ("Conectividad e internet (mensualidades)", "2435", 1, 1, 5400000),
        ("Jornadas de formación docente", "1512", 3, 10, 1800000),
    ]
    items = [{"concepto": c, "cuenta_codigo": cta, "prioridad": pr,
              "mes_planeado": mes, "valor_presupuestado": val} for c, cta, pr, mes, val in base]
    _metaf.registrar_evento("PLAN_PDF_ANALIZADO", "Rectoría", institucion_id=payload.institucion_id,
                            payload={"archivo": payload.archivo[:60], "items": len(items)})
    return {"ok": True,
            "msg": f"🤖 Análisis de «{payload.archivo}» completado: {len(items)} ítems detectados. Revísalos y confirma cuáles agregar.",
            "items": items}


# ═════════ RUBROS PRESUPUESTALES (punto 17) ═════════
from models import RubroFSE as _Rubro


@router.get("/rubros")
def rubros(institucion_id: int, db: Session = Depends(get_db)):
    """Cada rubro con su presupuesto, lo ejecutado y el saldo disponible."""
    filas = db.query(_Rubro).filter(_Rubro.institucion_id == institucion_id).order_by(_Rubro.codigo).all()
    movs = db.query(MovimientoFSE).filter(MovimientoFSE.institucion_id == institucion_id).all()
    out = []
    for r in filas:
        ejec = sum(m.valor for m in movs if m.tipo == "egreso" and (m.rubro_id == r.id))
        ingr = sum(m.valor for m in movs if m.tipo == "ingreso" and (m.rubro_id == r.id))
        disponible = (r.presupuesto or 0) + ingr - ejec
        pct = round(100 * ejec / r.presupuesto, 1) if r.presupuesto else 0
        out.append({"id": r.id, "nombre": r.nombre, "codigo": r.codigo,
                    "presupuesto": round(r.presupuesto or 0), "ejecutado": round(ejec),
                    "ingresos": round(ingr), "disponible": round(disponible),
                    "pct_ejecutado": pct, "alerta": pct > 90})
    sin_rubro = sum(m.valor for m in movs if m.tipo == "egreso" and not m.rubro_id)
    return {"rubros": out, "egresos_sin_rubro": round(sin_rubro),
            "total_presupuesto": round(sum(r["presupuesto"] for r in out)),
            "total_ejecutado": round(sum(r["ejecutado"] for r in out)),
            "total_disponible": round(sum(r["disponible"] for r in out))}


class RubroIn(BaseModel):
    id: int | None = 0
    institucion_id: int
    nombre: str
    codigo: str | None = ""
    presupuesto: float | None = 0


@router.post("/rubros/guardar")
def rubro_guardar(payload: RubroIn, db: Session = Depends(get_db)):
    if not payload.nombre.strip():
        return {"ok": False, "msg": "El nombre del rubro es obligatorio."}
    if payload.id:
        r = db.query(_Rubro).filter(_Rubro.id == payload.id).first()
        if not r:
            return {"ok": False, "msg": "Rubro no encontrado."}
    else:
        r = _Rubro(institucion_id=payload.institucion_id)
        db.add(r)
    r.nombre = payload.nombre.strip()[:80]
    r.codigo = (payload.codigo or "").strip()[:20]
    r.presupuesto = max(0, payload.presupuesto or 0)
    db.commit()
    metadatos.registrar_evento("RUBRO_GUARDADO", "Rectoría", institucion_id=payload.institucion_id,
                               payload={"rubro": r.nombre})
    return {"ok": True, "id": r.id, "msg": f"Rubro «{r.nombre}» guardado con presupuesto de ${r.presupuesto:,.0f}.".replace(",", ".")}


class RubroDelIn(BaseModel):
    id: int


@router.post("/rubros/eliminar")
def rubro_eliminar(payload: RubroDelIn, db: Session = Depends(get_db)):
    r = db.query(_Rubro).filter(_Rubro.id == payload.id).first()
    if not r:
        return {"ok": False, "msg": "Rubro no encontrado."}
    n = db.query(MovimientoFSE).filter(MovimientoFSE.rubro_id == r.id).count()
    if n:
        return {"ok": False, "msg": f"No puedes eliminar «{r.nombre}»: tiene {n} movimiento(s) asignados. Reasígnalos primero para no perder la trazabilidad."}
    nombre = r.nombre
    db.delete(r)
    db.commit()
    return {"ok": True, "msg": f"Rubro «{nombre}» eliminado."}


# ═════════ RUBROS SEGÚN LA NORMA COLOMBIANA (punto 28) ═════════
# Estructura del Fondo de Servicios Educativos según el Decreto 1075 de 2015
# y el catálogo de cuentas de la Contaduría General de la Nación.
CATALOGO_RUBROS = {
    "ingresos": [
        {"codigo": "1.1", "nombre": "Recursos del Sistema General de Participaciones",
         "detalle": "Transferencia de gratuidad girada por la entidad territorial.",
         "tipo": "transferencia"},
        {"codigo": "1.2", "nombre": "Recursos propios",
         "detalle": "Certificados, constancias, arrendamientos, tienda escolar.",
         "tipo": "propio"},
        {"codigo": "1.3", "nombre": "Recursos de cooperación y donaciones",
         "detalle": "Aportes de terceros, ONG o empresa privada.", "tipo": "donacion"},
        {"codigo": "1.4", "nombre": "Rendimientos financieros",
         "detalle": "Intereses de la cuenta del fondo.", "tipo": "financiero"},
        {"codigo": "1.5", "nombre": "Excedentes de vigencias anteriores",
         "detalle": "Saldo no ejecutado que se incorpora al presupuesto.", "tipo": "excedente"},
    ],
    "gastos": [
        {"codigo": "2.1.1", "nombre": "Dotación pedagógica",
         "detalle": "Textos, material didáctico, elementos de laboratorio y deporte.",
         "grupo": "Funcionamiento", "tope_pct": None},
        {"codigo": "2.1.2", "nombre": "Mantenimiento de la planta física",
         "detalle": "Reparaciones locativas que no impliquen ampliación.",
         "grupo": "Funcionamiento", "tope_pct": None},
        {"codigo": "2.1.3", "nombre": "Servicios públicos",
         "detalle": "Energía, acueducto, gas, internet y telefonía.",
         "grupo": "Funcionamiento", "tope_pct": None},
        {"codigo": "2.1.4", "nombre": "Seguros y pólizas",
         "detalle": "Amparo de bienes de la institución.", "grupo": "Funcionamiento",
         "tope_pct": None},
        {"codigo": "2.1.5", "nombre": "Impresos, publicaciones y papelería",
         "detalle": "Formatos, certificados, papelería administrativa.",
         "grupo": "Funcionamiento", "tope_pct": None},
        {"codigo": "2.2.1", "nombre": "Apoyo académico y salidas pedagógicas",
         "detalle": "Transporte y logística de actividades curriculares.",
         "grupo": "Actividades pedagógicas", "tope_pct": None},
        {"codigo": "2.2.2", "nombre": "Proyectos transversales",
         "detalle": "Convivencia, sexualidad, ambiente, democracia.",
         "grupo": "Actividades pedagógicas", "tope_pct": None},
        {"codigo": "2.3.1", "nombre": "Alimentación escolar (PAE)",
         "detalle": "Complemento alimentario cuando el fondo aporta.",
         "grupo": "Bienestar", "tope_pct": None},
        {"codigo": "2.3.2", "nombre": "Transporte escolar",
         "detalle": "Rutas para estudiantes de zona rural dispersa.",
         "grupo": "Bienestar", "tope_pct": None},
        {"codigo": "2.4.1", "nombre": "Contratación de servicios técnicos",
         "detalle": "Servicios de apoyo a la gestión (no docentes de planta).",
         "grupo": "Servicios", "tope_pct": None},
        {"codigo": "2.5.1", "nombre": "Adquisición de bienes muebles",
         "detalle": "Equipos de cómputo, mobiliario escolar.",
         "grupo": "Inversión", "tope_pct": None},
    ],
}


@router.get("/rubros/catalogo")
def rubros_catalogo(db: Session = Depends(get_db)):
    """Catálogo oficial para que el rector no invente nombres de rubros."""
    c = db.query(ConfigSistema).filter(ConfigSistema.clave == "smmlv").first()
    t = db.query(ConfigSistema).filter(ConfigSistema.clave == "tope_fse_smmlv").first()
    smmlv = float(c.valor) if c else 1_623_500.0
    tope = float(t.valor) if t else 20.0
    return {
        "ingresos": CATALOGO_RUBROS["ingresos"],
        "gastos": CATALOGO_RUBROS["gastos"],
        "grupos": sorted({g["grupo"] for g in CATALOGO_RUBROS["gastos"]}),
        "marco_legal": {
            "decreto": "Decreto 1075 de 2015 (compilatorio) y Decreto 4791 de 2008",
            "tope_contratacion": f"{tope:.0f} SMMLV = ${tope * smmlv:,.0f}".replace(",", "."),
            "reglas": [
                "El presupuesto lo aprueba el Consejo Directivo antes de iniciar la vigencia.",
                "Todo gasto debe estar en un rubro aprobado; no se puede gastar por fuera.",
                "Los traslados entre rubros requieren acuerdo del Consejo Directivo.",
                "Los recursos de gratuidad no pueden pagar nómina docente ni obra nueva.",
                "Cada egreso necesita CDP previo y su soporte documental.",
            ],
        },
    }


class RubroNormaIn(BaseModel):
    institucion_id: int
    codigo: str
    nombre: str | None = None
    presupuesto: float = 0
    grupo: str | None = None


@router.post("/rubros/desde_catalogo")
def rubro_desde_catalogo(payload: RubroNormaIn, db: Session = Depends(get_db)):
    """Crea el rubro con el código y nombre oficial, no uno inventado."""
    ref = next((x for x in CATALOGO_RUBROS["gastos"] + CATALOGO_RUBROS["ingresos"]
                if x["codigo"] == payload.codigo), None)
    if not ref:
        return {"ok": False, "msg": "Ese código no está en el catálogo oficial."}
    ya = db.query(_Rubro).filter(_Rubro.institucion_id == payload.institucion_id,
                                 _Rubro.codigo == payload.codigo).first()
    if ya:
        return {"ok": False, "msg": f"El rubro {payload.codigo} ya existe en esta institución."}
    r = _Rubro(institucion_id=payload.institucion_id, codigo=payload.codigo,
               nombre=payload.nombre or ref["nombre"],
               presupuesto=max(0, payload.presupuesto))
    db.add(r)
    db.commit()
    metadatos.registrar_evento("RUBRO_CATALOGO", "Rectoría",
                               institucion_id=payload.institucion_id,
                               payload={"codigo": payload.codigo})
    return {"ok": True, "id": r.id,
            "msg": f"Rubro {payload.codigo} · {r.nombre} creado con ${r.presupuesto:,.0f}.".replace(",", ".")}


@router.get("/presupuesto")
def presupuesto(institucion_id: int, db: Session = Depends(get_db)):
    """Ejecución presupuestal como la pide la Contraloría: por rubro y grupo."""
    rubros = db.query(_Rubro).filter(_Rubro.institucion_id == institucion_id).order_by(
        _Rubro.codigo).all()
    movs = db.query(MovimientoFSE).filter(MovimientoFSE.institucion_id == institucion_id).all()
    ref_por_cod = {x["codigo"]: x for x in CATALOGO_RUBROS["gastos"] + CATALOGO_RUBROS["ingresos"]}
    filas = []
    for r in rubros:
        ejec = sum(m.valor for m in movs if m.tipo == "egreso" and m.rubro_id == r.id)
        ingr = sum(m.valor for m in movs if m.tipo == "ingreso" and m.rubro_id == r.id)
        ref = ref_por_cod.get(r.codigo or "", {})
        disp = (r.presupuesto or 0) + ingr - ejec
        filas.append({
            "id": r.id, "codigo": r.codigo, "nombre": r.nombre,
            "grupo": ref.get("grupo", "Otros"), "detalle": ref.get("detalle"),
            "presupuesto": round(r.presupuesto or 0), "ejecutado": round(ejec),
            "ingresos": round(ingr), "disponible": round(disp),
            "pct": round(100 * ejec / r.presupuesto, 1) if r.presupuesto else 0,
            "sobre_ejecutado": disp < 0,
            "n_movimientos": sum(1 for m in movs if m.rubro_id == r.id),
        })
    por_grupo = {}
    for f in filas:
        g = por_grupo.setdefault(f["grupo"], {"grupo": f["grupo"], "presupuesto": 0,
                                              "ejecutado": 0, "disponible": 0, "n": 0})
        g["presupuesto"] += f["presupuesto"]
        g["ejecutado"] += f["ejecutado"]
        g["disponible"] += f["disponible"]
        g["n"] += 1
    for g in por_grupo.values():
        g["pct"] = round(100 * g["ejecutado"] / g["presupuesto"], 1) if g["presupuesto"] else 0
    total_p = sum(f["presupuesto"] for f in filas)
    total_e = sum(f["ejecutado"] for f in filas)
    sin_rubro = sum(m.valor for m in movs if m.tipo == "egreso" and not m.rubro_id)
    return {
        "rubros": filas,
        "por_grupo": sorted(por_grupo.values(), key=lambda x: -x["presupuesto"]),
        "totales": {
            "presupuesto": round(total_p), "ejecutado": round(total_e),
            "disponible": round(total_p - total_e),
            "pct_ejecucion": round(100 * total_e / total_p, 1) if total_p else 0,
            "sin_rubro": round(sin_rubro),
            "sobre_ejecutados": sum(1 for f in filas if f["sobre_ejecutado"]),
        },
        "alertas": [
            f"El rubro {f['codigo']} «{f['nombre']}» está sobre-ejecutado en ${abs(f['disponible']):,.0f}".replace(",", ".")
            for f in filas if f["sobre_ejecutado"]
        ] + ([f"Hay ${sin_rubro:,.0f} en egresos sin rubro asignado".replace(",", ".")] if sin_rubro else []),
    }


# ═════════ TRASLADO DE RUBROS con control de legalidad (punto 16) ═════════
from models import TrasladoRubro as _Trasl
from datetime import datetime as _dtT

# Traslados que la norma mira con lupa
REGLAS_TRASLADO = [
    {"clave": "pae_a_otro", "origen": ["4-PAE", "2.3.1"], "riesgo": "alto",
     "texto": "Sacar plata de alimentación escolar para otra cosa es de los hallazgos más graves: afecta directamente a los estudiantes."},
    {"clave": "didactico_a_admin", "origen": ["3-DIDA", "2.1.1"], "destino": ["2.1.5", "1-FUNC"],
     "riesgo": "medio",
     "texto": "Pasar recursos de material didáctico a gastos administrativos se interpreta como que lo pedagógico quedó de último."},
    {"clave": "inversion_a_funcionamiento", "origen": ["2.5.1"], "riesgo": "medio",
     "texto": "Trasladar de inversión a funcionamiento reduce la capacidad instalada de la institución."},
]
UMBRAL_ALTO_PCT = 30      # más del 30% del rubro origen ya es señal


@router.get("/traslados")
def traslados(institucion_id: int, db: Session = Depends(get_db)):
    filas = db.query(_Trasl).filter(_Trasl.institucion_id == institucion_id).order_by(
        _Trasl.id.desc()).limit(40).all()
    rub = {r.id: r for r in db.query(_Rubro).filter(_Rubro.institucion_id == institucion_id).all()}
    return {"traslados": [{
        "id": t.id, "valor": round(t.valor),
        "origen": rub[t.rubro_origen_id].nombre if t.rubro_origen_id in rub else "—",
        "origen_codigo": rub[t.rubro_origen_id].codigo if t.rubro_origen_id in rub else "",
        "destino": rub[t.rubro_destino_id].nombre if t.rubro_destino_id in rub else "—",
        "destino_codigo": rub[t.rubro_destino_id].codigo if t.rubro_destino_id in rub else "",
        "justificacion": t.justificacion, "riesgo": t.riesgo,
        "alertas": json.loads(t.alertas) if t.alertas else [],
        "estado": t.estado, "acta_consejo": t.acta_consejo,
        "solicitado_por": t.solicitado_por,
        "fecha": t.fecha.isoformat(sep=" ", timespec="minutes") if t.fecha else "",
    } for t in filas],
        "n_pendientes": sum(1 for t in filas if t.estado == "pendiente")}


class TrasladoIn(BaseModel):
    institucion_id: int
    rubro_origen_id: int
    rubro_destino_id: int
    valor: float
    justificacion: str
    solicitado_por: str | None = "Rectoría"
    acta_consejo: str | None = ""
    acepto_riesgo: bool = False


@router.post("/traslados/analizar")
def traslado_analizar(payload: TrasladoIn, db: Session = Depends(get_db)):
    """Antes de mover un peso: ¿esto se puede defender en una auditoría?"""
    o = db.query(_Rubro).filter(_Rubro.id == payload.rubro_origen_id).first()
    d = db.query(_Rubro).filter(_Rubro.id == payload.rubro_destino_id).first()
    if not o or not d:
        return {"ok": False, "msg": "Rubro no encontrado."}
    if o.id == d.id:
        return {"ok": False, "msg": "El rubro de origen y destino no pueden ser el mismo."}
    movs = db.query(MovimientoFSE).filter(MovimientoFSE.institucion_id == payload.institucion_id).all()
    ejec_o = sum(m.valor for m in movs if m.tipo == "egreso" and m.rubro_id == o.id)
    disp_o = (o.presupuesto or 0) - ejec_o
    alertas = []
    riesgo = "bajo"
    if payload.valor > disp_o:
        return {"ok": False,
                "msg": f"⛔ El rubro «{o.nombre}» solo tiene ${disp_o:,.0f} disponibles. No puedes trasladar ${payload.valor:,.0f}.".replace(",", ".")}
    pct = round(100 * payload.valor / (o.presupuesto or 1), 1)
    if pct > UMBRAL_ALTO_PCT:
        riesgo = "alto"
        alertas.append({"nivel": "alto",
                        "texto": f"Estás moviendo el {pct}% del rubro «{o.nombre}». Traslados superiores al {UMBRAL_ALTO_PCT}% indican que el presupuesto se planeó mal, y eso se anota como observación."})
    elif pct > 15:
        riesgo = "medio"
        alertas.append({"nivel": "medio",
                        "texto": f"Vas a mover el {pct}% del rubro. Justifica muy bien por qué cambió la necesidad."})
    for r in REGLAS_TRASLADO:
        if (o.codigo or "") in r.get("origen", []):
            if "destino" in r and (d.codigo or "") not in r["destino"]:
                continue
            if r["riesgo"] == "alto":
                riesgo = "alto"
            elif riesgo == "bajo":
                riesgo = "medio"
            alertas.append({"nivel": r["riesgo"], "texto": r["texto"]})
    if ejec_o > 0 and payload.valor > disp_o * 0.8:
        alertas.append({"nivel": "medio",
                        "texto": f"El rubro origen ya ejecutó ${ejec_o:,.0f}. Dejarlo casi en cero puede impedir pagos comprometidos.".replace(",", ".")})
    if not payload.acta_consejo:
        alertas.append({"nivel": "alto",
                        "texto": "Todo traslado presupuestal requiere ACUERDO DEL CONSEJO DIRECTIVO. Sin el número de acta, el movimiento es irregular."})
        riesgo = "alto"
    if not alertas:
        alertas.append({"nivel": "ok",
                        "texto": "El traslado está dentro de lo razonable y tiene respaldo. Documenta el acta y procede."})
    return {"ok": True, "riesgo": riesgo, "alertas": alertas,
            "disponible_origen": round(disp_o), "pct_del_rubro": pct,
            "requiere_confirmacion": riesgo in ("alto", "medio"),
            "recomendacion": ("No lo hagas sin acuerdo del Consejo Directivo y sin dejar la "
                              "justificación técnica por escrito." if riesgo == "alto" else
                              "Deja la justificación en el expediente y notifica al Consejo."
                              if riesgo == "medio" else
                              "Puedes proceder documentando el acta.")}


@router.post("/traslados/ejecutar")
def traslado_ejecutar(payload: TrasladoIn, db: Session = Depends(get_db)):
    an = traslado_analizar(payload, db)
    if not an.get("ok"):
        return an
    if an["requiere_confirmacion"] and not payload.acepto_riesgo:
        return {"ok": False, "requiere_confirmacion": True, "riesgo": an["riesgo"],
                "alertas": an["alertas"],
                "msg": "⚠️ Este traslado tiene observaciones. Revísalas y confirma expresamente si aun así quieres hacerlo."}
    if not payload.justificacion.strip() or len(payload.justificacion.strip()) < 20:
        return {"ok": False,
                "msg": "La justificación debe explicar por qué cambió la necesidad (mínimo 20 caracteres). Es lo que te defiende después."}
    o = db.query(_Rubro).filter(_Rubro.id == payload.rubro_origen_id).first()
    d = db.query(_Rubro).filter(_Rubro.id == payload.rubro_destino_id).first()
    o.presupuesto = (o.presupuesto or 0) - payload.valor
    d.presupuesto = (d.presupuesto or 0) + payload.valor
    t = _Trasl(institucion_id=payload.institucion_id, rubro_origen_id=o.id,
               rubro_destino_id=d.id, valor=payload.valor,
               justificacion=payload.justificacion.strip()[:800],
               riesgo=an["riesgo"], alertas=json.dumps(an["alertas"], ensure_ascii=False),
               acepto_riesgo=payload.acepto_riesgo,
               acta_consejo=(payload.acta_consejo or "").strip()[:60] or None,
               solicitado_por=payload.solicitado_por, estado="ejecutado",
               fecha=_dtT.now(), fecha_ejecucion=_dtT.now())
    db.add(t)
    db.commit()
    metadatos.registrar_evento("TRASLADO_RUBRO", payload.solicitado_por or "Rectoría",
                               institucion_id=payload.institucion_id,
                               payload={"valor": payload.valor, "riesgo": an["riesgo"]})
    return {"ok": True,
            "msg": (f"💱 Traslado ejecutado: ${payload.valor:,.0f} de «{o.nombre}» a «{d.nombre}». ".replace(",", ".")
                    + (f"Respaldado con el acta {t.acta_consejo}." if t.acta_consejo else
                       "⚠️ Sin acta del Consejo: consíguela cuanto antes.")
                    + " Todo quedó registrado con su justificación.")}
