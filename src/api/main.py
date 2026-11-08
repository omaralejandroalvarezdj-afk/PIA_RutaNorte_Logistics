"""Punto de entrada FastAPI. Traduce excepciones de dominio a códigos HTTP en un solo lugar:

    404  EntityNotFound               (orden / cliente inexistente)
    409  InvalidOrderTransition,      (transición prohibida)
         WeightDiscrepancyDetected,   (peso > 15%)
         DuplicateEntity              (folio / cliente repetido)
    422  InvalidOrderData            (datos que violan reglas de negocio) y validación Pydantic
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from src.api.routers import clientes, consultas, ordenes
from src.domain.exceptions import (
    CreditoBloqueado,
    DuplicateEntity,
    EntityNotFound,
    InvalidOrderData,
    InvalidOrderTransition,
    WeightDiscrepancyDetected,
)

ERROR_STATUS: dict[type[Exception], int] = {
    EntityNotFound: 404,
    InvalidOrderTransition: 409,
    WeightDiscrepancyDetected: 409,
    DuplicateEntity: 409,
    InvalidOrderData: 422,
    CreditoBloqueado: 409,
}

MENSAJES_ERROR = {
    EntityNotFound: "No encontramos el cliente o la orden solicitada. Revisa el identificador.",
    InvalidOrderTransition: "No puedes realizar esta operación en el estado actual de la orden.",
    WeightDiscrepancyDetected: "El peso supera el límite permitido. Tu orden necesita revisión antes de continuar.",
    DuplicateEntity: "Ya existe un registro con ese identificador. Utiliza uno diferente.",
    CreditoBloqueado: "No se puede confirmar la orden porque el cliente tiene pagos vencidos. Comunícate con Finanzas.",
    InvalidOrderData: "No se pudo completar la operación. Revisa que los datos sean correctos.",
}

STATIC_DIR = Path(__file__).parent / "static"

def create_app() -> FastAPI:
    application = FastAPI(
        title="RutaNorte Logistics - API de Lógica de Negocio",
        description="API REST para la gestión de órdenes de transporte, control de flota, validaciones de recolección y entrega POD.",
        version="2.0.0",
    )
    application.include_router(clientes.router)
    application.include_router(ordenes.router)
    application.include_router(consultas.router)

   
    def _handler(status_code: int):
        async def handle(_: Request, exc: Exception) -> JSONResponse:
            mensaje = MENSAJES_ERROR.get(
                type(exc),
                "No se pudo completar la operación."
            )
            return JSONResponse(
                status_code=status_code,
                content={"mensaje": mensaje}
            )

        return handle

    for exc_type, code in ERROR_STATUS.items():
        application.add_exception_handler(exc_type, _handler(code))

    @application.exception_handler(RequestValidationError)
    async def error_datos_invalidos(
        request: Request,
        exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=422,
            content={
                "mensaje": "Revisa los datos ingresados. Hay información faltante o incorrecta."
            }
        )

    @application.get("/health", tags=["Sistema"], summary="Estado del servicio")
    def health():
        return {"mensaje": "El sistema está funcionando correctamente."}
   #se muestra interfaz web
    application.mount(
        "/",
        StaticFiles(directory=STATIC_DIR, html=True),
        name="interfaz"
    )
    return application


app = create_app()
