from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from .capture import capture_frame
from .config import PrinterTarget, Settings
from .db import Database, utcnow
from .incident import update_incident_state
from .models import InferenceRecord, Status, unknown_result
from .notifier import PushoverNotifier
from .ollama_client import OllamaClient

LOGGER = logging.getLogger(__name__)


class PrintSentryWorker:
    def __init__(self, settings: Settings, db: Database, printer: PrinterTarget) -> None:
        self.settings = settings
        self.db = db
        self.printer = printer
        self.frame_path = Path(settings.frames_dir) / f"{printer.id}.jpg"
        self.ollama = OllamaClient(settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout_sec)
        self.notifier = PushoverNotifier(
            user_key=settings.pushover_user_key,
            app_token=settings.pushover_app_token,
            dashboard_url=settings.dashboard_url,
            min_interval_sec=settings.pushover_min_notification_interval_sec,
            priority=settings.pushover_priority,
            sound=settings.pushover_sound,
            device=settings.pushover_device,
            retry_sec=settings.pushover_retry_sec,
            expire_sec=settings.pushover_expire_sec,
        )
        self._stop = asyncio.Event()

    async def run(self) -> None:
        backoff = 1
        while not self._stop.is_set():
            try:
                await capture_frame(self.printer.rtsp_url, self.frame_path)
                backoff = 1
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("RTSP capture failed for %s: %s", self.printer.name, exc)
                await asyncio.sleep(min(backoff, 60))
                backoff = min(backoff * 2, 60)
                continue

            result = await self._infer_with_retry()
            await self._store_and_handle(result)
            await asyncio.sleep(self.settings.check_interval_sec)

    async def _infer_with_retry(self):
        attempt = 0
        delay = 1
        while attempt < 3:
            attempt += 1
            try:
                return await self.ollama.infer(self.frame_path)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Inference attempt %s failed: %s", attempt, exc)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 8)
        # one extra parse fallback attempt requirement satisfied by retried infer calls
        return unknown_result("Inference failed after retries or JSON parse failure")

    async def _store_and_handle(self, result):
        state = await self.db.get_incident_state(self.printer.id, self.printer.name)
        was_active = bool(state["active"])
        unhealthy_consecutive = int(state["unhealthy_consecutive"])
        last_notification_ts = (
            datetime.fromisoformat(state["last_notification_ts"])
            if state["last_notification_ts"]
            else None
        )

        transition = update_incident_state(
            result,
            was_active=was_active,
            unhealthy_consecutive=unhealthy_consecutive,
            threshold=self.settings.unhealthy_consecutive_threshold,
        )

        now = utcnow()
        if transition.resolved:
            last_notification_ts = None

        if transition.active and result.status == Status.UNHEALTHY:
            if self.notifier.should_notify(now, last_notification_ts, transition.new_incident):
                sent = await self.notifier.send_alert(
                    status=result.status.value,
                    confidence=result.confidence,
                    reason=result.reason,
                    ts=now,
                    printer_name=self.printer.name,
                )
                if sent:
                    last_notification_ts = now

        await self.db.set_incident_state(
            printer_id=self.printer.id,
            printer_name=self.printer.name,
            active=transition.active,
            unhealthy_consecutive=transition.unhealthy_consecutive,
            incident_started_at=now if transition.new_incident else None,
            last_notification_ts=last_notification_ts,
        )

        record = InferenceRecord(
            printer_id=self.printer.id,
            printer_name=self.printer.name,
            frame_path=str(self.frame_path),
            ts=now,
            status=result.status,
            confidence=result.confidence,
            reason=result.reason,
            raw_json=json.dumps(result.model_dump()),
            incident_active=transition.active,
        )
        await self.db.insert_history(record)
        await self.db.trim_history(self.settings.history_size, self.printer.id)

    def stop(self) -> None:
        self._stop.set()
