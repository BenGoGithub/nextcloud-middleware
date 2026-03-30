from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from middleware.config import settings
from middleware.llm import call_llm
from middleware.models import TaskRequest, TaskResponse
from middleware.router import dispatch

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Nextcloud Middleware", version="0.1.0")

_bearer = HTTPBearer()


def _verify_token(credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)]) -> None:
    if credentials.credentials != settings.api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@app.post("/task", response_model=TaskResponse, dependencies=[Depends(_verify_token)])
async def create_task_endpoint(request: TaskRequest) -> TaskResponse:
    output = await call_llm(request.text)
    await dispatch(output)

    due_str = output.due_date.date().isoformat() if output.due_date else None

    return TaskResponse(
        status="created",
        target_type=output.target_type,
        nextcloud_list=output.nextcloud_list,
        deck_board=output.deck_board,
        deck_stack=output.deck_stack,
        title=output.title,
        due_date=due_str,
    )
