from __future__ import annotations
from core.ports import Event, EventStore

class InMemoryEventStore(EventStore):
    def __init__(self):
        self._events: list[Event] = []

    def append(self, event: Event) -> None:
        self._events.append(event)

    def tail(self, n: int):
        return self._events[-n:]
