"""Unit tests for the FastAPI /task endpoint."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from middleware.main import app
from middleware.models import TaskOutput

client = TestClient(app, raise_server_exceptions=True)


class TestTaskEndpoint:
    def _auth(self) -> dict:
        return {"Authorization": "Bearer test-token"}

    def test_missing_auth_returns_401(self):
        resp = client.post("/task", json={"text": "do something"})
        assert resp.status_code == 401

    def test_wrong_token_returns_401(self):
        resp = client.post(
            "/task",
            json={"text": "do something"},
            headers={"Authorization": "Bearer wrong"},
        )
        assert resp.status_code == 401

    def test_create_task_success(self):
        fake_output = TaskOutput(
            target_type="task",
            title="Préparer slides",
            nextcloud_list="Alternance",
        )
        with patch("middleware.main.call_llm", new_callable=AsyncMock, return_value=fake_output), \
             patch("middleware.main.dispatch", new_callable=AsyncMock):
            resp = client.post(
                "/task",
                json={"text": "prépare les slides soutenance vendredi"},
                headers=self._auth(),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert data["target_type"] == "task"
        assert data["nextcloud_list"] == "Alternance"
        assert data["title"] == "Préparer slides"

    def test_create_deck_card_success(self):
        fake_output = TaskOutput(
            target_type="deck",
            title="Fix login bug",
            deck_board="Aboriginal Way",
            deck_stack="Backlog",
            due_date=datetime(2026, 3, 28, 10, 0),
        )
        with patch("middleware.main.call_llm", new_callable=AsyncMock, return_value=fake_output), \
             patch("middleware.main.dispatch", new_callable=AsyncMock):
            resp = client.post(
                "/task",
                json={"text": "fix the login bug"},
                headers=self._auth(),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["target_type"] == "deck"
        assert data["deck_board"] == "Aboriginal Way"
        assert data["due_date"] == "2026-03-28"
