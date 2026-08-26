from __future__ import annotations
from typing import Dict, Any, Optional, List
from core.ports import EventStore, Event
from core.util import utcnow

class EventService:
    def __init__(self, store: EventStore):
        self.store = store

    def emit(self, event_type: str, user_id: str, session_id: str, payload: Dict[str, Any]) -> None:
        self.store.append(Event(
            ts=utcnow(),
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            payload=payload
        ))

    def tail(self, n: int = 10) -> List[Event]:
        return self.store.tail(n)
