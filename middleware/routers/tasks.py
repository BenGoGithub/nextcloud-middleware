from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from middleware.adapters.deck import create_card_by_ids
from middleware.adapters.tasks import create_task
from middleware.config import settings
from middleware.models import TaskOutput, TaskResponse
from middleware.schemas import DeckCardCreateInput, StructuredTaskInput

logger = logging.getLogger(__name__)

_bearer = HTTPBearer()


def _verify_token(credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)]) -> None:
    if credentials.credentials != settings.api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


router = APIRouter()


@router.post("/task/structured", dependencies=[Depends(_verify_token)])
async def create_structured_task(request: StructuredTaskInput) -> TaskResponse:
    if request.target_system == "caldav":
        output = TaskOutput(
            target_type="task",
            title=request.title,
            description=request.description,
            due_date=request.due_at,
            nextcloud_list=request.calendar_id,
        )
        await create_task(output)
        due_str = output.due_date.date().isoformat() if output.due_date else None
        return TaskResponse(
            status="created",
            target_type="task",
            nextcloud_list=output.nextcloud_list,
            title=output.title,
            due_date=due_str,
        )

    # target_system == "deck"
    deck_input = DeckCardCreateInput(
        board_id=request.board_id,  # type: ignore[arg-type]  # validated by StructuredTaskInput
        stack_id=request.stack_id,  # type: ignore[arg-type]
        title=request.title,
        description=request.description,
        due_at=request.due_at,
    )
    await create_card_by_ids(deck_input)
    due_str = request.due_at.date().isoformat() if request.due_at else None
    return TaskResponse(
        status="created",
        target_type="deck",
        deck_board=str(request.board_id),
        deck_stack=str(request.stack_id),
        title=request.title,
        due_date=due_str,
    )
