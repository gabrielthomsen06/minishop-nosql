# MiniShop NoSQL

Projeto didático de uma loja fictícia (MiniShop) que usa três bancos NoSQL, cada um resolvendo um problema diferente:

- **Redis** — sessão de usuário e carrinho de compras (dados voláteis, com TTL)
- **MongoDB** — log de eventos da aplicação (login, visualizações, buscas, checkout...)
- **Cassandra** — métricas e contadores em série temporal

A lógica de negócio é a mesma para as duas formas de uso:

- **CLI** (`src/main.py`) — menu no terminal, pensado para fins didáticos/aula.
- **Web** (`src/webapp.py`) — API REST (FastAPI) + frontend simples (HTML/CSS/JS puro), para usar tudo isso pelo navegador em vez do terminal.

## Estrutura do projeto

```
.
├── docker-compose.yml       # Sobe Mongo, Redis, Cassandra e a aplicação web
├── Dockerfile                # Imagem da aplicação web (API + frontend estático)
├── requirements-web.txt      # Dependências da API web (FastAPI, uvicorn, drivers)
├── requirements.txt           # Dependências para rodar tudo localmente (fora do Docker)
├── requeriments.txt           # Dependências específicas do app (Windows/Python 3.12)
├── src/
│   ├── main.py                # Entrypoint da CLI (Redis + Mongo + Cassandra)
│   ├── mainRedis.py           # Variante da CLI usando só Redis
│   ├── mainInMemory.py        # Variante da CLI 100% em memória (sem bancos)
│   ├── webapp.py              # API REST + serve o frontend estático
│   ├── core/                  # Modelos de domínio, interfaces (ports) e MiniShopApp (CLI)
│   ├── services/               # Regras de negócio (catálogo, carrinho, sessão, eventos, métricas)
│   └── adapters/               # Implementações concretas por banco (Redis, Mongo, Cassandra, em memória)
└── static/                    # Frontend (index.html, style.css, app.js)
```

## Rodando com Docker (recomendado)

Sobe os três bancos e a aplicação web em containers:

```bash
docker compose up -d --build
```

Depois, acesse **http://localhost:8000** no navegador.

Serviços expostos:

| Serviço   | Porta local | Descrição                          |
|-----------|-------------|-------------------------------------|
| web       | 8000        | Frontend + API REST                 |
| mongodb   | 27017       | Eventos                             |
| redis     | 6379        | Sessão e carrinho                   |
| cassandra | 9042        | Métricas                            |

Para parar tudo:

```bash
docker compose down
```

Para apagar também os volumes (dados persistidos dos bancos):

```bash
docker compose down -v
```

> O serviço `web` só inicia depois que Mongo, Redis e Cassandra reportam `healthy` (via `healthcheck` no `docker-compose.yml`), então o primeiro `up` pode levar cerca de 1 minuto até o Cassandra ficar pronto.

## Usando o frontend

1. Faça login informando um `user_id` (ex: `u123`) — cria/retoma uma sessão no Redis.
2. **Catálogo** — lista os produtos fixos da loja.
3. **Buscar** — filtra produtos por nome, categoria ou SKU.
4. **Carrinho** — adiciona/remove itens e finaliza a compra (checkout).
5. **Eventos** — mostra os últimos eventos da sua sessão, gravados no MongoDB.
6. **Métricas** — mostra contadores e latências agregadas, gravados no Cassandra.

O frontend guarda o `session_id` no `localStorage` do navegador e o envia em todo request via o header `X-Session-Id`.

## Rodando a CLI localmente (sem Docker)

Requer Python 3.12 (o driver do Cassandra não tem wheel pronto para 3.13 no Windows — veja os comentários em `requeriments.txt`).

```bash
pip install -r requirements.txt
# suba os bancos manualmente ou via: docker compose up -d mongodb redis cassandra
cd src
python main.py
```

Também existem variantes reduzidas para focar em um banco por vez: `python mainRedis.py` (só Redis, resto em memória) e `python mainInMemory.py` (tudo em memória, sem nenhum banco).

## API REST (resumo)

Todas as rotas autenticadas esperam o header `X-Session-Id` (obtido no login).

| Método | Rota                | Autenticado | Descrição                          |
|--------|---------------------|:-----------:|--------------------------------------|
| POST   | `/api/login`         |             | Cria/retoma sessão (Redis)           |
| POST   | `/api/logout`        |             | Limpa eventos expirados da sessão    |
| GET    | `/api/catalog`        |             | Lista o catálogo                     |
| GET    | `/api/products/{sku}` | sim         | Detalhe de um produto                |
| GET    | `/api/search?q=`      |             | Busca produtos                       |
| GET    | `/api/cart`            | sim         | Vê o carrinho                        |
| POST   | `/api/cart/add`        | sim         | Adiciona item ao carrinho            |
| POST   | `/api/cart/remove`     | sim         | Remove item do carrinho              |
| POST   | `/api/checkout`        | sim         | Finaliza a compra                    |
| GET    | `/api/events`           | sim         | Últimos eventos da sessão (Mongo)    |
| GET    | `/api/metrics`          |             | Métricas e contadores (Cassandra)    |
| GET    | `/api/health`           |             | Healthcheck simples                  |

## Variáveis de ambiente (aplicação web)

| Variável        | Padrão      | Uso                          |
|------------------|-------------|-------------------------------|
| `REDIS_HOST`      | `localhost` | Host do Redis                |
| `MONGO_HOST`       | `localhost` | Host do MongoDB              |
| `CASSANDRA_HOST`   | `127.0.0.1` | Host do Cassandra            |

No `docker-compose.yml`, essas variáveis já apontam para os nomes dos serviços (`redis`, `mongodb`, `cassandra`).
