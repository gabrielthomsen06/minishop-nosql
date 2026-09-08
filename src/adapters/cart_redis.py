from __future__ import annotations

import json
from typing import List
import redis

from core.ports import CartItem, CartStore


class RedisCartStore(CartStore):
    """
    Carrinho persistido no Redis.

    Chave:
      cart:<session_id> -> JSON list[CartItem]

    Regras:
      - load(): se não existir, retorna []
      - save(): grava o JSON e renova o TTL (alinhado com a sessão)
      - delete(): remove a chave do carrinho
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        session_ttl_seconds: int,
        cart_prefix: str = "cart",
    ):
        self._r = redis_client
        self._ttl = session_ttl_seconds
        self._prefix = cart_prefix

        # Fail-fast (opcional, mas ajuda no curso)
        self._r.ping()

    def _key(self, session_id: str) -> str:
        return f"{self._prefix}:{session_id}"

    def load(self, session_id: str) -> List[CartItem]:
        raw = self._r.get(self._key(session_id))
        if not raw:
            return []

        try:
            data = json.loads(raw)
            return [CartItem(**x) for x in data]
        except Exception:
            # Se algo corromper, não explode a app
            return []

    def save(self, session_id: str, items: List[CartItem]) -> None:
        payload = json.dumps(
            [
                {
                    "sku": i.sku,
                    "name": i.name,
                    "unit_price": float(i.unit_price),
                    "qty": int(i.qty),
                }
                for i in items
            ],
            ensure_ascii=False,
        )

        key = self._key(session_id)
        with self._r.pipeline() as pipe:
            pipe.set(key, payload)
            pipe.expire(key, self._ttl)  # TTL alinhado com a sessão
            pipe.execute()

    def delete(self, session_id: str) -> None:
        self._r.delete(self._key(session_id))
