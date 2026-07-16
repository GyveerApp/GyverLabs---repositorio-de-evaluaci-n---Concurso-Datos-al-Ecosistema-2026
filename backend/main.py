"""
GyverLabs Backend — Repositorio de evaluación
Concurso Datos al Ecosistema 2026: IA para Colombia — MinTIC

Punto de entrada de la API. Monta los routers de cada módulo.
Ver LICENSE en la raíz del repositorio antes de reutilizar este código.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routers import auth, academico, asistencia, srd, fse, censo

app = FastAPI(
    title="GyverLabs API",
    description="Plataforma SaaS multi-tenant de gestión educativa — repositorio de evaluación",
    version="0.1.0-evaluacion",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
app.include_router(academico.router, prefix="/academico", tags=["Estructura académica"])
app.include_router(asistencia.router, prefix="/asistencia", tags=["Asistencia y alertas"])
app.include_router(srd.router, prefix="/srd", tags=["Score de Riesgo de Deserción"])
app.include_router(fse.router, prefix="/fse", tags=["Contabilidad FSE"])
app.include_router(censo.router, prefix="/censo", tags=["Censo Juvenil Territorial"])


@app.get("/health")
def health_check():
    return {"status": "ok", "servicio": "gyverlabs-backend-eval"}
