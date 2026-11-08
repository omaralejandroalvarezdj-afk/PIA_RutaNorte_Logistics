"""Verifica que la API sin overrides lee DATABASE_URL y persiste en esa BD."""
from fastapi.testclient import TestClient

from src.api import dependencies
from src.api.main import app


def test_api_usa_database_url_del_entorno(monkeypatch, tmp_path):
    db = tmp_path / "entorno.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    dependencies._build_service.cache_clear()
    try:
        c = TestClient(app)
        assert c.post("/clientes", json={"id": "C1", "razon_social": "Env SA"}).status_code == 201
        res = c.post("/orders", json={"cliente_id": "C1", "origen": "A", "destino": "B",
                                      "distancia_km": 5, "subtotal": "10", "total": "10"})
        assert res.status_code == 201
        assert db.exists()  # el archivo configurado por variable de entorno fue creado
        assert [e.name for e in dependencies.get_event_bus().history] == ["OrdenRegistrada"]
    finally:
        dependencies._build_service.cache_clear()
