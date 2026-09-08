from __future__ import annotations

from typing import Optional
import datetime as dt

import redis

from core.ports import Session, SessionStore
from core.util import utcnow, new_id


class RedisSessionStore(SessionStore):
    """
    Implementação de SessionStore usando Redis.

    Objetivos (alinhados ao curso e ao slide):
      1) A sessão deixa de depender do processo da aplicação (fica no Redis).
      2) Múltiplas instâncias podem compartilhar as mesmas sessões (Redis compartilhado).
      3) Redis oferece expiração automática nativa (TTL).

    Como armazenamos:
      - Sessão como HASH:
          key = session:<session_id>
          fields = {session_id, user_id, created_at}

      - Índice por usuário (para CLI "retomar sessão"):
          key = session_user:<user_id>  -> value = <session_id>

    Observação didática:
      - Para a CLI, é útil que "login com user_id" retome a sessão existente.
        Por isso, nesta implementação, create_session(user_id) faz:
          - se existir sessão válida para o user_id, retorna ela
          - senão, cria uma nova
        (No InMemorySessionStore, create_session continua criando sempre.)
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        session_ttl_seconds: int = 30 * 60,  # 30 minutos
        session_prefix: str = "session",
        user_index_prefix: str = "session_user",
        sliding_ttl: bool = True,  # renova TTL ao acessar a sessão
    ):
        self._r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self._ttl = session_ttl_seconds
        self._session_prefix = session_prefix
        self._user_index_prefix = user_index_prefix
        self._sliding = sliding_ttl

        # Fail-fast: se não conectar no Redis, melhor falhar aqui com erro claro
        self._r.ping()

    # -------------------------
    # Helpers de chave
    # -------------------------

    def _sess_key(self, session_id: str) -> str:
        return f"{self._session_prefix}:{session_id}"

    def _user_key(self, user_id: str) -> str:
        return f"{self._user_index_prefix}:{user_id}"

    # -------------------------
    # Interface SessionStore
    # -------------------------

    def create_session(self, user_id: str) -> Session:
        """
        Para CLI didática: cria OU retoma uma sessão existente do usuário.

        - Se existir um índice session_user:<user_id> -> <session_id>
          e a sessão ainda estiver válida, retornamos a sessão existente.
        - Se não existir, criamos uma nova e atualizamos sessão + índice.

        Assim o core pode chamar sempre create_session(user_id) sem ifs:
          - InMemory: cria sempre uma nova
          - Redis: retoma se existir (enquanto TTL não expira)
        """
        ukey = self._user_key(user_id)

        # 1) Tenta retomar sessão existente via índice user_id -> session_id
        existing_session_id = self._r.get(ukey)
        if existing_session_id:
            existing = self.get_session(existing_session_id)
            if existing:
                return existing
            # Índice órfão (sessão expirou). Limpa para evitar repetição.
            self._r.delete(ukey)

        # 2) Cria sessão nova (comportamento padrão)
        session_id = new_id("sess")
        sess = Session(session_id=session_id, user_id=user_id, created_at=utcnow())

        skey = self._sess_key(session_id)

        # Grava sessão e índice com TTL (pipeline: aplica tudo junto)
        with self._r.pipeline() as pipe:
            pipe.hset(
                skey,
                mapping={
                    "session_id": sess.session_id,
                    "user_id": sess.user_id,
                    "created_at": sess.created_at.isoformat(),
                },
            )
            pipe.expire(skey, self._ttl)

            # Índice por usuário com o mesmo TTL
            pipe.set(ukey, session_id, ex=self._ttl)

            pipe.execute()

        return sess

    def get_session(self, session_id: str) -> Optional[Session]:
        skey = self._sess_key(session_id)

        data = self._r.hgetall(skey)
        if not data:
            return None

        # Sliding TTL: renovamos o TTL da sessão e do índice do usuário
        if self._sliding:
            user_id = data.get("user_id")
            with self._r.pipeline() as pipe:
                pipe.expire(skey, self._ttl)
                if user_id:
                    pipe.expire(self._user_key(user_id), self._ttl)
                pipe.execute()

        created_at_str = data.get("created_at")
        created_at = None
        if created_at_str:
            created_at = dt.datetime.fromisoformat(created_at_str)

        return Session(
            session_id=data.get("session_id", session_id),
            user_id=data["user_id"],
            created_at=created_at if created_at is not None else utcnow(),
        )

    def delete_session(self, session_id: str) -> None:
        """
        Remove a sessão do Redis e limpa o índice user_id -> session_id.
        """
        skey = self._sess_key(session_id)

        # Precisamos do user_id para remover o índice
        data = self._r.hgetall(skey)
        user_id = data.get("user_id") if data else None

        with self._r.pipeline() as pipe:
            pipe.delete(skey)
            if user_id:
                pipe.delete(self._user_key(user_id))
            pipe.execute()

    @property
    def client(self):
        return self._r

    @property
    def ttl_seconds(self) -> int:
        return self._ttl

