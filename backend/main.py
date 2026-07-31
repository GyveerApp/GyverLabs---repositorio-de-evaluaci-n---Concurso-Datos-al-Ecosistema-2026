"""
GyverLabs Backend PRO — Repositorio de evaluación
Concurso Datos al Ecosistema 2026: IA para Colombia — MinTIC

Punto de entrada de la API. Monta los routers de cada módulo y de los NUEVE
perfiles (Súper Admin, Docente, Coordinación, Rectoría, Contratación,
Contaduría, Jurídica, Secretaría y Ministerio).
Ver LICENSE en la raíz del repositorio antes de reutilizar este código.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routers import (auth, perfiles, academico, asistencia, srd, fse, aula,
                     territorio, censo, alertas, contratos, admin)
from routers import (metadatos_router, comunicados, alumno, sedes, cursos, usuarios,
                     clases, dominios, vivo, proceso, legal, secretaria)

app = FastAPI(
    title="GyverLabs API",
    description="Plataforma de gestión educativa multi-perfil PRO — repositorio de evaluación",
    version="0.3.0-evaluacion",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
app.include_router(perfiles.router, prefix="/perfiles", tags=["Perfiles (selector)"])
app.include_router(admin.router, prefix="/admin", tags=["Súper Admin (tenants)"])
app.include_router(academico.router, prefix="/academico", tags=["Estructura académica"])
app.include_router(asistencia.router, prefix="/asistencia", tags=["Asistencia"])
app.include_router(alertas.router, prefix="/alertas", tags=["Alertas y WhatsApp"])
app.include_router(srd.router, prefix="/srd", tags=["Score de Riesgo de Deserción"])
app.include_router(fse.router, prefix="/fse", tags=["Contabilidad FSE"])
app.include_router(contratos.router, prefix="/contratos", tags=["Contratación SECOP 2"])
app.include_router(aula.router, prefix="/aula", tags=["Aula Virtual PRO"])
app.include_router(territorio.router, prefix="/territorio", tags=["Secretaría y Ministerio"])
app.include_router(censo.router, prefix="/censo", tags=["Censo Juvenil Territorial"])
app.include_router(metadatos_router.router, prefix="/metadatos", tags=["Datos & IA (log unificado)"])
app.include_router(comunicados.router, prefix="/comunicados", tags=["Comunicados y notificaciones"])
app.include_router(alumno.router, prefix="/alumno", tags=["Portal del estudiante"])
app.include_router(sedes.router, prefix="/sedes", tags=["Sedes, necesidades y junta directiva"])
app.include_router(cursos.router, prefix="/cursos", tags=["Cursos preinstalados (LMS)"])
app.include_router(usuarios.router, prefix="/usuarios", tags=["Gestión de usuarios y auditoría"])
app.include_router(clases.router, prefix="/clases", tags=["Clases estructuradas y biblioteca"])
app.include_router(dominios.router, prefix="/dominios", tags=["Dominios, DNS, suscripciones y offline"])
app.include_router(vivo.router, prefix="/vivo", tags=["Sincronización en vivo"])
app.include_router(proceso.router, prefix="/proceso", tags=["Proceso de contratación, actas y minuta"])
app.include_router(legal.router, prefix="/legal", tags=["Perfil legal, rejilla y documentos"])
app.include_router(secretaria.router, prefix="/secretaria", tags=["Planeación, SIMAT y certificados"])


@app.get("/health")
def health_check():
    return {"status": "ok", "servicio": "gyverlabs-backend-eval"}


@app.on_event("startup")
def _asegurar_riesgo():
    """Red de seguridad: si la base ya tiene estudiantes pero aún no se ha
    calculado el Score de Riesgo, lo calcula al arrancar."""
    try:
        from database import SessionLocal
        from models import Estudiante, SRDScore
        from services import srd_service
        db = SessionLocal()
        try:
            hay_est = db.query(Estudiante).first() is not None
            hay_srd = db.query(SRDScore).first() is not None
            if hay_est and not hay_srd:
                srd_service.recalcular_todos(db)
        finally:
            db.close()
    except Exception as e:
        print("Aviso: no se pudo precalcular el riesgo al inicio:", e)
