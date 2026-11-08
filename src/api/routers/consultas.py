from fastapi import APIRouter, Depends

from src.api.dependencies import get_service
from src.api.schemas import CotizarRequest
from src.application.services import OrdenApplicationService

router = APIRouter(tags=["Cotización e indicadores"])


@router.get("/catalogo", summary="Ciudades, tipos de unidad y de carga")
def catalogo(service: OrdenApplicationService = Depends(get_service)):
    return service.catalogo()


@router.post("/cotizaciones", summary="Calcular tarifa y validar crédito corporativo (US-13)")
def cotizar(data: CotizarRequest, service: OrdenApplicationService = Depends(get_service)):
    return service.cotizar(**data.model_dump())


@router.get("/flota", summary="Vehículos (con estado) y operadores")
def flota(service: OrdenApplicationService = Depends(get_service)):
    return service.flota()


@router.get("/kpis", summary="Indicadores del tablero")
def kpis(service: OrdenApplicationService = Depends(get_service)):
    return service.kpis()
