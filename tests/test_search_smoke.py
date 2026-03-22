import os
import sys
from pathlib import Path
from unittest.mock import patch

import django
from django.test import Client, TestCase, override_settings


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyaysaathi_project.settings")
django.setup()


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class SearchSmokeTest(TestCase):
    @patch("legal_cases.views.generate_legal_guidance")
    def test_search_endpoint_smoke(self, mock_guidance):
        mock_guidance.return_value = {
            "data": [],
            "query": "salary not paid",
            "language": "en",
            "total": 0,
            "message": "Search completed.",
        }

        client = Client()
        response = client.get("/api/search/", {"query": "salary not paid"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("success", payload)
        self.assertTrue(payload["success"])
