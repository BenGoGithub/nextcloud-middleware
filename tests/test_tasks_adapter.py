"""Unit tests for middleware/adapters/tasks.py."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from middleware.adapters.tasks import _ical_due, create_task
from middleware.models import TaskOutput


def _task_output(**kwargs) -> TaskOutput:
    defaults = dict(target_type="task", title="Test task", nextcloud_list="Inbox")
    defaults.update(kwargs)
    return TaskOutput(**defaults)


def _make_api(list_name: str = "Inbox", list_uid: str = "abc-123") -> MagicMock:
    task_list = MagicMock()
    task_list.name = list_name
    task_list.uid = list_uid
    api = MagicMock()
    api.task_lists = [task_list]
    api.load_remote_data = MagicMock()
    api.add_task = MagicMock()
    return api


# ---------------------------------------------------------------------------
# _ical_due — timezone localisation
# ---------------------------------------------------------------------------

class TestIcalDue:
    def test_naive_all_day(self):
        assert _ical_due(datetime(2026, 6, 15)) == "20260615"

    def test_naive_with_time(self):
        assert _ical_due(datetime(2026, 6, 15, 9, 30)) == "20260615T093000"

    def test_aware_paris_all_day(self):
        dt = datetime(2026, 6, 15, tzinfo=ZoneInfo("Europe/Paris"))
        assert _ical_due(dt) == "20260615"

    def test_aware_paris_with_time(self):
        dt = datetime(2026, 6, 15, 9, 30, tzinfo=ZoneInfo("Europe/Paris"))
        assert _ical_due(dt) == "20260615T093000"


# ---------------------------------------------------------------------------
# create_task
# ---------------------------------------------------------------------------

class TestCreateTask:
    @pytest.mark.asyncio
    async def test_happy_path_calls_add_task(self):
        output = _task_output()
        api = _make_api()
        with patch("middleware.adapters.tasks._get_api", return_value=api):
            await create_task(output)
        api.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_correct_list_uid(self):
        output = _task_output(nextcloud_list="Alternance")
        api = _make_api(list_name="Alternance", list_uid="xyz-456")
        with patch("middleware.adapters.tasks._get_api", return_value=api):
            await create_task(output)
        _, kwargs = api.add_task.call_args
        assert kwargs["list_uid"] == "xyz-456"

    @pytest.mark.asyncio
    async def test_unknown_list_raises_value_error(self):
        output = _task_output(nextcloud_list="ListeInexistante")
        api = _make_api(list_name="Inbox")
        with patch("middleware.adapters.tasks._get_api", return_value=api):
            with pytest.raises(ValueError, match="not found"):
                await create_task(output)

    @pytest.mark.asyncio
    async def test_uses_default_list_when_nextcloud_list_is_none(self):
        # default_task_list = "Inbox" (config default)
        output = _task_output(nextcloud_list=None)
        api = _make_api(list_name="Inbox")
        with patch("middleware.adapters.tasks._get_api", return_value=api):
            await create_task(output)
        api.add_task.assert_called_once()
