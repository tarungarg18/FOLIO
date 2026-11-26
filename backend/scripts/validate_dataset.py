from app.db import close, connect, get_db


def main() -> None:
    connect()
    db = get_db()
    collections = ["instruments", "prices", "fund_schemes", "fund_navs", "fund_constituents", "benchmark_values"]
    for name in collections:
        print(f"{name}: {db[name].count_documents({})} records")
    close()


if __name__ == "__main__":
    main()
