from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from middleware.adapters.events import create_event
from middleware.config import settings
from middleware.llm import call_llm, call_llm_event
from middleware.models import EventResponse, TaskRequest, TaskResponse
from middleware.router import dispatch

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Nextcloud Middleware", version="0.1.0")


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(httpx.HTTPStatusError)
async def http_status_error_handler(request: Request, exc: httpx.HTTPStatusError) -> JSONResponse:
    logging.warning("Backend HTTP error: %s", exc)
    return JSONResponse(status_code=502, content={"detail": "Backend unavailable"})

_bearer = HTTPBearer()


def _verify_token(credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)]) -> None:
    if credentials.credentials != settings.api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


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


@app.post("/event", response_model=EventResponse, dependencies=[Depends(_verify_token)])
async def create_event_endpoint(request: TaskRequest) -> EventResponse:
    output = await call_llm_event(request.text)
    await create_event(output)

    return EventResponse(
        status="created",
        title=output.title,
        start=output.start.isoformat(),
        end=output.end.isoformat() if output.end else None,
        location=output.location,
        confidence=output.confidence,
    )
