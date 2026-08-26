from __future__ import annotations

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider


def get_session(host: str = "127.0.0.1", port: int = 9042):
    """
    Cria uma sessão de conexão com o Cassandra.

    - host/port: onde o Cassandra está exposto (Docker geralmente mapeia 9042).
    - Se o seu Cassandra estiver com usuário/senha, habilite o auth abaixo.
    """
    # Se você tiver autenticação, use algo assim:
    # auth_provider = PlainTextAuthProvider(username="cassandra", password="cassandra")
    # cluster = Cluster([host], port=port, auth_provider=auth_provider)

    cluster = Cluster([host], port=port)
    session = cluster.connect()
    return cluster, session