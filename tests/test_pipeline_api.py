"""End-to-end pipeline + HTTP layer (FastAPI TestClient)."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_BRIEF = (
    "Need something for the new sneaker drop targeting gen z, "
    "kinda hype energy, has to be ready by friday."
)


def test_health() -> None:
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_provider_endpoint() -> None:
    res = client.get("/api/v1/provider")
    assert res.status_code == 200
    assert res.json()["provider"] == "local"


def test_generate_ok_with_sample_brief() -> None:
    res = client.post("/api/v1/generate", json={"raw_brief": SAMPLE_BRIEF})

    assert res.status_code == 200
    body = res.json()

    brief = body["validated_brief"]
    assert brief["campaign_name"] == "Sneaker Drop Campaign"
    assert brief["target_audience"] == "Gen Z"
    assert brief["tone"] == "hype"

    creative = body["creative"]
    assert creative["ad_concept"]
    assert creative["social_caption"]

    meta = body["meta"]
    assert meta["provider"] == "local"
    assert meta["validation_attempts"] >= 1


def test_generate_applies_and_reports_fallbacks() -> None:
    future = (date.today() + timedelta(days=60)).isoformat()
    res = client.post(
        "/api/v1/generate", json={"raw_brief": f"Perfume launch ad by {future}."}
    )

    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["fallbacks_applied"]
    assert body["validated_brief"]["tone"] == "professional"


def test_generate_unusable_brief_returns_422_with_clear_errors() -> None:
    res = client.post(
        "/api/v1/generate",
        json={"raw_brief": "blah blah random filler nothing useful at all"},
    )

    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["error"] == "brief_validation_failed"
    assert detail["attempts"] >= 1
    assert any(issue["field"] == "deadline" for issue in detail["issues"])


def test_generate_rejects_empty_request() -> None:
    res = client.post("/api/v1/generate", json={"raw_brief": "hi"})  # too short
    assert res.status_code == 422
