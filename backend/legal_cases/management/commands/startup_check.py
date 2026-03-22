"""Production startup validation checks."""

from __future__ import annotations

import importlib
import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from legal_cases.db_connection import get_client
from utils.env_validator import validate_environment

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run startup readiness checks for environment, DB, dataset, and AI modules"

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail command on critical readiness checks.",
        )

    def handle(self, *args, **options):
        strict = bool(options.get("strict", False))

        logger.info("startup_check: starting")
        self.stdout.write("[startup] Running environment validation...")
        env_result = validate_environment()

        if env_result.missing_required:
            msg = f"Missing required env vars: {', '.join(env_result.missing_required)}"
            if strict:
                raise CommandError(msg)
            self.stderr.write(self.style.WARNING(msg))

        if env_result.missing_optional:
            self.stderr.write(
                self.style.WARNING(
                    f"Missing optional env vars: {', '.join(env_result.missing_optional)}"
                )
            )

        self.stdout.write("[startup] Checking MongoDB reachability...")
        try:
            client = get_client(raise_on_error=strict, quick=not strict)
            if client is None:
                raise RuntimeError("MongoDB unavailable in quick-check mode")
            client.admin.command("ping")
        except Exception as exc:  # noqa: BLE001
            msg = f"MongoDB unreachable: {exc}"
            if strict:
                raise CommandError(msg)
            self.stderr.write(self.style.WARNING(msg))

        self.stdout.write("[startup] Checking dataset files...")
        required_files = [
            settings.BASE_DIR / "data" / "nyaysaathi_en.json",
            settings.BASE_DIR / "data" / "nyaysaathi_hi.json",
            settings.BASE_DIR / "data" / "nyaysaathi_mr.json",
        ]
        missing_files = [str(path) for path in required_files if not Path(path).exists()]
        if missing_files:
            msg = f"Dataset files missing: {', '.join(missing_files)}"
            if strict:
                raise CommandError(msg)
            self.stderr.write(self.style.WARNING(msg))

        self.stdout.write("[startup] Checking AI module imports...")
        modules = [
            "ai_engine.intent_detection",
            "ai_engine.embedding_engine",
            "ai_engine.semantic_search",
            "ai_engine.response_generation",
            "ai_engine.language_processing",
            "ai_engine.translation",
        ]
        failed = []
        for module_name in modules:
            try:
                importlib.import_module(module_name)
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{module_name} ({exc})")

        if failed:
            msg = f"AI module import failures: {'; '.join(failed)}"
            if strict:
                raise CommandError(msg)
            self.stderr.write(self.style.WARNING(msg))

        logger.info("startup_check: completed")
        self.stdout.write(self.style.SUCCESS("Startup checks completed."))
