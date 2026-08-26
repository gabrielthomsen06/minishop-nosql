from __future__ import annotations

from typing import Optional, List, Dict, Any
from pymongo import MongoClient, ASCENDING, DESCENDING

from core.ports import Event, EventStore

from datetime import timedelta
from core.util import utcnow


def get_db():
    client = MongoClient(
        "mongodb+srv://root:root@cluster0.jtw3dfe.mongodb.net/"
    )
    db = client["minishop"]

    db.events.create_index([("session_id", ASCENDING), ("ts", DESCENDING)])
    db.events.create_index([("ts", DESCENDING)])

    return db


class MongoEventStore(EventStore):
    def __init__(self, retention_days: int = 7):
        self._db = get_db()
        self._db.command("ping")
        self._retention_days = int(retention_days)

    def append(self, event: Event) -> None:
        expire_at = event.ts + timedelta(days=self._retention_days)

        self._db.events.insert_one({
             "ts": event.ts,
             "expire_at": expire_at,
              "event_type": event.event_type,
              "user_id": event.user_id,
              "session_id": event.session_id,
              "payload": dict(event.payload),
         })

    def tail(self, n: int, session_id: Optional[str] = None) -> List[Event]:
        q: Dict[str, Any] = {}
        if session_id:
            q["session_id"] = session_id

        docs = list(
            self._db.events
                .find(q)
                .sort("ts", DESCENDING)
                .limit(int(n))
        )

        docs.reverse()

        return [
            Event(
                ts=d["ts"],
                event_type=d["event_type"],
                user_id=d.get("user_id"),
                session_id=d.get("session_id"),
                payload=d.get("payload", {}),
            )
            for d in docs
        ]

    def delete_session(self, session_id: str) -> None:
    # Agora: remove apenas eventos EXPIRADOS daquela sessão
        now = utcnow()
        now2 = now - timedelta(days=self._retention_days)
        self._db.events.delete_many({
             "session_id": session_id,
                "expire_at": {"$lte": now2}
            })