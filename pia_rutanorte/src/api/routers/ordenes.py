from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_service
from src.api.schemas import (
    AsignarRecursosRequest,
    CancelarOrdenRequest,
    CrearOrdenRequest,
    RegistrarEntregaRequest,
    ValidarRecoleccionRequest,
)
from src.application.services import OrdenApplicationService

router = APIRouter(prefix="/orders", tags=["Órdenes de servicio"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una nueva orden de servicio (estado inicial REGISTRADO/DRAFT)",
)
def crear_orden(data: CrearOrdenRequest, service: OrdenApplicationService = Depends(get_service)):
    return service.crear_orden(
        cliente_id=data.cliente_id,
        origen=data.origen,
        destino=data.destino,
        distancia_km=data.distancia_km,
        subtotal=data.subtotal,
        total=data.total,
        porcentaje_descuento=data.porcentaje_descuento,
        promocion_activa=data.promocion_activa,
        orden_id=data.orden_id,
    )


@router.get("/{orden_id}", summary="Consultar una orden")
def consultar_orden(orden_id: str, service: OrdenApplicationService = Depends(get_service)):
    return service.consultar_orden(orden_id)


@router.post("/{orden_id}/confirmar", summary="CU-01: Confirmar Cotización")
def confirmar_cotizacion(orden_id: str, service: OrdenApplicationService = Depends(get_service)):
    return service.confirmar_cotizacion_orden(orden_id)


@router.post("/{orden_id}/asignar-recursos", summary="CU-02: Asignar Unidad y Operador")
def asignar_recursos(orden_id: str, data: AsignarRecursosRequest, service: OrdenApplicationService = Depends(get_service)):
    return service.asignar_recursos_orden(
        orden_id, data.vehiculo_id, data.placas, data.tipo_unidad, data.operador_id, data.nombre_operador
    )


@router.post("/{orden_id}/validar-recoleccion", summary="CU-03 y CU-04: Validar Recolección y Tolerancia de Peso")
def validar_recoleccion(orden_id: str, data: ValidarRecoleccionRequest, service: OrdenApplicationService = Depends(get_service)):
    return service.validar_recoleccion_en_origen(orden_id, data.peso_cotizado, data.peso_real)


@router.post("/{orden_id}/entregar", summary="CU-05: Registrar Entrega con Evidencia POD")
def registrar_entrega(orden_id: str, data: RegistrarEntregaRequest, service: OrdenApplicationService = Depends(get_service)):
    return service.registrar_entrega_con_pod(orden_id, data.firma_digital, data.ine, data.fotografias)


@router.post("/{orden_id}/cancelar", summary="Cancelar una orden")
def cancelar_orden(orden_id: str, data: CancelarOrdenRequest, service: OrdenApplicationService = Depends(get_service)):
    return service.cancelar_orden(orden_id, data.motivo)
