from django.apps import AppConfig


class LegalCasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "legal_cases"
    verbose_name = "Legal Cases"

    def ready(self):
        try:
            from .db_connection import create_indexes

            create_indexes()
        except Exception:
            # Startup should never fail only because DB is temporarily unavailable.
            pass
