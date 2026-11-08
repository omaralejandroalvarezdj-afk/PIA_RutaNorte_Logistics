"""Modelo de dominio de RutaNorte Logistics.

Aggregate Root: ``OrdenServicio``. Value Objects: ``Money``, ``Ruta``,
``Cotizacion``, ``EvidenciaPOD``. Entidades de referencia: ``Cliente``,
``Vehiculo``, ``Operador``. No depende de FastAPI ni de SQLAlchemy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from src.domain.exceptions import (
    CreditoBloqueado,
    InvalidOrderData,
    InvalidOrderTransition,
    WeightDiscrepancyDetected,
)
from src.domain.specifications import (
    ClienteActivoSpecification,
    ClienteCorporativoSpecification,
    MorosidadDentroLimiteSpecification,
    ClientePreferenteSpecification,
    MontoMinimoSpecification,
    PromocionActivaSpecification,
)

TOLERANCIA_PESO_PORCENTUAL = Decimal("15")


# --- Máquina de estados de la orden ---------------------------------------
class OrderStatus(str, Enum):
    DRAFT = "REGISTRADO"  # estado inicial (alias: REGISTRADO)
    REGISTRADO = "REGISTRADO"
    CONFIRMED = "CONFIRMADA"
    UNIT_ASSIGNED = "UNIDAD_ASIGNADA"
    COLLECTED = "RECOLECTADO"
    IN_REVIEW = "EN_REVISION_POR_VENTAS"  # discrepancia de peso > 15%
    DELIVERED = "ENTREGADO_CON_POD"
    CANCELLED = "CANCELADA"


TRANSICIONES_VALIDAS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.DRAFT: frozenset({OrderStatus.CONFIRMED, OrderStatus.CANCELLED}),
    OrderStatus.CONFIRMED: frozenset({OrderStatus.UNIT_ASSIGNED, OrderStatus.CANCELLED}),
    OrderStatus.UNIT_ASSIGNED: frozenset(
        {OrderStatus.COLLECTED, OrderStatus.IN_REVIEW, OrderStatus.CANCELLED}
    ),
    OrderStatus.COLLECTED: frozenset({OrderStatus.DELIVERED, OrderStatus.CANCELLED}),
    OrderStatus.IN_REVIEW: frozenset({OrderStatus.CANCELLED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


# --- Value Objects (inmutables) --------------------------------------------
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "MXN"

    def __post_init__(self):
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite() or self.amount < 0:
            raise InvalidOrderData(
                f"El monto proporcionado (${self.amount}) no es válido. "
                "Por favor, verifique que la cantidad sea un valor numérico positivo."
            )

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise InvalidOrderData(
                f"No es posible sumar montos con monedas distintas ({self.currency} y {other.currency})."
            )
        return Money(self.amount + other.amount, self.currency)


@dataclass(frozen=True)
class Ruta:
    origen: str
    destino: str
    distancia_km: float

    def __post_init__(self):
        if not self.origen.strip() or not self.destino.strip() or self.distancia_km <= 0:
            raise InvalidOrderData(
                "La ruta de transporte debe contener un origen, destino y una distancia en kilómetros válida."
            )


@dataclass(frozen=True)
class Cotizacion:
    subtotal: Money
    total: Money
    porcentaje_descuento: float = 0.0


@dataclass(frozen=True)
class EvidenciaPOD:
    """Proof of Delivery (POD) requerida en el CU-05."""

    firma_digital: str
    ine: str
    fotografias: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.firma_digital.strip() or not self.ine.strip():
            raise InvalidOrderData(
                "La evidencia de entrega (POD) está incompleta: se requiere la firma digital "
                "y el número de INE del receptor."
            )


# --- Entidades de apoyo ------------------------------------------------------
@dataclass(frozen=True)
class Cliente:
    id: str
    razon_social: str
    es_corporativo: bool = False
    activo: bool = True
    es_preferente: bool = False
    dias_morosidad: int = 0

    def __post_init__(self):
        if not self.id.strip() or not self.razon_social.strip():
            raise InvalidOrderData("El cliente requiere un identificador y una razón social.")
        if self.dias_morosidad < 0:
            raise InvalidOrderData("Los días de morosidad no pueden ser negativos.")


@dataclass(frozen=True)
class Vehiculo:
    id: str
    placas: str
    tipo_unidad: str


@dataclass(frozen=True)
class Operador:
    id: str
    nombre: str
    disponible: bool = True


@dataclass(frozen=True)
class DomainEvent:
    name: str
    order_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    detail: str = ""


# --- Aggregate Root ----------------------------------------------------------
@dataclass
class OrdenServicio:
    id: str
    cliente: Cliente
    ruta: Ruta
    cotizacion: Cotizacion
    status: OrderStatus = OrderStatus.DRAFT
    vehiculo: Vehiculo | None = None
    operador: Operador | None = None
    evidencia_pod: EvidenciaPOD | None = None
    promocion_activa: bool = False
    events: list[DomainEvent] = field(default_factory=list)

    # -- Fábrica ----------------------------------------------------------
    @classmethod
    def registrar(
        cls,
        id: str,
        cliente: Cliente,
        ruta: Ruta,
        cotizacion: Cotizacion,
        promocion_activa: bool = False,
    ) -> "OrdenServicio":
        """Crea una orden nueva en su estado inicial (REGISTRADO) y emite OrdenRegistrada."""
        if not id.strip():
            raise InvalidOrderData("La orden requiere un folio.")
        orden = cls(
            id=id,
            cliente=cliente,
            ruta=ruta,
            cotizacion=cotizacion,
            status=OrderStatus.DRAFT,
            promocion_activa=promocion_activa,
        )
        orden.events.append(DomainEvent("OrdenRegistrada", id))
        return orden

    # -- Reglas expresadas con Specifications -------------------------------
    def cumple_beneficio_referencia(self) -> bool:
        """preferente AND total >= 1500 MXN AND NOT promoción activa."""
        regla = (
            ClientePreferenteSpecification()
            & MontoMinimoSpecification()
            & ~PromocionActivaSpecification()
        )
        return regla.is_satisfied_by(self)

    def credito_vigente(self) -> bool:
        """US-13: NOT corporativo OR morosidad <= 30 días."""
        regla = ~ClienteCorporativoSpecification() | MorosidadDentroLimiteSpecification()
        return regla.is_satisfied_by(self)

    # -- Máquina de estados -----------------------------------------------
    def _transicionar(self, destino: OrderStatus) -> None:
        if destino not in TRANSICIONES_VALIDAS[self.status]:
            raise InvalidOrderTransition(
                f"La transición de '{self.status.value}' a '{destino.value}' no está permitida "
                f"para la orden {self.id}."
            )
        self.status = destino

    # CU-01
    def confirmar_cotizacion(self):
        if self.status != OrderStatus.DRAFT:
            raise InvalidOrderTransition(
                f"La orden {self.id} no se puede confirmar porque su estado actual es '{self.status.value}'. "
                "Solo las órdenes en estado de borrador o cotización inicial pueden confirmarse."
            )
        if not ClienteActivoSpecification().is_satisfied_by(self):
            raise InvalidOrderData(
                f"No es posible confirmar la orden para el cliente '{self.cliente.razon_social}' "
                "debido a que su cuenta se encuentra inactiva o con restricciones financieras."
            )
        if not self.credito_vigente():
            raise CreditoBloqueado(
                f"Crédito bloqueado: '{self.cliente.razon_social}' acumula {self.cliente.dias_morosidad} días de "
                "morosidad (límite 30). Se requiere la intervención de Gerencia de Finanzas."
            )
        self._transicionar(OrderStatus.CONFIRMED)
        self.events.append(DomainEvent("OrdenConfirmada", self.id))

    # CU-02
    def asignar_recursos(self, vehiculo: Vehiculo, operador: Operador):
        if self.status != OrderStatus.CONFIRMED:
            raise InvalidOrderTransition(
                "La asignación de flota requiere que la orden esté previamente confirmada por el cliente."
            )
        if not operador.disponible:
            raise InvalidOrderData(f"El operador {operador.nombre} no se encuentra disponible en este momento.")
        self._transicionar(OrderStatus.UNIT_ASSIGNED)
        self.vehiculo = vehiculo
        self.operador = operador
        self.events.append(DomainEvent("UnidadYOperadorAsignados", self.id, detail=f"Unidad {vehiculo.placas} · operador {operador.nombre}"))

    # CU-03 y CU-04
    def validar_recoleccion(self, peso_cotizado: float, peso_real: float):
        if self.status != OrderStatus.UNIT_ASSIGNED:
            raise InvalidOrderTransition(
                "No se puede realizar la validación de recolección en campo si la unidad no ha sido asignada previamente."
            )
        if peso_cotizado <= 0 or peso_real <= 0:
            raise InvalidOrderData("Los pesos cotizado y real deben ser mayores a cero.")

        cotizado, real = Decimal(str(peso_cotizado)), Decimal(str(peso_real))
        diferencia = (real - cotizado) / cotizado * 100

        if diferencia > TOLERANCIA_PESO_PORCENTUAL:
            self._transicionar(OrderStatus.IN_REVIEW)
            self.events.append(
                DomainEvent("DiscrepanciaDetectada", self.id, detail=f"Peso cotizado {peso_cotizado} kg · real {peso_real} kg · variación {diferencia:.1f}%")
            )
            raise WeightDiscrepancyDetected(
                f"Alerta operativa: El peso real registrado ({peso_real} kg) supera en un {diferencia:.1f}% "
                f"al peso cotizado ({peso_cotizado} kg), sobrepasando la tolerancia permitida del 15%. "
                "La orden ha sido pausada y derivada automáticamente al departamento de Ventas para recotización."
            )

        self._transicionar(OrderStatus.COLLECTED)
        self.events.append(
            DomainEvent("RecoleccionRegistrada", self.id, detail=f"Variación de peso {diferencia:.1f}% dentro de tolerancia")
        )

    # CU-05
    def registrar_entrega(self, evidencia: EvidenciaPOD):
        if self.status != OrderStatus.COLLECTED:
            raise InvalidOrderTransition(
                "No se puede registrar la entrega final porque la mercancía aún no ha sido marcada como recolectada en origen."
            )
        self._transicionar(OrderStatus.DELIVERED)
        self.evidencia_pod = evidencia
        self.events.append(DomainEvent("EntregaCompletada", self.id, detail="POD registrada (firma, INE y fotografías)"))

    def cancelar_orden(self, motivo: str):
        if self.status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
            raise InvalidOrderTransition(
                f"No es posible cancelar la orden {self.id} ya que se encuentra en un estado definitivo: '{self.status.value}'."
            )
        if not motivo.strip():
            raise InvalidOrderData("Debe proporcionar un motivo claro y justificado para la cancelación de la orden.")
        self._transicionar(OrderStatus.CANCELLED)
        self.events.append(DomainEvent("OrdenCancelada", self.id, detail=motivo))
