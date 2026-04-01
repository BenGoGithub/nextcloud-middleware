"""End-to-end tests for confidence flow, confirm endpoints, and calendar routing."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from middleware.main import app
from middleware.models import EventOutput, TaskOutput

client = TestClient(app, raise_server_exceptions=True)

AUTH = {"Authorization": "Bearer test-token"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _low_confidence_task(**kwargs) -> TaskOutput:
    defaults = dict(
        target_type="task",
        title="RDV médecin",
        nextcloud_list="Santé",
        confidence=0.5,
        candidates=["RDV médecin vendredi 4 avril", "RDV médecin vendredi 11 avril"],
    )
    defaults.update(kwargs)
    return TaskOutput(**defaults)


def _confirmed_task(**kwargs) -> TaskOutput:
    defaults = dict(
        target_type="task",
        title="RDV médecin vendredi 4 avril",
        nextcloud_list="Santé",
        confidence=0.95,
    )
    defaults.update(kwargs)
    return TaskOutput(**defaults)


def _low_confidence_event(**kwargs) -> EventOutput:
    defaults = dict(
        title="Séance sport",
        start=datetime(2026, 4, 4, 9, 0),
        calendar="Workout Rotator",
        confidence=0.4,
        candidates=["Séance sport vendredi 4 avril", "Séance sport vendredi 11 avril"],
    )
    defaults.update(kwargs)
    return EventOutput(**defaults)


def _confirmed_event(**kwargs) -> EventOutput:
    defaults = dict(
        title="Séance sport vendredi 4 avril",
        start=datetime(2026, 4, 4, 9, 0),
        calendar="Workout Rotator",
        confidence=0.95,
    )
    defaults.update(kwargs)
    return EventOutput(**defaults)


# ---------------------------------------------------------------------------
# /task — confidence flow
# ---------------------------------------------------------------------------

class TestTaskClarificationFlow:
    def test_low_confidence_returns_clarification(self):
        fake = _low_confidence_task()
        with patch("middleware.main.call_llm", new_callable=AsyncMock, return_value=fake):
            resp = client.post("/task", json={"text": "rdv médecin vendredi"}, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "clarification_needed"
        assert len(data["request_id"]) == 36  # UUID
        assert data["options"] == fake.candidates
        assert data["confidence"] == 0.5

    def test_confirm_task_valid_choice(self):
        fake_low = _low_confidence_task()
        fake_ok = _confirmed_task()

        with patch("middleware.main.call_llm", new_callable=AsyncMock, return_value=fake_low):
            r1 = client.post("/task", json={"text": "rdv médecin vendredi"}, headers=AUTH)
        request_id = r1.json()["request_id"]

        with patch("middleware.main.call_llm", new_callable=AsyncMock, return_value=fake_ok), \
             patch("middleware.main.dispatch", new_callable=AsyncMock):
            r2 = client.post(
                "/task/confirm",
                json={"request_id": request_id, "choice": fake_low.candidates[0]},
                headers=AUTH,
            )

        assert r2.status_code == 200
        data = r2.json()
        assert data["status"] == "created"
        assert data["title"] == fake_ok.title
        assert data["nextcloud_list"] == "Santé"

    def test_confirm_task_unknown_request_id_returns_404(self):
        resp = client.post(
            "/task/confirm",
            json={"request_id": "00000000-0000-0000-0000-000000000000", "choice": "anything"},
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_confirm_task_invalid_choice_returns_400(self):
        fake_low = _low_confidence_task()

        with patch("middleware.main.call_llm", new_callable=AsyncMock, return_value=fake_low):
            r1 = client.post("/task", json={"text": "rdv médecin vendredi"}, headers=AUTH)
        request_id = r1.json()["request_id"]

        r2 = client.post(
            "/task/confirm",
            json={"request_id": request_id, "choice": "option qui n'existe pas"},
            headers=AUTH,
        )
        assert r2.status_code == 400

    def test_confirm_task_request_id_consumed_after_use(self):
        fake_low = _low_confidence_task()
        fake_ok = _confirmed_task()

        with patch("middleware.main.call_llm", new_callable=AsyncMock, return_value=fake_low):
            r1 = client.post("/task", json={"text": "rdv médecin vendredi"}, headers=AUTH)
        request_id = r1.json()["request_id"]

        with patch("middleware.main.call_llm", new_callable=AsyncMock, return_value=fake_ok), \
             patch("middleware.main.dispatch", new_callable=AsyncMock):
            client.post(
                "/task/confirm",
                json={"request_id": request_id, "choice": fake_low.candidates[0]},
                headers=AUTH,
            )

        # Deuxième usage du même request_id → 404
        r3 = client.post(
            "/task/confirm",
            json={"request_id": request_id, "choice": fake_low.candidates[0]},
            headers=AUTH,
        )
        assert r3.status_code == 404


# ---------------------------------------------------------------------------
# /event — confidence flow + calendar
# ---------------------------------------------------------------------------

class TestEventFlow:
    def test_low_confidence_event_returns_clarification(self):
        fake = _low_confidence_event()
        with patch("middleware.main.call_llm_event", new_callable=AsyncMock, return_value=fake):
            resp = client.post("/event", json={"text": "séance sport vendredi"}, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "clarification_needed"
        assert len(data["request_id"]) == 36
        assert data["options"] == fake.candidates

    def test_confirm_event_valid_choice(self):
        fake_low = _low_confidence_event()
        fake_ok = _confirmed_event()

        with patch("middleware.main.call_llm_event", new_callable=AsyncMock, return_value=fake_low):
            r1 = client.post("/event", json={"text": "séance sport vendredi"}, headers=AUTH)
        request_id = r1.json()["request_id"]

        with patch("middleware.main.call_llm_event", new_callable=AsyncMock, return_value=fake_ok), \
             patch("middleware.main.create_event", new_callable=AsyncMock, return_value="Workout Rotator"):
            r2 = client.post(
                "/event/confirm",
                json={"request_id": request_id, "choice": fake_low.candidates[0]},
                headers=AUTH,
            )

        assert r2.status_code == 200
        data = r2.json()
        assert data["status"] == "created"
        assert data["calendar"] == "Workout Rotator"

    def test_confirm_event_unknown_request_id_returns_404(self):
        resp = client.post(
            "/event/confirm",
            json={"request_id": "00000000-0000-0000-0000-000000000000", "choice": "anything"},
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_confirm_event_invalid_choice_returns_400(self):
        fake_low = _low_confidence_event()

        with patch("middleware.main.call_llm_event", new_callable=AsyncMock, return_value=fake_low):
            r1 = client.post("/event", json={"text": "séance sport vendredi"}, headers=AUTH)
        request_id = r1.json()["request_id"]

        r2 = client.post(
            "/event/confirm",
            json={"request_id": request_id, "choice": "option invalide"},
            headers=AUTH,
        )
        assert r2.status_code == 400

    def test_event_success_includes_calendar(self):
        fake = _confirmed_event()
        with patch("middleware.main.call_llm_event", new_callable=AsyncMock, return_value=fake), \
             patch("middleware.main.create_event", new_callable=AsyncMock, return_value="Workout Rotator"):
            resp = client.post("/event", json={"text": "séance sport vendredi à 9h"}, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert data["calendar"] == "Workout Rotator"

    def test_unknown_calendar_returns_400(self):
        fake = _confirmed_event(calendar="CalendrierFantôme")
        with patch("middleware.main.call_llm_event", new_callable=AsyncMock, return_value=fake):
            resp = client.post("/event", json={"text": "réunion dans un calendrier inconnu"}, headers=AUTH)

        assert resp.status_code == 400
        assert "Calendrier inconnu" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
