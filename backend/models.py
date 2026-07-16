"""
Modelos de base de datos — versión de evaluación/demo.

Este esquema es una SIMPLIFICACIÓN pública del modelo de datos real
(descrito completo en docs/ARQUITECTURA.md y en el Mapa Maestro interno).
Sirve para poblar la base de datos de demostración (SQLite) que alimenta
la API y el dashboard durante la evaluación del jurado.

No representa el esquema multi-tenant completo de producción (que usa
un schema de PostgreSQL por institución) — aquí se usa una sola base
SQLite de un colegio de ejemplo para que la demo corra sin
dependencias externas (sin Postgres, sin Redis, sin Docker).
"""

from datetime import date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Estudiante(Base):
    __tablename__ = "estudiantes"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    grado = Column(String, nullable=False)       # p.ej. "901"
    nivel_sisben = Column(String, nullable=False)  # A1, A2, B1, C1... (simulado)
    zona = Column(String, nullable=False)          # "urbana" / "rural"

    asistencias = relationship("Asistencia", back_populates="estudiante")
    notas = relationship("Nota", back_populates="estudiante")
    scores = relationship("SRDScore", back_populates="estudiante")


class Asistencia(Base):
    __tablename__ = "asistencia"

    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    fecha = Column(Date, nullable=False)
    presente = Column(Boolean, nullable=False)

    estudiante = relationship("Estudiante", back_populates="asistencias")


class Nota(Base):
    __tablename__ = "notas"

    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    semana = Column(Integer, nullable=False)
    promedio = Column(Float, nullable=False)

    estudiante = relationship("Estudiante", back_populates="notas")


class SRDScore(Base):
    """Última puntuación calculada por el modelo demo para cada estudiante."""
    __tablename__ = "srd_scores"

    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    score = Column(Float, nullable=False)
    nivel = Column(String, nullable=False)
    factores = Column(String, nullable=False)  # separados por "|"

    estudiante = relationship("Estudiante", back_populates="scores")


class MovimientoFSE(Base):
    __tablename__ = "movimientos_fse"

    id = Column(Integer, primary_key=True)
    fecha = Column(Date, nullable=False)
    concepto = Column(String, nullable=False)
    cuenta_cgn = Column(String, nullable=False)
    valor = Column(Float, nullable=False)  # positivo = ingreso, negativo = egreso


def get_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def get_sessionmaker(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
