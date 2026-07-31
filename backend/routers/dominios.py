"""Dominios, DNS, suscripciones y modo sin internet.

Puntos 1, 2, 3 del feedback + operacion offline:

  - El super admin configura el dominio de cada institucion y el sistema le
    entrega los registros DNS exactos que debe pegar en Hostinger, GoDaddy,
    Namecheap o Cloudflare.
  - Tres formas de montarlo segun donde este hoy la pagina del colegio
    (normalmente WordPress).
  - Suscripcion por tenant: desde cuando, cuanto falta, cuanto paga.
  - Cola de sincronizacion: lo que el docente hace SIN internet se guarda y
    sube cuando vuelve la senal.
"""
import json
import re
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (Tenant, Institucion, ConfigDominio, Suscripcion, ColaOffline,
                    Estudiante, Personal, Asistencia, NotaPeriodo,
                    MensajeWhatsApp, NotificacionCoord)
import metadatos

router = APIRouter()

IP_DEMO = "203.0.113.45"        # IP de ejemplo del servidor (documentacion RFC 5737)

PROVEEDORES = {
    "hostinger": {"label": "Hostinger", "panel": "hPanel → Dominios → Zona DNS",
                  "ayuda": "https://support.hostinger.com/es/articles/1583227"},
    "godaddy":   {"label": "GoDaddy", "panel": "Mis productos → DNS → Administrar zonas",
                  "ayuda": "https://co.godaddy.com/help/administrar-registros-dns-680"},
    "namecheap": {"label": "Namecheap", "panel": "Domain List → Manage → Advanced DNS",
                  "ayuda": "https://www.namecheap.com/support/knowledgebase/"},
    "cloudflare": {"label": "Cloudflare", "panel": "DNS → Records",
                   "ayuda": "https://developers.cloudflare.com/dns/"},
    "otro":      {"label": "Otro proveedor", "panel": "Zona DNS del proveedor", "ayuda": None},
}

MODOS = {
    "subdominio": {
        "label": "Subdominio (recomendado)",
        "desc": "La pagina web del colegio sigue igual en WordPress y el sistema vive en un subdominio.",
        "ejemplo": "sistema.ietac.edu.co",
        "ventaja": "No se toca la web actual. Es el cambio mas seguro y el mas rapido de montar.",
    },
    "dominio_propio": {
        "label": "Dominio completo",
        "desc": "Todo el dominio apunta al sistema. Solo si el colegio no tiene web o la va a reemplazar.",
        "ejemplo": "ietac.edu.co",
        "ventaja": "Marca blanca total: la institucion se ve como dueña de todo.",
    },
    "ruta": {
        "label": "Subcarpeta del sitio actual",
        "desc": "El sistema se sirve dentro de la web existente mediante proxy inverso.",
        "ejemplo": "ietac.edu.co/plataforma",
        "ventaja": "Un solo dominio, pero requiere tocar la configuracion del servidor de WordPress.",
    },
}


def _registros_dns(cfg, dominio_raiz, sub):
    """Los registros exactos que hay que pegar en el panel del proveedor."""
    regs = []
    if cfg.modo_montaje == "subdominio":
        regs.append({"tipo": "A", "nombre": sub or "sistema",
                     "valor": cfg.ip_servidor or IP_DEMO, "ttl": "3600",
                     "para": f"Hace que {sub or 'sistema'}.{dominio_raiz} llegue al sistema."})
        regs.append({"tipo": "CNAME", "nombre": f"www.{sub or 'sistema'}",
                     "valor": f"{sub or 'sistema'}.{dominio_raiz}", "ttl": "3600",
                     "para": "Para que funcione también con www adelante."})
    elif cfg.modo_montaje == "dominio_propio":
        regs.append({"tipo": "A", "nombre": "@", "valor": cfg.ip_servidor or IP_DEMO,
                     "ttl": "3600", "para": f"Apunta {dominio_raiz} al servidor del sistema."})
        regs.append({"tipo": "CNAME", "nombre": "www", "valor": dominio_raiz, "ttl": "3600",
                     "para": "Para que www.dominio también entre."})
    else:
        regs.append({"tipo": "—", "nombre": "(no requiere DNS)", "valor": "proxy inverso",
                     "ttl": "—",
                     "para": "En este modo se configura el servidor web, no el DNS."})
    regs.append({"tipo": "TXT", "nombre": "_gyver-verify",
                 "valor": f"gyver-verify={abs(hash(dominio_raiz)) % 10**12:012d}", "ttl": "3600",
                 "para": "Prueba que el dominio es de la institución. Se valida al conectar."})
    return regs


@router.get("/catalogo")
def catalogo():
    return {"proveedores": [{"id": k, **v} for k, v in PROVEEDORES.items()],
            "modos": [{"id": k, **v} for k, v in MODOS.items()],
            "ip_servidor": IP_DEMO}


@router.get("/")
def listar(db: Session = Depends(get_db)):
    """Todos los tenants con su dominio, su DNS y su suscripción (punto 2)."""
    hoy = date.today()
    out = []
    for t in db.query(Tenant).order_by(Tenant.tipo.desc(), Tenant.nombre).all():
        cfg = db.query(ConfigDominio).filter(ConfigDominio.tenant_id == t.id).first()
        sus = db.query(Suscripcion).filter(Suscripcion.tenant_id == t.id).first()
        ie = db.query(Institucion).filter(Institucion.id == t.institucion_id).first()
        n_est = db.query(Estudiante).filter(Estudiante.institucion_id == t.institucion_id).count() if ie else 0
        n_per = db.query(Personal).filter(Personal.institucion_id == t.institucion_id).count() if ie else 0
        dias = (sus.fecha_fin - hoy).days if (sus and sus.fecha_fin) else None
        pagado = 0
        if sus and sus.facturas:
            try:
                pagado = sum(f.get("valor", 0) for f in json.loads(sus.facturas))
            except Exception:
                pagado = 0
        out.append({
            "tenant_id": t.id, "nombre": t.nombre, "tipo": t.tipo,
            "dominio": t.dominio, "color": t.color, "logo": t.logo,
            "estado": t.estado, "institucion_id": t.institucion_id,
            "n_estudiantes": n_est, "n_personal": n_per,
            "dns": {
                "configurado": bool(cfg),
                "dominio": cfg.dominio if cfg else None,
                "subdominio": cfg.subdominio if cfg else None,
                "proveedor": cfg.proveedor if cfg else None,
                "modo": cfg.modo_montaje if cfg else None,
                "estado_dns": cfg.estado_dns if cfg else "sin_configurar",
                "ssl": cfg.ssl_estado if cfg else "pendiente",
                "verificado": bool(cfg.verificado) if cfg else False,
                "wordpress_url": cfg.wordpress_url if cfg else None,
                "integracion_wp": cfg.integracion_wp if cfg else "ninguna",
            },
            "suscripcion": {
                "activa": bool(sus),
                "plan": sus.plan if sus else None,
                "inicio": sus.fecha_inicio.isoformat() if (sus and sus.fecha_inicio) else None,
                "fin": sus.fecha_fin.isoformat() if (sus and sus.fecha_fin) else None,
                "dias_restantes": dias,
                "por_vencer": dias is not None and 0 <= dias <= 45,
                "vencida": dias is not None and dias < 0,
                "valor_anual": round(sus.valor_anual) if sus else 0,
                "pagado": round(pagado),
                "saldo": round((sus.valor_anual or 0) - pagado) if sus else 0,
                "estado": sus.estado if sus else None,
            },
        })
    tot_anual = sum(x["suscripcion"]["valor_anual"] for x in out)
    tot_pagado = sum(x["suscripcion"]["pagado"] for x in out)
    return {
        "tenants": out,
        "resumen": {
            "n_tenants": len(out),
            "con_dominio": sum(1 for x in out if x["dns"]["configurado"]),
            "dns_activos": sum(1 for x in out if x["dns"]["estado_dns"] == "activo"),
            "por_vencer": sum(1 for x in out if x["suscripcion"]["por_vencer"]),
            "vencidas": sum(1 for x in out if x["suscripcion"]["vencida"]),
            "ingreso_anual": tot_anual, "recaudado": tot_pagado,
            "por_cobrar": tot_anual - tot_pagado,
            "total_estudiantes": sum(x["n_estudiantes"] for x in out),
        },
    }


@router.get("/detalle")
def detalle(tenant_id: int, db: Session = Depends(get_db)):
    """Configuración completa + los registros DNS listos para copiar."""
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        return {"ok": False, "msg": "Tenant no encontrado."}
    cfg = db.query(ConfigDominio).filter(ConfigDominio.tenant_id == tenant_id).first()
    if not cfg:
        base = (t.dominio or "institucion.edu.co")
        partes = base.split(".")
        sub = partes[0] if len(partes) > 2 else "sistema"
        raiz = ".".join(partes[1:]) if len(partes) > 2 else base
        cfg = ConfigDominio(tenant_id=tenant_id, dominio=raiz, subdominio=sub,
                            proveedor="hostinger", modo_montaje="subdominio",
                            ip_servidor=IP_DEMO, estado_dns="sin_configurar")
    sus = db.query(Suscripcion).filter(Suscripcion.tenant_id == tenant_id).first()
    facturas = []
    if sus and sus.facturas:
        try:
            facturas = json.loads(sus.facturas)
        except Exception:
            facturas = []
    url_final = (f"https://{cfg.subdominio}.{cfg.dominio}" if cfg.modo_montaje == "subdominio"
                 else f"https://{cfg.dominio}" if cfg.modo_montaje == "dominio_propio"
                 else f"https://{cfg.dominio}/plataforma")
    return {
        "ok": True, "tenant": {"id": t.id, "nombre": t.nombre, "tipo": t.tipo,
                               "color": t.color, "logo": t.logo, "estado": t.estado},
        "config": {
            "dominio": cfg.dominio, "subdominio": cfg.subdominio,
            "proveedor": cfg.proveedor, "modo_montaje": cfg.modo_montaje,
            "ip_servidor": cfg.ip_servidor or IP_DEMO,
            "estado_dns": cfg.estado_dns, "ssl_estado": cfg.ssl_estado,
            "verificado": bool(cfg.verificado),
            "wordpress_url": cfg.wordpress_url, "integracion_wp": cfg.integracion_wp,
            "notas": cfg.notas,
            "ultima_verificacion": cfg.ultima_verificacion.isoformat(sep=" ", timespec="minutes") if cfg.ultima_verificacion else None,
        },
        "url_final": url_final,
        "registros_dns": _registros_dns(cfg, cfg.dominio, cfg.subdominio),
        "proveedor_info": PROVEEDORES.get(cfg.proveedor or "otro"),
        "modo_info": MODOS.get(cfg.modo_montaje or "subdominio"),
        "suscripcion": {
            "plan": sus.plan if sus else "institucional",
            "inicio": sus.fecha_inicio.isoformat() if (sus and sus.fecha_inicio) else None,
            "fin": sus.fecha_fin.isoformat() if (sus and sus.fecha_fin) else None,
            "valor_anual": round(sus.valor_anual) if sus else 0,
            "estado": sus.estado if sus else "sin_suscripcion",
            "n_usuarios_incluidos": sus.n_usuarios_incluidos if sus else 100,
            "facturas": facturas,
        },
    }


class DominioIn(BaseModel):
    tenant_id: int
    dominio: str
    subdominio: str | None = "sistema"
    proveedor: str | None = "hostinger"
    modo_montaje: str | None = "subdominio"
    ip_servidor: str | None = None
    wordpress_url: str | None = ""
    integracion_wp: str | None = "ninguna"
    notas: str | None = ""


@router.post("/guardar")
def guardar(payload: DominioIn, db: Session = Depends(get_db)):
    dom = (payload.dominio or "").strip().lower().replace("https://", "").replace("http://", "").strip("/")
    if not re.match(r"^[a-z0-9][a-z0-9\-.]*\.[a-z]{2,}$", dom):
        return {"ok": False, "msg": "El dominio no es válido. Ejemplo correcto: ietac.edu.co"}
    t = db.query(Tenant).filter(Tenant.id == payload.tenant_id).first()
    if not t:
        return {"ok": False, "msg": "Tenant no encontrado."}
    sub = re.sub(r"[^a-z0-9-]", "", (payload.subdominio or "sistema").strip().lower()) or "sistema"
    otro = db.query(ConfigDominio).filter(ConfigDominio.dominio == dom,
                                          ConfigDominio.subdominio == sub,
                                          ConfigDominio.tenant_id != payload.tenant_id).first()
    if otro:
        return {"ok": False, "msg": f"Ese dominio ya está asignado a otra institución."}
    cfg = db.query(ConfigDominio).filter(ConfigDominio.tenant_id == payload.tenant_id).first()
    if not cfg:
        cfg = ConfigDominio(tenant_id=payload.tenant_id)
        db.add(cfg)
    cfg.dominio = dom
    cfg.subdominio = sub
    cfg.proveedor = payload.proveedor if payload.proveedor in PROVEEDORES else "otro"
    cfg.modo_montaje = payload.modo_montaje if payload.modo_montaje in MODOS else "subdominio"
    cfg.ip_servidor = (payload.ip_servidor or IP_DEMO).strip()
    cfg.wordpress_url = (payload.wordpress_url or "").strip()[:200] or None
    cfg.integracion_wp = payload.integracion_wp or "ninguna"
    cfg.notas = (payload.notas or "").strip()[:600] or None
    if cfg.estado_dns == "sin_configurar":
        cfg.estado_dns = "pendiente"
    t.dominio = f"{sub}.{dom}" if cfg.modo_montaje == "subdominio" else dom
    db.commit()
    metadatos.registrar_evento("DOMINIO_CONFIGURADO", "Súper Admin",
                               payload={"dominio": t.dominio})
    return {"ok": True, "msg": f"🌐 Dominio configurado: {t.dominio}. Ahora copia los registros DNS en el panel de {PROVEEDORES.get(cfg.proveedor, {}).get('label', 'tu proveedor')}."}


class VerificarIn(BaseModel):
    tenant_id: int


@router.post("/verificar")
def verificar(payload: VerificarIn, db: Session = Depends(get_db)):
    """Comprueba si el DNS ya apunta al servidor (simulado en la demo)."""
    cfg = db.query(ConfigDominio).filter(ConfigDominio.tenant_id == payload.tenant_id).first()
    if not cfg:
        return {"ok": False, "msg": "Primero configura el dominio."}
    # En la demo se simula la propagación: pendiente -> propagando -> activo
    orden = {"sin_configurar": "pendiente", "pendiente": "propagando",
             "propagando": "activo", "activo": "activo", "error": "propagando"}
    cfg.estado_dns = orden.get(cfg.estado_dns, "pendiente")
    cfg.ultima_verificacion = datetime.now()
    if cfg.estado_dns == "activo":
        cfg.verificado = True
        cfg.ssl_estado = "activo"
    db.commit()
    MSG = {
        "pendiente": "⏳ Todavía no se ven los registros. Pégalos en tu proveedor y vuelve a verificar en unos minutos.",
        "propagando": "🔄 Los registros ya aparecen pero están propagándose. Puede tardar de 5 minutos a 24 horas.",
        "activo": "✅ ¡Dominio activo y con certificado SSL! La institución ya puede entrar por su propia dirección.",
    }
    return {"ok": True, "estado": cfg.estado_dns, "ssl": cfg.ssl_estado,
            "msg": MSG.get(cfg.estado_dns, "Verificando…")}


class SuscripcionIn(BaseModel):
    tenant_id: int
    plan: str | None = "institucional"
    fecha_inicio: str | None = None
    meses: int | None = 12
    valor_anual: float | None = 0
    n_usuarios_incluidos: int | None = 100
    notas: str | None = ""


@router.post("/suscripcion/guardar")
def suscripcion_guardar(payload: SuscripcionIn, db: Session = Depends(get_db)):
    s = db.query(Suscripcion).filter(Suscripcion.tenant_id == payload.tenant_id).first()
    if not s:
        s = Suscripcion(tenant_id=payload.tenant_id, facturas=json.dumps([]))
        db.add(s)
    s.plan = payload.plan or "institucional"
    try:
        ini = date.fromisoformat(payload.fecha_inicio) if payload.fecha_inicio else date.today()
    except ValueError:
        ini = date.today()
    s.fecha_inicio = ini
    s.fecha_fin = ini + timedelta(days=30 * max(1, payload.meses or 12))
    s.valor_anual = max(0, payload.valor_anual or 0)
    s.n_usuarios_incluidos = payload.n_usuarios_incluidos or 100
    s.notas = (payload.notas or "").strip()[:400] or None
    dias = (s.fecha_fin - date.today()).days
    s.estado = "vencida" if dias < 0 else ("por_vencer" if dias <= 45 else "activa")
    db.commit()
    return {"ok": True,
            "msg": f"Contrato guardado: del {s.fecha_inicio} al {s.fecha_fin} ({dias} días restantes)."}


class FacturaIn(BaseModel):
    tenant_id: int
    valor: float
    concepto: str | None = ""
    fecha: str | None = None


@router.post("/suscripcion/pago")
def suscripcion_pago(payload: FacturaIn, db: Session = Depends(get_db)):
    s = db.query(Suscripcion).filter(Suscripcion.tenant_id == payload.tenant_id).first()
    if not s:
        return {"ok": False, "msg": "Esta institución no tiene contrato registrado."}
    try:
        f = json.loads(s.facturas) if s.facturas else []
    except Exception:
        f = []
    f.append({"fecha": payload.fecha or date.today().isoformat(),
              "valor": round(payload.valor), "concepto": (payload.concepto or "Pago de suscripción")[:120]})
    s.facturas = json.dumps(f, ensure_ascii=False)
    db.commit()
    total = sum(x.get("valor", 0) for x in f)
    return {"ok": True,
            "msg": f"💰 Pago registrado. Recaudado: ${total:,.0f} de ${s.valor_anual:,.0f}.".replace(",", ".")}


# ═════════════════ MODO SIN INTERNET ═════════════════
class ColaIn(BaseModel):
    institucion_id: int | None = None
    origen: str | None = ""
    acciones: list          # [{tipo, payload, creado_en}]


@router.post("/offline/sincronizar")
def offline_sincronizar(payload: ColaIn, db: Session = Depends(get_db)):
    """Sube lo que el docente hizo sin internet.

    El navegador guarda cada acción localmente mientras no hay señal; cuando
    vuelve, envía todo aquí de una vez. Se procesa en orden y se responde qué
    se aplicó, para que el docente vea que su trabajo no se perdió.
    """
    aplicadas, fallidas, detalles = 0, 0, []
    for acc in (payload.acciones or [])[:300]:
        tipo = acc.get("tipo")
        datos = acc.get("payload") or {}
        creado = acc.get("creado_en")
        try:
            ts = datetime.fromisoformat(creado) if creado else datetime.now()
        except Exception:
            ts = datetime.now()
        registro = ColaOffline(institucion_id=payload.institucion_id, origen=payload.origen,
                               tipo=tipo or "otro", payload=json.dumps(datos, ensure_ascii=False),
                               creado_en=ts)
        db.add(registro)
        try:
            if tipo == "asistencia":
                sid = datos.get("salon_id")
                fecha = date.fromisoformat(datos.get("fecha")) if datos.get("fecha") else date.today()
                n = 0
                for fila in datos.get("filas", []):
                    est = fila.get("estudiante_id")
                    a = db.query(Asistencia).filter(Asistencia.estudiante_id == est,
                                                    Asistencia.fecha == fecha).first()
                    if not a:
                        a = Asistencia(estudiante_id=est, salon_id=sid, fecha=fecha)
                        db.add(a)
                    a.estado = fila.get("estado", "present")
                    a.observacion = fila.get("observacion")
                    n += 1
                detalles.append(f"Asistencia del {fecha}: {n} estudiantes")
            elif tipo == "alerta":
                db.add(NotificacionCoord(
                    institucion_id=payload.institucion_id,
                    estudiante_id=datos.get("estudiante_id"),
                    tipo=datos.get("subtipo", "ausencia"),
                    titulo=datos.get("titulo", "Alerta registrada sin conexión"),
                    detalle=datos.get("mensaje", ""),
                    fecha=ts, estado="abierta"))
                detalles.append("Alerta enviada a coordinación")
            elif tipo == "nota":
                n = db.query(NotaPeriodo).filter(
                    NotaPeriodo.estudiante_id == datos.get("estudiante_id"),
                    NotaPeriodo.periodo_id == datos.get("periodo_id"),
                    NotaPeriodo.materia == datos.get("materia")).first()
                if n:
                    n.nota = datos.get("nota")
                    detalles.append(f"Nota de {datos.get('materia')}")
            elif tipo == "whatsapp":
                db.add(MensajeWhatsApp(
                    estudiante_id=datos.get("estudiante_id"),
                    destinatario=datos.get("destinatario", "Acudiente"),
                    telefono=datos.get("telefono", "—"),
                    contenido=datos.get("mensaje", "")[:500], fecha=ts,
                    estado="ENVIADO (simulado)", contexto="offline"))
                detalles.append("Mensaje al acudiente")
            registro.sincronizado = True
            registro.sincronizado_en = datetime.now()
            registro.resultado = "ok"
            aplicadas += 1
        except Exception as exc:  # noqa: BLE001
            registro.resultado = f"error: {type(exc).__name__}"
            fallidas += 1
    db.commit()
    metadatos.registrar_evento("SYNC_OFFLINE", payload.origen or "Docente",
                               institucion_id=payload.institucion_id,
                               payload={"aplicadas": aplicadas, "fallidas": fallidas})
    return {"ok": True, "aplicadas": aplicadas, "fallidas": fallidas,
            "detalles": detalles[:12],
            "msg": (f"🔄 Se sincronizaron {aplicadas} acción(es) que hiciste sin internet."
                    + (f" {fallidas} no se pudieron aplicar." if fallidas else ""))}


@router.get("/offline/pendientes")
def offline_pendientes(institucion_id: int, db: Session = Depends(get_db)):
    filas = db.query(ColaOffline).filter(ColaOffline.institucion_id == institucion_id).order_by(
        ColaOffline.id.desc()).limit(60).all()
    return {
        "eventos": [{
            "id": x.id, "tipo": x.tipo, "origen": x.origen,
            "creado_en": x.creado_en.isoformat(sep=" ", timespec="minutes") if x.creado_en else "",
            "sincronizado": bool(x.sincronizado),
            "sincronizado_en": x.sincronizado_en.isoformat(sep=" ", timespec="minutes") if x.sincronizado_en else None,
            "resultado": x.resultado,
        } for x in filas],
        "pendientes": sum(1 for x in filas if not x.sincronizado),
        "sincronizados": sum(1 for x in filas if x.sincronizado),
    }
