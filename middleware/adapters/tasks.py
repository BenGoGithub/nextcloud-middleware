from __future__ import annotations

import logging
from datetime import datetime

import caldav  # type: ignore[import]
from caldav_tasks_api import TaskData, TasksAPI  # type: ignore[import]

from middleware.config import settings
from middleware.models import TaskOutput

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
    """Create a VEVENT in the matching calendar using the raw caldav library."""
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

    dtstart = due.strftime("%Y%m%dT%H%M%S")
    description_line = (
        f"DESCRIPTION:{output.description}\n" if output.description else ""
    )
    ical = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "BEGIN:VEVENT\n"
        f"SUMMARY:{output.title}\n"
        f"DTSTART:{dtstart}\n"
        f"DTEND:{dtstart}\n"
        f"{description_line}"
        "END:VEVENT\n"
        "END:VCALENDAR\n"
    )
    target_cal.add_event(ical)
    logger.info("CalDAV VEVENT created: calendar=%s title=%r", output.nextcloud_list, output.title)
