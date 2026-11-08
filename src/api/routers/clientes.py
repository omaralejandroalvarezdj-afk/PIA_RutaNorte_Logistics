from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_service
from src.api.schemas import RegistrarClienteRequest
from src.application.services import OrdenApplicationService

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post("", status_code=status.HTTP_201_CREATED, summary="Registrar un cliente")
def registrar_cliente(data: RegistrarClienteRequest, service: OrdenApplicationService = Depends(get_service)):
    service.registrar_cliente(
        cliente_id=data.id,
        razon_social=data.razon_social,
        es_corporativo=data.es_corporativo,
        es_preferente=data.es_preferente,
        activo=data.activo,
        dias_morosidad=data.dias_morosidad,
    )
    return {"mensaje": "El cliente fue registrado correctamente.", "cliente": data.razon_social}


@router.get("", summary="Consultar clientes")
def listar_clientes(service: OrdenApplicationService = Depends(get_service)):
    return service.listar_clientes()
