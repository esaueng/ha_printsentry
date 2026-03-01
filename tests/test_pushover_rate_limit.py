from datetime import datetime, timedelta, timezone

from app.notifier import PushoverNotifier


def test_should_notify_new_incident_always_true():
    n = PushoverNotifier("u", "t", "http://localhost", 300)
    now = datetime.now(timezone.utc)
    assert n.should_notify(now, now, new_incident=True)


def test_should_notify_respects_interval():
    n = PushoverNotifier("u", "t", "http://localhost", 300)
    now = datetime.now(timezone.utc)
    assert not n.should_notify(now, now - timedelta(seconds=100), new_incident=False)
    assert n.should_notify(now, now - timedelta(seconds=301), new_incident=False)
