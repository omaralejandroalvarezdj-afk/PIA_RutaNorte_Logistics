"""Punto de entrada FastAPI. Traduce excepciones de dominio a códigos HTTP en un solo lugar:

    404  EntityNotFound               (orden / cliente inexistente)
    409  InvalidOrderTransition,      (transición prohibida)
         WeightDiscrepancyDetected,   (peso > 15%)
         DuplicateEntity              (folio / cliente repetido)
    422  InvalidOrderData            (datos que violan reglas de negocio) y validación Pydantic
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.routers import clientes, ordenes
from src.domain.exceptions import (
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
}


def create_app() -> FastAPI:
    application = FastAPI(
        title="RutaNorte Logistics - API de Lógica de Negocio",
        description="API REST para la gestión de órdenes de transporte, control de flota, validaciones de recolección y entrega POD.",
        version="2.0.0",
    )
    application.include_router(clientes.router)
    application.include_router(ordenes.router)

    def _handler(status_code: int):
        async def handle(_: Request, exc: Exception) -> JSONResponse:
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})

        return handle

    for exc_type, code in ERROR_STATUS.items():
        application.add_exception_handler(exc_type, _handler(code))

    @application.get("/health", tags=["Sistema"], summary="Estado del servicio")
    def health():
        return {"status": "ok"}

    return application


app = create_app()
