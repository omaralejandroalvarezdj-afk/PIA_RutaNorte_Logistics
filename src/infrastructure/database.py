"""Configuración de base de datos.

La URL se lee de la variable de entorno ``DATABASE_URL``; si no existe se usa un
SQLite local (``rutanorte.db``). La lectura se hace en tiempo de ejecución, no al importar.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.orm_models import Base

DEFAULT_DATABASE_URL = "sqlite:///rutanorte.db"


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip() or DEFAULT_DATABASE_URL
    # Render entrega "postgres://" o "postgresql://"; se fuerza psycopg2, el driver instalado en la imagen.
    for prefijo in ("postgres://", "postgresql://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg2://" + url[len(prefijo):]
    return url


def build_engine(url: str | None = None) -> Engine:
    url = url or get_database_url()
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url or url in ("sqlite://", "sqlite:///"):
            # una sola conexión compartida para que la BD en memoria sobreviva entre sesiones
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)
