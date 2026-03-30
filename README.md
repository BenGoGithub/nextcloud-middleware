# nextcloud-middleware

FastAPI middleware running on a VPS. Receives a natural-language sentence and creates a task in Nextcloud Tasks (CalDAV) or a card in Nextcloud Deck (REST API) based on detected context.

## Stack

- Python 3.12, FastAPI + Uvicorn
- Pydantic v2 + pydantic-settings
- anthropic SDK (structured output via `client.messages.parse()`)
- caldav-tasks-api, httpx, tenacity, cachetools

## Installation

```bash
cp .env.example .env   # fill in credentials
pip install -r requirements.txt
uvicorn middleware.main:app --reload
```

## Usage

```bash
POST /task
Content-Type: application/json

{"text": "Appeler le plombier jeudi pour la salle de bain"}
```

## Structure

```
middleware/
├── main.py          # FastAPI app, POST /task endpoint
├── llm.py           # LLM call + tenacity retries
├── prompt.py        # system prompt + routing rules
├── router.py        # dispatches to task or deck adapter
├── models.py        # Pydantic models
├── config.py        # pydantic-settings from .env
└── adapters/
    ├── tasks.py     # CalDAV task creation
    └── deck.py      # Deck card creation
```

<!-- Phase 6 validation - 2026-03-30 -->
