from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, model_validator


class DeckCardCreateInput(BaseModel):
    """Typed input for direct Deck card creation with known board/stack IDs."""

    board_id: int
    stack_id: int
    title: str
    description: Optional[str] = None
    due_at: Optional[datetime] = None


class StructuredTaskInput(BaseModel):
    """Input schema for POST /task/structured.

    Consumed by Claude (claude.ai) acting as the upstream semantic layer.
    No LLM call is made server-side — routing is deterministic.
    """

    intent: Literal["create_task", "create_event"]
    target_system: Literal["caldav", "deck"]
    title: str
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    start_at: Optional[datetime] = None
    timezone: str = "UTC"
    labels: List[str] = []
    board_id: Optional[int] = None    # required when target_system="deck"
    stack_id: Optional[int] = None    # required when target_system="deck"
    calendar_id: Optional[str] = None  # required when target_system="caldav"
    confidence: Optional[float] = None

    @model_validator(mode="after")
    def _check_target_fields(self) -> "StructuredTaskInput":
        if self.target_system == "deck":
            if self.board_id is None:
                raise ValueError("board_id is required when target_system='deck'")
            if self.stack_id is None:
                raise ValueError("stack_id is required when target_system='deck'")
        elif self.target_system == "caldav":
            if self.calendar_id is None:
                raise ValueError("calendar_id is required when target_system='caldav'")
        return self
