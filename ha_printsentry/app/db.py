from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite

from .models import InferenceRecord, Status


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS inference_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    reason TEXT NOT NULL,
                    raw_json TEXT NOT NULL,
                    incident_active INTEGER NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    active INTEGER NOT NULL,
                    unhealthy_consecutive INTEGER NOT NULL,
                    incident_started_at TEXT,
                    last_notification_ts TEXT
                )
                """
            )
            await db.execute(
                """
                INSERT OR IGNORE INTO incident_state (id, active, unhealthy_consecutive, incident_started_at, last_notification_ts)
                VALUES (1, 0, 0, NULL, NULL)
                """
            )
            await db.commit()

    async def insert_history(self, record: InferenceRecord) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO inference_history (ts, status, confidence, reason, raw_json, incident_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.ts.isoformat(),
                    record.status.value,
                    record.confidence,
                    record.reason,
                    record.raw_json,
                    int(record.incident_active),
                ),
            )
            await db.commit()

    async def trim_history(self, keep: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                DELETE FROM inference_history
                WHERE id NOT IN (
                    SELECT id FROM inference_history ORDER BY ts DESC LIMIT ?
                )
                """,
                (keep,),
            )
            await db.commit()

    async def get_latest(self) -> InferenceRecord | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM inference_history ORDER BY ts DESC LIMIT 1"
            )
            row = await cursor.fetchone()
        if not row:
            return None
        return InferenceRecord(
            id=row["id"],
            ts=datetime.fromisoformat(row["ts"]),
            status=Status(row["status"]),
            confidence=row["confidence"],
            reason=row["reason"],
            raw_json=row["raw_json"],
            incident_active=bool(row["incident_active"]),
        )

    async def get_history(self, limit: int) -> list[InferenceRecord]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM inference_history ORDER BY ts DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
        return [
            InferenceRecord(
                id=row["id"],
                ts=datetime.fromisoformat(row["ts"]),
                status=Status(row["status"]),
                confidence=row["confidence"],
                reason=row["reason"],
                raw_json=row["raw_json"],
                incident_active=bool(row["incident_active"]),
            )
            for row in rows
        ]

    async def get_incident_state(self) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM incident_state WHERE id = 1")
            row = await cursor.fetchone()
        return dict(row)

    async def set_incident_state(
        self,
        active: bool,
        unhealthy_consecutive: int,
        incident_started_at: datetime | None,
        last_notification_ts: datetime | None,
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE incident_state
                SET active = ?, unhealthy_consecutive = ?, incident_started_at = ?, last_notification_ts = ?
                WHERE id = 1
                """,
                (
                    int(active),
                    unhealthy_consecutive,
                    incident_started_at.isoformat() if incident_started_at else None,
                    last_notification_ts.isoformat() if last_notification_ts else None,
                ),
            )
            await db.commit()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
