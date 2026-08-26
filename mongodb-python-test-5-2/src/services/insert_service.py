from datetime import datetime

def insert_events(db):
    print("Inserindo eventos...")

    db.events.insert_one({
        "event_type": "APP_STARTED",
        "message": "MiniShop iniciada",
        "user_id": None,
        "session_id": "s-001",
        "created_at": datetime.fromisoformat("2026-01-28T10:00:00")
    })

    db.events.insert_one({
        "event_type": "LOGIN",
        "message": "Usuário autenticado",
        "user_id": "u-100",
        "session_id": "s-001",
        "created_at": datetime.fromisoformat("2026-01-28T10:02:10")
    })

    db.events.insert_one({
        "event_type": "ADD_TO_CART",
        "message": "Adicionou item ao carrinho",
        "user_id": "u-100",
        "session_id": "s-001",
        "created_at": datetime.fromisoformat("2026-01-28T10:03:25"),
        "meta": {
            "sku": "SKU-001",
            "qty": 2
        }
    })