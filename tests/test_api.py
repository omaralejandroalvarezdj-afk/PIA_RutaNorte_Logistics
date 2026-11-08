import pytest

CLIENTE = {"id": "CLI-REST", "razon_social": "Empresa de Pruebas SA", "es_preferente": True}
ORDEN = {
    "cliente_id": "CLI-REST",
    "origen": "Monterrey",
    "destino": "CDMX",
    "distancia_km": 900.0,
    "subtotal": "5000.00",
    "total": "5800.00",
}
FLOTA = {"vehiculo_id": "V-01", "placas": "ABC-123", "tipo_unidad": "Caja Seca", "operador_id": "OP-01", "nombre_operador": "Juan Pérez"}


@pytest.fixture
def folio(client):
    assert client.post("/clientes", json=CLIENTE).status_code == 201
    res = client.post("/orders", json=ORDEN)
    assert res.status_code == 201
    return res.json()["folio"]


# --- POST /orders ---
def test_post_orders_crea_orden_en_estado_inicial(client):
    client.post("/clientes", json=CLIENTE)
    res = client.post("/orders", json={**ORDEN, "orden_id": "ORD-FIJA-1"})
    assert res.status_code == 201
    body = res.json()
    assert body["folio"] == "ORD-FIJA-1" and body["estatus_actual"] == "REGISTRADO"
    assert body["beneficio_referencia"] is True

    detalle = client.get("/orders/ORD-FIJA-1").json()
    assert detalle["cliente"]["razon_social"] == "Empresa de Pruebas SA"
    assert detalle["cotizacion"]["total"] == "5800.00"


def test_post_orders_genera_folio_si_no_se_envia(client, folio):
    assert folio.startswith("ORD-")


def test_post_orders_cliente_inexistente_404(client):
    assert client.post("/orders", json=ORDEN).status_code == 404


def test_post_orders_folio_duplicado_409(client, folio):
    assert client.post("/orders", json={**ORDEN, "orden_id": folio}).status_code == 409


@pytest.mark.parametrize(
    "cambio",
    [{"distancia_km": 0}, {"total": "-1"}, {"origen": ""}, {"porcentaje_descuento": 150}, {"total": "abc"}],
)
def test_post_orders_validacion_422(client, cambio):
    client.post("/clientes", json=CLIENTE)
    assert client.post("/orders", json={**ORDEN, **cambio}).status_code == 422


def test_post_orders_sin_campos_requeridos_422(client):
    assert client.post("/orders", json={}).status_code == 422


def test_post_clientes_duplicado_409(client):
    client.post("/clientes", json=CLIENTE)
    assert client.post("/clientes", json=CLIENTE).status_code == 409


# --- Flujo completo ---
def test_flujo_completo_endpoints(client, folio):
    res = client.post(f"/orders/{folio}/confirmar")
    assert res.status_code == 200 and res.json()["estatus_actual"] == "CONFIRMADA"
    assert "¡Cotización confirmada exitosamente!" in res.json()["mensaje"]

    res = client.post(f"/orders/{folio}/asignar-recursos", json=FLOTA)
    assert res.status_code == 200 and res.json()["estatus_actual"] == "UNIDAD_ASIGNADA"

    res = client.post(f"/orders/{folio}/validar-recoleccion", json={"peso_cotizado": 100.0, "peso_real": 105.0})
    assert res.status_code == 200 and res.json()["estatus_actual"] == "RECOLECTADO"

    res = client.post(
        f"/orders/{folio}/entregar",
        json={"firma_digital": "FirmaValidaJuanPerez", "ine": "1234567890", "fotografias": ["evidencia.jpg"]},
    )
    assert res.status_code == 200 and res.json()["estatus_actual"] == "ENTREGADO_CON_POD"

    final = client.get(f"/orders/{folio}").json()
    assert final["pod_registrada"] is True and final["vehiculo"]["placas"] == "ABC-123"


# --- Códigos de error ---
def test_orden_no_encontrada_404(client):
    res = client.post("/orders/FOLIO-INEXISTENTE/confirmar")
    assert res.status_code == 404
    assert "no encontramos ninguna orden" in res.json()["detail"]
    assert client.get("/orders/FOLIO-INEXISTENTE").status_code == 404


def test_discrepancia_peso_409(client, folio):
    client.post(f"/orders/{folio}/confirmar")
    client.post(f"/orders/{folio}/asignar-recursos", json=FLOTA)
    res = client.post(f"/orders/{folio}/validar-recoleccion", json={"peso_cotizado": 100.0, "peso_real": 130.0})
    assert res.status_code == 409
    assert "sobrepasando la tolerancia permitida del 15%" in res.json()["detail"]
    assert "departamento de Ventas" in res.json()["detail"]
    assert client.get(f"/orders/{folio}").json()["estatus_actual"] == "EN_REVISION_POR_VENTAS"


def test_transicion_invalida_409(client, folio):
    assert client.post(f"/orders/{folio}/entregar", json={"firma_digital": "f", "ine": "i"}).status_code == 409
    client.post(f"/orders/{folio}/confirmar")
    assert client.post(f"/orders/{folio}/confirmar").status_code == 409
    assert client.post(f"/orders/{folio}/asignar-recursos", json={**FLOTA}).status_code == 200
    assert client.post(f"/orders/{folio}/asignar-recursos", json={**FLOTA}).status_code == 409


def test_datos_de_negocio_invalidos_422(client, folio):
    client.post(f"/orders/{folio}/confirmar")
    client.post(f"/orders/{folio}/asignar-recursos", json=FLOTA)
    client.post(f"/orders/{folio}/validar-recoleccion", json={"peso_cotizado": 100.0, "peso_real": 100.0})
    res = client.post(f"/orders/{folio}/entregar", json={"firma_digital": "  ", "ine": "123"})
    assert res.status_code == 422  # POD incompleta


def test_peso_cero_422_en_validacion(client, folio):
    res = client.post(f"/orders/{folio}/validar-recoleccion", json={"peso_cotizado": 0, "peso_real": 10})
    assert res.status_code == 422


def test_cliente_inactivo_no_confirma_422(client):
    client.post("/clientes", json={"id": "CLI-OFF", "razon_social": "Inactivo SA", "activo": False})
    folio = client.post("/orders", json={**ORDEN, "cliente_id": "CLI-OFF"}).json()["folio"]
    assert client.post(f"/orders/{folio}/confirmar").status_code == 422


def test_cancelar_orden(client, folio):
    res = client.post(f"/orders/{folio}/cancelar", json={"motivo": "Cliente desistió"})
    assert res.status_code == 200 and res.json()["estatus_actual"] == "CANCELADA"
    assert client.post(f"/orders/{folio}/cancelar", json={"motivo": "otra vez"}).status_code == 409


def test_health_y_openapi(client):
    assert client.get("/health").json() == {"status": "ok"}
    paths = client.get("/openapi.json").json()["paths"]
    assert "post" in paths["/orders"] and "post" in paths["/clientes"]
