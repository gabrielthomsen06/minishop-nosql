# MiniShop NoSQL — nosql-python-5-3

CLI didática de um mini e-commerce, usada para praticar bancos NoSQL a partir de uma arquitetura hexagonal (ports & adapters) em Python. Cada conceito de domínio (sessão, carrinho, eventos, métricas) tem uma porta (`core/ports.py`) e pode trocar de implementação (em memória, Redis, MongoDB) sem alterar as regras de negócio.

> Este README é só uma explicação básica do estado atual do projeto. Ele vai ser reescrito quando o front-end for adicionado.

## Bancos utilizados

| Conceito       | Implementação atual        |
|----------------|-----------------------------|
| Sessão de usuário | Redis (com TTL / expiração automática) |
| Carrinho       | Redis (associado à sessão)  |
| Eventos        | MongoDB                     |
| Métricas       | Em memória (ainda não persistido) |
| Catálogo       | Em memória (dados fixos)    |

Cassandra ainda não está integrado nesta versão (ver banner do menu no `core/app.py`).

## Estrutura

```
src/
  core/
    app.py       # MiniShopApp: CLI e orquestração das ações (login, catálogo, carrinho, checkout...)
    ports.py     # Interfaces (Protocol) + modelos de domínio (Session, Event, Product, CartItem...)
    util.py      # Helpers (Timer, formatação de dinheiro, geração de IDs)
  services/       # Regras de negócio, um serviço por conceito (session, cart, catalog, event, metrics)
  adapters/       # Implementações concretas das ports (in-memory, Redis, MongoDB)
  main.py         # Entry point "completo": Redis (sessão/carrinho) + MongoDB (eventos)
  mainInMemory.py # Entry point alternativo, tudo em memória (exceto sessão, que pode usar Redis)
  mainRedis.py    # Entry point intermediário: sessão + carrinho no Redis, eventos em memória
```

## Pré-requisitos

- Python 3.12 (o `cassandra-driver` usado no ambiente maior não tem wheel para 3.13 no Windows)
- Docker (para subir Redis e MongoDB via `docker-compose.yml` na raiz do repositório)

## Como rodar

1. Suba os bancos (na raiz do `nosql-ambiente`):
   ```
   docker-compose up -d redis mongodb
   ```
2. Instale as dependências (arquivo `requirements.txt` na raiz do repositório):
   ```
   pip install -r ../requirements.txt
   ```
3. Rode a aplicação:
   ```
   cd src
   python main.py
   ```

O menu interativo permite login, navegação no catálogo, busca, carrinho, checkout, e visualização de eventos/métricas recentes.

## Próximos passos

- [ ] Front-end web consumindo esta lógica de aplicação
- [ ] Persistência de métricas
- [ ] Integração com Cassandra
