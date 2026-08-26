"""
Diagnostico isolado do Cassandra.
Imprime cada etapa para identificar exatamente onde o processo morre.

Uso:
    python diag_cassandra.py
    echo $LASTEXITCODE
"""

import sys

print("1. iniciando", flush=True)

try:
    from cassandra.cluster import Cluster
    print("2. import ok", flush=True)
except BaseException as e:
    print(f"   FALHOU no import: {type(e).__name__}: {e}", flush=True)
    sys.exit(1)

try:
    cluster = Cluster(["127.0.0.1"], port=9042, connect_timeout=10)
    print("3. objeto Cluster criado", flush=True)
except BaseException as e:
    print(f"   FALHOU ao criar Cluster: {type(e).__name__}: {e}", flush=True)
    sys.exit(1)

try:
    print("4. chamando connect()...", flush=True)
    session = cluster.connect()
    print("5. connect() ok", flush=True)
except BaseException as e:
    print(f"   FALHOU no connect(): {type(e).__name__}: {e}", flush=True)
    sys.exit(1)

try:
    row = session.execute("SELECT release_version FROM system.local").one()
    print(f"6. query ok, versao do Cassandra: {row.release_version}", flush=True)
    cluster.shutdown()
    print("7. tudo certo", flush=True)
except BaseException as e:
    print(f"   FALHOU na query: {type(e).__name__}: {e}", flush=True)
    sys.exit(1)
