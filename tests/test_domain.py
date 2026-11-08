from decimal import Decimal

import pytest

from src.domain.exceptions import InvalidOrderData, InvalidOrderTransition, WeightDiscrepancyDetected
from src.domain.models import (
    Cliente,
    Cotizacion,
    EvidenciaPOD,
    Money,
    Operador,
    OrderStatus,
    OrdenServicio,
    Ruta,
    Vehiculo,
)


@pytest.fixture
def base():
    cliente = Cliente(id="C-001", razon_social="Industrial Regiomontana SA", es_corporativo=True, activo=True)
    ruta = Ruta(origen="Monterrey", destino="Saltillo", distancia_km=85.5)
    cotizacion = Cotizacion(subtotal=Money(Decimal("2500.00")), total=Money(Decimal("2900.00")))
    orden = OrdenServicio.registrar("ORD-2026-001", cliente, ruta, cotizacion)
    vehiculo = Vehiculo(id="V-10", placas="ABC-123", tipo_unidad="Caja Seca 53ft")
    operador = Operador(id="OP-05", nombre="Rigoberto Garza", disponible=True)
    return orden, vehiculo, operador


def asignada(base):
    orden, vehiculo, operador = base
    orden.confirmar_cotizacion()
    orden.asignar_recursos(vehiculo, operador)
    return orden


# --- Value Objects ---
def test_money_valido_y_positivo():
    m = Money(Decimal("1500.50"))
    assert m.amount == Decimal("1500.50") and m.currency == "MXN"
    with pytest.raises(InvalidOrderData, match="no es válido"):
        Money(Decimal("-50.00"))


def test_money_rechaza_no_decimal_y_no_finito():
    with pytest.raises(InvalidOrderData):
        Money(100.0)  # float: se exige Decimal
    with pytest.raises(InvalidOrderData):
        Money(Decimal("NaN"))


def test_money_suma_y_monedas_distintas():
    assert Money(Decimal("10")).add(Money(Decimal("5"))).amount == Decimal("15")
    with pytest.raises(InvalidOrderData, match="monedas distintas"):
        Money(Decimal("10")).add(Money(Decimal("5"), "USD"))


@pytest.mark.parametrize("origen,destino,km", [("", "X", 10), ("X", " ", 10), ("X", "Y", 0)])
def test_ruta_invalida(origen, destino, km):
    with pytest.raises(InvalidOrderData):
        Ruta(origen, destino, km)


def test_pod_incompleta():
    with pytest.raises(InvalidOrderData, match="incompleta"):
        EvidenciaPOD(firma_digital=" ", ine="123")


def test_cliente_requiere_id_y_razon_social():
    with pytest.raises(InvalidOrderData):
        Cliente(id="", razon_social="X")


# --- Registro ---
def test_registrar_orden_estado_inicial_y_evento(base):
    orden, _, _ = base
    assert orden.status == OrderStatus.DRAFT == OrderStatus.REGISTRADO
    assert orden.status.value == "REGISTRADO"
    assert [e.name for e in orden.events] == ["OrdenRegistrada"]


def test_registrar_orden_sin_folio(base):
    orden, _, _ = base
    with pytest.raises(InvalidOrderData):
        OrdenServicio.registrar(" ", orden.cliente, orden.ruta, orden.cotizacion)


# --- Ciclo de vida ---
def test_flujo_exitoso_orden_servicio(base):
    orden, vehiculo, operador = base
    orden.confirmar_cotizacion()
    assert orden.status == OrderStatus.CONFIRMED
    orden.asignar_recursos(vehiculo, operador)
    assert orden.status == OrderStatus.UNIT_ASSIGNED and orden.vehiculo.placas == "ABC-123"
    orden.validar_recoleccion(peso_cotizado=100.0, peso_real=105.0)
    assert orden.status == OrderStatus.COLLECTED
    orden.registrar_entrega(EvidenciaPOD("FirmaJuanPerez", "1234567890", ["foto1.jpg"]))
    assert orden.status == OrderStatus.DELIVERED
    assert [e.name for e in orden.events] == [
        "OrdenRegistrada",
        "OrdenConfirmada",
        "UnidadYOperadorAsignados",
        "RecoleccionRegistrada",
        "EntregaCompletada",
    ]


def test_discrepancia_peso_mayor_15_porciento(base):
    orden = asignada(base)
    with pytest.raises(WeightDiscrepancyDetected) as exc:
        orden.validar_recoleccion(100.0, 130.0)
    assert orden.status == OrderStatus.IN_REVIEW
    assert "supera en un 30.0%" in str(exc.value) and "departamento de Ventas" in str(exc.value)
    assert orden.events[-1].name == "DiscrepanciaDetectada"


def test_peso_exactamente_15_porciento_es_tolerado(base):
    orden = asignada(base)
    orden.validar_recoleccion(100.0, 115.0)
    assert orden.status == OrderStatus.COLLECTED


@pytest.mark.parametrize("cotizado,real", [(0, 10), (-5, 10), (100, 0), (100, -1)])
def test_pesos_invalidos_no_rompen_con_division_por_cero(base, cotizado, real):
    orden = asignada(base)
    with pytest.raises(InvalidOrderData, match="mayores a cero"):
        orden.validar_recoleccion(cotizado, real)
    assert orden.status == OrderStatus.UNIT_ASSIGNED


def test_transicion_prohibida_doble_confirmacion(base):
    orden, _, _ = base
    orden.confirmar_cotizacion()
    with pytest.raises(InvalidOrderTransition, match="no se puede confirmar porque su estado actual es"):
        orden.confirmar_cotizacion()
    assert len([e for e in orden.events if e.name == "OrdenConfirmada"]) == 1


def test_confirmar_con_cliente_inactivo(base):
    orden, _, _ = base
    orden.cliente = Cliente(id="C-9", razon_social="Moroso SA", activo=False)
    with pytest.raises(InvalidOrderData, match="inactiva"):
        orden.confirmar_cotizacion()
    assert orden.status == OrderStatus.DRAFT


def test_asignar_requiere_confirmacion(base):
    orden, vehiculo, operador = base
    with pytest.raises(InvalidOrderTransition, match="previamente confirmada"):
        orden.asignar_recursos(vehiculo, operador)


def test_asignar_operador_no_disponible(base):
    orden, vehiculo, _ = base
    orden.confirmar_cotizacion()
    with pytest.raises(InvalidOrderData, match="no se encuentra disponible"):
        orden.asignar_recursos(vehiculo, Operador("OP-9", "Ocupado", disponible=False))
    assert orden.status == OrderStatus.CONFIRMED


def test_recoleccion_y_entrega_fuera_de_orden(base):
    orden, _, _ = base
    with pytest.raises(InvalidOrderTransition):
        orden.validar_recoleccion(100, 100)
    with pytest.raises(InvalidOrderTransition):
        orden.registrar_entrega(EvidenciaPOD("firma", "ine"))


def test_cancelar_orden_y_estados_finales(base):
    orden, _, _ = base
    with pytest.raises(InvalidOrderData, match="motivo"):
        orden.cancelar_orden("  ")
    orden.cancelar_orden("Cliente desistió")
    assert orden.status == OrderStatus.CANCELLED and orden.events[-1].name == "OrdenCancelada"
    with pytest.raises(InvalidOrderTransition, match="estado definitivo"):
        orden.cancelar_orden("otra vez")
    with pytest.raises(InvalidOrderTransition):
        orden.confirmar_cotizacion()


def test_transicion_directa_no_permitida(base):
    orden, _, _ = base
    with pytest.raises(InvalidOrderTransition, match="no está permitida"):
        orden._transicionar(OrderStatus.DELIVERED)
