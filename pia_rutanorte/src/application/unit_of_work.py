"""Puerto del Unit of Work: frontera transaccional de cada caso de uso."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from src.domain.models import DomainEvent
from src.domain.repositories import (
    ClienteRepository,
    OperadorRepository,
    OrdenServicioRepository,
    VehiculoRepository,
)


class AbstractUnitOfWork(ABC):
    clientes: ClienteRepository
    vehiculos: VehiculoRepository
    operadores: OperadorRepository
    ordenes: OrdenServicioRepository

    def __init__(self, event_publisher: Callable[[DomainEvent], None] | None = None):
        self.published_events: list[DomainEvent] = []
        self._event_publisher = event_publisher

    def __enter__(self) -> "AbstractUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Cualquier cambio no confirmado se descarta (ROLLBACK).
        self.rollback()

    def commit(self) -> None:
        """COMMIT y, solo después, publicación de los Domain Events acumulados."""
        self._commit()
        self._publish_events()

    def _publish_events(self) -> None:
        for orden in self.ordenes.seen.values():
            while orden.events:
                evento = orden.events.pop(0)
                self.published_events.append(evento)
                if self._event_publisher:
                    self._event_publisher(evento)

    @abstractmethod
    def _commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
