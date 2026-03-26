"""Security-focused auth regression tests."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from unittest.mock import patch

import django
from django.test import Client, TestCase, override_settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyaysaathi_project.settings")
django.setup()

from auth.auth_service import signup_user  # noqa: E402
from search.semantic_engine import QueryMeta  # noqa: E402


class _FakeUsersCollection:
    def __init__(self):
        self._doc = None

    def find_one(self, *_args, **_kwargs):
        return None

    def insert_one(self, doc):
        self._doc = dict(doc)
        return SimpleNamespace(inserted_id="abc123")


def _post_json(client: Client, url: str, payload: dict):
    return client.post(url, data=json.dumps(payload), content_type="application/json", HTTP_HOST="localhost")


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class AuthSecurityTest(TestCase):
    def test_signup_rejects_invalid_email_format(self):
        client = Client()
        resp = _post_json(client, "/api/auth/signup", {"email": "bad-email", "password": "StrongPass123"})

        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.content.decode("utf-8"))
        self.assertFalse(body["success"])
        self.assertIn("invalid email format", str(body.get("error", "")).lower())

    @patch("auth.auth_service.create_jwt", return_value="token")
    @patch("auth.auth_service.get_collection")
    def test_public_signup_never_grants_admin_role(self, mock_get_collection, _mock_create_jwt):
        fake_users = _FakeUsersCollection()
        mock_get_collection.return_value = fake_users

        result = signup_user(email="safe@example.com", password="StrongPass123", role="admin")

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["role"], "user")
        self.assertIsNotNone(fake_users._doc)
        self.assertEqual(fake_users._doc.get("role"), "user")

    def test_query_meta_contains_understood_as_alias(self):
        meta = QueryMeta(
            detected_language="en",
            normalized_query="salary not paid",
            search_ready_query="salary unpaid by employer",
            keywords=["salary", "employer"],
            problem_domain="labor",
            problem_type="salary_non_payment",
            likely_authority="labor_department",
            matched_intent="salary_issue",
            confidence="High",
        ).to_dict()

        self.assertEqual(meta["search_ready_query"], "salary unpaid by employer")
        self.assertEqual(meta["understood_as"], "salary unpaid by employer")

    @patch("legal_cases.db_connection.get_client", return_value=object())
    @patch("ai_engine.response_generator.generate_legal_guidance")
    def test_search_response_contains_clarification_contract(self, mock_guidance, _mock_get_client):
        mock_guidance.return_value = {
            "data": [],
            "query": "help with landlord issue",
            "language": "en",
            "detected_language": "en",
            "normalized_query": "landlord issue",
            "nlp": {"understood_as": "landlord issue", "confidence": "Low"},
            "clarification_required": True,
            "clarification_message": "Please clarify your issue.",
            "clarification_questions": ["Did you receive a notice?", "When did this start?"],
        }

        client = Client()
        resp = _post_json(client, "/api/search/", {"query": "help landlord"})

        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(body["success"])
        self.assertTrue(body.get("clarification_required"))
        self.assertIsInstance(body.get("clarification_questions"), list)
        self.assertIn("clarification_message", body)
