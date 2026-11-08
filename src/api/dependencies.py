"""Composition root: arma el servicio de aplicación con su infraestructura.

La BD se crea de forma perezosa (primer request) leyendo ``DATABASE_URL``.
En pruebas se reemplaza ``get_service`` con ``app.dependency_overrides``.
"""
from __future__ import annotations

from functools import lru_cache

from src.application.services import OrdenApplicationService
from src.infrastructure.database import build_engine, build_session_factory, init_db
from src.infrastructure.event_bus import InMemoryEventBus
from src.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@lru_cache(maxsize=1)
def get_event_bus() -> InMemoryEventBus:
    return InMemoryEventBus()


@lru_cache(maxsize=1)
def _build_service() -> OrdenApplicationService:
    engine = build_engine()
    init_db(engine)
    session_factory = build_session_factory(engine)
    bus = get_event_bus()
    return OrdenApplicationService(lambda: SqlAlchemyUnitOfWork(session_factory, bus.publish))


def get_service() -> OrdenApplicationService:
    return _build_service()
