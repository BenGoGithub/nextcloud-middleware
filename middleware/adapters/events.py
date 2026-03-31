from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import caldav  # type: ignore[import]

from middleware.config import settings
from middleware.models import EventOutput

logger = logging.getLogger(__name__)


def _fmt_local(dt: datetime, tz_name: str) -> str:
    """Convert a datetime to iCalendar local-time format (no Z suffix) for a given TZID."""
    tz = ZoneInfo(tz_name)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    else:
        dt = dt.astimezone(tz)
    return dt.strftime("%Y%m%dT%H%M%S")


async def create_event(output: EventOutput) -> None:
    tz_name = output.timezone or "Europe/Paris"

    uid = str(uuid.uuid4())
    dtstamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dtstart = _fmt_local(output.start, tz_name)

    if output.end:
        dtend = _fmt_local(output.end, tz_name)
    else:
        dtend = _fmt_local(output.start + timedelta(hours=1), tz_name)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//nextcloud-middleware//EN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;TZID={tz_name}:{dtstart}",
        f"DTEND;TZID={tz_name}:{dtend}",
        f"SUMMARY:{output.title}",
    ]
    if output.description:
        lines.append(f"DESCRIPTION:{output.description}")
    if output.location:
        lines.append(f"LOCATION:{output.location}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    ical = "\r\n".join(lines) + "\r\n"

    client = caldav.DAVClient(
        url=settings.caldav_url,
        username=settings.caldav_username,
        password=settings.caldav_password,
    )
    principal = client.principal()

    # Use the first calendar that supports VEVENT (skips task-only collections)
    target_cal = _find_vevent_calendar(principal)
    if target_cal is None:
        raise ValueError("No VEVENT-capable CalDAV calendar found")

    target_cal.add_event(ical)
    logger.info("CalDAV VEVENT created: calendar=%s title=%r uid=%s", target_cal.name, output.title, uid)


def _find_vevent_calendar(principal: caldav.Principal) -> caldav.Calendar | None:
    """Return the first calendar that can hold VEVENT objects."""
    for cal in principal.calendars():
        try:
            components = cal.get_supported_components()
            if "VEVENT" in components:
                return cal
        except Exception:
            # Fallback: assume the calendar supports VEVENT if we can't check
            return cal
    return None
