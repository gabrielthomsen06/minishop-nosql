from __future__ import annotations

from typing import Optional, List, Dict, Any
from pymongo import MongoClient, ASCENDING, DESCENDING

from core.ports import Event, EventStore


def get_db():
    client = MongoClient(
        "mongodb+srv://root:root@cluster0.lgjfzis.mongodb.net/"
    )
    db = client["minishop"]

    db.events.create_index([("session_id", ASCENDING), ("ts", DESCENDING)])
    db.events.create_index([("ts", DESCENDING)])

    return db


class MongoEventStore(EventStore):
    def __init__(self):
        self._db = get_db()
        self._db.command("ping")

    def append(self, event: Event) -> None:
        self._db.events.insert_one({
            "ts": event.ts,
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
        self._db.events.delete_many({"session_id": session_id})