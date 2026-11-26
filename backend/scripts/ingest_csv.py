"""Load a provider-downloaded and locally reviewed CSV into an allow-listed collection.

Expected formats are documented in docs/DATA_DICTIONARY.md. This script deliberately
does not fetch remote data: provider terms and file shapes must be verified first.
"""
import argparse
import csv
from datetime import datetime, timezone

from pymongo import UpdateOne

from app.db import close, connect, get_db

FORMATS = {
    "prices": ("prices", ("instrument_id", "date")),
    "fund_navs": ("fund_navs", ("scheme_code", "date")),
    "benchmark_values": ("benchmark_values", ("benchmark_id", "date")),
    "fund_constituents": ("fund_constituents", ("scheme_code", "reporting_date", "security_isin")),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a reviewed normalized CSV file.")
    parser.add_argument("dataset", choices=FORMATS)
    parser.add_argument("csv_path")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--usage-status", required=True, choices=["permitted", "research_only", "license_required", "unknown"])
    args = parser.parse_args()
    collection_name, key_fields = FORMATS[args.dataset]
    with open(args.csv_path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or any(not all(row.get(key) for key in key_fields) for row in rows):
        raise SystemExit("CSV is empty or missing a required identity/date key")
    operations = []
    for row in rows:
        key = {field: row[field] for field in key_fields}
        operations.append(UpdateOne(key, {"$set": {**row, "provider": args.provider, "source_url": args.source_url, "retrieved_at": datetime.now(timezone.utc), "usage_status": args.usage_status}}, upsert=True))
    connect()
    result = get_db()[collection_name].bulk_write(operations, ordered=False)
    get_db().data_manifests.insert_one({"dataset": args.dataset, "provider": args.provider, "source_url": args.source_url, "retrieved_at": datetime.now(timezone.utc), "record_count": len(rows), "usage_status": args.usage_status, "upserted": result.upserted_count})
    print(f"Processed {len(rows)} rows; inserted {result.upserted_count}; updated {result.modified_count}")
    close()


if __name__ == "__main__":
    main()
