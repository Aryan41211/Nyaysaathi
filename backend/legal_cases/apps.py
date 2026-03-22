from django.apps import AppConfig
import logging
import threading

logger = logging.getLogger(__name__)


class LegalCasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "legal_cases"
    verbose_name = "Legal Cases"

    def ready(self):
        def _ensure_indexes_non_blocking() -> None:
            try:
                from .db_connection import create_indexes

                create_indexes()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Deferred Mongo index creation skipped: %s", exc)

        # Never block Django startup waiting on Mongo.
        threading.Thread(target=_ensure_indexes_non_blocking, daemon=True).start()
