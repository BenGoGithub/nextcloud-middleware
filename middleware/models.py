from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class TaskOutput(BaseModel):
    target_type: Literal["task", "deck"]
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[int] = None        # CalDAV: 1-9
    nextcloud_list: Optional[str] = None  # e.g. "Alternance", "Veille"
    deck_board: Optional[str] = None      # e.g. "Aboriginal Way"
    deck_stack: Optional[str] = None      # e.g. "Backlog"
    needs_calendar_event: bool = False
    confidence: float = 1.0
    notes: Optional[str] = None


class EventOutput(BaseModel):
    title: str
    description: Optional[str] = None
    start: datetime                        # DTSTART — required
    end: Optional[datetime] = None        # DTEND — defaults to start + 1h if absent
    location: Optional[str] = None
    timezone: str = "Europe/Paris"
    confidence: float = 1.0
    notes: Optional[str] = None


class TaskRequest(BaseModel):
    text: str


class TaskResponse(BaseModel):
    status: str
    target_type: str
    nextcloud_list: Optional[str] = None
    deck_board: Optional[str] = None
    deck_stack: Optional[str] = None
    title: str
    due_date: Optional[str] = None


class EventResponse(BaseModel):
    status: str
    title: str
    start: str
    end: Optional[str] = None
    location: Optional[str] = None
    confidence: float


class ClarificationResponse(BaseModel):
    status: Literal["clarification_needed"]
    question: str
    confidence: float
