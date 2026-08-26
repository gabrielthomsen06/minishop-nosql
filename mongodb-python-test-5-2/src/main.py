from mongo_client import get_db

from services.setup_service import reset_collection
from services.insert_service import insert_events
from services.query_service import run_queries
from services.update_service import update_events
from services.delete_service import delete_events

def main():
    db = get_db()

    # reset_collection(db)
    # insert_events(db)
    # run_queries(db)
    # update_events(db)
    # delete_events(db)


if __name__ == "__main__":
    main()
