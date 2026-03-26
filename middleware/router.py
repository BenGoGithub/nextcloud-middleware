from __future__ import annotations

from middleware.adapters.deck import create_card
from middleware.adapters.tasks import create_task
from middleware.models import TaskOutput


async def dispatch(output: TaskOutput) -> None:
    """Route a parsed TaskOutput to the appropriate Nextcloud backend."""
    if output.target_type == "task":
        await create_task(output)
    elif output.target_type == "deck":
        await create_card(output)
    else:
        raise ValueError(f"Unknown target_type: {output.target_type!r}")
