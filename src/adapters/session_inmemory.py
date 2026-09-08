from __future__ import annotations
import datetime as dt
from typing import Optional
from core.ports import Session, SessionStore
from core.util import utcnow, new_id

class InMemorySessionStore(SessionStore):
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create_session(self, user_id: str) -> Session:
        session_id = new_id("sess")
        sess = Session(session_id=session_id, user_id=user_id, created_at=utcnow())
        self._sessions[session_id] = sess
        return sess

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
