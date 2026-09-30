from app.database import database_status, init_db


if __name__ == "__main__":
    init_db()
    status = database_status()
    print(f"engine={status['engine']}")
    print(f"status={status['status']}")
    print(f"persistent={status['persistent']}")
    print(f"table_count={status['table_count']}")
    print("tables=" + ",".join(status["tables"]))
