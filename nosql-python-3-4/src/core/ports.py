from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional, List, Dict, Any
import datetime as dt

# -------------------------
# Domain models
# -------------------------
@dataclass(frozen=True)
class Session:
    session_id: str
    user_id: str
    created_at: dt.datetime

@dataclass(frozen=True)
class Event:
    ts: dt.datetime
    event_type: str
    user_id: str
    session_id: str
    payload: Dict[str, Any]

@dataclass(frozen=True)
class MetricPoint:
    ts: dt.datetime
    metric: str          # e.g. latency_ms, counter
    value: float
    tags: Dict[str, str] # e.g. {"op":"checkout"}

@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    category: str
    price: float

@dataclass
class CartItem:
    sku: str
    name: str
    unit_price: float
    qty: int

# -------------------------
# Ports (interfaces)
# -------------------------
class SessionStore(Protocol):
    def create_session(self, user_id: str) -> Session: ...
    def get_session(self, session_id: str) -> Optional[Session]: ...
    def delete_session(self, session_id: str) -> None: ...

class EventStore(Protocol):
    def append(self, event: Event) -> None: ...
    def tail(self, n: int) -> List[Event]: ...

class MetricsStore(Protocol):
    def write(self, point: MetricPoint) -> None: ...
    def latest(self, n: int) -> List[MetricPoint]: ...
    def snapshot_counters(self) -> Dict[str, int]: ...
