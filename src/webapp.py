from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.util import Timer, money
from services.catalog_service import CatalogService
from services.cart_service import CartService
from services.session_service import SessionService
from services.event_service import EventService
from services.metrics_service import MetricsService

from adapters.session_redis import RedisSessionStore
from adapters.event_mongodb import MongoEventStore
from adapters.cart_redis import RedisCartStore
from adapters.metrics_cassandra import CassandraMetricsStore


def _retry(build, name: str, attempts: int = 20, delay_seconds: float = 3.0):
    """Os containers (Mongo/Redis/Cassandra) podem demorar para ficar prontos.
    Tenta várias vezes antes de desistir, para o backend não morrer no boot."""
    last_error: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            return build()
        except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha de conexão
            last_error = exc
            print(f"[startup] {name}: tentativa {attempt}/{attempts} falhou ({exc}). Retentando em {delay_seconds}s...")
            time.sleep(delay_seconds)
    raise RuntimeError(f"Não foi possível conectar em {name} após {attempts} tentativas") from last_error


session_store = _retry(
    lambda: RedisSessionStore(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        session_ttl_seconds=30 * 60,
    ),
    "Redis (sessão)",
)

cart_store = _retry(
    lambda: RedisCartStore(
        redis_client=session_store.client,
        session_ttl_seconds=session_store.ttl_seconds,
    ),
    "Redis (carrinho)",
)

event_store = _retry(lambda: MongoEventStore(retention_days=7), "MongoDB (eventos)")

metrics_store = _retry(
    lambda: CassandraMetricsStore(
        host=os.environ.get("CASSANDRA_HOST", "127.0.0.1"),
        port=int(os.environ.get("CASSANDRA_PORT", "9042")),
        keyspace="minishop_metrics",
        ensure_schema=True,
    ),
    "Cassandra (métricas)",
    attempts=40,
    delay_seconds=5.0,
)

catalog_svc = CatalogService()
session_svc = SessionService(session_store)
event_svc = EventService(event_store)
metrics_svc = MetricsService(metrics_store)


def cart_for(session_id: str) -> CartService:
    svc = CartService(cart_store)
    svc.bind_session(session_id)
    return svc


def require_session(x_session_id: Optional[str]):
    sess = session_svc.current(x_session_id)
    if not sess:
        raise HTTPException(status_code=401, detail="Sessão inválida. Faça login novamente.")
    return sess


app = FastAPI(title="MiniShop NoSQL")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# Schemas
# -------------------------
class LoginBody(BaseModel):
    user_id: str


class CartItemBody(BaseModel):
    sku: str
    qty: int = 1


def product_out(p):
    return {"sku": p.sku, "name": p.name, "category": p.category, "price": p.price, "price_fmt": money(p.price)}


def cart_out(svc: CartService):
    items = [
        {
            "sku": i.sku,
            "name": i.name,
            "unit_price": i.unit_price,
            "unit_price_fmt": money(i.unit_price),
            "qty": i.qty,
            "line_total_fmt": money(i.unit_price * i.qty),
        }
        for i in svc.items()
    ]
    return {"items": items, "total": svc.total(), "total_fmt": money(svc.total()), "count": svc.count_items()}


# -------------------------
# Auth / sessão
# -------------------------
@app.post("/api/login")
def login(body: LoginBody):
    sess = session_svc.login(body.user_id.strip() or "u123")
    cart = cart_for(sess.session_id)

    event_svc.emit("user_login", sess.user_id, sess.session_id, {"created_at": sess.created_at.isoformat()})
    metrics_svc.inc("logins", 1)

    return {
        "session_id": sess.session_id,
        "user_id": sess.user_id,
        "created_at": sess.created_at.isoformat(),
        "cart": cart_out(cart),
    }


@app.post("/api/logout")
def logout(x_session_id: Optional[str] = Header(None)):
    if x_session_id:
        event_svc.cleanup_expired_for_session(x_session_id)
    return {"ok": True}


# -------------------------
# Catálogo
# -------------------------
@app.get("/api/catalog")
def view_catalog(x_session_id: Optional[str] = Header(None)):
    with Timer() as t:
        products = catalog_svc.list_all()

    metrics_svc.latency("view_catalog", t.elapsed_ms)
    metrics_svc.inc("catalog_views", 1)

    sess = session_svc.current(x_session_id)
    if sess:
        event_svc.emit("view_catalog", sess.user_id, sess.session_id, {"count": len(products)})

    return [product_out(p) for p in products]


@app.get("/api/products/{sku}")
def view_product(sku: str, x_session_id: Optional[str] = Header(None)):
    sess = require_session(x_session_id)

    with Timer() as t:
        product = catalog_svc.get_by_sku(sku)

    metrics_svc.latency("view_product", t.elapsed_ms)
    metrics_svc.inc("product_views", 1)

    if not product:
        event_svc.emit("view_product_not_found", sess.user_id, sess.session_id, {"sku": sku})
        metrics_svc.inc("product_not_found", 1)
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    event_svc.emit("view_product", sess.user_id, sess.session_id, {"sku": product.sku, "price": product.price})
    return product_out(product)


@app.get("/api/search")
def search_product(q: str = "", x_session_id: Optional[str] = Header(None)):
    with Timer() as t:
        results = catalog_svc.search(q)

    metrics_svc.latency("search_product", t.elapsed_ms)
    metrics_svc.inc("searches", 1)

    sess = session_svc.current(x_session_id)
    if sess:
        event_svc.emit("search_product", sess.user_id, sess.session_id, {"query": q, "results": len(results)})

    return [product_out(p) for p in results]


# -------------------------
# Carrinho
# -------------------------
@app.get("/api/cart")
def view_cart(x_session_id: Optional[str] = Header(None)):
    sess = require_session(x_session_id)
    cart = cart_for(sess.session_id)

    metrics_svc.inc("cart_views", 1)
    event_svc.emit("view_cart", sess.user_id, sess.session_id, {
        "cart_items": cart.count_items(), "cart_total": cart.total(),
    })
    return cart_out(cart)


@app.post("/api/cart/add")
def add_to_cart(body: CartItemBody, x_session_id: Optional[str] = Header(None)):
    sess = require_session(x_session_id)

    product = catalog_svc.get_by_sku(body.sku)
    if not product:
        event_svc.emit("add_to_cart_failed", sess.user_id, sess.session_id, {"sku": body.sku})
        metrics_svc.inc("add_to_cart_failed", 1)
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    qty = body.qty if body.qty and body.qty > 0 else 1
    cart = cart_for(sess.session_id)
    cart.add(product, qty)
    metrics_svc.inc("adds_to_cart", 1)

    event_svc.emit("add_to_cart", sess.user_id, sess.session_id, {
        "sku": product.sku, "qty": qty, "cart_items": cart.count_items(), "cart_total": cart.total(),
    })
    return cart_out(cart)


@app.post("/api/cart/remove")
def remove_from_cart(body: CartItemBody, x_session_id: Optional[str] = Header(None)):
    sess = require_session(x_session_id)
    qty = body.qty if body.qty and body.qty > 0 else 1

    cart = cart_for(sess.session_id)
    ok = cart.remove(body.sku, qty)
    if not ok:
        metrics_svc.inc("remove_from_cart_failed", 1)
        event_svc.emit("remove_from_cart_failed", sess.user_id, sess.session_id, {"sku": body.sku, "qty": qty})
        raise HTTPException(status_code=404, detail="Item não encontrado no carrinho.")

    metrics_svc.inc("removes_from_cart", 1)
    event_svc.emit("remove_from_cart", sess.user_id, sess.session_id, {
        "sku": body.sku, "qty": qty, "cart_items": cart.count_items(), "cart_total": cart.total(),
    })
    return cart_out(cart)


@app.post("/api/checkout")
def checkout(x_session_id: Optional[str] = Header(None)):
    sess = require_session(x_session_id)
    cart = cart_for(sess.session_id)

    if cart.is_empty():
        metrics_svc.inc("checkout_failed_empty_cart", 1)
        event_svc.emit("checkout_failed", sess.user_id, sess.session_id, {"reason": "empty_cart"})
        raise HTTPException(status_code=400, detail="Carrinho vazio. Nada para fechar.")

    from core.util import new_id

    with Timer() as t:
        total = cart.total()
        items = cart.count_items()
        order_id = new_id("ord")

    metrics_svc.latency("checkout", t.elapsed_ms)
    metrics_svc.inc("checkouts", 1)

    event_svc.emit("checkout_success", sess.user_id, sess.session_id, {
        "order_id": order_id, "total": total, "items": items,
    })

    cart.clear()

    return {"order_id": order_id, "items": items, "total": total, "total_fmt": money(total)}


# -------------------------
# Eventos & métricas
# -------------------------
@app.get("/api/events")
def show_events(x_session_id: Optional[str] = Header(None)):
    sess = require_session(x_session_id)
    events = event_svc.tail(12, session_id=sess.session_id)
    return [
        {"ts": e.ts.isoformat(), "event_type": e.event_type, "payload": e.payload}
        for e in events
    ]


@app.get("/api/metrics")
def show_metrics():
    points = metrics_svc.latest(12)
    counters = metrics_svc.counters()
    return {
        "points": [
            {"ts": p.ts.isoformat(), "metric": p.metric, "value": p.value, "tags": p.tags}
            for p in points
        ],
        "counters": counters,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


# -------------------------
# Frontend estático
# -------------------------
_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
