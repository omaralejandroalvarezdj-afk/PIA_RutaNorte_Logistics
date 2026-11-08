"""Servicios de dominio: CalculadoraTarifa y catálogo de rutas/unidades."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from src.domain.exceptions import InvalidOrderData
from src.domain.models import Cotizacion, Money

CIUDADES = ["Monterrey", "Apodaca", "Saltillo", "Reynosa", "San Luis Potosí", "Querétaro"]
_DISTANCIAS = {
    ("Monterrey", "Apodaca"): 24, ("Monterrey", "Saltillo"): 86, ("Monterrey", "Reynosa"): 220,
    ("Monterrey", "San Luis Potosí"): 520, ("Monterrey", "Querétaro"): 715, ("Saltillo", "San Luis Potosí"): 435,
    ("Saltillo", "Querétaro"): 625, ("Reynosa", "Saltillo"): 310, ("San Luis Potosí", "Querétaro"): 215,
    ("Apodaca", "Saltillo"): 107,
}
IVA = Decimal("0.16")
COSTO_M3 = Decimal("18")
MULTIPLICADOR_CARGA = {"general": Decimal("1"), "perecedera": Decimal("1.14"), "alto-valor": Decimal("1.25")}


@dataclass(frozen=True)
class TipoUnidad:
    clave: str
    nombre: str
    peso_max_kg: int
    tarifa_base: Decimal
    tarifa_km: Decimal


UNIDADES = {
    u.clave: u
    for u in (
        TipoUnidad("ligera", "Carga ligera", 1500, Decimal("650"), Decimal("7.5")),
        TipoUnidad("rabon", "Rabón", 8000, Decimal("1050"), Decimal("11")),
        TipoUnidad("caja", "Caja seca 53\'", 25000, Decimal("1800"), Decimal("16")),
        TipoUnidad("trailer", "Tráiler", 25000, Decimal("2100"), Decimal("18")),
    )
}


def distancia_km(origen: str, destino: str) -> int:
    if (origen, destino) in _DISTANCIAS:
        return _DISTANCIAS[(origen, destino)]
    if (destino, origen) in _DISTANCIAS:
        return _DISTANCIAS[(destino, origen)]
    idx = lambda c: CIUDADES.index(c) if c in CIUDADES else 0  # noqa: E731
    return max(65, (idx(origen) + idx(destino) + 2) * 68)


class CalculadoraTarifa:
    """Calcula la cotización (subtotal + IVA 16 %) con Decimal."""

    @staticmethod
    def cotizar(origen: str, destino: str, unidad: str, peso_kg: float, volumen_m3: float, tipo_carga: str = "general"):
        if origen == destino:
            raise InvalidOrderData("El origen y el destino deben ser distintos.")
        if unidad not in UNIDADES:
            raise InvalidOrderData(f"Tipo de unidad desconocido: '{unidad}'.")
        if tipo_carga not in MULTIPLICADOR_CARGA:
            raise InvalidOrderData(f"Tipo de carga desconocido: '{tipo_carga}'.")
        if peso_kg <= 0 or volumen_m3 <= 0:
            raise InvalidOrderData("El peso y el volumen deben ser mayores a cero.")
        u = UNIDADES[unidad]
        if peso_kg > u.peso_max_kg:
            raise InvalidOrderData(f"La unidad {u.nombre} admite hasta {u.peso_max_kg:,} kg.")
        km = distancia_km(origen, destino)
        bruto = (u.tarifa_base + km * u.tarifa_km + Decimal(str(volumen_m3)) * COSTO_M3) * MULTIPLICADOR_CARGA[tipo_carga]
        subtotal = bruto.quantize(Decimal("0.01"), ROUND_HALF_UP)
        total = (subtotal * (1 + IVA)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        return Cotizacion(Money(subtotal), Money(total)), km
