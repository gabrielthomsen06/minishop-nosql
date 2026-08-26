from __future__ import annotations

from cassandra_client import get_session
import cql_steps as steps


def run_exec(session, label: str, cql: str) -> None:
    """
    Executa um comando CQL que não precisa imprimir linhas (DDL/DML).
    """
    print(f"\n=== {label} ===")
    print(cql.strip())
    session.execute(cql)
    print("OK")


def run_select(session, label: str, cql: str) -> None:
    """
    Executa SELECT e imprime as linhas no terminal.
    """
    print(f"\n=== {label} ===")
    print(cql.strip())
    rows = session.execute(cql)

    count = 0
    for row in rows:
        # row é um objeto que permite acesso por atributo
        print(dict(row._asdict()))
        count += 1

    if count == 0:
        print("(sem resultados)")
    else:
        print(f"Total de linhas: {count}")


def main() -> None:
    cluster, session = get_session(host="127.0.0.1", port=9042)

    try:
        # 1) reset do keyspace (reprodutibilidade)
        run_exec(session, "DROP KEYSPACE (reset)", steps.CQL_DROP_KEYSPACE)
        run_exec(session, "CREATE KEYSPACE", steps.CQL_CREATE_KEYSPACE)
        run_exec(session, "USE KEYSPACE", steps.CQL_USE_KEYSPACE)

        # 2) tabela principal
        run_exec(session, "CREATE TABLE metric_points_by_day", steps.CQL_CREATE_TABLE_METRIC_POINTS)

        # 3) inserts
        run_exec(session, "INSERT counter logins", steps.CQL_INSERT_1)
        run_exec(session, "INSERT latency_ms view_catalog", steps.CQL_INSERT_2)
        run_exec(session, "INSERT counter catalog_views", steps.CQL_INSERT_3)

        # 4) select com print no prompt
        run_select(session, "SELECT counters (imprimir no terminal)", steps.CQL_SELECT_COUNTERS)

        # 5) tabela snapshot de counters
        run_exec(session, "CREATE TABLE counters_snapshot", steps.CQL_CREATE_TABLE_COUNTERS_SNAPSHOT)
        run_exec(session, "INSERT snapshot logins", steps.CQL_INSERT_SNAPSHOT_1)
        run_exec(session, "INSERT snapshot catalog_views", steps.CQL_INSERT_SNAPSHOT_2)

        # 6) select snapshot
        run_select(session, "SELECT * FROM counters_snapshot (imprimir no terminal)", steps.CQL_SELECT_SNAPSHOT)

        print("\nFim: conexão + execução CQL + SELECT impresso no prompt.")

    finally:
        session.shutdown()
        cluster.shutdown()


if __name__ == "__main__":
    main()