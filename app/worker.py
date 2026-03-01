from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from .capture import capture_frame
from .config import Settings
from .db import Database, utcnow
from .incident import update_incident_state
from .models import InferenceRecord, unknown_result
from .ollama_client import OllamaClient

LOGGER = logging.getLogger(__name__)


class PrintSentryWorker:
    def __init__(self, settings: Settings, db: Database) -> None:
        self.settings = settings
        self.db = db
        self.frame_path = Path(settings.latest_frame_path)
        self.ollama = OllamaClient(settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout_sec)
        self._stop = asyncio.Event()

    async def run(self) -> None:
        backoff = 1
        while not self._stop.is_set():
            try:
                await capture_frame(self.settings.rtsp_url, self.frame_path)
                backoff = 1
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("RTSP capture failed: %s", exc)
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
        return unknown_result("Inference failed after retries or JSON parse failure")

    async def _store_and_handle(self, result):
        state = await self.db.get_incident_state()
        was_active = bool(state["active"])
        unhealthy_consecutive = int(state["unhealthy_consecutive"])

        transition = update_incident_state(
            result,
            was_active=was_active,
            unhealthy_consecutive=unhealthy_consecutive,
            threshold=self.settings.unhealthy_consecutive_threshold,
        )

        now = utcnow()

        await self.db.set_incident_state(
            active=transition.active,
            unhealthy_consecutive=transition.unhealthy_consecutive,
            incident_started_at=now if transition.new_incident else None,
        )

        record = InferenceRecord(
            ts=now,
            status=result.status,
            confidence=result.confidence,
            reason=result.reason,
            raw_json=json.dumps(result.model_dump()),
            incident_active=transition.active,
        )
        await self.db.insert_history(record)
        await self.db.trim_history(self.settings.history_size)

    def stop(self) -> None:
        self._stop.set()
