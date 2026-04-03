from __future__ import annotations

import base64
import logging
from typing import Any

import httpx
from cachetools import TTLCache

from middleware.config import settings
from middleware.models import TaskOutput
from middleware.schemas import DeckCardCreateInput

logger = logging.getLogger(__name__)

# TTL cache: boards/stacks loaded once per hour
_board_cache: TTLCache[str, dict[str, Any]] = TTLCache(maxsize=64, ttl=3600)

_HEADERS = {
    "OCS-APIRequest": "true",
    "Content-Type": "application/json",
}


def _auth_header() -> dict[str, str]:
    token = base64.b64encode(
        f"{settings.nextcloud_username}:{settings.nextcloud_password}".encode()
    ).decode()
    return {"Authorization": f"Basic {token}"}


def _base_url() -> str:
    return settings.nextcloud_url.rstrip("/") + "/index.php/apps/deck/api/v1.0"


def _load_boards(client: httpx.Client) -> dict[str, int]:
    """Return {board_name: board_id}."""
    if "boards" in _board_cache:
        return _board_cache["boards"]

    resp = client.get(f"{_base_url()}/boards")
    resp.raise_for_status()
    boards = {b["title"]: b["id"] for b in resp.json()}
    _board_cache["boards"] = boards
    return boards


def _load_stacks(client: httpx.Client, board_id: int) -> dict[str, int]:
    """Return {stack_name: stack_id} for a given board."""
    key = f"stacks_{board_id}"
    if key in _board_cache:
        return _board_cache[key]

    resp = client.get(f"{_base_url()}/boards/{board_id}/stacks")
    resp.raise_for_status()
    stacks = {s["title"]: s["id"] for s in resp.json()}
    _board_cache[key] = stacks
    return stacks


def _invalidate_board_cache() -> None:
    _board_cache.clear()


async def create_card(output: TaskOutput) -> None:
    headers = {**_HEADERS, **_auth_header()}

    with httpx.Client(headers=headers) as client:
        # Resolve board
        try:
            boards = _load_boards(client)
        except httpx.HTTPStatusError:
            _invalidate_board_cache()
            raise

        board_name = output.deck_board or ""
        board_id = boards.get(board_name)
        if board_id is None:
            raise ValueError(f"Board '{board_name}' not found. Available: {list(boards)}")

        # Resolve stack
        try:
            stacks = _load_stacks(client, board_id)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                _invalidate_board_cache()
            raise

        stack_name = output.deck_stack or "Backlog"
        stack_id = stacks.get(stack_name)
        if stack_id is None:
            raise ValueError(f"Stack '{stack_name}' not found. Available: {list(stacks)}")

        # Create card
        card_payload: dict[str, Any] = {
            "title": output.title,
            "description": output.description or "",
            "order": 999,
        }
        create_resp = client.post(
            f"{_base_url()}/boards/{board_id}/stacks/{stack_id}/cards",
            json=card_payload,
        )
        create_resp.raise_for_status()
        card = create_resp.json()
        card_id = card["id"]

        # Add due date via PUT (API limitation #4106)
        if output.due_date:
            due_ts = int(output.due_date.timestamp())
            update_resp = client.put(
                f"{_base_url()}/boards/{board_id}/stacks/{stack_id}/cards/{card_id}",
                json={**card_payload, "duedate": due_ts},
            )
            update_resp.raise_for_status()

        logger.info("Deck card created: board=%s stack=%s title=%r", board_name, stack_name, output.title)


async def create_card_by_ids(input: DeckCardCreateInput) -> None:
    """Create a Deck card using known board_id and stack_id directly (no name lookup)."""
    headers = {**_HEADERS, **_auth_header()}

    with httpx.Client(headers=headers) as client:
        card_payload: dict[str, Any] = {
            "title": input.title,
            "description": input.description or "",
            "order": 999,
        }
        create_resp = client.post(
            f"{_base_url()}/boards/{input.board_id}/stacks/{input.stack_id}/cards",
            json=card_payload,
        )
        create_resp.raise_for_status()
        card_id = create_resp.json()["id"]

        if input.due_at:
            due_ts = int(input.due_at.timestamp())
            update_resp = client.put(
                f"{_base_url()}/boards/{input.board_id}/stacks/{input.stack_id}/cards/{card_id}",
                json={**card_payload, "duedate": due_ts},
            )
            update_resp.raise_for_status()

        logger.info(
            "Deck card created by IDs: board_id=%s stack_id=%s title=%r",
            input.board_id, input.stack_id, input.title,
        )
