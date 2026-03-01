from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

LOGGER = logging.getLogger(__name__)


class PushoverNotifier:
    def __init__(
        self,
        user_key: str,
        app_token: str,
        dashboard_url: str,
        min_interval_sec: int,
        priority: int = 0,
        sound: str = "pushover",
        device: str = "",
        retry_sec: int | None = None,
        expire_sec: int | None = None,
    ) -> None:
        self.user_key = user_key
        self.app_token = app_token
        self.dashboard_url = dashboard_url
        self.min_interval_sec = min_interval_sec
        self.priority = priority
        self.sound = sound
        self.device = device
        self.retry_sec = retry_sec
        self.expire_sec = expire_sec

    @property
    def enabled(self) -> bool:
        return bool(self.user_key and self.app_token)

    def should_notify(
        self,
        now: datetime,
        last_notification_ts: datetime | None,
        new_incident: bool,
    ) -> bool:
        if new_incident:
            return True
        if not last_notification_ts:
            return True
        return (now - last_notification_ts) >= timedelta(seconds=self.min_interval_sec)

    async def send_alert(
        self,
        status: str,
        confidence: float,
        reason: str,
        ts: datetime,
        printer_name: str,
    ) -> bool:
        if not self.enabled:
            LOGGER.warning("Pushover is not configured; skipping notification")
            return False

        message = (
            f"Printer: {printer_name}\n"
            f"Status: {status}\n"
            f"Confidence: {confidence:.2f}\n"
            f"Reason: {reason}\n"
            f"Time: {ts.isoformat()}\n"
            f"Dashboard: {self.dashboard_url}"
        )
        payload = {
            "token": self.app_token,
            "user": self.user_key,
            "title": f"ha_printsentry Alert: {printer_name} Unhealthy",
            "message": message,
            "priority": self.priority,
            "sound": self.sound,
        }
        if self.device:
            payload["device"] = self.device
        if self.priority == 2:
            if self.retry_sec:
                payload["retry"] = self.retry_sec
            if self.expire_sec:
                payload["expire"] = self.expire_sec

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post("https://api.pushover.net/1/messages.json", data=payload)
                resp.raise_for_status()
            LOGGER.info("Sent Pushover notification")
            return True
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Failed to send Pushover notification: %s", exc)
            return False
