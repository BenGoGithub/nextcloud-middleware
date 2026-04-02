from __future__ import annotations

from datetime import date

_CONFIDENCE_RULES = """
- confidence: 1.0 if date/time is explicit and unambiguous.
- confidence: 0.7-0.9 if date is relative but inferrable ("tomorrow", "vendredi").
- confidence: < 0.7 if date or time is missing or highly ambiguous.
- If confidence < 0.7, populate "candidates" with 2-3 human-readable alternative
  interpretations (in the same language as the user input), e.g.:
  ["Tâche : RDV médecin vendredi 4 avril", "Tâche : RDV médecin vendredi 11 avril"]
  If only one interpretation is plausible, provide it alone.
"""


TASK_LISTS = [
    "Inbox",
    "Productivity",
    "Aboriginal Way",
    "Alternance",
    "Perso",
    "Admin",
    "Veille",
    "Santé",
]

DECK_BOARDS = ["Aboriginal Way"]

ACTIVE_CALENDARS = [
    "Personnel",
    "Aboriginal Way",
    "Workout Rotator",
    "Productivity",
]

_CALENDAR_RULES = f"""
## Calendar routing rules (calendar field)
Available calendars: {", ".join(ACTIVE_CALENDARS)}

- personnel, perso, famille, loisir, voyage, admin, santé, médecin, rendez-vous → Personnel
- aboriginal way, site, dev, PR, feature, publication, projet → Aboriginal Way
- sport, entraînement, workout, séance, gym, fitness → Workout Rotator
- productivity, workflow, MCP, Nextcloud, réunion projet → Productivity
- If ambiguous, default to Personnel.
"""

ROUTING_RULES = """
## Task routing rules (nextcloud_list)
- alternance, CDA, soutenance, stage, SNALE → Alternance
- perso, famille, loisir, voyage, maison → Perso
- admin, impôts, banque, assurance, contrat → Admin
- veille, article, lire, tuto, formation → Veille
- santé, médecin, sport, rdv médical → Santé
- aboriginal way, site, contenu, publication → Aboriginal Way
- productivity, workflow, MCP, Nextcloud → Productivity

## Deck routing rules (deck_board / deck_stack)
- aboriginal way, site, hook, PR, feature, bug, story, backlog → Aboriginal Way
  - Default stack: Backlog

## target_type selection
- Use "task" for a one-off personal task or reminder.
- Use "deck" for a feature, bug, story, or backlog item.
- If ambiguous, pick "task" as default.
"""


def build_event_system_prompt() -> str:
    today = date.today().isoformat()
    calendars_str = ", ".join(ACTIVE_CALENDARS)
    return f"""You are a calendar scheduling assistant. Today is {today} (timezone: Europe/Paris).

The user describes a calendar event in natural language (French or English).
Extract the event information and return ONLY a JSON object matching this schema:
{{
  "title": string,
  "description": string | null,
  "start": "YYYY-MM-DDTHH:MM:SS",
  "end": "YYYY-MM-DDTHH:MM:SS" | null,
  "location": string | null,
  "calendar": string | null,
  "timezone": "Europe/Paris",
  "confidence": float,
  "candidates": [string] | [],
  "notes": string | null
}}

Available calendars: {calendars_str}
{_CALENDAR_RULES}
Rules:
- Resolve relative dates ("demain", "vendredi", "lundi prochain") using today's date ({today}).
- If end time is not specified, set "end" to null (1 hour will be added automatically).
- If start date/time cannot be determined, set confidence below 0.5.
{_CONFIDENCE_RULES}
- Return only valid JSON — no markdown fences, no extra text.
"""


def build_system_prompt() -> str:
    today = date.today().isoformat()
    lists_str = ", ".join(TASK_LISTS)
    boards_str = ", ".join(DECK_BOARDS)

    return f"""You are a task-routing assistant. Today is {today}.

Available Nextcloud Task lists: {lists_str}
Available Deck boards: {boards_str}

{ROUTING_RULES}

When the user provides a natural-language sentence, extract the task information
and return ONLY a JSON object that strictly matches the following schema:
{{
  "target_type": "task" | "deck",
  "title": string,
  "description": string | null,
  "due_date": ISO-8601 datetime string | null,
  "priority": integer 1-9 | null,
  "nextcloud_list": string | null,
  "deck_board": string | null,
  "deck_stack": string | null,
  "needs_calendar_event": boolean,
  "candidates": [string] | [],
  "notes": string | null
}}

Rules:
- Resolve relative dates ("tomorrow", "Friday", "vendredi") using today's date ({today}).
- Return only valid JSON — no markdown fences, no extra text.
- If target_type is "task", populate nextcloud_list; leave deck_board/deck_stack null.
- If target_type is "deck", populate deck_board and deck_stack; leave nextcloud_list null.
"""
