# Audit & VEVENT implementation — March 2026

## Context

Pre-implementation audit of `nextcloud-middleware` before extending CalDAV support
to calendar events (VEVENT), complementing the existing task (VTODO) and Deck card flows.

Date: 2026-03-31
Branch: `claude/audit-nextcloud-middleware-32bUC`
Commit: `0ac4ea3`

---

## Gaps identified

Six gaps were identified during the audit. All were addressed in a single commit.

### Gap 1 — VEVENT support absent

`llm.py`, `models.py`, `prompt.py`, `main.py`, `adapters/`

No `/event` endpoint existed. The only partial VEVENT path was via
`needs_calendar_event=true` on a `TaskOutput`, but the helper `_create_vevent()`
was RFC non-compliant (see Gap 3). No `EventOutput` model, no dedicated LLM prompt,
no routing.

**Fix:** see *Changes* section below.

### Gap 2 — No ambiguity / confidence mechanism

`llm.py`, `models.py`, `prompt.py`

`TaskOutput` had no `confidence` field. Ambiguous input was silently routed to
`target_type="task"` with no feedback to the caller.

**Fix (partial):** `confidence: float = 1.0` added to both `TaskOutput` and
`EventOutput`; exposed in `TaskResponse` and `EventResponse`. The `202 +
clarification_needed` flow (return a question when `confidence < 0.7`) is a
conscious deferral — decision required before implementation.

### Gap 3 — Naive datetimes in `_create_vevent`

`middleware/adapters/tasks.py`

`_create_vevent()` produced RFC 5545-invalid iCalendar:
- No `UID` property (required by RFC 5545 §3.8.4.7)
- No `DTSTAMP` property (required by RFC 5545 §3.8.7.2)
- Datetime strings without `TZID` parameter (naive local time, rejected by Nextcloud — issue #48598)
- `DTEND` equal to `DTSTART` (zero-duration event)
- Lines separated by `\n` instead of RFC 5545-mandated `\r\n`

**Fix:** `_create_vevent` now generates:
```
UID:<uuid4>
DTSTAMP:<UTC timestamp>Z
DTSTART;TZID=Europe/Paris:<local datetime>
DTEND;TZID=Europe/Paris:<local datetime + 1h if timed, same if all-day>
```
All lines use `\r\n`.

### Gap 4 — Unhandled exceptions propagate as HTTP 500

`middleware/main.py`

`ValueError` (unknown Nextcloud list, unknown Deck board/stack) and
`httpx.HTTPStatusError` (Deck API unavailable) were not caught, resulting in
unstructured 500 responses. No `/health` endpoint existed.

**Fix:**
- `@app.exception_handler(ValueError)` → HTTP 400 with `{"detail": "..."}`
- `@app.exception_handler(httpx.HTTPStatusError)` → HTTP 502 with `{"detail": "Backend unavailable"}`
- `GET /health` → `{"status": "ok"}` (no auth required)

### Gap 5 — LLM tests mocked the wrong method

`tests/test_routing.py`

`TestCallLLM` patched `mock_client.messages.create` and inspected
`message.content[0].text`, but `llm.py` calls `_client.messages.parse()` and
reads `message.parsed_output`. The tests passed only because the mock short-circuited
before reaching the actual parse path.

**Fix:** both test cases now patch `messages.parse` and return a `MagicMock` with
`.parsed_output` set to a real `TaskOutput` instance.

### Gap 6 — Anthropic SDK version constraint too loose

`requirements.txt`

`anthropic>=0.26.0` allowed installing versions that predate `messages.parse()`.
The `output_format=` parameter used in `llm.py` requires SDK ≥ 0.86.0.

**Fix:** `anthropic>=0.86.0`

---

## Changes

### New files

#### `middleware/adapters/events.py`

RFC 5545-compliant VEVENT creation via raw `caldav` library.

- `create_event(output: EventOutput)` — async, writes to the first
  VEVENT-capable CalDAV calendar found on the principal.
- `_fmt_local(dt, tz_name)` — converts a naive or aware `datetime` to
  iCalendar local-time format for use with `DTSTART;TZID=`.
- `_find_vevent_calendar(principal)` — iterates calendars, calls
  `get_supported_components()` to skip task-only collections, falls back
  gracefully if the method is unavailable.

Generated iCalendar skeleton:

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//nextcloud-middleware//EN
BEGIN:VEVENT
UID:<uuid4>
DTSTAMP:<UTC>Z
DTSTART;TZID=Europe/Paris:<local>
DTEND;TZID=Europe/Paris:<local + 1h>
SUMMARY:<title>
DESCRIPTION:<description>        (if present)
LOCATION:<location>              (if present)
END:VEVENT
END:VCALENDAR
```

### Modified files

#### `middleware/models.py`

Added:
- `EventOutput` — LLM output schema for calendar events:
  `title`, `description`, `start` (required), `end` (optional, defaults to
  `start + 1h`), `location`, `timezone`, `confidence`, `notes`
- `EventResponse` — HTTP response schema for `POST /event`
- `confidence: float = 1.0` field on `TaskOutput`

#### `middleware/prompt.py`

Added `build_event_system_prompt()`:
- Instructs the LLM to resolve relative French/English dates
- Defines the `EventOutput` JSON schema expected in the response
- Includes `_CONFIDENCE_RULES` (shared constant) documenting the confidence scale

#### `middleware/llm.py`

Added `call_llm_event(text: str) -> EventOutput`:
- Same tenacity retry decorator as `call_llm` (3 attempts, exponential backoff)
- Uses `messages.parse()` with `output_format=EventOutput`

#### `middleware/main.py`

- `GET /health` — public health check
- `POST /event` — protected by Bearer token; calls `call_llm_event()` then
  `create_event()`; returns `EventResponse`
- `@app.exception_handler(ValueError)` → 400
- `@app.exception_handler(httpx.HTTPStatusError)` → 502

#### `middleware/adapters/tasks.py`

`_create_vevent()` rewritten:
- Added `import uuid`, `timedelta`, `timezone` (stdlib)
- Generates `UID`, `DTSTAMP`, `DTSTART;TZID`, `DTEND` (start + 1h when timed)
- CRLF line endings throughout

#### `tests/test_routing.py`

`TestCallLLM` — both test cases updated to mock `messages.parse` and return
`fake_message.parsed_output = TaskOutput(...)`.

#### `requirements.txt`

`anthropic>=0.86.0`

---

## Endpoint summary (post-audit)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health` | GET | None | Service liveness check |
| `/task` | POST | Bearer | Create VTODO or Deck card via LLM routing |
| `/event` | POST | Bearer | Create VEVENT in CalDAV calendar |

---

## Known limitations and deferred decisions

### Gap 2 — Confidence-based clarification flow

`confidence` is now returned in all responses. The intended behaviour when
`confidence < 0.7` (return `200 {"status": "clarification_needed", "question": "..."}`)
has not been implemented. It requires:

1. Decision on the threshold value (0.7 suggested)
2. A second LLM call to generate the clarifying question, or a static template
3. Client-side handling of the new response shape

### Calendar selection for VEVENT

`_find_vevent_calendar()` currently picks the **first** calendar that advertises
`VEVENT` support. For users with multiple calendars (personal, work, etc.) this
may not be the desired target. A `CALDAV_DEFAULT_CALENDAR` setting or a
`calendar` field on `EventOutput` (populated by the LLM from context) would
address this.

### RFC 4791 — mixed-component collections

Nextcloud Tasks (VTODO collections) reject VEVENT objects (Nextcloud issue #41014).
The existing `_create_vevent()` in `tasks.py` searches for a *calendar* by name
matching `nextcloud_list`. If the names differ, the VEVENT is silently skipped.
The new `/event` endpoint avoids this by targeting any VEVENT-capable calendar
directly.

---

## References

| Source | Reference |
|---|---|
| RFC 5545 — iCalendar | https://datatracker.ietf.org/doc/html/rfc5545 |
| RFC 4791 — CalDAV | https://www.rfc-editor.org/rfc/rfc4791.html |
| python-caldav issue #187 (timezone) | https://github.com/python-caldav/caldav/issues/187 |
| Nextcloud issue #48598 (timezone CalDAV) | https://github.com/nextcloud/server/issues/48598 |
| Nextcloud issue #41014 (VTODO task list) | https://github.com/nextcloud/server/issues/41014 |
