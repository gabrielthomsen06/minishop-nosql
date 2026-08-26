def delete_events(db):
    db.events.delete_many({ "event_type": "APP_STARTED" })