from app.incident import update_incident_state
from app.models import Signals, Status, VisionResult


def _result(status: Status) -> VisionResult:
    return VisionResult(
        status=status,
        confidence=0.8,
        reason="test",
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


def test_incident_triggers_after_threshold():
    t1 = update_incident_state(_result(Status.UNHEALTHY), False, 0, 3)
    assert not t1.active
    t2 = update_incident_state(_result(Status.UNHEALTHY), t1.active, t1.unhealthy_consecutive, 3)
    assert not t2.active
    t3 = update_incident_state(_result(Status.UNHEALTHY), t2.active, t2.unhealthy_consecutive, 3)
    assert t3.active
    assert t3.new_incident


def test_incident_resolves_on_healthy():
    t = update_incident_state(_result(Status.HEALTHY), True, 4, 3)
    assert not t.active
    assert t.unhealthy_consecutive == 0
    assert t.resolved
