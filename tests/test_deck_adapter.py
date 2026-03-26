"""Unit tests for the Deck adapter (no real HTTP calls)."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from middleware.models import TaskOutput


def _deck_output(**kwargs) -> TaskOutput:
    defaults = dict(
        target_type="deck",
        title="Add dark mode",
        deck_board="Aboriginal Way",
        deck_stack="Backlog",
    )
    defaults.update(kwargs)
    return TaskOutput(**defaults)


class TestDeckAdapter:
    @pytest.mark.asyncio
    async def test_create_card_no_due_date(self):
        output = _deck_output()

        mock_response_boards = MagicMock()
        mock_response_boards.raise_for_status = MagicMock()
        mock_response_boards.json.return_value = [{"title": "Aboriginal Way", "id": 1}]

        mock_response_stacks = MagicMock()
        mock_response_stacks.raise_for_status = MagicMock()
        mock_response_stacks.json.return_value = [{"title": "Backlog", "id": 10}]

        mock_response_create = MagicMock()
        mock_response_create.raise_for_status = MagicMock()
        mock_response_create.json.return_value = {"id": 42}

        mock_client = MagicMock()
        mock_client.get.side_effect = [mock_response_boards, mock_response_stacks]
        mock_client.post.return_value = mock_response_create
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("middleware.adapters.deck._board_cache", {}), \
             patch("middleware.adapters.deck.httpx.Client", return_value=mock_client):
            from middleware.adapters.deck import create_card
            await create_card(output)

        mock_client.post.assert_called_once()
        mock_client.put.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_card_with_due_date(self):
        output = _deck_output(due_date=datetime(2026, 3, 28, 10, 0))

        mock_response_boards = MagicMock()
        mock_response_boards.raise_for_status = MagicMock()
        mock_response_boards.json.return_value = [{"title": "Aboriginal Way", "id": 1}]

        mock_response_stacks = MagicMock()
        mock_response_stacks.raise_for_status = MagicMock()
        mock_response_stacks.json.return_value = [{"title": "Backlog", "id": 10}]

        mock_response_create = MagicMock()
        mock_response_create.raise_for_status = MagicMock()
        mock_response_create.json.return_value = {"id": 42}

        mock_response_put = MagicMock()
        mock_response_put.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.side_effect = [mock_response_boards, mock_response_stacks]
        mock_client.post.return_value = mock_response_create
        mock_client.put.return_value = mock_response_put
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("middleware.adapters.deck._board_cache", {}), \
             patch("middleware.adapters.deck.httpx.Client", return_value=mock_client):
            from middleware.adapters.deck import create_card
            await create_card(output)

        mock_client.put.assert_called_once()
        call_kwargs = mock_client.put.call_args
        assert "duedate" in call_kwargs.kwargs["json"]

    @pytest.mark.asyncio
    async def test_unknown_board_raises(self):
        output = _deck_output(deck_board="Nonexistent Board")

        mock_response_boards = MagicMock()
        mock_response_boards.raise_for_status = MagicMock()
        mock_response_boards.json.return_value = [{"title": "Aboriginal Way", "id": 1}]

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response_boards
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("middleware.adapters.deck._board_cache", {}), \
             patch("middleware.adapters.deck.httpx.Client", return_value=mock_client):
            from middleware.adapters.deck import create_card
            with pytest.raises(ValueError, match="Board"):
                await create_card(output)
