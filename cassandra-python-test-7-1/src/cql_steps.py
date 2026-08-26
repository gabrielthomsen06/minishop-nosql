from __future__ import annotations

KEYSPACE = "minishop_metrics"

CQL_DROP_KEYSPACE = f"DROP KEYSPACE IF EXISTS {KEYSPACE};"

# Simples e didático: replicação para ambiente local (1 nó).
CQL_CREATE_KEYSPACE = f"""
CREATE KEYSPACE IF NOT EXISTS {KEYSPACE}
WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}};
"""

CQL_USE_KEYSPACE = f"USE {KEYSPACE};"

CQL_CREATE_TABLE_METRIC_POINTS = """
CREATE TABLE IF NOT EXISTS metric_points_by_day (
  metric text,
  day date,
  ts timestamp,
  value double,
  tags map<text, text>,
  PRIMARY KEY ((metric, day), ts)
) WITH CLUSTERING ORDER BY (ts DESC);
"""

# Suas inserções (mantidas com a data 2026-02-02)
CQL_INSERT_1 = """
INSERT INTO metric_points_by_day (metric, day, ts, value, tags)
VALUES ('counter', '2026-02-02', toTimestamp(now()), 1, {'name':'logins'});
"""

CQL_INSERT_2 = """
INSERT INTO metric_points_by_day (metric, day, ts, value, tags)
VALUES ('latency_ms', '2026-02-02', toTimestamp(now()), 150.44, {'op':'view_catalog'});
"""

CQL_INSERT_3 = """
INSERT INTO metric_points_by_day (metric, day, ts, value, tags)
VALUES ('counter', '2026-02-02', toTimestamp(now()), 1, {'name':'catalog_views'});
"""

CQL_SELECT_COUNTERS = """
SELECT ts, metric, value, tags
FROM metric_points_by_day
WHERE metric = 'counter'
  AND day = '2026-02-02'
LIMIT 10;
"""

CQL_CREATE_TABLE_COUNTERS_SNAPSHOT = """
CREATE TABLE IF NOT EXISTS counters_snapshot (
  name text PRIMARY KEY,
  value bigint,
  updated_at timestamp
);
"""

CQL_INSERT_SNAPSHOT_1 = """
INSERT INTO counters_snapshot (name, value, updated_at)
VALUES ('logins', 1, toTimestamp(now()));
"""

CQL_INSERT_SNAPSHOT_2 = """
INSERT INTO counters_snapshot (name, value, updated_at)
VALUES ('catalog_views', 1, toTimestamp(now()));
"""

CQL_SELECT_SNAPSHOT = "SELECT * FROM counters_snapshot;"