"""Publicador de Domain Events en memoria (suficiente para el alcance del PIA)."""
from __future__ import annotations

from typing import Callable

from src.domain.models import DomainEvent


class InMemoryEventBus:
    def __init__(self) -> None:
        self.history: list[DomainEvent] = []
        self._subscribers: list[Callable[[DomainEvent], None]] = []

    def subscribe(self, handler: Callable[[DomainEvent], None]) -> None:
        self._subscribers.append(handler)

    def publish(self, event: DomainEvent) -> None:
        self.history.append(event)
        for handler in self._subscribers:
            handler(event)
