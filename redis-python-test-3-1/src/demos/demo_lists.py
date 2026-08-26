from redis_client import get_client

def run():
    r = get_client()

    print("\n=== DEMO 3: LISTAS (LPUSH/LRANGE/LTRIM) ===")

    key = "demo:recent_actions:100"

    print(f"\n[1] Limpando lista anterior (DEL {key})")
    r.delete(key)

    print("\n[2] Adicionando ações com LPUSH (insere no começo)")
    r.lpush(key, "login")
    r.lpush(key, "view_product:A100")
    r.lpush(key, "add_to_cart:A100")
    r.lpush(key, "checkout")

    print("\n[3] LRANGE 0 -1 -> lendo lista completa (captura em variável Python)")
    actions = r.lrange(key, 0, -1)
    print("    Lista de ações:", actions)

    print("\n[4] Mantendo apenas as 3 ações mais recentes com LTRIM 0 2")
    r.ltrim(key, 0, 2)

    actions_trimmed = r.lrange(key, 0, -1)
    print("    Lista após trim:", actions_trimmed)