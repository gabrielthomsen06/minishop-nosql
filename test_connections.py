"""
Verificacao rapida: confirma se MongoDB, Redis e Cassandra estao
respondendo depois do `docker compose up -d`.

Uso:
    pip install -r requirements.txt
    python test_connections.py
"""

from pymongo import MongoClient
import redis
from cassandra.cluster import Cluster


def test_mongodb():
    try:
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        print("[OK] MongoDB respondendo em localhost:27017")
    except Exception as e:
        print(f"[FALHOU] MongoDB: {e}")


def test_redis():
    try:
        r = redis.Redis(host="localhost", port=6379, socket_connect_timeout=3)
        r.ping()
        print("[OK] Redis respondendo em localhost:6379")
    except Exception as e:
        print(f"[FALHOU] Redis: {e}")


def test_cassandra():
    try:
        cluster = Cluster(["127.0.0.1"], port=9042, connect_timeout=10)
        session = cluster.connect()
        session.execute("SELECT release_version FROM system.local")
        print("[OK] Cassandra respondendo em localhost:9042")
        cluster.shutdown()
    except Exception as e:
        print(f"[FALHOU] Cassandra: {e}")
        print("       (o Cassandra demora de 30 a 90s para subir, tente de novo)")


if __name__ == "__main__":
    test_mongodb()
    test_redis()
    test_cassandra()
