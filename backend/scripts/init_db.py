from app.db import close, connect, get_db


if __name__ == "__main__":
    connect()
    print(f"MongoDB ready: {get_db().name}; indexes verified")
    close()
