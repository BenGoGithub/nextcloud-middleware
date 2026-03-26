from __future__ import annotations

from datetime import datetime

from caldav_tasks_api import CalDAVTasksClient  # type: ignore[import]

from middleware.config import settings
from middleware.models import TaskOutput


def _get_client() -> CalDAVTasksClient:
    return CalDAVTasksClient(
        url=settings.caldav_url,
        username=settings.caldav_username,
        password=settings.caldav_password,
    )


async def create_task(output: TaskOutput) -> None:
    client = _get_client()

    due: datetime | None = output.due_date

    client.create_task(
        list_name=output.nextcloud_list,
        title=output.title,
        description=output.description,
        due_date=due,
        priority=output.priority,
    )

    if output.needs_calendar_event and due:
        client.create_event(
            calendar_name=output.nextcloud_list,
            title=output.title,
            dtstart=due,
            description=output.description,
        )
