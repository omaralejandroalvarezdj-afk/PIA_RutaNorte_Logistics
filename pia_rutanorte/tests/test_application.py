from decimal import Decimal

import pytest

from src.domain.exceptions import (
    DuplicateEntity,
    EntityNotFound,
    InvalidOrderData,
    InvalidOrderTransition,
    WeightDiscrepancyDetected,
)
from src.domain.models import OrderStatus


@pytest.fixture
def con_orden(service):
    service.registrar_cliente("CLI-01", "Comercializadora del Norte", es_preferente=True)
    service.crear_orden(
        cliente_id="CLI-01",
        origen="Monterrey",
        destino="Saltillo",
        distancia_km=90.0,
        subtotal=Decimal("3000.00"),
        total=Decimal("3480.00"),
        orden_id="ORD-APP-001",
    )
    return service


def asignar(service, oid="ORD-APP-001"):
    return service.asignar_recursos_orden(oid, "V-50", "XYZ-999", "Tractocamión 53ft", "OP-02", "Esteban Mendiola")


def test_flujo_completo(con_orden):
    s = con_orden
    assert s.confirmar_cotizacion_orden("ORD-APP-001")["estatus_actual"] == OrderStatus.CONFIRMED.value
    assert asignar(s)["estatus_actual"] == OrderStatus.UNIT_ASSIGNED.value
    assert s.validar_recoleccion_en_origen("ORD-APP-001", 150.0, 155.0)["estatus_actual"] == OrderStatus.COLLECTED.value
    res = s.registrar_entrega_con_pod("ORD-APP-001", "FirmaDigitalValidadaCliente", "8888999900", ["e1.jpg"])
    assert res["estatus_actual"] == OrderStatus.DELIVERED.value
    assert "¡Entrega cerrada oficialmente!" in res["mensaje"]


def test_crear_orden_queda_registrada_y_ligada_al_cliente(service):
    service.registrar_cliente("CLI-7", "Siete SA", es_preferente=True)
    res = service.crear_orden("CLI-7", "A", "B", 10.0, Decimal("2000"), Decimal("2000"))
    assert res["estatus_actual"] == "REGISTRADO"
    assert res["folio"].startswith("ORD-")
    assert res["beneficio_referencia"] is True
    vista = service.consultar_orden(res["folio"])
    assert vista["cliente"]["id"] == "CLI-7" and vista["cliente"]["es_preferente"] is True
    assert vista["vehiculo"] is None and vista["operador"] is None and vista["pod_registrada"] is False


def test_crear_orden_cliente_inexistente(service):
    with pytest.raises(EntityNotFound, match="ningún cliente"):
        service.crear_orden("NO-EXISTE", "A", "B", 10.0, Decimal("1"), Decimal("1"))


def test_crear_orden_folio_duplicado(con_orden):
    with pytest.raises(DuplicateEntity, match="folio"):
        con_orden.crear_orden("CLI-01", "A", "B", 10.0, Decimal("1"), Decimal("1"), orden_id="ORD-APP-001")


def test_crear_orden_datos_invalidos(con_orden):
    with pytest.raises(InvalidOrderData):
        con_orden.crear_orden("CLI-01", "A", "B", 0, Decimal("1"), Decimal("1"))
    with pytest.raises(InvalidOrderData):
        con_orden.crear_orden("CLI-01", "A", "B", 5.0, Decimal("-1"), Decimal("1"))


def test_registrar_cliente_duplicado(service):
    service.registrar_cliente("CLI-1", "Uno")
    with pytest.raises(DuplicateEntity):
        service.registrar_cliente("CLI-1", "Otro")


def test_orden_inexistente_en_todos_los_casos_de_uso(service):
    for llamada in (
        lambda: service.consultar_orden("X"),
        lambda: service.confirmar_cotizacion_orden("X"),
        lambda: service.asignar_recursos_orden("X", "V", "P", "T", "O", "N"),
        lambda: service.validar_recoleccion_en_origen("X", 1, 1),
        lambda: service.registrar_entrega_con_pod("X", "f", "i", []),
        lambda: service.cancelar_orden("X", "m"),
    ):
        with pytest.raises(EntityNotFound, match="no encontramos ninguna orden"):
            llamada()


def test_discrepancia_de_peso_persiste_estado_en_revision(con_orden):
    s = con_orden
    s.confirmar_cotizacion_orden("ORD-APP-001")
    asignar(s)
    with pytest.raises(WeightDiscrepancyDetected) as exc:
        s.validar_recoleccion_en_origen("ORD-APP-001", 150.0, 190.0)
    assert "supera en un 26.7%" in str(exc.value) and "departamento de Ventas" in str(exc.value)
    assert s.consultar_orden("ORD-APP-001")["estatus_actual"] == OrderStatus.IN_REVIEW.value


def test_asignacion_persiste_vehiculo_y_operador(con_orden):
    s = con_orden
    s.confirmar_cotizacion_orden("ORD-APP-001")
    asignar(s)
    vista = s.consultar_orden("ORD-APP-001")
    assert vista["vehiculo"]["placas"] == "XYZ-999"
    assert vista["operador"]["nombre"] == "Esteban Mendiola"


def test_transicion_invalida_hace_rollback_y_no_cambia_estado(con_orden):
    with pytest.raises(InvalidOrderTransition):
        con_orden.registrar_entrega_con_pod("ORD-APP-001", "firma", "ine", [])
    assert con_orden.consultar_orden("ORD-APP-001")["estatus_actual"] == "REGISTRADO"


def test_cliente_inactivo_no_puede_confirmar(service):
    service.registrar_cliente("CLI-X", "Moroso SA", activo=False)
    service.crear_orden("CLI-X", "A", "B", 10.0, Decimal("100"), Decimal("100"), orden_id="O-X")
    with pytest.raises(InvalidOrderData, match="inactiva"):
        service.confirmar_cotizacion_orden("O-X")


def test_cancelar_orden(con_orden):
    res = con_orden.cancelar_orden("ORD-APP-001", "Cliente desistió")
    assert res["estatus_actual"] == "CANCELADA"
    with pytest.raises(InvalidOrderTransition):
        con_orden.cancelar_orden("ORD-APP-001", "otra vez")


def test_eventos_de_dominio_se_publican_tras_commit(con_orden, event_bus):
    con_orden.confirmar_cotizacion_orden("ORD-APP-001")
    nombres = [e.name for e in event_bus.history]
    assert nombres == ["OrdenRegistrada", "OrdenConfirmada"]


def test_operador_no_disponible_registrado_es_respetado(service, uow_factory):
    from src.domain.models import Operador

    service.registrar_cliente("C", "C SA")
    service.crear_orden("C", "A", "B", 1.0, Decimal("1"), Decimal("1"), orden_id="O1")
    service.confirmar_cotizacion_orden("O1")
    with uow_factory() as uow:
        uow.operadores.guardar(Operador("OP-OCUPADO", "Ocupado", disponible=False))
        uow.commit()
    with pytest.raises(InvalidOrderData, match="no se encuentra disponible"):
        service.asignar_recursos_orden("O1", "V1", "P", "T", "OP-OCUPADO", "Ocupado")
