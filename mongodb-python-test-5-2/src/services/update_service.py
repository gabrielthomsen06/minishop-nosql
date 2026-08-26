def update_events(db):
    event = db.events.find_one({ "event_type": "ADD_TO_CART" })

    if event:
        db.events.update_one(
            { "_id": event["_id"] },
            { "$set": { "status": "confirmed" } }
        )

    db.events.update_many(
        { "session_id": "s-001" },
        { "$set": { "session_tag": "aula-4-3" } }
    )