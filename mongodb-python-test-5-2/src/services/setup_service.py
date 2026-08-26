def reset_collection(db):
    db.events.drop()
    db.create_collection("events")