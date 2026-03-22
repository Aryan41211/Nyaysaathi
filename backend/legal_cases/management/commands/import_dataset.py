"""
Management command: python manage.py import_dataset
Imports the legal_cases.json dataset into MongoDB.

Options:
  --file   Path to JSON file (default: ../../dataset/legal_cases.json)
  --wipe   Drop the collection before importing
"""
import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from legal_cases.db_connection import get_collection
from legal_cases.services import invalidate_cache

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parents[5] / "nyaysaathi_part1.json"


class Command(BaseCommand):
    help = "Import legal_cases.json into MongoDB (upsert, no duplicates)"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=Path, default=DEFAULT_PATH, help="Path to JSON dataset")
        parser.add_argument("--wipe", action="store_true", help="Drop collection before import")

    def handle(self, *args, **options):
        filepath: Path = options["file"]
        if not filepath.exists():
            raise CommandError(f"File not found: {filepath}")

        col = get_collection("legal_cases")

        if options["wipe"]:
            col.drop()
            self.stdout.write(self.style.WARNING("Collection dropped."))

        col.create_index("subcategory", unique=True)

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise CommandError("Dataset must be a JSON array.")

        inserted = updated = errors = 0
        for record in data:
            sub = record.get("subcategory")
            if not sub:
                self.stderr.write(f"Skipping record with no subcategory: {record}")
                errors += 1
                continue
            try:
                result = col.update_one({"subcategory": sub}, {"$set": record}, upsert=True)
                if result.upserted_id:
                    inserted += 1
                else:
                    updated += 1
            except Exception as e:
                self.stderr.write(f"Error for '{sub}': {e}")
                errors += 1

        invalidate_cache()
        total = col.count_documents({})
        self.stdout.write(self.style.SUCCESS(
            f"Import complete — inserted: {inserted}, updated: {updated}, "
            f"errors: {errors}, total in DB: {total}"
        ))
