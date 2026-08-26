from datetime import datetime

def run_queries(db):
    print(list(db.events.find({ "event_type": "LOGIN" })))
    print(list(db.events.find({ "meta.sku": "SKU-001" })))

    print(list(db.events.find({
        "event_type": { "$in": ["LOGIN", "ADD_TO_CART"] }
    })))

    print(list(db.events.find({
        "user_id": "u-100",
        "event_type": "ADD_TO_CART"
    })))

    print(list(db.events.find({
        "created_at": {
            "$gte": datetime.fromisoformat("2026-01-28T10:02:00"),
            "$lte": datetime.fromisoformat("2026-01-28T10:04:00")
        }
    })))

    print(list(db.events.find().sort("created_at", -1)))

    print(list(db.events.find(
        {},
        {
            "event_type": 1,
            "message": 1,
            "user_id": 1,
            "created_at": 1
        }
    )))