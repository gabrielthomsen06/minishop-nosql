import redis

def get_client() -> redis.Redis:
    return redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True  # retorna strings ao invés de bytes
    )