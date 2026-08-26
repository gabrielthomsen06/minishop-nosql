from __future__ import annotations
import datetime as dt
import time
import uuid

def utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)

def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"

class Timer:
    def __init__(self):
        self._start = 0.0
    def __enter__(self):
        self._start = time.perf_counter()
        return self
    def __exit__(self, exc_type, exc, tb):
        pass
    @property
    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0

def money(value: float) -> str:
    # formato simples (você pode trocar por locale depois)
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
