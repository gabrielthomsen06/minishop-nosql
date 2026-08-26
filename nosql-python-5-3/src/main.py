from core.app import MiniShopApp

from adapters.session_inmemory import InMemorySessionStore
from adapters.session_redis import RedisSessionStore

from adapters.event_inmemory import InMemoryEventStore
from adapters.event_mongodb import MongoEventStore

from adapters.metrics_inmemory import InMemoryMetricsStore

from adapters.cart_inmemory import InMemoryCartStore
from adapters.cart_redis import RedisCartStore

USE_REDIS_FOR_SESSION = True  # chave didática
USE_MONGODB_FOR_EVENTS = True

def build_session_store():
    if USE_REDIS_FOR_SESSION:
        return RedisSessionStore(host="localhost", port=6379, session_ttl_seconds=30 * 60)
    return InMemorySessionStore()

def build_cart_store(session_store):
    if isinstance(session_store, RedisSessionStore):
        return RedisCartStore(
            redis_client=session_store.client,
            session_ttl_seconds=session_store.ttl_seconds
        )
    return InMemoryCartStore()

def build_event_store():
    if USE_MONGODB_FOR_EVENTS:
        return MongoEventStore()
    return InMemoryEventStore()

def main():
    session_store = build_session_store()
    cart_store = build_cart_store(session_store)

    app = MiniShopApp(
         session_store=session_store,
         event_store=build_event_store(),
         metrics_store=InMemoryMetricsStore(),
         cart_store=cart_store,
    )
    app.run_cli()

if __name__ == "__main__":
    main()
