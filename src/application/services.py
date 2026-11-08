"""Application Service: coordina casos de uso sin contener reglas de negocio.

Cada método abre un Unit of Work, recupera agregados mediante repositorios,
invoca el comportamiento del dominio y confirma la transacción.
"""
from __future__ import annotations

import uuid
from collections import Counter
from decimal import Decimal
from typing import Callable

from src.application.unit_of_work import AbstractUnitOfWork
from src.domain.exceptions import DuplicateEntity, EntityNotFound, WeightDiscrepancyDetected
from src.domain.services import CIUDADES, UNIDADES, CalculadoraTarifa
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
        dias_morosidad: int = 0,
    ) -> dict:
        cliente = Cliente(
            id=cliente_id,
            razon_social=razon_social,
            es_corporativo=es_corporativo,
            activo=activo,
            es_preferente=es_preferente,
            dias_morosidad=dias_morosidad,
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
                    "dias_morosidad": orden.cliente.dias_morosidad,
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

    # =====================  Consultas (lado lectura, CQRS)  =====================
    def catalogo(self) -> dict:
        return {
            "ciudades": CIUDADES,
            "unidades": [
                {"clave": u.clave, "nombre": u.nombre, "peso_max_kg": u.peso_max_kg} for u in UNIDADES.values()
            ],
            "tipos_carga": ["general", "perecedera", "alto-valor"],
        }

    def listar_clientes(self) -> list[dict]:
        with self.uow_factory() as uow:
            return [
                {
                    "id": c.id,
                    "razon_social": c.razon_social,
                    "es_corporativo": c.es_corporativo,
                    "es_preferente": c.es_preferente,
                    "activo": c.activo,
                    "dias_morosidad": c.dias_morosidad,
                }
                for c in uow.clientes.listar()
            ]

    def cotizar(
        self,
        origen: str,
        destino: str,
        unidad: str,
        peso_kg: float,
        volumen_m3: float,
        tipo_carga: str = "general",
        cliente_id: str | None = None,
    ) -> dict:
        """Calcula la tarifa y, si se indica cliente, valida su crédito corporativo (US-13). No guarda nada."""
        cotizacion, km = CalculadoraTarifa.cotizar(origen, destino, unidad, peso_kg, volumen_m3, tipo_carga)
        credito = {"evaluado": False, "apto": True, "mensaje": "Sin cliente seleccionado."}
        if cliente_id:
            with self.uow_factory() as uow:
                cliente = uow.clientes.buscar_por_id(cliente_id)
                if cliente is None:
                    raise EntityNotFound(f"No encontramos ningún cliente registrado con el identificador '{cliente_id}'.")
                borrador = OrdenServicio.registrar("SIMULACION", cliente, Ruta(origen, destino, km), cotizacion)
                apto = borrador.credito_vigente() and cliente.activo
                if not cliente.activo:
                    msg = "Cuenta inactiva: no puede confirmar órdenes."
                elif not apto:
                    msg = f"Crédito bloqueado por {cliente.dias_morosidad} días de morosidad (límite 30). Requiere Gerencia de Finanzas."
                else:
                    msg = "Crédito vigente." if cliente.es_corporativo else "Cliente sin línea de crédito corporativo."
                credito = {"evaluado": True, "apto": apto, "mensaje": msg}
        return {
            "origen": origen,
            "destino": destino,
            "distancia_km": km,
            "unidad": UNIDADES[unidad].nombre,
            "subtotal": str(cotizacion.subtotal.amount),
            "iva": str(cotizacion.total.amount - cotizacion.subtotal.amount),
            "total": str(cotizacion.total.amount),
            "moneda": "MXN",
            "credito": credito,
        }

    def listar_ordenes(self) -> list[dict]:
        with self.uow_factory() as uow:
            return [
                {
                    "folio": o.id,
                    "estatus_actual": o.status.value,
                    "cliente": o.cliente.razon_social,
                    "origen": o.ruta.origen,
                    "destino": o.ruta.destino,
                    "total": str(o.cotizacion.total.amount),
                    "vehiculo": o.vehiculo.placas if o.vehiculo else None,
                }
                for o in uow.ordenes.listar()
            ]

    def eventos_orden(self, orden_id: str) -> list[dict]:
        with self.uow_factory() as uow:
            self._cargar_orden(uow, orden_id)
            return [
                {"evento": e.name, "detalle": e.detail, "ocurrido_en": e.occurred_at.isoformat()}
                for e in uow.eventos.listar_por_orden(orden_id)
            ]

    def flota(self) -> dict:
        with self.uow_factory() as uow:
            estado_por_vehiculo: dict[str, str] = {}
            for o in uow.ordenes.listar():
                if o.vehiculo is None:
                    continue
                if o.status.value in ("UNIDAD_ASIGNADA", "RECOLECTADO"):
                    estado_por_vehiculo[o.vehiculo.id] = "En servicio"
                elif o.status.value == "EN_REVISION_POR_VENTAS":
                    estado_por_vehiculo[o.vehiculo.id] = "En revisión"
            return {
                "vehiculos": [
                    {"id": v.id, "placas": v.placas, "tipo_unidad": v.tipo_unidad, "estado": estado_por_vehiculo.get(v.id, "Disponible")}
                    for v in uow.vehiculos.listar()
                ],
                "operadores": [{"id": o.id, "nombre": o.nombre, "disponible": o.disponible} for o in uow.operadores.listar()],
            }

    def kpis(self) -> dict:
        """Indicadores del tablero: calculados sobre las órdenes y el historial de eventos persistido."""
        with self.uow_factory() as uow:
            ordenes = uow.ordenes.listar()
            eventos = uow.eventos.listar_todos()
        por_estado = Counter(o.status.value for o in ordenes)
        registro = {e.order_id: e.occurred_at for e in eventos if e.name == "OrdenRegistrada"}
        ciclos = [
            (e.occurred_at - registro[e.order_id]).total_seconds() / 3600
            for e in eventos
            if e.name == "EntregaCompletada" and e.order_id in registro
        ]
        total = len(ordenes)
        revision = por_estado.get("EN_REVISION_POR_VENTAS", 0)
        confirmado = sum(
            (o.cotizacion.total.amount for o in ordenes if o.status.value not in ("REGISTRADO", "CANCELADA")),
            Decimal("0"),
        )
        return {
            "total_ordenes": total,
            "por_estado": dict(por_estado),
            "discrepancias_peso": revision,
            "tasa_discrepancia_pct": round(revision / total * 100, 1) if total else 0.0,
            "entregas_completadas": por_estado.get("ENTREGADO_CON_POD", 0),
            "ciclo_promedio_horas": round(sum(ciclos) / len(ciclos), 2) if ciclos else None,
            "monto_confirmado_mxn": str(confirmado),
        }
