"""Esquemas Pydantic (DTOs de entrada) de la API."""
from decimal import Decimal

from pydantic import BaseModel, Field


class RegistrarClienteRequest(BaseModel):
    id: str = Field(..., min_length=1, json_schema_extra={"examples": ["CLI-001"]})
    razon_social: str = Field(..., min_length=1, json_schema_extra={"examples": ["Industrial Regiomontana SA"]})
    es_corporativo: bool = False
    es_preferente: bool = False
    activo: bool = True
    dias_morosidad: int = Field(0, ge=0)


class CotizarRequest(BaseModel):
    origen: str = Field(..., min_length=1)
    destino: str = Field(..., min_length=1)
    unidad: str = Field(..., json_schema_extra={"examples": ["rabon"]})
    peso_kg: float = Field(..., gt=0)
    volumen_m3: float = Field(..., gt=0)
    tipo_carga: str = "general"
    cliente_id: str | None = None


class CrearOrdenRequest(BaseModel):
    cliente_id: str = Field(..., min_length=1, json_schema_extra={"examples": ["CLI-001"]})
    origen: str = Field(..., min_length=1, json_schema_extra={"examples": ["Monterrey"]})
    destino: str = Field(..., min_length=1, json_schema_extra={"examples": ["Saltillo"]})
    distancia_km: float = Field(..., gt=0, json_schema_extra={"examples": [85.5]})
    subtotal: Decimal = Field(..., ge=0, json_schema_extra={"examples": ["2500.00"]})
    total: Decimal = Field(..., ge=0, json_schema_extra={"examples": ["2900.00"]})
    porcentaje_descuento: float = Field(0.0, ge=0, le=100)
    promocion_activa: bool = False
    orden_id: str | None = Field(None, description="Folio opcional; si se omite el sistema lo genera.")


class CancelarOrdenRequest(BaseModel):
    motivo: str = Field(..., json_schema_extra={"examples": ["El cliente solicitó cancelar el envío"]})


class AsignarRecursosRequest(BaseModel):
    vehiculo_id: str = Field(..., json_schema_extra={"examples": ["V-10"]})
    placas: str = Field(..., json_schema_extra={"examples": ["ABC-123"]})
    tipo_unidad: str = Field(..., json_schema_extra={"examples": ["Caja Seca 53ft"]})
    operador_id: str = Field(..., json_schema_extra={"examples": ["OP-05"]})
    nombre_operador: str = Field(..., json_schema_extra={"examples": ["Rigoberto Garza"]})


class ValidarRecoleccionRequest(BaseModel):
    peso_cotizado: float = Field(..., gt=0, json_schema_extra={"examples": [100.0]})
    peso_real: float = Field(..., gt=0, json_schema_extra={"examples": [130.0]})


class RegistrarEntregaRequest(BaseModel):
    firma_digital: str = Field(..., json_schema_extra={"examples": ["FirmaDigitalJuanPerezABC"]})
    ine: str = Field(..., json_schema_extra={"examples": ["1234567890"]})
    fotografias: list[str] = Field(default_factory=list)
