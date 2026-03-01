from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import Status, VisionResult


@dataclass
class Transition:
    active: bool
    unhealthy_consecutive: int
    new_incident: bool
    resolved: bool


def update_incident_state(
    result: VisionResult,
    was_active: bool,
    unhealthy_consecutive: int,
    threshold: int,
) -> Transition:
    new_incident = False
    resolved = False

    if result.status == Status.UNHEALTHY:
        unhealthy_consecutive += 1
        if not was_active and unhealthy_consecutive >= threshold:
            was_active = True
            new_incident = True
    elif result.status == Status.HEALTHY:
        if was_active:
            resolved = True
        was_active = False
        unhealthy_consecutive = 0
    else:
        unhealthy_consecutive = 0

    return Transition(
        active=was_active,
        unhealthy_consecutive=unhealthy_consecutive,
        new_incident=new_incident,
        resolved=resolved,
    )
