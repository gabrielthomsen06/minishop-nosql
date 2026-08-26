from __future__ import annotations
from typing import Dict
from core.ports import MetricsStore, MetricPoint
from core.util import utcnow

class MetricsService:
    def __init__(self, store: MetricsStore):
        self.store = store

    def latency(self, op: str, ms: float) -> None:
        self.store.write(MetricPoint(
            ts=utcnow(),
            metric="latency_ms",
            value=float(ms),
            tags={"op": op}
        ))

    def inc(self, counter_name: str, amount: int = 1) -> None:
        # Armazenamos como métrica (counter) + também num snapshot simples in-memory
        self.store.write(MetricPoint(
            ts=utcnow(),
            metric="counter",
            value=float(amount),
            tags={"name": counter_name}
        ))

    def latest(self, n: int = 10):
        return self.store.latest(n)

    def counters(self) -> Dict[str, int]:
        return self.store.snapshot_counters()
