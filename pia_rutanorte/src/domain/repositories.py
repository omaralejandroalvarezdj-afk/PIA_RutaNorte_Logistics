"""Interfaces (puertos) de Repository expresadas en términos del dominio.

Las implementaciones concretas viven en ``src/infrastructure``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import Cliente, Operador, OrdenServicio, Vehiculo


class ClienteRepository(ABC):
    @abstractmethod
    def guardar(self, cliente: Cliente) -> None: ...

    @abstractmethod
    def buscar_por_id(self, cliente_id: str) -> Cliente | None: ...


class VehiculoRepository(ABC):
    @abstractmethod
    def guardar(self, vehiculo: Vehiculo) -> None: ...

    @abstractmethod
    def buscar_por_id(self, vehiculo_id: str) -> Vehiculo | None: ...

    @abstractmethod
    def buscar_por_placas(self, placas: str) -> Vehiculo | None: ...


class OperadorRepository(ABC):
    @abstractmethod
    def guardar(self, operador: Operador) -> None: ...

    @abstractmethod
    def buscar_por_id(self, operador_id: str) -> Operador | None: ...


class OrdenServicioRepository(ABC):
    """Repositorio del Aggregate Root. Recuerda las órdenes tocadas (``seen``)
    para que el Unit of Work pueda publicar sus Domain Events tras el COMMIT."""

    def __init__(self) -> None:
        self.seen: dict[str, OrdenServicio] = {}

    def guardar(self, orden: OrdenServicio) -> None:
        self._guardar(orden)
        self.seen[orden.id] = orden

    def buscar_por_id(self, orden_id: str) -> OrdenServicio | None:
        orden = self._buscar_por_id(orden_id)
        if orden is not None:
            self.seen[orden.id] = orden
        return orden

    @abstractmethod
    def _guardar(self, orden: OrdenServicio) -> None: ...

    @abstractmethod
    def _buscar_por_id(self, orden_id: str) -> OrdenServicio | None: ...
