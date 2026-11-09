from src.infrastructure.database import DEFAULT_DATABASE_URL, build_engine, get_database_url


def test_lee_database_url_del_entorno(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///otra.db")
    assert get_database_url() == "sqlite:///otra.db"


def test_fallback_a_sqlite_local(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert get_database_url() == DEFAULT_DATABASE_URL == "sqlite:///rutanorte.db"
    monkeypatch.setenv("DATABASE_URL", "   ")
    assert get_database_url() == DEFAULT_DATABASE_URL


def test_normaliza_esquema_postgres(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host/db")
    assert get_database_url() == "postgresql+psycopg2://u:p@host/db"
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")
    assert get_database_url() == "postgresql+psycopg2://u:p@host/db"


def test_build_engine_usa_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    assert build_engine().url.database == ":memory:"


def test_build_engine_no_sqlite_usa_pool_pre_ping(monkeypatch):
    capturado = {}

    def falso_create_engine(url, **kwargs):
        capturado.update(url=url, **kwargs)
        return "engine"

    monkeypatch.setattr("src.infrastructure.database.create_engine", falso_create_engine)
    assert build_engine("postgresql+psycopg2://u:p@db:5432/x") == "engine"
    assert capturado == {"url": "postgresql+psycopg2://u:p@db:5432/x", "pool_pre_ping": True}
