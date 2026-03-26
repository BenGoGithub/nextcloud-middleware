# nextcloud-middleware — CLAUDE.md

## Project overview
FastAPI service on the VPS. Receives a natural-language sentence,
creates a task in Nextcloud Tasks (CalDAV) or a card in Nextcloud Deck
(REST API) based on detected context.

## Stack
- FastAPI + Uvicorn
- Pydantic v2 + pydantic-settings
- anthropic SDK (structured JSON output via **client.messages.parse()**)
- caldav-tasks-api (CalDAV Tasks)
- httpx (Deck REST API)
- tenacity (LLM retries)
- cachetools TTLCache (Deck board/stack IDs, TTL=1h)

## Key files
- `middleware/main.py` — FastAPI app, POST /task endpoint
- `middleware/llm.py` — LLM call with tenacity retries
- `middleware/prompt.py` — system prompt + routing rules
- `middleware/router.py` — dispatches TaskOutput to task or deck adapter
- `middleware/adapters/tasks.py` — CalDAV task (and optional VEVENT) creation
- `middleware/adapters/deck.py` — Deck card creation (2-step PUT for duedate)
- `middleware/models.py` — TaskOutput, TaskRequest, TaskResponse
- `middleware/config.py` — pydantic-settings from .env

## LLM call
Use `client.messages.parse()` (not `client.messages.create`) in `middleware/llm.py`
to benefit from native Anthropic Pydantic validation on the structured output.

## Routing keyword rules
Source of truth: `TASK_ROUTING.md` in the Productivity repo.
The `ROUTING_RULES` constant in `middleware/prompt.py` must stay in sync with it.

Active Deck board: **Aboriginal Way** (only).
SNALE is NOT a Deck board — SNALE-related tasks go to Nextcloud Tasks (CalDAV).

## Deck API notes
- Board/stack IDs are cached (TTLCache, 1h). Cache is invalidated on 404.
- Due date requires a second PUT request (upstream issue #4106).
- Headers required: `OCS-APIRequest: true`, `Authorization: Basic`.

## Running locally
```
cp .env.example .env   # fill in credentials
pip install -r requirements.txt
uvicorn middleware.main:app --reload
```

## Git workflow
Feature branch → `feature/middleware-nlp` → `actualisation` → `main`
Conventional commits in English.
No Co-Authored-By trailer in commit messages.
