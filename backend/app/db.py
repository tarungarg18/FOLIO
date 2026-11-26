from pymongo import ASCENDING, MongoClient

from .config import settings

client: MongoClient | None = None
database = None


def connect() -> None:
    global client, database
    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2500)
    client.admin.command("ping")
    database = client[settings.mongodb_database]
    ensure_indexes()


def close() -> None:
    global client, database
    if client is not None:
        client.close()
    client = None
    database = None


def ensure_indexes() -> None:
    if database is None:
        return
    database.users.create_index([("email", ASCENDING)], unique=True)
    database.sessions.create_index([("token_hash", ASCENDING)], unique=True)
    database.sessions.create_index("expires_at", expireAfterSeconds=0)
    database.portfolios.create_index([("owner_id", ASCENDING), ("slug", ASCENDING)], unique=True)
    database.holdings.create_index([("portfolio_id", ASCENDING), ("instrument_id", ASCENDING)], unique=True)
    database.instruments.create_index([("isin", ASCENDING)], unique=True, sparse=True)
    database.instruments.create_index([("symbol", ASCENDING)])
    database.prices.create_index([("instrument_id", ASCENDING), ("date", ASCENDING)], unique=True)
    database.fund_schemes.create_index([("scheme_code", ASCENDING)], unique=True)
    database.fund_navs.create_index([("scheme_code", ASCENDING), ("date", ASCENDING)], unique=True)
    database.fund_constituents.create_index(
        [("scheme_code", ASCENDING), ("reporting_date", ASCENDING), ("security_isin", ASCENDING)],
        unique=True,
    )
    database.benchmark_values.create_index([("benchmark_id", ASCENDING), ("date", ASCENDING)], unique=True)
    database.data_manifests.create_index([("dataset", ASCENDING), ("retrieved_at", ASCENDING)])
    database.ingestion_jobs.create_index([("job_id", ASCENDING)], unique=True)


def get_db():
    if database is None:
        raise RuntimeError("MongoDB is not connected. Start the local MongoDB Community Server.")
    return database
