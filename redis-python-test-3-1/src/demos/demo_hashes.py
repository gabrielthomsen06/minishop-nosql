from redis_client import get_client

def run():
    r = get_client()

    print("\n=== DEMO 2: HASHES (HSET/HGET/HGETALL/HINCRBY) ===")

    key = "demo:user:100"

    print(f"\n[1] Criando um 'objeto' no Redis com HSET: {key}")
    r.hset(key, mapping={
        "nome": "Carlos",
        "email": "carlos@email.com",
        "status": "ativo",
        "acessos": 0
    })

    print("\n[2] HGETALL -> trazendo tudo para um dict Python")
    user_dict = r.hgetall(key)
    print("    Resultado (dict):", user_dict)

    print("\n[3] Acessando um campo específico com HGET")
    nome = r.hget(key, "nome")
    print("    nome =", nome)

    print("\n[4] Incrementando um campo numérico com HINCRBY")
    new_access = r.hincrby(key, "acessos", 1)
    print("    acessos agora =", new_access)

    print("\n[5] Atualizando status com HSET (sobrescreve apenas o campo)")
    r.hset(key, "status", "premium")

    status = r.hget(key, "status")
    print("    status =", status)