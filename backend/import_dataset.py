"""
import_dataset.py
=================
Imports legal_cases.json into MongoDB.

Usage:
    python import_dataset.py                      # uses default path
    python import_dataset.py --file path/to/file.json
    python import_dataset.py --wipe               # drop collection first

Run from inside the backend/ directory after setting up .env.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Allow running standalone (outside Django)
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyaysaathi_project.settings")

import django
django.setup()

from legal_cases.db_connection import get_collection
from legal_cases.services import invalidate_cache

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_DATASET = Path(__file__).resolve().parent.parent / "nyaysaathi_part1.json"


def import_dataset(filepath: Path, wipe: bool = False):
    col = get_collection("legal_cases")

    if wipe:
        col.drop()
        logger.info("Collection dropped.")

    # Create a unique index on subcategory to prevent duplicates
    col.create_index("subcategory", unique=True)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        logger.error("Dataset must be a JSON array of objects.")
        sys.exit(1)

    inserted = 0
    skipped = 0
    errors = 0

    for record in data:
        subcategory = record.get("subcategory")
        if not subcategory:
            logger.warning("Skipping record with missing subcategory: %s", record)
            errors += 1
            continue

        try:
            # upsert: update if exists, insert if not
            result = col.update_one(
                {"subcategory": subcategory},
                {"$set": record},
                upsert=True,
            )
            if result.upserted_id:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            logger.error("Error upserting '%s': %s", subcategory, e)
            errors += 1

    logger.info("Import complete — inserted: %d, updated/skipped: %d, errors: %d",
                inserted, skipped, errors)
    logger.info("Total records in collection: %d", col.count_documents({}))

    # Clear in-memory cache so next search loads fresh data
    invalidate_cache()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import NyaySaathi dataset into MongoDB")
    parser.add_argument("--file", type=Path, default=DEFAULT_DATASET, help="Path to JSON dataset")
    parser.add_argument("--wipe", action="store_true", help="Drop collection before import")
    args = parser.parse_args()

    if not args.file.exists():
        logger.error("Dataset file not found: %s", args.file)
        sys.exit(1)

    logger.info("Importing from: %s", args.file)
    import_dataset(args.file, wipe=args.wipe)
