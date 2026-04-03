"""Tests for POST /task/structured."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from middleware.adapters.deck import _to_paris_timestamp
from middleware.main import app

client = TestClient(app, raise_server_exceptions=True)
AUTH = {"Authorization": "Bearer test-token"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _caldav_payload(**kwargs) -> dict:
    base = {
        "intent": "create_task",
        "target_system": "caldav",
        "title": "Appeler le dentiste",
        "calendar_id": "Santé",
    }
    base.update(kwargs)
    return base


def _deck_payload(**kwargs) -> dict:
    base = {
        "intent": "create_task",
        "target_system": "deck",
        "title": "Fix dark mode",
        "board_id": 1,
        "stack_id": 10,
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestStructuredEndpointAuth:
    def test_missing_auth_returns_401(self):
        resp = client.post("/task/structured", json=_caldav_payload())
        assert resp.status_code == 401

    def test_wrong_token_returns_401(self):
        resp = client.post(
            "/task/structured",
            json=_caldav_payload(),
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# CalDAV path
# ---------------------------------------------------------------------------

class TestStructuredEndpointCaldav:
    def test_caldav_task_created(self):
        with patch("middleware.routers.tasks.create_task", new_callable=AsyncMock) as mock_ct:
            resp = client.post("/task/structured", json=_caldav_payload(), headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert data["target_type"] == "task"
        assert data["nextcloud_list"] == "Santé"
        assert data["title"] == "Appeler le dentiste"
        mock_ct.assert_awaited_once()

    def test_caldav_missing_calendar_id_returns_422(self):
        payload = _caldav_payload()
        del payload["calendar_id"]
        resp = client.post("/task/structured", json=payload, headers=AUTH)
        assert resp.status_code == 422

    def test_caldav_due_date_in_response(self):
        with patch("middleware.routers.tasks.create_task", new_callable=AsyncMock):
            resp = client.post(
                "/task/structured",
                json=_caldav_payload(due_at="2026-06-15T09:30:00"),
                headers=AUTH,
            )
        assert resp.status_code == 200
        assert resp.json()["due_date"] == "2026-06-15"

    def test_caldav_no_due_date(self):
        with patch("middleware.routers.tasks.create_task", new_callable=AsyncMock):
            resp = client.post("/task/structured", json=_caldav_payload(), headers=AUTH)
        assert resp.json()["due_date"] is None


# ---------------------------------------------------------------------------
# Deck path
# ---------------------------------------------------------------------------

class TestStructuredEndpointDeck:
    def test_deck_card_created(self):
        with patch("middleware.routers.tasks.create_card_by_ids", new_callable=AsyncMock) as mock_cc:
            resp = client.post("/task/structured", json=_deck_payload(), headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert data["target_type"] == "deck"
        assert data["deck_board"] == "1"
        assert data["deck_stack"] == "10"
        assert data["title"] == "Fix dark mode"
        mock_cc.assert_awaited_once()

    def test_deck_missing_board_id_returns_422(self):
        payload = _deck_payload()
        del payload["board_id"]
        resp = client.post("/task/structured", json=payload, headers=AUTH)
        assert resp.status_code == 422

    def test_deck_missing_stack_id_returns_422(self):
        payload = _deck_payload()
        del payload["stack_id"]
        resp = client.post("/task/structured", json=payload, headers=AUTH)
        assert resp.status_code == 422

    def test_deck_due_date_in_response(self):
        with patch("middleware.routers.tasks.create_card_by_ids", new_callable=AsyncMock):
            resp = client.post(
                "/task/structured",
                json=_deck_payload(due_at="2026-06-15T09:30:00"),
                headers=AUTH,
            )
        assert resp.status_code == 200
        assert resp.json()["due_date"] == "2026-06-15"

    def test_deck_create_card_by_ids_receives_correct_input(self):
        with patch("middleware.routers.tasks.create_card_by_ids", new_callable=AsyncMock) as mock_cc:
            client.post(
                "/task/structured",
                json=_deck_payload(description="Ajouter toggle sombre"),
                headers=AUTH,
            )
        call_arg = mock_cc.call_args.args[0]
        assert call_arg.board_id == 1
        assert call_arg.stack_id == 10
        assert call_arg.description == "Ajouter toggle sombre"


# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------

class TestTimezone:
    def test_to_paris_timestamp_naive_differs_from_utc_by_offset(self):
        """Naive datetime is treated as Europe/Paris (CEST = UTC+2 in summer)."""
        dt_naive = datetime(2026, 6, 15, 9, 30)
        dt_utc = datetime(2026, 6, 15, 9, 30, tzinfo=ZoneInfo("UTC"))
        ts_paris = _to_paris_timestamp(dt_naive)
        ts_utc = _to_paris_timestamp(dt_utc)
        assert ts_utc - ts_paris == 7200  # CEST offset

    def test_to_paris_timestamp_aware_not_re_localized(self):
        dt = datetime(2026, 6, 15, 9, 30, tzinfo=ZoneInfo("Europe/Paris"))
        assert _to_paris_timestamp(dt) == int(dt.timestamp())
