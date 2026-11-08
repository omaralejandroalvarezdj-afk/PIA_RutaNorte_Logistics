"""Composition root: arma el servicio de aplicación con su infraestructura.

La BD se crea de forma perezosa (primer request) leyendo ``DATABASE_URL``.
En pruebas se reemplaza ``get_service`` con ``app.dependency_overrides``.
"""
from __future__ import annotations

import os
from functools import lru_cache

from src.application.services import OrdenApplicationService
from src.infrastructure.database import build_engine, build_session_factory, init_db
from src.infrastructure.event_bus import InMemoryEventBus
from src.infrastructure.seed import sembrar_demo
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
    uow_factory = lambda: SqlAlchemyUnitOfWork(session_factory, bus.publish)  # noqa: E731
    if os.getenv("SEED_DEMO", "1") != "0":
        sembrar_demo(uow_factory)
    return OrdenApplicationService(uow_factory)


def get_service() -> OrdenApplicationService:
    return _build_service()
