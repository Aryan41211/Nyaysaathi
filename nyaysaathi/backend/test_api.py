"""Basic API regression tests for NyaySaathi production readiness."""

from __future__ import annotations

import json
import os

import django
from django.test import Client

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyaysaathi_project.settings")
django.setup()


def _call_json(client: Client, method: str, url: str, payload: dict | None = None):
    if method == "GET":
        return client.get(url, payload or {}, HTTP_HOST="localhost")
    return client.post(url, data=json.dumps(payload or {}), content_type="application/json", HTTP_HOST="localhost")


def test_classify_success_shape():
    client = Client()
    resp = _call_json(client, "POST", "/api/classify", {"user_input": "salary not paid", "user_id": "t1"})
    assert resp.status_code == 200
    body = json.loads(resp.content.decode("utf-8"))
    assert body["success"] is True
    assert body["error"] is None
    assert "data" in body
    assert "workflow_steps" in body["data"]


def test_search_validation_rejects_empty():
    client = Client()
    resp = _call_json(client, "POST", "/api/search/", {"query": ""})
    assert resp.status_code == 400
    body = json.loads(resp.content.decode("utf-8"))
    assert body["success"] is False
    assert body["status_code"] == 400
    assert isinstance(body["error"], str)


def test_case_detail_response_shape():
    client = Client()
    resp = _call_json(client, "GET", "/api/case/Salary%20Not%20Paid%20by%20Employer/")
    assert resp.status_code == 200
    body = json.loads(resp.content.decode("utf-8"))
    assert body["success"] is True
    assert body["error"] is None
    assert "data" in body


def test_auth_signup_login_shape():
    client = Client()
    email = "test_user_nyaysaathi@example.com"
    password = "StrongPass123"

    signup_resp = _call_json(
        client,
        "POST",
        "/api/auth/signup",
        {"email": email, "password": password, "role": "user"},
    )
    assert signup_resp.status_code in {201, 400, 503}

    login_resp = _call_json(
        client,
        "POST",
        "/api/auth/login",
        {"email": email, "password": password},
    )
    assert login_resp.status_code in {200, 503}
    body = json.loads(login_resp.content.decode("utf-8"))
    if login_resp.status_code == 503:
        assert body["success"] is False
        return
    assert body["success"] is True
    assert "token" in body["data"]
