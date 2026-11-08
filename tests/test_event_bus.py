from src.domain.models import DomainEvent
from src.infrastructure.event_bus import InMemoryEventBus


def test_event_bus_notifica_suscriptores_y_guarda_historial():
    bus, recibidos = InMemoryEventBus(), []
    bus.subscribe(recibidos.append)
    evento = DomainEvent("OrdenConfirmada", "ORD-1")
    bus.publish(evento)
    assert recibidos == [evento] and bus.history == [evento]
