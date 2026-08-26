import time
from redis_client import get_client

def run():
    r = get_client()

    print("\n=== DEMO 1: STRINGS (SET/GET) + TTL (EXPIRE/TTL) ===")

    key = "demo:status"
    value = "ativo"

    print(f"\n[1] SET {key} = '{value}'")
    r.set(key, value)

    print("[2] GET -> capturando retorno em variável")
    result = r.get(key)
    print("    Resultado:", result)

    print("\n[3] Definindo expiração (EXPIRE 5s)")
    r.expire(key, 5)

    ttl_now = r.ttl(key)
    print("    TTL agora:", ttl_now, "segundos")

    print("\n[4] Esperando 6 segundos para expirar...")
    time.sleep(6)

    result_after = r.get(key)
    print("    GET após expiração:", result_after)
    print("    (None significa: chave não existe mais)")

    # Exemplo extra: SET com expiração no mesmo comando
    key2 = "demo:token"
    token = "abc123"

    print(f"\n[5] SET com expiração embutida (ex=10): {key2}='{token}'")
    r.set(key2, token, ex=20)

    print("[6] TTL do token:", r.ttl(key2), "segundos")
    print("[7] GET token:", r.get(key2))