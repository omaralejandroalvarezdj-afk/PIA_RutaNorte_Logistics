"""Puerto del Unit of Work: frontera transaccional de cada caso de uso."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from src.domain.models import DomainEvent
from src.domain.repositories import (
    EventoRepository,
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
    eventos: EventoRepository

    def __init__(self, event_publisher: Callable[[DomainEvent], None] | None = None):
        self.published_events: list[DomainEvent] = []
        self._event_publisher = event_publisher

    def __enter__(self) -> "AbstractUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Cualquier cambio no confirmado se descarta (ROLLBACK).
        self.rollback()

    def commit(self) -> None:
        """Guarda los eventos en la MISMA transacción, hace COMMIT y solo después los publica."""
        pendientes = self._recolectar_eventos()
        self._guardar_eventos(pendientes)
        self._commit()
        for evento in pendientes:
            self.published_events.append(evento)
            if self._event_publisher:
                self._event_publisher(evento)

    def _recolectar_eventos(self) -> list[DomainEvent]:
        pendientes: list[DomainEvent] = []
        for orden in self.ordenes.seen.values():
            pendientes.extend(orden.events)
            orden.events.clear()
        return pendientes

    def _guardar_eventos(self, eventos: list[DomainEvent]) -> None:
        if eventos:
            self.eventos.registrar(eventos)

    @abstractmethod
    def _commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
