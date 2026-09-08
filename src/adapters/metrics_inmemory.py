from __future__ import annotations
from core.ports import MetricPoint, MetricsStore

class InMemoryMetricsStore(MetricsStore):
    def __init__(self):
        self._points: list[MetricPoint] = []
        self._counters: dict[str, int] = {}

    def write(self, point: MetricPoint) -> None:
        self._points.append(point)
        if point.metric == "counter":
            name = point.tags.get("name", "unknown")
            self._counters[name] = self._counters.get(name, 0) + int(point.value)

    def latest(self, n: int):
        return self._points[-n:]

    def snapshot_counters(self):
        return dict(self._counters)
