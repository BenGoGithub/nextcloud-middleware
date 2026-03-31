"""Unit tests for LLM routing and dispatch logic."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from middleware.models import TaskOutput
from middleware.router import dispatch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _task_output(**kwargs) -> TaskOutput:
    defaults = dict(
        target_type="task",
        title="Test task",
        nextcloud_list="Perso",
    )
    defaults.update(kwargs)
    return TaskOutput(**defaults)


def _deck_output(**kwargs) -> TaskOutput:
    defaults = dict(
        target_type="deck",
        title="Test card",
        deck_board="Aboriginal Way",
        deck_stack="Backlog",
    )
    defaults.update(kwargs)
    return TaskOutput(**defaults)


# ---------------------------------------------------------------------------
# TaskOutput model validation
# ---------------------------------------------------------------------------

class TestTaskOutputModel:
    def test_task_defaults(self):
        out = _task_output()
        assert out.target_type == "task"
        assert out.needs_calendar_event is False
        assert out.due_date is None
        assert out.priority is None

    def test_deck_defaults(self):
        out = _deck_output()
        assert out.target_type == "deck"
        assert out.deck_board == "Aboriginal Way"
        assert out.deck_stack == "Backlog"

    def test_due_date_parsed(self):
        out = _task_output(due_date=datetime(2026, 3, 28, 9, 0))
        assert out.due_date.year == 2026

    def test_invalid_target_type(self):
        with pytest.raises(Exception):
            TaskOutput(target_type="invalid", title="x")


# ---------------------------------------------------------------------------
# Router dispatch
# ---------------------------------------------------------------------------

class TestDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_task(self):
        output = _task_output()
        with patch("middleware.router.create_task", new_callable=AsyncMock) as mock_ct:
            await dispatch(output)
            mock_ct.assert_awaited_once_with(output)

    @pytest.mark.asyncio
    async def test_dispatch_deck(self):
        output = _deck_output()
        with patch("middleware.router.create_card", new_callable=AsyncMock) as mock_cc:
            await dispatch(output)
            mock_cc.assert_awaited_once_with(output)

    @pytest.mark.asyncio
    async def test_dispatch_unknown_raises(self):
        output = _task_output()
        object.__setattr__(output, "target_type", "unknown")
        with pytest.raises(ValueError, match="Unknown target_type"):
            await dispatch(output)


# ---------------------------------------------------------------------------
# LLM call (mocked Anthropic response)
# ---------------------------------------------------------------------------

class TestCallLLM:
    @pytest.mark.asyncio
    async def test_call_llm_task(self):
        fake_output = TaskOutput(
            target_type="task",
            title="Préparer slides",
            nextcloud_list="Alternance",
        )
        fake_message = MagicMock()
        fake_message.parsed_output = fake_output

        with patch("middleware.llm._client") as mock_client:
            mock_client.messages.parse.return_value = fake_message
            from middleware.llm import call_llm
            result = await call_llm("prépare les slides pour la soutenance")

        assert result.target_type == "task"
        assert result.nextcloud_list == "Alternance"
        assert result.title == "Préparer slides"

    @pytest.mark.asyncio
    async def test_call_llm_deck(self):
        fake_output = TaskOutput(
            target_type="deck",
            title="Fix login bug",
            deck_board="Aboriginal Way",
            deck_stack="Backlog",
        )
        fake_message = MagicMock()
        fake_message.parsed_output = fake_output

        with patch("middleware.llm._client") as mock_client:
            mock_client.messages.parse.return_value = fake_message
            from middleware.llm import call_llm
            result = await call_llm("fix the login bug on the site")

        assert result.target_type == "deck"
        assert result.deck_board == "Aboriginal Way"
