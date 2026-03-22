from django.apps import AppConfig


class LegalCasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "legal_cases"
    verbose_name = "Legal Cases"

    def ready(self):
        # Keep startup path lightweight; initialize heavy dependencies lazily per request.
        return None
