from __future__ import annotations
from typing import Optional
from core.ports import SessionStore, Session

class SessionService:
    def __init__(self, store: SessionStore):
        self.store = store

    def login(self, user_id: str) -> Session:
        return self.store.create_session(user_id=user_id)

    def current(self, session_id: Optional[str]) -> Optional[Session]:
        if not session_id:
            return None
        return self.store.get_session(session_id)

    def logout(self, session_id: Optional[str]) -> None:
        if session_id:
            self.store.delete_session(session_id)
