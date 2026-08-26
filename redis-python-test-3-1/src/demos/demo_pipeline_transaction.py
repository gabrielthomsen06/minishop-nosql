import redis
from redis_client import get_client


def reserve_stock_atomic(sku: str, qty: int) -> bool:
    r = get_client()

    stock_key = f"demo:stock:{sku}"
    reserved_key = f"demo:reserved:{sku}"

    # Inicializa estoque para demo (somente se não existir)
    r.setnx(stock_key, 5)

    while True:
        try:
            # WATCH: “vigia” a chave de estoque.
            # Se outro cliente mudar stock_key antes do EXEC, a transação falha.
            r.watch(stock_key)

            current_stock = r.get(stock_key)
            current_stock = int(current_stock) if current_stock is not None else 0

            if current_stock < qty:
                r.unwatch()
                return False

            # transaction=True => MULTI/EXEC (atomicidade)
            pipe = r.pipeline(transaction=True)

            # Decrementa estoque e incrementa reservado como uma unidade lógica
            pipe.decrby(stock_key, qty)
            pipe.incrby(reserved_key, qty)

            # EXEC: tenta aplicar tudo. Se alguém mexeu no stock_key, levanta WatchError.
            pipe.execute()
            return True

        except redis.WatchError:
            # Outro usuário alterou o estoque entre o WATCH e o EXEC.
            # Repetimos o loop para ler o valor atualizado e tentar novamente.
            continue


def run():
    sku = "SKU-001"

    print("\n=== DEMO 4: PIPELINE + TRANSACTION (MULTI/EXEC) PARA ATOMICIDADE ===")
    print(f"SKU: {sku} | Tentando reservar 3 unidades em um bloco atômico.")

    ok = reserve_stock_atomic(sku, 3)

    r = get_client()
    stock = r.get(f"demo:stock:{sku}")
    reserved = r.get(f"demo:reserved:{sku}")

    print("Reserva realizada?", ok)
    print("Estoque restante:", stock)
    print("Reservado:", reserved)
