from core.app import MiniShopApp

from adapters.session_inmemory import InMemorySessionStore
from adapters.session_redis import RedisSessionStore

from adapters.event_inmemory import InMemoryEventStore
from adapters.metrics_inmemory import InMemoryMetricsStore

USE_REDIS_FOR_SESSION = True  # <-- chave didática

def build_session_store():
    if USE_REDIS_FOR_SESSION:
        return RedisSessionStore(
            host="localhost",
            port=6379,
            session_ttl_seconds=30 * 60
        )
    else:
        return InMemorySessionStore()


def main():
    app = MiniShopApp(
        session_store=build_session_store(),
        event_store=InMemoryEventStore(),
        metrics_store=InMemoryMetricsStore(),
    )
    app.run_cli()

if __name__ == "__main__":
    main()
