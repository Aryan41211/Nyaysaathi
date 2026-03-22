import os
import sys
from pathlib import Path

import django
from django.test import Client, TestCase, override_settings


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyaysaathi_project.settings")
django.setup()


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class BasicApiTest(TestCase):
    def test_health_root(self):
        client = Client()
        response = client.get("/health/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("status"), "ok")
