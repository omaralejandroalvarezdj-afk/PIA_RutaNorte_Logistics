"""Application Service: coordina casos de uso sin contener reglas de negocio.

Cada método abre un Unit of Work, recupera agregados mediante repositorios,
invoca el comportamiento del dominio y confirma la transacción.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Callable

from src.application.unit_of_work import AbstractUnitOfWork
from src.domain.exceptions import DuplicateEntity, EntityNotFound, WeightDiscrepancyDetected
from src.domain.models import (
    Cliente,
    Cotizacion,
    EvidenciaPOD,
    Money,
    Operador,
    OrdenServicio,
    Ruta,
    Vehiculo,
)


def _no_encontrada(orden_id: str) -> EntityNotFound:
    return EntityNotFound(f"Lo sentimos, no encontramos ninguna orden registrada con el folio '{orden_id}'.")


def _resumen(orden: OrdenServicio, mensaje: str) -> dict:
    return {
        "estado": "EXITO",
        "mensaje": mensaje,
        "folio": orden.id,
        "estatus_actual": orden.status.value,
    }


class OrdenApplicationService:
    def __init__(self, uow_factory: Callable[[], AbstractUnitOfWork]):
        self.uow_factory = uow_factory

    # ---- helpers ----------------------------------------------------------
    @staticmethod
    def _cargar_orden(uow: AbstractUnitOfWork, orden_id: str) -> OrdenServicio:
        orden = uow.ordenes.buscar_por_id(orden_id)
        if orden is None:
            raise _no_encontrada(orden_id)
        return orden

    # ---- Clientes -----------------------------------------------------------
    def registrar_cliente(
        self,
        cliente_id: str,
        razon_social: str,
        es_corporativo: bool = False,
        es_preferente: bool = False,
        activo: bool = True,
    ) -> dict:
        cliente = Cliente(
            id=cliente_id,
            razon_social=razon_social,
            es_corporativo=es_corporativo,
            activo=activo,
            es_preferente=es_preferente,
        )
        with self.uow_factory() as uow:
            if uow.clientes.buscar_por_id(cliente_id) is not None:
                raise DuplicateEntity(f"Ya existe un cliente registrado con el identificador '{cliente_id}'.")
            uow.clientes.guardar(cliente)
            uow.commit()
        return {
            "estado": "EXITO",
            "mensaje": f"Cliente '{razon_social}' registrado correctamente.",
            "cliente_id": cliente_id,
        }

    # ---- Alta de la orden -----------------------------------------------------
    def crear_orden(
        self,
        cliente_id: str,
        origen: str,
        destino: str,
        distancia_km: float,
        subtotal: Decimal,
        total: Decimal,
        porcentaje_descuento: float = 0.0,
        promocion_activa: bool = False,
        orden_id: str | None = None,
    ) -> dict:
        """Registra una orden nueva en estado inicial REGISTRADO (DRAFT) ligada a un cliente existente."""
        orden_id = orden_id or f"ORD-{uuid.uuid4().hex[:10].upper()}"
        with self.uow_factory() as uow:
            cliente = uow.clientes.buscar_por_id(cliente_id)
            if cliente is None:
                raise EntityNotFound(f"No encontramos ningún cliente registrado con el identificador '{cliente_id}'.")
            if uow.ordenes.buscar_por_id(orden_id) is not None:
                raise DuplicateEntity(f"Ya existe una orden registrada con el folio '{orden_id}'.")

            orden = OrdenServicio.registrar(
                id=orden_id,
                cliente=cliente,
                ruta=Ruta(origen=origen, destino=destino, distancia_km=distancia_km),
                cotizacion=Cotizacion(
                    subtotal=Money(subtotal),
                    total=Money(total),
                    porcentaje_descuento=porcentaje_descuento,
                ),
                promocion_activa=promocion_activa,
            )
            uow.ordenes.guardar(orden)
            uow.commit()
            resultado = _resumen(
                orden,
                f"Orden '{orden.id}' registrada correctamente para el cliente '{cliente.razon_social}'.",
            )
            resultado["beneficio_referencia"] = orden.cumple_beneficio_referencia()
            return resultado

    def consultar_orden(self, orden_id: str) -> dict:
        """Query de lectura: devuelve la vista de la orden (no modifica estado)."""
        with self.uow_factory() as uow:
            orden = self._cargar_orden(uow, orden_id)
            return {
                "folio": orden.id,
                "estatus_actual": orden.status.value,
                "cliente": {
                    "id": orden.cliente.id,
                    "razon_social": orden.cliente.razon_social,
                    "activo": orden.cliente.activo,
                    "es_preferente": orden.cliente.es_preferente,
                    "es_corporativo": orden.cliente.es_corporativo,
                },
                "ruta": {
                    "origen": orden.ruta.origen,
                    "destino": orden.ruta.destino,
                    "distancia_km": orden.ruta.distancia_km,
                },
                "cotizacion": {
                    "subtotal": str(orden.cotizacion.subtotal.amount),
                    "total": str(orden.cotizacion.total.amount),
                    "moneda": orden.cotizacion.total.currency,
                    "porcentaje_descuento": orden.cotizacion.porcentaje_descuento,
                },
                "promocion_activa": orden.promocion_activa,
                "beneficio_referencia": orden.cumple_beneficio_referencia(),
                "vehiculo": (
                    {"id": orden.vehiculo.id, "placas": orden.vehiculo.placas, "tipo_unidad": orden.vehiculo.tipo_unidad}
                    if orden.vehiculo
                    else None
                ),
                "operador": (
                    {"id": orden.operador.id, "nombre": orden.operador.nombre}
                    if orden.operador
                    else None
                ),
                "pod_registrada": orden.evidencia_pod is not None,
            }

    # ---- CU-01 ------------------------------------------------------------------
    def confirmar_cotizacion_orden(self, orden_id: str) -> dict:
        with self.uow_factory() as uow:
            orden = self._cargar_orden(uow, orden_id)
            orden.confirmar_cotizacion()
            uow.ordenes.guardar(orden)
            uow.commit()
            return _resumen(
                orden,
                f"¡Cotización confirmada exitosamente! La orden con folio '{orden.id}' ha sido aperturada "
                "bajo el estatus 'CONFIRMADA'. Se ha emitido la guía de despacho.",
            )

    # ---- CU-02 ------------------------------------------------------------------
    def asignar_recursos_orden(
        self,
        orden_id: str,
        vehiculo_id: str,
        placas: str,
        tipo_unidad: str,
        operador_id: str,
        nombre_operador: str,
    ) -> dict:
        with self.uow_factory() as uow:
            orden = self._cargar_orden(uow, orden_id)
            # Si ya existen en la flota se usan tal como están registrados (p. ej. disponibilidad real).
            vehiculo = uow.vehiculos.buscar_por_id(vehiculo_id) or Vehiculo(
                id=vehiculo_id, placas=placas, tipo_unidad=tipo_unidad
            )
            operador = uow.operadores.buscar_por_id(operador_id) or Operador(
                id=operador_id, nombre=nombre_operador, disponible=True
            )
            orden.asignar_recursos(vehiculo, operador)
            uow.vehiculos.guardar(vehiculo)
            uow.operadores.guardar(operador)
            uow.ordenes.guardar(orden)
            uow.commit()
            return _resumen(
                orden,
                f"Asignación completada: La unidad con placas '{vehiculo.placas}' y el operador "
                f"'{operador.nombre}' han sido asignados correctamente a la orden '{orden.id}'.",
            )

    # ---- CU-03 / CU-04 ----------------------------------------------------------
    def validar_recoleccion_en_origen(self, orden_id: str, peso_cotizado: float, peso_real: float) -> dict:
        with self.uow_factory() as uow:
            orden = self._cargar_orden(uow, orden_id)
            try:
                orden.validar_recoleccion(peso_cotizado, peso_real)
            except WeightDiscrepancyDetected:
                # La orden queda EN_REVISION_POR_VENTAS: ese cambio de estado SÍ se persiste.
                uow.ordenes.guardar(orden)
                uow.commit()
                raise
            uow.ordenes.guardar(orden)
            uow.commit()
            return _resumen(
                orden,
                f"Recolección validada con éxito en origen para la orden '{orden.id}'. "
                "El peso real se encuentra dentro del rango permitido. Estado: RECOLECTADO.",
            )

    # ---- CU-05 --------------------------------------------------------------------
    def registrar_entrega_con_pod(self, orden_id: str, firma: str, ine: str, fotos: list[str]) -> dict:
        with self.uow_factory() as uow:
            orden = self._cargar_orden(uow, orden_id)
            orden.registrar_entrega(EvidenciaPOD(firma_digital=firma, ine=ine, fotografias=fotos))
            uow.ordenes.guardar(orden)
            uow.commit()
            return _resumen(
                orden,
                f"¡Entrega cerrada oficialmente! Se han registrado la firma digital y las evidencias POD "
                f"para la orden '{orden.id}'. Estatus final: ENTREGADO.",
            )

    # ---- Cancelación ---------------------------------------------------------------
    def cancelar_orden(self, orden_id: str, motivo: str) -> dict:
        with self.uow_factory() as uow:
            orden = self._cargar_orden(uow, orden_id)
            orden.cancelar_orden(motivo)
            uow.ordenes.guardar(orden)
            uow.commit()
            return _resumen(orden, f"La orden '{orden.id}' fue cancelada correctamente.")
