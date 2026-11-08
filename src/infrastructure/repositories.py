"""Implementaciones SQLAlchemy de los repositorios del dominio."""
from __future__ import annotations

from datetime import timezone

from sqlalchemy.orm import Session

from src.domain.models import (
    Cliente,
    Cotizacion,
    DomainEvent,
    EvidenciaPOD,
    Money,
    Operador,
    OrderStatus,
    OrdenServicio,
    Ruta,
    Vehiculo,
)
from src.domain.repositories import (
    ClienteRepository,
    EventoRepository,
    OperadorRepository,
    OrdenServicioRepository,
    VehiculoRepository,
)
from src.infrastructure.orm_models import ClienteRow, EventoRow, OperadorRow, OrdenRow, VehiculoRow


def _upsert(session: Session, model, pk: str, **values):
    row = session.get(model, pk)
    if row is None:
        row = model(id=pk, **values)
        session.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)
    session.flush()  # respeta el orden de las llaves foráneas dentro de la transacción
    return row


class SqlAlchemyClienteRepository(ClienteRepository):
    def __init__(self, session: Session):
        self.session = session

    def guardar(self, cliente: Cliente) -> None:
        _upsert(
            self.session,
            ClienteRow,
            cliente.id,
            razon_social=cliente.razon_social,
            es_corporativo=cliente.es_corporativo,
            es_preferente=cliente.es_preferente,
            activo=cliente.activo,
            dias_morosidad=cliente.dias_morosidad,
        )

    def buscar_por_id(self, cliente_id: str) -> Cliente | None:
        row = self.session.get(ClienteRow, cliente_id)
        return self._to_domain(row) if row else None

    def listar(self) -> list[Cliente]:
        return [self._to_domain(r) for r in self.session.query(ClienteRow).order_by(ClienteRow.id)]

    @staticmethod
    def _to_domain(row: ClienteRow) -> Cliente:
        return Cliente(
            id=row.id,
            razon_social=row.razon_social,
            es_corporativo=row.es_corporativo,
            activo=row.activo,
            es_preferente=row.es_preferente,
            dias_morosidad=row.dias_morosidad,
        )


class SqlAlchemyVehiculoRepository(VehiculoRepository):
    def __init__(self, session: Session):
        self.session = session

    def guardar(self, vehiculo: Vehiculo) -> None:
        _upsert(self.session, VehiculoRow, vehiculo.id, placas=vehiculo.placas, tipo_unidad=vehiculo.tipo_unidad)

    def buscar_por_id(self, vehiculo_id: str) -> Vehiculo | None:
        row = self.session.get(VehiculoRow, vehiculo_id)
        return self._to_domain(row) if row else None

    def buscar_por_placas(self, placas: str) -> Vehiculo | None:
        row = self.session.query(VehiculoRow).filter_by(placas=placas).first()
        return self._to_domain(row) if row else None

    def listar(self) -> list[Vehiculo]:
        return [self._to_domain(r) for r in self.session.query(VehiculoRow).order_by(VehiculoRow.id)]

    @staticmethod
    def _to_domain(row: VehiculoRow) -> Vehiculo:
        return Vehiculo(id=row.id, placas=row.placas, tipo_unidad=row.tipo_unidad)


class SqlAlchemyOperadorRepository(OperadorRepository):
    def __init__(self, session: Session):
        self.session = session

    def guardar(self, operador: Operador) -> None:
        _upsert(self.session, OperadorRow, operador.id, nombre=operador.nombre, disponible=operador.disponible)

    def buscar_por_id(self, operador_id: str) -> Operador | None:
        row = self.session.get(OperadorRow, operador_id)
        return self._to_domain(row) if row else None

    def listar(self) -> list[Operador]:
        return [self._to_domain(r) for r in self.session.query(OperadorRow).order_by(OperadorRow.id)]

    @staticmethod
    def _to_domain(row: OperadorRow) -> Operador:
        return Operador(id=row.id, nombre=row.nombre, disponible=row.disponible)


class SqlAlchemyOrdenServicioRepository(OrdenServicioRepository):
    """Persiste y rehidrata el Aggregate Root completo (cliente, ruta, cotización, flota y POD)."""

    def __init__(self, session: Session):
        super().__init__()
        self.session = session

    def _guardar(self, orden: OrdenServicio) -> None:
        pod = orden.evidencia_pod
        _upsert(
            self.session,
            OrdenRow,
            orden.id,
            cliente_id=orden.cliente.id,
            vehiculo_id=orden.vehiculo.id if orden.vehiculo else None,
            operador_id=orden.operador.id if orden.operador else None,
            origen=orden.ruta.origen,
            destino=orden.ruta.destino,
            distancia_km=orden.ruta.distancia_km,
            subtotal=orden.cotizacion.subtotal.amount,
            total=orden.cotizacion.total.amount,
            moneda=orden.cotizacion.total.currency,
            porcentaje_descuento=orden.cotizacion.porcentaje_descuento,
            promocion_activa=orden.promocion_activa,
            status=orden.status.value,
            pod_firma_digital=pod.firma_digital if pod else None,
            pod_ine=pod.ine if pod else None,
            pod_fotografias=list(pod.fotografias) if pod else None,
        )

    def _buscar_por_id(self, orden_id: str) -> OrdenServicio | None:
        row = self.session.get(OrdenRow, orden_id)
        return self._rehidratar(row) if row else None

    def listar(self) -> list[OrdenServicio]:
        return [self._rehidratar(r) for r in self.session.query(OrdenRow).order_by(OrdenRow.id)]

    def _rehidratar(self, row: OrdenRow) -> OrdenServicio:
        cliente_row = self.session.get(ClienteRow, row.cliente_id)
        vehiculo_row = self.session.get(VehiculoRow, row.vehiculo_id) if row.vehiculo_id else None
        operador_row = self.session.get(OperadorRow, row.operador_id) if row.operador_id else None
        pod = (
            EvidenciaPOD(
                firma_digital=row.pod_firma_digital,
                ine=row.pod_ine,
                fotografias=list(row.pod_fotografias or []),
            )
            if row.pod_firma_digital
            else None
        )
        return OrdenServicio(
            id=row.id,
            cliente=SqlAlchemyClienteRepository._to_domain(cliente_row),
            ruta=Ruta(origen=row.origen, destino=row.destino, distancia_km=row.distancia_km),
            cotizacion=Cotizacion(
                subtotal=Money(row.subtotal, row.moneda),
                total=Money(row.total, row.moneda),
                porcentaje_descuento=row.porcentaje_descuento,
            ),
            status=OrderStatus(row.status),
            vehiculo=SqlAlchemyVehiculoRepository._to_domain(vehiculo_row) if vehiculo_row else None,
            operador=SqlAlchemyOperadorRepository._to_domain(operador_row) if operador_row else None,
            evidencia_pod=pod,
            promocion_activa=row.promocion_activa,
        )


class SqlAlchemyEventoRepository(EventoRepository):
    def __init__(self, session: Session):
        self.session = session

    def registrar(self, eventos: list[DomainEvent]) -> None:
        for e in eventos:
            self.session.add(
                EventoRow(
                    orden_id=e.order_id,
                    nombre=e.name,
                    detalle=e.detail,
                    ocurrido_en=e.occurred_at.astimezone(timezone.utc).replace(tzinfo=None),
                )
            )
        self.session.flush()

    def listar_por_orden(self, orden_id: str) -> list[DomainEvent]:
        rows = self.session.query(EventoRow).filter_by(orden_id=orden_id).order_by(EventoRow.id)
        return [self._to_domain(r) for r in rows]

    def listar_todos(self) -> list[DomainEvent]:
        return [self._to_domain(r) for r in self.session.query(EventoRow).order_by(EventoRow.id)]

    @staticmethod
    def _to_domain(row: EventoRow) -> DomainEvent:
        return DomainEvent(row.nombre, row.orden_id, row.ocurrido_en.replace(tzinfo=timezone.utc), row.detalle)
