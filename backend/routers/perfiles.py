"""Selector de perfiles tipo 'Netflix' para la demostración — 9 perfiles.

El súper-usuario de la demo entra a cualquier rol para mostrar qué ve y qué
hace cada uno: Súper Admin GyverLabs (nivel 1), Secretaría (nivel 2),
Ministerio, y dentro del colegio (nivel 3): Rectoría, Coordinación, Docente
y el equipo administrativo (Contratación, Contaduría, Jurídica).
Soporta foto de perfil editable (círculo) para el personal.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Institucion, Personal, Salon, Autorizacion, Tenant, Estudiante

router = APIRouter()


def _p(db, ie_id, rol):
    return db.query(Personal).filter(Personal.institucion_id == ie_id, Personal.rol == rol,
                                     Personal.activo == True).first()  # noqa: E712


@router.get("/")
def perfiles(db: Session = Depends(get_db)):
    ie = db.query(Institucion).filter(Institucion.sector.like("%urbana%")).first() or db.query(Institucion).first()
    docente = _p(db, ie.id, "docente")
    coord = _p(db, ie.id, "coordinador")
    rector = _p(db, ie.id, "rector")
    aux = _p(db, ie.id, "auxiliar")
    contador = _p(db, ie.id, "contador")
    abogado = _p(db, ie.id, "abogado")
    salon = db.query(Salon).filter(Salon.director_id == docente.id).first() if docente else None
    if salon is None and docente:
        salon = db.query(Salon).filter(Salon.institucion_id == ie.id).first()
    tenant = db.query(Tenant).filter(Tenant.institucion_id == ie.id).first()
    logo_ie = (tenant.logo if tenant and tenant.logo else ie.logo)
    n_tenants = db.query(Tenant).count()
    n_est = db.query(Estudiante).count()

    aut = {a.personal_id: a.paneles for a in db.query(Autorizacion).filter(Autorizacion.institucion_id == ie.id).all()}

    def card(rol, titulo, persona, detalle, avatar, color, desc, extra=None):
        base = {
            "rol": rol, "titulo": titulo,
            "nombre": persona.nombre if hasattr(persona, "nombre") else persona,
            "detalle": detalle, "avatar": avatar, "color": color,
            "institucion_id": ie.id, "salon_id": None, "descripcion": desc,
            "personal_id": getattr(persona, "id", None),
            "foto": getattr(persona, "foto", None),
            "logo": logo_ie,
        }
        if extra:
            base.update(extra)
        return base

    municipio, depto = ie.municipio, ie.departamento
    return {
        "institucion_demo": {"id": ie.id, "nombre": ie.nombre, "municipio": municipio,
                             "departamento": depto,
                             "dominio": tenant.dominio if tenant else None},
        "perfiles": [
            card("superadmin", "Súper Admin GyverLabs", "Juan David Quesada", "Nivel 1 · admin.gyverlabs.co",
                 "🧠", "#E8A33D",
                 f"Crea secretarías y colegios (tenants). {n_tenants} dominios activos, {n_est} estudiantes en la red. Un solo código, N dominios.",
                 {"institucion_id": None, "logo": None}),
            card("docente", "Docente", docente or "Docente Demo",
                 f"{(salon.nombre if salon else '—')} · {ie.nombre}", "👨‍🏫", "#0891B2",
                 "Toma asistencia, crea clases con el asistente IA, gestiona su calendario, notas y el riesgo de sus estudiantes.",
                 {"salon_id": salon.id if salon else None}),
            card("coordinador", "Coordinación", coord or "Coordinación Demo", ie.nombre, "📋", "#7C3AED",
                 "Recibe las alertas del día (ausencias en tiempo real), gestiona casos, docentes y su asistencia."),
            card("rector", "Rectoría", rector or (ie.rector or "Rectoría"), ie.nombre, "🎓", "#059669",
                 "Control total: salones, personal con hojas de vida, riesgo, FSE, contratación SECOP 2, equipos de trabajo y Datos & IA."),
            card("auxiliar", "Contratación", aux or "Auxiliar Administrativa", f"Equipo administrativo · {ie.nombre}", "🗂️", "#0E7C86",
                 "Recibe los documentos de los contratistas (cédula, contraloría, procuraduría, REDAM…), arma expedientes y envía a firma.",
                 {"paneles": aut.get(aux.id if aux else -1, "contratos,fse")}),
            card("contador", "Contaduría", contador or "Contador FSE", f"Equipo administrativo · {ie.nombre}", "🧮", "#1D4ED8",
                 "Libro del FSE, CDP/RP, conciliación y reportes financieros listos para la Contraloría.",
                 {"paneles": aut.get(contador.id if contador else -1, "fse,contratos,datos")}),
            card("abogado", "Jurídica", abogado or "Abogada", f"Equipo administrativo · {ie.nombre}", "⚖️", "#9333EA",
                 "Revisión legal del pipeline de contratos, verificación de requisitos y firmas electrónicas.",
                 {"paneles": aut.get(abogado.id if abogado else -1, "contratos")}),
            card("secretaria", "Secretaría de Educación", f"Secretaría de {municipio}", f"{municipio}, {depto} · {municipio.lower().replace(' ','')}.gyverlabs.co",
                 "🏛️", "#D97706",
                 "Dashboard territorial: entra a cada colegio (personal, hojas de vida, compras), censo por zonas y datos abiertos.",
                 {"institucion_id": None, "municipio": municipio}),
            card("ministerio", "Ministerio de Educación", "Ministerio de Educación Nacional", "Vista nacional",
                 "🇨🇴", "#1D4ED8",
                 "Inteligencia nacional: comparativo departamental, tendencia de asistencia, cumplimiento PND y datos abiertos.",
                 {"institucion_id": None, "logo": None}),
            _card_alumno(db, ie, logo_ie),
        ],
    }


def _card_alumno(db, ie, logo_ie):
    """Tarjeta de acceso de un ALUMNO (demo): entra a su portal con clases,
    tareas, calendario, notas y el curso de contabilidad."""
    est = (db.query(Estudiante).filter(Estudiante.institucion_id == ie.id,
                                       Estudiante.salon_id != None)  # noqa: E711
           .order_by(Estudiante.id).first())
    salon = db.query(Salon).filter(Salon.id == est.salon_id).first() if est else None
    return {
        "rol": "alumno", "titulo": "Alumno / Estudiante",
        "nombre": est.nombre if est else "Estudiante Demo",
        "detalle": f"{(salon.nombre if salon else '—')} · {ie.nombre}",
        "avatar": "🎒", "color": "#0EA5E9",
        "institucion_id": ie.id, "salon_id": salon.id if salon else None,
        "descripcion": "Portal del estudiante: clases en vivo, tareas y talleres con fechas, evaluaciones, notas, chat con compañeros y el curso de Contabilidad para aprender a manejar una empresa.",
        "personal_id": None, "estudiante_id": est.id if est else None,
        "foto": None, "logo": logo_ie,
    }


class FotoIn(BaseModel):
    personal_id: int
    foto: str | None = None


@router.post("/foto")
def guardar_foto(payload: FotoIn, db: Session = Depends(get_db)):
    p = db.query(Personal).filter(Personal.id == payload.personal_id).first()
    if not p:
        return {"ok": False, "msg": "Persona no encontrada."}
    if payload.foto and len(payload.foto) > 900_000:
        return {"ok": False, "msg": "La imagen es muy pesada. Usa una foto más pequeña."}
    p.foto = payload.foto
    db.commit()
    return {"ok": True, "msg": "Foto de perfil actualizada." if payload.foto else "Foto eliminada."}
