"""Pruebas de lo que consume la interfaz: crédito (US-13), tarifas, eventos, KPIs, flota y estáticos."""
from decimal import Decimal

import pytest

from src.domain.exceptions import CreditoBloqueado, InvalidOrderData
from src.domain.models import Cliente, Cotizacion, Money, OrdenServicio, Ruta
from src.domain.services import CalculadoraTarifa, distancia_km
from src.domain.specifications import MorosidadDentroLimiteSpecification
from src.infrastructure.seed import sembrar_demo

COT = {"origen": "Monterrey", "destino": "Saltillo", "unidad": "rabon", "peso_kg": 1000, "volumen_m3": 8}


def orden(cliente):
    return OrdenServicio.registrar("O-1", cliente, Ruta("A", "B", 10), Cotizacion(Money(Decimal("100")), Money(Decimal("116"))))


# ---- dominio
@pytest.mark.parametrize(
    "corp,dias,ok", [(True, 30, True), (True, 31, False), (True, 45, False), (False, 99, True), (False, 0, True)]
)
def test_credito_vigente_not_corporativo_or_morosidad(corp, dias, ok):
    assert orden(Cliente("C", "C SA", es_corporativo=corp, dias_morosidad=dias)).credito_vigente() is ok


def test_confirmar_con_credito_bloqueado_lanza_excepcion():
    o = orden(Cliente("C", "Moroso SA", es_corporativo=True, dias_morosidad=45))
    with pytest.raises(CreditoBloqueado, match="Gerencia de Finanzas"):
        o.confirmar_cotizacion()


def test_morosidad_negativa_invalida():
    with pytest.raises(InvalidOrderData):
        Cliente("C", "C SA", dias_morosidad=-1)


def test_repr_spec_morosidad():
    assert repr(MorosidadDentroLimiteSpecification()) == "MorosidadDentroLimite(<=30d)"


def test_calculadora_tarifa_decimal_exacta():
    cot, km = CalculadoraTarifa.cotizar("Monterrey", "Saltillo", "rabon", 1000, 8)
    assert km == 86 and cot.subtotal.amount == Decimal("2140.00") and cot.total.amount == Decimal("2482.40")
    alto, _ = CalculadoraTarifa.cotizar("Monterrey", "Saltillo", "rabon", 1000, 8, "alto-valor")
    assert alto.subtotal.amount == Decimal("2675.00")


@pytest.mark.parametrize(
    "args",
    [("A", "A", "rabon", 1, 1), ("Monterrey", "Saltillo", "xx", 1, 1), ("Monterrey", "Saltillo", "ligera", 2000, 1),
     ("Monterrey", "Saltillo", "rabon", 0, 1), ("Monterrey", "Saltillo", "rabon", 1, 0)],
)
def test_calculadora_validaciones(args):
    with pytest.raises(InvalidOrderData):
        CalculadoraTarifa.cotizar(*args)


def test_carga_desconocida_y_distancias():
    with pytest.raises(InvalidOrderData):
        CalculadoraTarifa.cotizar("Monterrey", "Saltillo", "rabon", 1, 1, "radiactiva")
    assert distancia_km("Saltillo", "Monterrey") == 86  # simétrica
    assert distancia_km("Reynosa", "Apodaca") >= 65  # par sin tabla: fórmula de respaldo
    assert distancia_km("Mérida", "Cancún") >= 65


# ---- API
def test_catalogo_y_estaticos(client):
    cat = client.get("/catalogo").json()
    assert "Monterrey" in cat["ciudades"] and {u["clave"] for u in cat["unidades"]} == {"ligera", "rabon", "caja", "trailer"}
    home = client.get("/")
    assert home.status_code == 200 and "Proyecto Equipo #2, Grupo 003, FIME UANL." in home.text
    assert client.get("/js/main.js").status_code == 200
    assert client.get("/docs").status_code == 200  # Swagger sigue activo


def test_cotizar_api_con_credito(client):
    client.post("/clientes", json={"id": "OK", "razon_social": "Al corriente", "es_corporativo": True, "dias_morosidad": 10})
    client.post("/clientes", json={"id": "MORA", "razon_social": "Moroso", "es_corporativo": True, "dias_morosidad": 45})
    ok = client.post("/cotizaciones", json={**COT, "cliente_id": "OK"}).json()
    assert ok["total"] == "2482.40" and ok["iva"] == "342.40" and ok["credito"] == {"evaluado": True, "apto": True, "mensaje": "Crédito vigente."}
    mora = client.post("/cotizaciones", json={**COT, "cliente_id": "MORA"}).json()
    assert mora["credito"]["apto"] is False and "45 días" in mora["credito"]["mensaje"]
    assert client.post("/cotizaciones", json=COT).json()["credito"]["evaluado"] is False


def test_cotizar_api_clientes_especiales_y_errores(client):
    client.post("/clientes", json={"id": "OFF", "razon_social": "Inactivo", "activo": False})
    client.post("/clientes", json={"id": "OCA", "razon_social": "Ocasional"})
    assert "inactiva" in client.post("/cotizaciones", json={**COT, "cliente_id": "OFF"}).json()["credito"]["mensaje"]
    assert "sin línea" in client.post("/cotizaciones", json={**COT, "cliente_id": "OCA"}).json()["credito"]["mensaje"]
    assert client.post("/cotizaciones", json={**COT, "cliente_id": "NOPE"}).status_code == 404
    assert client.post("/cotizaciones", json={**COT, "destino": "Monterrey"}).status_code == 422
    assert client.post("/cotizaciones", json={**COT, "peso_kg": 0}).status_code == 422


def test_confirmar_con_credito_bloqueado_409_y_orden_queda_registrada(client):
    client.post("/clientes", json={"id": "MORA", "razon_social": "Moroso", "es_corporativo": True, "dias_morosidad": 45})
    folio = client.post("/orders", json={"cliente_id": "MORA", "origen": "A", "destino": "B", "distancia_km": 5, "subtotal": "10", "total": "11"}).json()["numero_orden"]
    res = client.post(f"/orders/{folio}/confirmar")
    assert res.status_code == 409 and "pagos vencidos" in res.json()["mensaje"]
    assert client.get(f"/orders/{folio}").json()["estado"] == "Pendiente de confirmación"


def _flujo_completo(client):
    client.post("/clientes", json={"id": "C1", "razon_social": "Uno SA", "es_preferente": True})
    folio = client.post("/orders", json={"cliente_id": "C1", "origen": "Monterrey", "destino": "Saltillo", "distancia_km": 86, "subtotal": "2140", "total": "2482.40"}).json()["numero_orden"]
    client.post(f"/orders/{folio}/confirmar")
    client.post(f"/orders/{folio}/asignar-recursos", json={"vehiculo_id": "V-1", "placas": "AAA-111", "tipo_unidad": "Rabón", "operador_id": "OP-1", "nombre_operador": "Juan"})
    return folio


def test_eventos_persistidos_con_detalle_y_orden(client):
    folio = _flujo_completo(client)
    client.post(f"/orders/{folio}/validar-recoleccion", json={"peso_cotizado": 100, "peso_real": 130})
    ev = client.get(f"/orders/{folio}/eventos").json()
    assert [e["evento"] for e in ev] == ["OrdenRegistrada", "OrdenConfirmada", "UnidadYOperadorAsignados", "DiscrepanciaDetectada"]
    assert "AAA-111" in ev[2]["detalle"] and "variación 30.0%" in ev[3]["detalle"]
    assert client.get("/orders/NADA/eventos").status_code == 404


def test_listados_flota_y_kpis(client):
    assert client.get("/kpis").json() == {
        "total_ordenes": 0, "por_estado": {}, "discrepancias_peso": 0, "tasa_discrepancia_pct": 0.0,
        "entregas_completadas": 0, "ciclo_promedio_horas": None, "monto_confirmado_mxn": "0",
    }
    folio = _flujo_completo(client)
    assert client.get("/clientes").json()[0]["id"] == "C1"
    assert client.get("/orders").json()[0]["vehiculo"] == "AAA-111"
    assert client.get("/flota").json()["vehiculos"][0]["estado"] == "En servicio"

    client.post(f"/orders/{folio}/validar-recoleccion", json={"peso_cotizado": 100, "peso_real": 130})
    assert client.get("/flota").json()["vehiculos"][0]["estado"] == "En revisión"

    f2 = client.post("/orders", json={"cliente_id": "C1", "origen": "A", "destino": "B", "distancia_km": 5, "subtotal": "10", "total": "11.60"}).json()["numero_orden"]
    client.post(f"/orders/{f2}/confirmar")
    client.post(f"/orders/{f2}/asignar-recursos", json={"vehiculo_id": "V-1", "placas": "AAA-111", "tipo_unidad": "Rabón", "operador_id": "OP-1", "nombre_operador": "Juan"})
    client.post(f"/orders/{f2}/validar-recoleccion", json={"peso_cotizado": 100, "peso_real": 100})
    client.post(f"/orders/{f2}/entregar", json={"firma_digital": "f", "ine": "i"})
    k = client.get("/kpis").json()
    assert k["total_ordenes"] == 2 and k["discrepancias_peso"] == 1 and k["tasa_discrepancia_pct"] == 50.0
    assert k["entregas_completadas"] == 1 and k["ciclo_promedio_horas"] is not None
    assert k["por_estado"] == {"EN_REVISION_POR_VENTAS": 1, "ENTREGADO_CON_POD": 1}
    assert Decimal(k["monto_confirmado_mxn"]) == Decimal("2494.00")
    # V-1 sigue retenido por la primera orden (en revisión); la segunda, ya entregada, no lo ocupa
    assert client.get("/flota").json()["vehiculos"][0]["estado"] == "En revisión"


# ---- seed
def test_seed_demo_es_idempotente(uow_factory, service):
    sembrar_demo(uow_factory)
    sembrar_demo(uow_factory)
    assert len(service.listar_clientes()) == 4 and len(service.flota()["vehiculos"]) == 3
    moroso = next(c for c in service.listar_clientes() if c["id"] == "CLI-002")
    assert moroso["dias_morosidad"] == 45
