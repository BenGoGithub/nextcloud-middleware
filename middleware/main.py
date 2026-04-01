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
from middleware.prompt import ACTIVE_CALENDARS
from middleware.models import (
    ClarificationResponse,
    ConfirmRequest,
    EventResponse,
    TaskRequest,
    TaskResponse,
)
from middleware.router import dispatch
from middleware.store import pending_store

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Nextcloud Middleware", version="0.1.0")

CONFIDENCE_THRESHOLD = 0.7


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


@app.post("/task", dependencies=[Depends(_verify_token)])
async def create_task_endpoint(request: TaskRequest) -> TaskResponse | ClarificationResponse:
    output = await call_llm(request.text)

    if output.confidence < CONFIDENCE_THRESHOLD:
        request_id = pending_store.save(output)
        return ClarificationResponse(
            status="clarification_needed",
            request_id=request_id,
            question="Je n'ai pas bien compris. Que vouliez-vous dire ?",
            options=output.candidates,
            confidence=output.confidence,
        )

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


@app.post("/task/confirm", dependencies=[Depends(_verify_token)])
async def confirm_task_endpoint(request: ConfirmRequest) -> TaskResponse:
    stored = pending_store.pop(request.request_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="request_id inconnu ou expiré")
    if request.choice not in stored.candidates:
        raise ValueError("Choix invalide — ne correspond pas aux options proposées")

    output = await call_llm(request.choice)
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


@app.post("/event", dependencies=[Depends(_verify_token)])
async def create_event_endpoint(request: TaskRequest) -> EventResponse | ClarificationResponse:
    output = await call_llm_event(request.text)

    if output.confidence < CONFIDENCE_THRESHOLD:
        request_id = pending_store.save(output)
        return ClarificationResponse(
            status="clarification_needed",
            request_id=request_id,
            question="Je n'ai pas bien compris. Que vouliez-vous dire ?",
            options=output.candidates,
            confidence=output.confidence,
        )

    if output.calendar is not None and output.calendar not in ACTIVE_CALENDARS:
        raise ValueError(f"Calendrier inconnu : {output.calendar}")

    calendar_used = await create_event(output)

    return EventResponse(
        status="created",
        title=output.title,
        start=output.start.isoformat(),
        end=output.end.isoformat() if output.end else None,
        location=output.location,
        calendar=calendar_used,
        confidence=output.confidence,
    )


@app.post("/event/confirm", dependencies=[Depends(_verify_token)])
async def confirm_event_endpoint(request: ConfirmRequest) -> EventResponse:
    stored = pending_store.pop(request.request_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="request_id inconnu ou expiré")
    if request.choice not in stored.candidates:
        raise ValueError("Choix invalide — ne correspond pas aux options proposées")

    output = await call_llm_event(request.choice)
    if output.calendar is not None and output.calendar not in ACTIVE_CALENDARS:
        raise ValueError(f"Calendrier inconnu : {output.calendar}")

    calendar_used = await create_event(output)

    return EventResponse(
        status="created",
        title=output.title,
        start=output.start.isoformat(),
        end=output.end.isoformat() if output.end else None,
        location=output.location,
        calendar=calendar_used,
        confidence=output.confidence,
    )
