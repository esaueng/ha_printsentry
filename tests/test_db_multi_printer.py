from datetime import timezone

import pytest

pytest.importorskip("aiosqlite")

from app.db import Database, utcnow
from app.models import InferenceRecord, Signals, Status, VisionResult


@pytest.mark.asyncio
async def test_incident_state_is_isolated_per_printer(tmp_path):
    db = Database(str(tmp_path / "state.db"))
    await db.init()

    await db.set_incident_state(
        printer_id="mk4",
        printer_name="Prusa MK4",
        active=True,
        unhealthy_consecutive=4,
        incident_started_at=utcnow(),
        last_notification_ts=None,
    )

    mk4 = await db.get_incident_state("mk4", "Prusa MK4")
    p1s = await db.get_incident_state("p1s", "Bambu P1S")

    assert bool(mk4["active"])
    assert int(mk4["unhealthy_consecutive"]) == 4
    assert not bool(p1s["active"])
    assert int(p1s["unhealthy_consecutive"]) == 0


@pytest.mark.asyncio
async def test_history_queries_filter_by_printer(tmp_path):
    db = Database(str(tmp_path / "history.db"))
    await db.init()

    now = utcnow().astimezone(timezone.utc)
    base_result = VisionResult(
        status=Status.HEALTHY,
        confidence=0.9,
        reason="ok",
        signals=Signals(
            bed_adhesion_ok=True,
            spaghetti_detected=False,
            layer_shift_detected=False,
            detached_part_detected=False,
            blob_detected=False,
            supports_failed_detected=False,
            print_missing_detected=False,
        ),
    )

    await db.insert_history(
        InferenceRecord(
            printer_id="mk4",
            printer_name="Prusa MK4",
            frame_path="/data/frames/mk4.jpg",
            ts=now,
            status=base_result.status,
            confidence=base_result.confidence,
            reason=base_result.reason,
            raw_json=base_result.model_dump_json(),
            incident_active=False,
        )
    )
    await db.insert_history(
        InferenceRecord(
            printer_id="p1s",
            printer_name="Bambu P1S",
            frame_path="/data/frames/p1s.jpg",
            ts=now,
            status=base_result.status,
            confidence=base_result.confidence,
            reason=base_result.reason,
            raw_json=base_result.model_dump_json(),
            incident_active=False,
        )
    )

    mk4_history = await db.get_history(limit=10, printer_id="mk4")
    p1s_history = await db.get_history(limit=10, printer_id="p1s")

    assert len(mk4_history) == 1
    assert len(p1s_history) == 1
    assert mk4_history[0].printer_id == "mk4"
    assert p1s_history[0].printer_id == "p1s"
