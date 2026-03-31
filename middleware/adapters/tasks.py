from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

import caldav  # type: ignore[import]
from caldav_tasks_api import TaskData, TasksAPI  # type: ignore[import]

from middleware.config import settings
from middleware.models import TaskOutput

_VEVENT_TZ = "Europe/Paris"

logger = logging.getLogger(__name__)


def _get_api() -> TasksAPI:
    return TasksAPI(
        url=settings.caldav_url,
        username=settings.caldav_username,
        password=settings.caldav_password,
        nextcloud_mode=True,
    )


def _ical_due(dt: datetime) -> str:
    """Format a datetime as an iCalendar DUE string."""
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        return dt.strftime("%Y%m%d")
    return dt.strftime("%Y%m%dT%H%M%S")


def _find_list_uid(api: TasksAPI, list_name: str) -> str | None:
    for task_list in api.task_lists:
        if task_list.name.lower() == list_name.lower():
            return task_list.uid
    return None


async def create_task(output: TaskOutput) -> None:
    api = _get_api()
    api.load_remote_data()

    list_uid = _find_list_uid(api, output.nextcloud_list or "")
    if list_uid is None:
        available = [tl.name for tl in api.task_lists]
        raise ValueError(
            f"Nextcloud list '{output.nextcloud_list}' not found. Available: {available}"
        )

    task = TaskData(
        summary=output.title,
        description=output.description or "",
        due_date=_ical_due(output.due_date) if output.due_date else "",
        priority=output.priority or 0,
    )
    api.add_task(task, list_uid=list_uid)
    logger.info("CalDAV task created: list=%s title=%r", output.nextcloud_list, output.title)

    if output.needs_calendar_event and output.due_date:
        try:
            _create_vevent(output)
        except Exception as exc:
            logger.warning("VEVENT creation skipped: %s", exc)


def _create_vevent(output: TaskOutput) -> None:
    """Create a companion VEVENT in the matching calendar using the raw caldav library."""
    due: datetime = output.due_date  # type: ignore[assignment]

    client = caldav.DAVClient(
        url=settings.caldav_url,
        username=settings.caldav_username,
        password=settings.caldav_password,
    )
    principal = client.principal()

    target_cal = None
    for cal in principal.calendars():
        if cal.name.lower() == (output.nextcloud_list or "").lower():
            target_cal = cal
            break

    if target_cal is None:
        logger.warning("VEVENT skipped: calendar '%s' not found", output.nextcloud_list)
        return

    uid = str(uuid.uuid4())
    dtstamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dtstart = due.strftime("%Y%m%dT%H%M%S")
    # Give a 1-hour duration when the time is set; all-day events keep same start/end date
    if due.hour != 0 or due.minute != 0:
        dtend = (due + timedelta(hours=1)).strftime("%Y%m%dT%H%M%S")
    else:
        dtend = dtstart

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//nextcloud-middleware//EN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;TZID={_VEVENT_TZ}:{dtstart}",
        f"DTEND;TZID={_VEVENT_TZ}:{dtend}",
        f"SUMMARY:{output.title}",
    ]
    if output.description:
        lines.append(f"DESCRIPTION:{output.description}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    ical = "\r\n".join(lines) + "\r\n"

    target_cal.add_event(ical)
    logger.info("CalDAV VEVENT created: calendar=%s title=%r", output.nextcloud_list, output.title)
