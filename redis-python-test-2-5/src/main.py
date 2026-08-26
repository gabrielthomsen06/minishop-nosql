import redis

def main():
    client = redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True
    )

    print("Conectando ao Redis...")
    response = client.ping()
    print("Resposta do Redis:", response)

if __name__ == "__main__":
    main()