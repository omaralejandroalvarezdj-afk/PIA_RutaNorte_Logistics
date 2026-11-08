"""Contrato público sencillo de Swagger compatible con la nueva interfaz web."""


def test_pagina_y_documentacion(client):
    assert client.get('/').status_code == 200
    assert client.get('/js/api.js').status_code == 200
    assert client.get('/js/views/envio.js').status_code == 200
    assert client.get('/docs').status_code == 200


def test_orden_sencilla_y_listados_compatibles(client):
    nuevo = client.post('/clientes', json={'id': 'CLUI', 'razon_social': 'Cliente Interfaz'})
    assert nuevo.status_code == 201
    assert nuevo.json() == {'mensaje': 'El cliente fue registrado correctamente.', 'cliente': 'Cliente Interfaz'}
    orden = client.post('/orders', json={'cliente_id': 'CLUI', 'origen': 'Monterrey', 'destino': 'Saltillo', 'distancia_km': 86, 'subtotal': '100', 'total': '116', 'orden_id': 'ORD-UI-001'})
    assert orden.status_code == 201
    assert orden.json() == {'mensaje': 'Tu orden fue creada correctamente.', 'numero_orden': 'ORD-UI-001', 'estado': 'Pendiente de confirmación'}
    assert client.get('/orders/ORD-UI-001').json()['estado'] == 'Pendiente de confirmación'
    assert client.get('/orders').json()[0]['folio'] == 'ORD-UI-001'
    assert client.get('/orders/ORD-UI-001/eventos').status_code == 200
    assert client.get('/clientes').json()[0]['id'] == 'CLUI'


def test_cotizacion_y_catalogos_para_web(client):
    assert client.get('/catalogo').status_code == 200
    assert client.get('/flota').status_code == 200
    assert client.get('/kpis').status_code == 200
    res = client.post('/cotizaciones', json={'origen': 'Monterrey', 'destino': 'Saltillo', 'unidad': 'rabon', 'peso_kg': 1000, 'volumen_m3': 8})
    assert res.status_code == 200
    assert res.json()['total'] == '2482.40'


def test_errores_sencillos_para_web(client):
    response = client.get('/orders/NO-EXISTE')
    assert response.status_code == 404
    assert 'No encontramos' in response.json()['mensaje']
    response = client.post('/orders', json={})
    assert response.status_code == 422
    assert 'Revisa los datos ingresados' in response.json()['mensaje']
