from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_empty_summary_is_honest() -> None:
    response = client.get("/api/v1/evaluation/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "no_results"
    assert payload["human_review"]["claim_precision"]["value"] is None


def test_score_endpoint_applies_contradiction_override() -> None:
    response = client.post(
        "/api/v1/evaluation/score",
        json={
            "components": {
                "relevance": 1,
                "entailment": 1,
                "provenance": 1,
                "independent_agreement": 1,
            },
            "relationship": "supports",
            "reliable_contradiction": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["support_status"] == "contradicted"


def test_invalid_component_returns_validation_error() -> None:
    response = client.post(
        "/api/v1/evaluation/score",
        json={
            "components": {"relevance": 2},
            "relationship": "supports",
        },
    )
    assert response.status_code == 422
