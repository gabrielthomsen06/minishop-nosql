from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

from core.ports import MetricPoint, MetricsStore


class CassandraMetricsStore(MetricsStore):
    """
    Implementação de MetricsStore usando Cassandra.

    Tabelas (mesmo modelo do laboratório 7.1):
      - metric_points_by_day: séries temporais por (metric, day), ordenadas por ts DESC
      - counters_snapshot: snapshot simples dos contadores (name -> value)

    Observação didática:
      - O particionamento da tabela principal é (metric, day).
        Isso significa que para consultar "últimas métricas" de tudo, precisamos
        buscar por métrica e depois combinar (limitado, mas ótimo para explicar modelagem Cassandra).
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9042,
        keyspace: str = "minishop_metrics",
        ensure_schema: bool = True,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self._host = host
        self._port = port
        self._keyspace = keyspace

        # Conexão (com ou sem auth)
        if username and password:
            auth = PlainTextAuthProvider(username=username, password=password)
            self._cluster = Cluster([host], port=port, auth_provider=auth)
        else:
            self._cluster = Cluster([host], port=port)

        self._session = self._cluster.connect()

        if ensure_schema:
            self._ensure_schema()

        # Mantemos um cache simples em memória para facilitar o lab:
        # - evita ter que fazer read-before-write em Cassandra a cada incremento
        # - quando quiser, você pode explicar que em produção existem abordagens melhores
        self._counter_cache: Dict[str, int] = {}

    # -------------------------
    # Schema
    # -------------------------

    def _ensure_schema(self) -> None:
        # 1) Keyspace
        self._session.execute(
            f"""
            CREATE KEYSPACE IF NOT EXISTS {self._keyspace}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}};
            """
        )
        self._session.execute(f"USE {self._keyspace};")

        # 2) Tabela principal: séries temporais por dia
        self._session.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_points_by_day (
              metric text,
              day date,
              ts timestamp,
              value double,
              tags map<text, text>,
              PRIMARY KEY ((metric, day), ts)
            ) WITH CLUSTERING ORDER BY (ts DESC);
            """
        )

        # 3) Snapshot de counters (tabela “de leitura rápida”)
        self._session.execute(
            """
            CREATE TABLE IF NOT EXISTS counters_snapshot (
              name text PRIMARY KEY,
              value bigint,
              updated_at timestamp
            );
            """
        )

    # -------------------------
    # Helpers
    # -------------------------

    def _day_from_ts(self, ts: dt.datetime) -> dt.date:
        # Cassandra date é YYYY-MM-DD (sem horário)
        if ts.tzinfo is not None:
            ts = ts.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return ts.date()

    # -------------------------
    # Interface MetricsStore
    # -------------------------

    def write(self, point: MetricPoint) -> None:
        """
        Escreve um ponto na tabela de série temporal.
        Se for counter, também atualiza o snapshot.
        """
        day = self._day_from_ts(point.ts)

        self._session.execute(
            f"""
            INSERT INTO {self._keyspace}.metric_points_by_day (metric, day, ts, value, tags)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (point.metric, day, point.ts, float(point.value), dict(point.tags)),
        )

        # Se for contador, mantemos também o snapshot (name -> value atual)
        if point.metric == "counter":
            name = point.tags.get("name", "unknown")
            amount = int(point.value)

            current = self._counter_cache.get(name)

            # Se o cache ainda não conhece esse contador, tenta ler 1 vez do Cassandra
            if current is None:
                rows = self._session.execute(
                    f"SELECT value FROM {self._keyspace}.counters_snapshot WHERE name=%s;",
                    (name,),
                )
                row = rows.one()
                current = int(row.value) if row and row.value is not None else 0

            new_value = current + amount
            self._counter_cache[name] = new_value

            self._session.execute(
                f"""
                INSERT INTO {self._keyspace}.counters_snapshot (name, value, updated_at)
                VALUES (%s, %s, toTimestamp(now()));
                """,
                (name, new_value),
            )

    def latest(self, n: int) -> List[MetricPoint]:
        """
        Retorna os últimos N pontos.

        Limitação didática (importante para explicar Cassandra):
        - Como o particionamento é por (metric, day), não existe um 'ORDER BY ts global'.
        - Então aqui fazemos uma estratégia simples:
            1) busca N de 'counter' de hoje
            2) busca N de 'latency_ms' de hoje
            3) combina e ordena por ts desc, e retorna N
        """
        today = dt.datetime.utcnow().date()

        def fetch(metric: str) -> List[MetricPoint]:
            rows = self._session.execute(
                f"""
                SELECT metric, day, ts, value, tags
                FROM {self._keyspace}.metric_points_by_day
                WHERE metric=%s AND day=%s
                LIMIT %s;
                """,
                (metric, today, int(n)),
            )
            out: List[MetricPoint] = []
            for r in rows:
                out.append(
                    MetricPoint(
                        ts=r.ts,
                        metric=r.metric,
                        value=float(r.value),
                        tags=dict(r.tags or {}),
                    )
                )
            return out

        candidates = fetch("counter") + fetch("latency_ms")
        candidates.sort(key=lambda p: p.ts, reverse=True)
        return candidates[: int(n)]

        def snapshot_counters(self) -> Dict[str, int]:
            """
            Lê a tabela counters_snapshot inteira e devolve um dict {name: value}.
            """
            rows = self._session.execute(f"SELECT name, value FROM {self._keyspace}.counters_snapshot;")
            result: Dict[str, int] = {}
            for r in rows:
                result[str(r.name)] = int(r.value) if r.value is not None else 0

            # mantém cache alinhado também (bom para o lab)
            self._counter_cache.update(result)
            return result

        # -------------------------
        # Fechamento (boa prática)
        # -------------------------

        def close(self) -> None:
            self._session.shutdown()
            self._cluster.shutdown()
