from __future__ import annotations
from typing import Optional, List
from core.ports import Event, EventStore

class InMemoryEventStore(EventStore):
    def __init__(self):
        self._events: list[Event] = []

    def append(self, event: Event) -> None:
        self._events.append(event)

    def tail(self, n: int, session_id: Optional[str] = None) -> List[Event]:
        if session_id:
            filtered = [e for e in self._events if e.session_id == session_id]
            return filtered[-n:]
        return self._events[-n:]

    def delete_session(self, session_id: str) -> None:
        self._events = [e for e in self._events if e.session_id != session_id]