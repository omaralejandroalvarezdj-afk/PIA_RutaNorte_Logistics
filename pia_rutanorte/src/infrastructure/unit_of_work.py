"""Unit of Work concreto sobre una sesión de SQLAlchemy."""
from __future__ import annotations

from typing import Callable

from sqlalchemy.orm import Session

from src.application.unit_of_work import AbstractUnitOfWork
from src.domain.models import DomainEvent
from src.infrastructure.repositories import (
    SqlAlchemyClienteRepository,
    SqlAlchemyOperadorRepository,
    SqlAlchemyOrdenServicioRepository,
    SqlAlchemyVehiculoRepository,
)


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """BEGIN al entrar, COMMIT explícito, ROLLBACK ante error o si no hubo commit."""

    def __init__(self, session_factory: Callable[[], Session], event_publisher: Callable[[DomainEvent], None] | None = None):
        super().__init__(event_publisher)
        self.session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self.session_factory()
        self.clientes = SqlAlchemyClienteRepository(self.session)
        self.vehiculos = SqlAlchemyVehiculoRepository(self.session)
        self.operadores = SqlAlchemyOperadorRepository(self.session)
        self.ordenes = SqlAlchemyOrdenServicioRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        super().__exit__(exc_type, exc_val, exc_tb)
        self.session.close()

    def _commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        if self.session is not None:
            self.session.rollback()
