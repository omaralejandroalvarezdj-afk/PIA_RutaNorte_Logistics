import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_service
from src.api.main import app
from src.application.services import OrdenApplicationService
from src.infrastructure.database import build_engine, build_session_factory, init_db
from src.infrastructure.event_bus import InMemoryEventBus
from src.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def session_factory():
    """BD SQLite en memoria, aislada por prueba."""
    engine = build_engine("sqlite:///:memory:")
    init_db(engine)
    yield build_session_factory(engine)
    engine.dispose()


@pytest.fixture
def event_bus():
    return InMemoryEventBus()


@pytest.fixture
def uow_factory(session_factory, event_bus):
    return lambda: SqlAlchemyUnitOfWork(session_factory, event_bus.publish)


@pytest.fixture
def service(uow_factory):
    return OrdenApplicationService(uow_factory)


@pytest.fixture
def client(service):
    app.dependency_overrides[get_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()
