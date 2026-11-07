"""Patrón Specification con composición lógica.

Las especificaciones evalúan una ``OrdenServicio`` (el candidato) y se combinan con
``&`` (AND), ``|`` (OR) y ``~`` (NOT)::

    beneficio = ClientePreferenteSpecification() & MontoMinimoSpecification() & ~PromocionActivaSpecification()
    beneficio.is_satisfied_by(orden)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # evita import circular con models.py
    from src.domain.models import OrdenServicio

MONTO_MINIMO_MXN = Decimal("1500")


class Specification(ABC):
    """Regla de negocio componible."""

    @abstractmethod
    def is_satisfied_by(self, candidate: "OrdenServicio") -> bool:
        ...

    def __and__(self, other: "Specification") -> "Specification":
        if not isinstance(other, Specification):
            return NotImplemented
        return AndSpecification(self, other)

    def __or__(self, other: "Specification") -> "Specification":
        if not isinstance(other, Specification):
            return NotImplemented
        return OrSpecification(self, other)

    def __invert__(self) -> "Specification":
        return NotSpecification(self)


class AndSpecification(Specification):
    def __init__(self, left: Specification, right: Specification):
        self.left, self.right = left, right

    def is_satisfied_by(self, candidate) -> bool:
        return self.left.is_satisfied_by(candidate) and self.right.is_satisfied_by(candidate)

    def __repr__(self) -> str:
        return f"({self.left!r} AND {self.right!r})"


class OrSpecification(Specification):
    def __init__(self, left: Specification, right: Specification):
        self.left, self.right = left, right

    def is_satisfied_by(self, candidate) -> bool:
        return self.left.is_satisfied_by(candidate) or self.right.is_satisfied_by(candidate)

    def __repr__(self) -> str:
        return f"({self.left!r} OR {self.right!r})"


class NotSpecification(Specification):
    def __init__(self, inner: Specification):
        self.inner = inner

    def is_satisfied_by(self, candidate) -> bool:
        return not self.inner.is_satisfied_by(candidate)

    def __repr__(self) -> str:
        return f"NOT {self.inner!r}"


# --- Especificaciones concretas ----------------------------------------------
class ClienteActivoSpecification(Specification):
    """El cliente de la orden tiene la cuenta activa."""

    def is_satisfied_by(self, candidate) -> bool:
        return candidate.cliente.activo

    def __repr__(self) -> str:
        return "ClienteActivo"


class ClientePreferenteSpecification(Specification):
    """El cliente de la orden es preferente."""

    def is_satisfied_by(self, candidate) -> bool:
        return candidate.cliente.es_preferente

    def __repr__(self) -> str:
        return "ClientePreferente"


class MontoMinimoSpecification(Specification):
    """El total de la cotización es >= al monto mínimo (1,500 MXN por defecto)."""

    def __init__(self, minimo: Decimal = MONTO_MINIMO_MXN):
        self.minimo = minimo

    def is_satisfied_by(self, candidate) -> bool:
        return candidate.cotizacion.total.amount >= self.minimo

    def __repr__(self) -> str:
        return f"MontoMinimo(>={self.minimo})"


class PromocionActivaSpecification(Specification):
    """La orden tiene una promoción activa."""

    def is_satisfied_by(self, candidate) -> bool:
        return candidate.promocion_activa

    def __repr__(self) -> str:
        return "PromocionActiva"
