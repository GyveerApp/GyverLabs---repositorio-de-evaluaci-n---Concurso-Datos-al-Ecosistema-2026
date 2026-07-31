"""
GyverLabs — Log Unificado de Metadatos (gyverlabs_unified_v1)
═════════════════════════════════════════════════════════════
Misma filosofía del log unificado de trading (warhound_unified_v2):
  · Cada ACCIÓN del sistema genera un EVENTO (una línea JSONL) con su
    contexto → auditoría total + materia prima para IA.
  · Cada estudiante genera SNAPSHOTS semanales (secuencias) con features
    y el "brain" (score del modelo) → formato listo para LSTM/Transformer,
    igual que los snapshots por trade.
  · El dataset tabular estudiante-semana con target REAL verificable
    ("¿faltó la semana siguiente?") alimenta LightGBM / meta-brain.

Todo anonimizado con hash (Ley 1581 de 2012): EST-xxxxxxxx no permite
identificar a la persona. En esta demo los datos son 100% sintéticos.
"""
import hashlib
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta

DIR_DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos")
RUTA_LOG = os.path.join(DIR_DATOS, "gyverlabs_unified_v1.jsonl")
SCHEMA = "gyverlabs_unified_v1"


def _asegurar_dir():
    os.makedirs(DIR_DATOS, exist_ok=True)


def anonimizar(nombre: str, id_: int) -> str:
    h = hashlib.sha1(f"{nombre}|{id_}|gyverlabs".encode()).hexdigest()[:8].upper()
    return f"EST-{h}"


def registrar_evento(event: str, actor: str = "", institucion_id=None,
                     estudiante_id=None, payload: dict | None = None):
    """Añade una línea al log unificado. Nunca rompe el flujo principal."""
    try:
        _asegurar_dir()
        linea = {
            "schema": SCHEMA,
            "event": event,
            "ts": datetime.now().isoformat(timespec="seconds"),
            "actor": actor or "sistema",
        }
        if institucion_id is not None:
            linea["institucion_id"] = institucion_id
        if estudiante_id is not None:
            linea["estudiante_id"] = estudiante_id
        if payload:
            linea.update(payload)
        with open(RUTA_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(linea, ensure_ascii=False) + "\n")
    except Exception as e:
        print("metadatos: no se pudo registrar evento:", e)


def resumen_log():
    _asegurar_dir()
    conteo = defaultdict(int)
    total = 0
    if os.path.exists(RUTA_LOG):
        with open(RUTA_LOG, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                total += 1
                try:
                    conteo[json.loads(ln).get("event", "?")] += 1
                except Exception:
                    conteo["?"] += 1
    tam = os.path.getsize(RUTA_LOG) if os.path.exists(RUTA_LOG) else 0
    return {"total_eventos": total, "por_evento": dict(conteo), "bytes": tam,
            "archivo": "datos/gyverlabs_unified_v1.jsonl", "schema": SCHEMA}


def ultimos_eventos(n=40):
    _asegurar_dir()
    if not os.path.exists(RUTA_LOG):
        return []
    with open(RUTA_LOG, encoding="utf-8") as f:
        lineas = [ln.strip() for ln in f if ln.strip()]
    out = []
    for ln in lineas[-n:][::-1]:
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out


# ════════════════════════════════════════════════════════════════════
#  DATASETS (estudiante-semana) — la mina de oro para los modelos
# ════════════════════════════════════════════════════════════════════
_NIVEL = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5}


def _lunes(f: date) -> date:
    return f - timedelta(days=f.weekday())


def construir_filas(db):
    """Filas estudiante-semana con features y target REAL verificable:
    target_ausencia_prox_sem = 1 si tuvo ≥1 ausencia la semana SIGUIENTE
    (etiqueta 'futuro observable', igual que en la auditoría de trading)."""
    from models import Estudiante, Asistencia, NotaPeriodo, Periodo, SRDScore, Institucion

    estudiantes = db.query(Estudiante).all()
    if not estudiantes:
        return []
    inst = {i.id: i for i in db.query(Institucion).all()}
    srd = {s.estudiante_id: s for s in db.query(SRDScore).all()}

    periodos = {p.id: p.numero for p in db.query(Periodo).all()}
    notas_est = defaultdict(lambda: defaultdict(list))
    for n in db.query(NotaPeriodo).all():
        num = periodos.get(n.periodo_id)
        if num:
            notas_est[n.estudiante_id][num].append(n.nota)
    prom_tend = {}
    for eid, por_p in notas_est.items():
        proms = [sum(v) / len(v) for _, v in sorted(por_p.items())]
        prom = proms[-1] if proms else 0.0
        tend = (proms[-1] - proms[0]) if len(proms) >= 2 else 0.0
        prom_tend[eid] = (round(prom, 2), round(tend, 2))

    asis = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))
    lunes_set = set()
    for a in db.query(Asistencia).all():
        L = _lunes(a.fecha)
        lunes_set.add(L)
        v = asis[a.estudiante_id][L]
        idx = {"present": 0, "late": 1, "excused": 2, "absent": 3}.get(a.estado, 0)
        v[idx] += 1
    semanas = sorted(lunes_set)
    if len(semanas) < 3:
        return []

    filas = []
    hoy = date.today()
    for e in estudiantes:
        ie = inst.get(e.institucion_id)
        cod = anonimizar(e.nombre, e.id)
        rec = srd.get(e.id)
        prom, tend = prom_tend.get(e.id, (0.0, 0.0))
        antig = round((hoy - e.fecha_ingreso).days / 365.0, 1) if e.fecha_ingreso else 0.0
        for i, L in enumerate(semanas):
            v = asis[e.id].get(L, [0, 0, 0, 0])
            tot = sum(v)
            if tot == 0:
                continue
            v4 = [0, 0, 0, 0]
            for L2 in semanas[max(0, i - 3):i + 1]:
                w = asis[e.id].get(L2, [0, 0, 0, 0])
                for k in range(4):
                    v4[k] += w[k]
            tot4 = sum(v4) or 1
            if i + 1 < len(semanas):
                vn = asis[e.id].get(semanas[i + 1], [0, 0, 0, 0])
                target = 1 if vn[3] > 0 else 0
                tiene_target = sum(vn) > 0
            else:
                target, tiene_target = 0, False
            filas.append({
                "estudiante_codigo": cod,
                "institucion": ie.nombre if ie else "",
                "municipio": ie.municipio if ie else "",
                "departamento": ie.departamento if ie else "",
                "grado": e.grado, "zona": e.zona,
                "semana_idx": i, "fecha_lunes": L.isoformat(),
                "asis_pct_sem": round(100 * (tot - v[3]) / tot, 1),
                "ausencias_sem": v[3], "tardanzas_sem": v[1], "excusas_sem": v[2],
                "asis_pct_4sem": round(100 * (tot4 - v4[3]) / tot4, 1),
                "ausencias_4sem": v4[3],
                "promedio_actual": prom, "tendencia_notas": tend,
                "nivel_sisben_num": _NIVEL.get(e.nivel_sisben, 3),
                "zona_rural": 1 if e.zona == "rural" else 0,
                "antiguedad_anios": antig,
                "srd_score": round(rec.score, 4) if rec else None,
                "srd_nivel": rec.nivel if rec else None,
                "target_ausencia_prox_sem": target if tiene_target else "",
            })
    return filas


def dataset_csv(db) -> str:
    filas = construir_filas(db)
    _asegurar_dir()
    ruta = os.path.join(DIR_DATOS, "dataset_ml_estudiante_semana.csv")
    if not filas:
        open(ruta, "w").close()
        return ruta
    cols = list(filas[0].keys())
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(cols) + "\n")
        for r in filas:
            vals = []
            for c in cols:
                s = str(r[c]) if r[c] is not None else ""
                vals.append('"' + s.replace('"', "'") + '"' if "," in s else s)
            f.write(",".join(vals) + "\n")
    return ruta


def secuencias_jsonl(db) -> str:
    """Secuencias por estudiante (SNAP semanal) — espejo de los snapshots
    por trade: formato directo para LSTM / Transformer."""
    filas = construir_filas(db)
    _asegurar_dir()
    ruta = os.path.join(DIR_DATOS, "secuencias_lstm_transformer.jsonl")
    por_est = defaultdict(list)
    for r in filas:
        por_est[r["estudiante_codigo"]].append(r)
    with open(ruta, "w", encoding="utf-8") as f:
        for cod, sec in por_est.items():
            sec.sort(key=lambda x: x["semana_idx"])
            for r in sec:
                f.write(json.dumps({
                    "schema": SCHEMA, "event": "SNAP",
                    "estudiante": cod, "semana": r["semana_idx"], "fecha": r["fecha_lunes"],
                    "features": {k: r[k] for k in (
                        "asis_pct_sem", "ausencias_sem", "tardanzas_sem", "asis_pct_4sem",
                        "ausencias_4sem", "promedio_actual", "tendencia_notas",
                        "nivel_sisben_num", "zona_rural", "antiguedad_anios")},
                    "brains": {"lgbm_srd": r["srd_score"]},
                    "target": r["target_ausencia_prox_sem"],
                }, ensure_ascii=False) + "\n")
    return ruta


def metadata_datosgov(db, titulo=None, descripcion=None, responsable=None):
    """Ficha de metadatos estilo datos.gov.co (DCAT) para el dataset abierto."""
    filas = construir_filas(db)
    munis = sorted({r["municipio"] for r in filas if r["municipio"]})
    return {
        "titulo": titulo or "Asistencia y riesgo de deserción escolar — estudiante-semana (anonimizado)",
        "descripcion": descripcion or (
            "Serie semanal anonimizada por estudiante: asistencia, tendencia académica, "
            "contexto (SISBEN, zona) y score del modelo de riesgo de deserción. "
            "Generada automáticamente por GyverLabs. Sin datos personales "
            "(códigos hash irreversibles — Ley 1581 de 2012)."),
        "categoria": "Educación",
        "palabras_clave": ["deserción escolar", "asistencia", "educación", "IA", "alerta temprana"],
        "licencia": "CC-BY 4.0",
        "frecuencia_actualizacion": "Semanal (automática)",
        "cobertura_geografica": ", ".join(munis) or "Colombia",
        "responsable": responsable or "GyverLabs — Secretaría de Educación",
        "correo": "datos@gyverlabs.co",
        "registros": len(filas),
        "formato": "CSV",
        "fecha_generacion": datetime.now().isoformat(timespec="seconds"),
    }
