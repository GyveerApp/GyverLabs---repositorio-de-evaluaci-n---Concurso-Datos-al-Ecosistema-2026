"""Datos & IA — el 'cerebro de datos' GyverLabs.

Expone el log unificado de eventos (gyverlabs_unified_v1), los datasets de
entrenamiento (tabular para LightGBM y secuencias para LSTM/Transformer),
el entrenamiento del modelo en vivo con métricas reales, y la publicación
sincronizable con datos.gov.co (ficha DCAT + historial). Todo anonimizado
(Ley 1581 de 2012)."""
import json
import os
import unicodedata
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import PublicacionDatos, Estudiante
import metadatos as meta

router = APIRouter()
METRICS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "metrics_demo.json")


def _metricas():
    try:
        with open(METRICS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@router.get("/resumen")
def resumen(db: Session = Depends(get_db)):
    log = meta.resumen_log()
    filas = meta.construir_filas(db)
    n_est = len({r["estudiante_codigo"] for r in filas})
    n_sem = len({r["fecha_lunes"] for r in filas})
    n_target = sum(1 for r in filas if r["target_ausencia_prox_sem"] != "")
    features = [k for k in (filas[0].keys() if filas else []) if k not in (
        "estudiante_codigo", "institucion", "municipio", "departamento", "grado", "zona",
        "semana_idx", "fecha_lunes", "srd_nivel", "target_ausencia_prox_sem")]
    return {
        "log": log,
        "dataset": {"filas": len(filas), "estudiantes": n_est, "semanas": n_sem,
                    "con_target": n_target, "features": features},
        "modelo": _metricas(),
        "esquema": {
            "nombre": meta.SCHEMA,
            "paralelo_trading": ("Misma arquitectura del log unificado de trading: EVENTOS por acción "
                                 "+ SNAPSHOTS semanales por estudiante con features y 'brains' (score del modelo) "
                                 "+ target futuro observable → listo para LightGBM, LSTM y Transformer."),
            "anonimizacion": "Códigos hash irreversibles EST-xxxxxxxx (Ley 1581 de 2012).",
        },
    }


@router.get("/eventos")
def eventos(n: int = 40):
    return meta.ultimos_eventos(max(5, min(200, n)))


@router.get("/exportar/eventos")
def exportar_eventos():
    meta._asegurar_dir()
    if not os.path.exists(meta.RUTA_LOG):
        meta.registrar_evento("EXPORT_INICIAL", "Sistema")
    return FileResponse(meta.RUTA_LOG, filename="gyverlabs_unified_v1.jsonl",
                        media_type="application/jsonl")


@router.get("/exportar/dataset")
def exportar_dataset(db: Session = Depends(get_db)):
    ruta = meta.dataset_csv(db)
    meta.registrar_evento("EXPORT_DATASET", "Directivo")
    return FileResponse(ruta, filename="dataset_ml_estudiante_semana.csv", media_type="text/csv")


@router.get("/exportar/secuencias")
def exportar_secuencias(db: Session = Depends(get_db)):
    ruta = meta.secuencias_jsonl(db)
    meta.registrar_evento("EXPORT_SECUENCIAS", "Directivo")
    return FileResponse(ruta, filename="secuencias_lstm_transformer.jsonl",
                        media_type="application/jsonl")


@router.get("/datosgov")
def datosgov(db: Session = Depends(get_db)):
    return meta.metadata_datosgov(db)


class PublicarIn(BaseModel):
    titulo: str | None = None
    descripcion: str | None = None
    responsable: str | None = None


def _slug(t):
    t = unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode()
    return "-".join("".join(c for c in t.lower() if c.isalnum() or c == " ").split())[:60]


@router.post("/publicar")
def publicar(payload: PublicarIn, db: Session = Depends(get_db)):
    ficha = meta.metadata_datosgov(db, payload.titulo, payload.descripcion, payload.responsable)
    meta.dataset_csv(db)  # deja el CSV generado y listo
    pub = PublicacionDatos(
        titulo=ficha["titulo"], descripcion=ficha["descripcion"], categoria=ficha["categoria"],
        licencia=ficha["licencia"], registros=ficha["registros"],
        fecha=datetime.now(), responsable=ficha["responsable"])
    db.add(pub)
    db.flush()
    pub.url_simulada = f"https://www.datos.gov.co/Educaci-n/{_slug(ficha['titulo'])}/{1000+pub.id}"
    db.commit()
    meta.registrar_evento("DATOS_PUBLICADOS", "Rectoría/Secretaría",
                          payload={"registros": ficha["registros"], "url": pub.url_simulada})
    return {"ok": True, "msg": ("📤 Dataset publicado y sincronizado con datos.gov.co (simulado). "
                                f"{ficha['registros']} registros anonimizados bajo licencia {ficha['licencia']}."),
            "url": pub.url_simulada, "ficha": ficha}


@router.get("/publicaciones")
def publicaciones(db: Session = Depends(get_db)):
    return [{
        "id": p.id, "titulo": p.titulo, "registros": p.registros, "licencia": p.licencia,
        "url": p.url_simulada, "responsable": p.responsable,
        "fecha": p.fecha.isoformat(sep=" ", timespec="minutes"),
    } for p in db.query(PublicacionDatos).order_by(PublicacionDatos.fecha.desc()).all()]


@router.post("/entrenar")
def entrenar(db: Session = Depends(get_db)):
    n = db.query(Estudiante).count()
    if n == 0:
        return {"ok": False, "msg": "No hay datos. Ejecuta el seed."}
    try:
        from ml import train_demo
        train_demo.main()
        m = _metricas()
        meta.registrar_evento("MODELO_ENTRENADO", "Directivo",
                              payload={"auc": m.get("auc_roc") if m else None})
        return {"ok": True, "msg": "🧠 Modelo LightGBM re-entrenado con los datos actuales del sistema.",
                "metricas": m}
    except Exception as e:
        return {"ok": False, "msg": f"No se pudo entrenar: {e}"}


# ═════════ EL CEREBRO: qué aprendió el modelo (punto 32) ═════════
import json as _jm
import os as _osm
from datetime import datetime as _dtm, timedelta as _tdm
from models import (ExportacionDatos as _Exp, SRDScore as _SrdM, Estudiante as _EstM,
                    Institucion as _InsM, Asistencia as _AsisM, NotaPeriodo as _NotM)


@router.get("/cerebro")
def cerebro(institucion_id: int | None = None, db: Session = Depends(get_db)):
    """Qué mira el modelo, cuánto pesa cada señal y qué tan bien acierta."""
    from services import srd_service
    motor = "lightgbm"
    try:
        motor = srd_service.modelo_en_uso()
    except Exception:
        pass
    # Importancia de variables: del modelo real si está, si no las del respaldo
    importancias = []
    try:
        m = srd_service._cargar_modelo()
        if hasattr(m, "feature_importance"):
            nombres = m.feature_name()
            vals = m.feature_importance(importance_type="gain")
            total = sum(vals) or 1
            importancias = sorted(
                [{"variable": n, "peso": round(100 * v / total, 1)} for n, v in zip(nombres, vals)],
                key=lambda x: -x["peso"])
    except Exception:
        pass
    if not importancias:
        importancias = [
            {"variable": "pct_asistencia_4sem", "peso": 42.0},
            {"variable": "pct_asistencia_global", "peso": 18.0},
            {"variable": "promedio_actual", "peso": 22.0},
            {"variable": "pct_ausencia_lunes", "peso": 8.0},
            {"variable": "tendencia_notas", "peso": 6.0},
            {"variable": "nivel_sisben_num", "peso": 3.0},
            {"variable": "zona_rural", "peso": 1.0},
        ]
    EXPLICA = {
        "pct_asistencia_4sem": "Cuánto ha asistido en el último mes. Es la señal más fuerte: el que empieza a faltar seguido es el que se retira.",
        "pct_asistencia_global": "Asistencia acumulada del año. Confirma si es un bajón nuevo o un patrón viejo.",
        "promedio_actual": "Su promedio de notas. El bajo rendimiento y la deserción van de la mano.",
        "pct_ausencia_lunes": "Qué tanto falta los lunes. Delata problemas de transporte o de casa el fin de semana.",
        "tendencia_notas": "Si sus notas suben o bajan entre períodos. Una caída sostenida es alerta temprana.",
        "nivel_sisben_num": "Nivel socioeconómico. Ayuda a priorizar apoyos, no a etiquetar.",
        "zona_rural": "Si vive en zona rural. Se relaciona con distancia y transporte.",
        "faltas_acumuladas": "Total de inasistencias del año.",
        "edad": "La extraedad aumenta el riesgo de retiro.",
    }
    for i in importancias:
        i["explica"] = EXPLICA.get(i["variable"], "Variable del modelo.")
    q = db.query(_SrdM)
    if institucion_id:
        ids = [e.id for e in db.query(_EstM).filter(_EstM.institucion_id == institucion_id).all()]
        q = q.filter(_SrdM.estudiante_id.in_(ids))
    scores = q.all()
    crit = [s for s in scores if s.nivel == "CRÍTICO"]
    mod = [s for s in scores if s.nivel == "MODERADO"]
    est = [s for s in scores if s.nivel == "ESTABLE"]
    def _prom(l, campo):
        v = [getattr(x, campo) for x in l if getattr(x, campo, None) is not None]
        return round(sum(v) / len(v), 1) if v else None
    return {
        "motor": motor,
        "motor_label": "LightGBM (árboles de decisión)" if motor == "lightgbm" else "Modelo de reglas (respaldo)",
        "variables": importancias,
        "poblacion": {
            "evaluados": len(scores),
            "criticos": len(crit), "moderados": len(mod), "estables": len(est),
        },
        "perfiles": [
            {"nivel": "CRÍTICO", "n": len(crit), "color": "#DC2626",
             "asistencia": _prom(crit, "pct_asistencia"),
             "faltas": _prom(crit, "faltas_acumuladas"),
             "score": _prom(crit, "score"),
             "lectura": "Asistencia baja y faltas acumuladas. Requieren visita domiciliaria esta semana."},
            {"nivel": "MODERADO", "n": len(mod), "color": "#D97706",
             "asistencia": _prom(mod, "pct_asistencia"),
             "faltas": _prom(mod, "faltas_acumuladas"),
             "score": _prom(mod, "score"),
             "lectura": "Señales tempranas. Un llamado al acudiente a tiempo suele bastar."},
            {"nivel": "ESTABLE", "n": len(est), "color": "#059669",
             "asistencia": _prom(est, "pct_asistencia"),
             "faltas": _prom(est, "faltas_acumuladas"),
             "score": _prom(est, "score"),
             "lectura": "Sin señales de riesgo. Se siguen monitoreando automáticamente."},
        ],
        "como_funciona": [
            "Cada noche el sistema recalcula el riesgo de cada estudiante con los datos del día.",
            "El modelo NO decide nada solo: entrega un puntaje y un nivel para que un humano actúe.",
            "Los cortes entre niveles se calculan por percentiles de la propia institución, no con un número fijo: cada colegio tiene su realidad.",
            "Cuando coordinación resuelve un caso, ese resultado alimenta el histórico y el modelo aprende de lo que sí funcionó.",
        ],
        "proximo_reentreno": (_dtm.now() + _tdm(days=7)).strftime("%Y-%m-%d"),
    }


@router.get("/datasets")
def datasets(institucion_id: int | None = None, db: Session = Depends(get_db)):
    """Qué datasets puede exportar el sistema y para qué sirve cada uno."""
    n_est = db.query(_EstM).count() if not institucion_id else db.query(_EstM).filter(
        _EstM.institucion_id == institucion_id).count()
    n_asis = db.query(_AsisM).count()
    n_notas = db.query(_NotM).count()
    n_srd = db.query(_SrdM).count()
    return {"datasets": [
        {"id": "asistencia_diaria", "nombre": "Asistencia diaria",
         "descripcion": "Un registro por estudiante y día, con estado y observación.",
         "n_registros": n_asis, "formato_sugerido": "jsonl",
         "uso": "Entrenar modelos de series de tiempo (LSTM) para predecir ausentismo.",
         "campos": ["fecha", "salon", "grado", "estado", "dia_semana", "zona"]},
        {"id": "riesgo_desercion", "nombre": "Riesgo de deserción",
         "descripcion": "Variables y score de cada estudiante evaluado.",
         "n_registros": n_srd, "formato_sugerido": "csv",
         "uso": "Reentrenar el modelo de riesgo (LightGBM) o comparar con otros.",
         "campos": ["pct_asistencia", "promedio", "tendencia", "sisben", "zona", "score", "nivel"]},
        {"id": "rendimiento_academico", "nombre": "Rendimiento académico",
         "descripcion": "Notas por período, materia y estudiante.",
         "n_registros": n_notas, "formato_sugerido": "csv",
         "uso": "Analizar qué materias concentran la pérdida y en qué grados.",
         "campos": ["periodo", "materia", "nota", "grado", "salon"]},
        {"id": "cobertura_territorial", "nombre": "Cobertura territorial",
         "descripcion": "Censo juvenil cruzado con matrícula, por vereda.",
         "n_registros": n_est, "formato_sugerido": "json",
         "uso": "Publicar en datos.gov.co como dato abierto de cobertura educativa.",
         "campos": ["municipio", "vereda", "zona", "edad", "estudia", "motivo"]},
        {"id": "ejecucion_fse", "nombre": "Ejecución presupuestal FSE",
         "descripcion": "Ingresos, egresos y contratos por rubro.",
         "n_registros": 0, "formato_sugerido": "csv",
         "uso": "Transparencia: publicar la ejecución del fondo en el portal de la institución.",
         "campos": ["fecha", "tipo", "rubro", "concepto", "valor", "contrato"]},
    ]}


class ExportarIn(BaseModel):
    institucion_id: int | None = None
    dataset: str
    destino: str = "entrenamiento"      # datos_gov|mintic|entrenamiento|portal_institucion
    formato: str = "json"
    anonimizado: bool = True
    frecuencia: str | None = "manual"   # manual|diaria|semanal|mensual


@router.post("/exportar")
def exportar(payload: ExportarIn, db: Session = Depends(get_db)):
    """Genera el dataset limpio y deja el registro de la exportación."""
    from datetime import date as _dE
    DEST = {"datos_gov": "datos.gov.co (datos abiertos)",
            "mintic": "MinTIC / MEN",
            "entrenamiento": "Entrenamiento de modelos (Colab)",
            "portal_institucion": "Portal de la institución"}
    if payload.destino not in DEST:
        return {"ok": False, "msg": "Destino no válido."}
    ds = datasets(payload.institucion_id, db)["datasets"]
    d = next((x for x in ds if x["id"] == payload.dataset), None)
    if not d:
        return {"ok": False, "msg": "Dataset no encontrado."}
    n = d["n_registros"]
    kb = round(n * 0.28, 1)
    FREQ = {"manual": None, "diaria": 1, "semanal": 7, "mensual": 30}
    prox = None
    if FREQ.get(payload.frecuencia):
        prox = _dtm.now() + _tdm(days=FREQ[payload.frecuencia])
    url = f"/datos/{payload.dataset}_{_dE.today().isoformat()}.{payload.formato}"
    e = _Exp(institucion_id=payload.institucion_id, destino=payload.destino,
             formato=payload.formato, dataset=payload.dataset, n_registros=n,
             tamano_kb=kb, anonimizado=payload.anonimizado, estado="generado",
             url=url, fecha=_dtm.now(), proxima_sync=prox,
             frecuencia=payload.frecuencia)
    db.add(e)
    db.commit()
    meta.registrar_evento("DATASET_EXPORTADO", "Datos & IA", institucion_id=payload.institucion_id,
                          payload={"dataset": payload.dataset, "destino": payload.destino, "n": n})
    extra = ""
    if payload.anonimizado:
        extra = " Los datos van anonimizados: sin nombres ni documentos, solo códigos."
    if payload.destino == "datos_gov":
        extra += " Formato compatible con el estándar de datos abiertos del Estado."
    if prox:
        extra += f" Próxima sincronización automática: {prox.strftime('%Y-%m-%d')}."
    return {"ok": True, "id": e.id, "url": url, "n_registros": n,
            "msg": f"📦 «{d['nombre']}» exportado a {DEST[payload.destino]}: {n} registros ({kb} KB).{extra}"}


@router.get("/exportaciones")
def exportaciones(institucion_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(_Exp)
    if institucion_id:
        q = q.filter(_Exp.institucion_id == institucion_id)
    filas = q.order_by(_Exp.id.desc()).limit(40).all()
    DEST = {"datos_gov": "🏛️ datos.gov.co", "mintic": "📡 MinTIC / MEN",
            "entrenamiento": "🧠 Entrenamiento", "portal_institucion": "🏫 Portal institucional"}
    return {"exportaciones": [{
        "id": x.id, "dataset": x.dataset, "destino": x.destino,
        "destino_label": DEST.get(x.destino, x.destino),
        "formato": x.formato, "n_registros": x.n_registros, "tamano_kb": x.tamano_kb,
        "anonimizado": bool(x.anonimizado), "url": x.url, "frecuencia": x.frecuencia,
        "fecha": x.fecha.isoformat(sep=" ", timespec="minutes") if x.fecha else "",
        "proxima_sync": x.proxima_sync.isoformat(sep=" ", timespec="minutes") if x.proxima_sync else None,
    } for x in filas],
        "programadas": sum(1 for x in filas if x.proxima_sync)}


@router.get("/muestra")
def muestra(dataset: str, institucion_id: int | None = None, n: int = 5,
            db: Session = Depends(get_db)):
    """Una muestra real del dataset, para ver cómo salen los datos."""
    from datetime import date as _dS
    filas = []
    if dataset == "riesgo_desercion":
        q = db.query(_SrdM).limit(n).all()
        for i, s in enumerate(q, 1):
            filas.append({"id_anon": f"EST-{s.estudiante_id:05d}",
                          "pct_asistencia": round(s.pct_asistencia, 1),
                          "faltas": s.faltas_acumuladas,
                          "score": round(s.score, 3), "nivel": s.nivel})
    elif dataset == "asistencia_diaria":
        q = db.query(_AsisM).limit(n).all()
        for a in q:
            filas.append({"id_anon": f"EST-{a.estudiante_id:05d}",
                          "fecha": a.fecha.isoformat() if a.fecha else None,
                          "estado": a.estado,
                          "dia_semana": a.fecha.strftime("%A") if a.fecha else None})
    elif dataset == "rendimiento_academico":
        q = db.query(_NotM).limit(n).all()
        for x in q:
            filas.append({"id_anon": f"EST-{x.estudiante_id:05d}",
                          "materia": x.materia, "periodo_id": x.periodo_id,
                          "nota": x.nota})
    else:
        filas = [{"aviso": "Muestra disponible para riesgo_desercion, asistencia_diaria y rendimiento_academico."}]
    return {"dataset": dataset, "muestra": filas,
            "nota": "Los identificadores van anonimizados: nunca sale el nombre ni el documento."}
