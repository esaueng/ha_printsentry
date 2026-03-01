from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite

from .models import InferenceRecord, Status

DEFAULT_PRINTER_ID = "printer-1"
DEFAULT_PRINTER_NAME = "Printer 1"


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS inference_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    printer_id TEXT NOT NULL DEFAULT 'printer-1',
                    printer_name TEXT NOT NULL DEFAULT 'Printer 1',
                    frame_path TEXT,
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
                CREATE TABLE IF NOT EXISTS incident_state_v2 (
                    printer_id TEXT PRIMARY KEY,
                    printer_name TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    unhealthy_consecutive INTEGER NOT NULL,
                    incident_started_at TEXT,
                    last_notification_ts TEXT
                )
                """
            )
            await self._ensure_history_columns(db)
            await self._migrate_legacy_incident_state(db)
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_inference_history_printer_ts
                ON inference_history (printer_id, ts DESC)
                """
            )
            await db.commit()

    async def _ensure_history_columns(self, db: aiosqlite.Connection) -> None:
        cursor = await db.execute("PRAGMA table_info(inference_history)")
        rows = await cursor.fetchall()
        columns = {row[1] for row in rows}
        if "printer_id" not in columns:
            await db.execute("ALTER TABLE inference_history ADD COLUMN printer_id TEXT NOT NULL DEFAULT 'printer-1'")
        if "printer_name" not in columns:
            await db.execute("ALTER TABLE inference_history ADD COLUMN printer_name TEXT NOT NULL DEFAULT 'Printer 1'")
        if "frame_path" not in columns:
            await db.execute("ALTER TABLE inference_history ADD COLUMN frame_path TEXT")

    async def _migrate_legacy_incident_state(self, db: aiosqlite.Connection) -> None:
        cursor = await db.execute("SELECT COUNT(*) FROM incident_state_v2")
        (count,) = await cursor.fetchone()
        if count > 0:
            return

        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='incident_state'"
        )
        if not await cursor.fetchone():
            return

        db.row_factory = aiosqlite.Row
        legacy = await db.execute(
            """
            SELECT active, unhealthy_consecutive, incident_started_at, last_notification_ts
            FROM incident_state
            WHERE id = 1
            """
        )
        row = await legacy.fetchone()
        if not row:
            return

        await db.execute(
            """
            INSERT OR IGNORE INTO incident_state_v2 (
                printer_id, printer_name, active, unhealthy_consecutive, incident_started_at, last_notification_ts
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                DEFAULT_PRINTER_ID,
                DEFAULT_PRINTER_NAME,
                int(row["active"]),
                int(row["unhealthy_consecutive"]),
                row["incident_started_at"],
                row["last_notification_ts"],
            ),
        )

    async def insert_history(self, record: InferenceRecord) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO inference_history (
                    printer_id, printer_name, frame_path, ts, status, confidence, reason, raw_json, incident_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.printer_id,
                    record.printer_name,
                    record.frame_path,
                    record.ts.isoformat(),
                    record.status.value,
                    record.confidence,
                    record.reason,
                    record.raw_json,
                    int(record.incident_active),
                ),
            )
            await db.commit()

    async def trim_history(self, keep: int, printer_id: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                DELETE FROM inference_history
                WHERE printer_id = ?
                AND id NOT IN (
                    SELECT id FROM inference_history WHERE printer_id = ? ORDER BY ts DESC LIMIT ?
                )
                """,
                (printer_id, printer_id, keep),
            )
            await db.commit()

    async def get_latest(self, printer_id: str | None = None) -> InferenceRecord | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if printer_id:
                cursor = await db.execute(
                    "SELECT * FROM inference_history WHERE printer_id = ? ORDER BY ts DESC LIMIT 1",
                    (printer_id,),
                )
            else:
                cursor = await db.execute("SELECT * FROM inference_history ORDER BY ts DESC LIMIT 1")
            row = await cursor.fetchone()
        if not row:
            return None
        return InferenceRecord(
            id=row["id"],
            printer_id=row["printer_id"] or DEFAULT_PRINTER_ID,
            printer_name=row["printer_name"] or DEFAULT_PRINTER_NAME,
            frame_path=row["frame_path"],
            ts=datetime.fromisoformat(row["ts"]),
            status=Status(row["status"]),
            confidence=row["confidence"],
            reason=row["reason"],
            raw_json=row["raw_json"],
            incident_active=bool(row["incident_active"]),
        )

    async def get_history(self, limit: int, printer_id: str | None = None) -> list[InferenceRecord]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if printer_id:
                cursor = await db.execute(
                    "SELECT * FROM inference_history WHERE printer_id = ? ORDER BY ts DESC LIMIT ?",
                    (printer_id, limit),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM inference_history ORDER BY ts DESC LIMIT ?",
                    (limit,),
                )
            rows = await cursor.fetchall()
        return [
            InferenceRecord(
                id=row["id"],
                printer_id=row["printer_id"] or DEFAULT_PRINTER_ID,
                printer_name=row["printer_name"] or DEFAULT_PRINTER_NAME,
                frame_path=row["frame_path"],
                ts=datetime.fromisoformat(row["ts"]),
                status=Status(row["status"]),
                confidence=row["confidence"],
                reason=row["reason"],
                raw_json=row["raw_json"],
                incident_active=bool(row["incident_active"]),
            )
            for row in rows
        ]

    async def get_incident_state(self, printer_id: str, printer_name: str) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM incident_state_v2 WHERE printer_id = ?",
                (printer_id,),
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)

            await db.execute(
                """
                INSERT OR IGNORE INTO incident_state_v2 (
                    printer_id, printer_name, active, unhealthy_consecutive, incident_started_at, last_notification_ts
                ) VALUES (?, ?, 0, 0, NULL, NULL)
                """,
                (printer_id, printer_name),
            )
            await db.commit()
        return {
            "printer_id": printer_id,
            "printer_name": printer_name,
            "active": 0,
            "unhealthy_consecutive": 0,
            "incident_started_at": None,
            "last_notification_ts": None,
        }

    async def set_incident_state(
        self,
        printer_id: str,
        printer_name: str,
        active: bool,
        unhealthy_consecutive: int,
        incident_started_at: datetime | None,
        last_notification_ts: datetime | None,
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO incident_state_v2 (
                    printer_id, printer_name, active, unhealthy_consecutive, incident_started_at, last_notification_ts
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(printer_id) DO UPDATE SET
                    printer_name = excluded.printer_name,
                    active = excluded.active,
                    unhealthy_consecutive = excluded.unhealthy_consecutive,
                    incident_started_at = excluded.incident_started_at,
                    last_notification_ts = excluded.last_notification_ts
                """,
                (
                    printer_id,
                    printer_name,
                    int(active),
                    unhealthy_consecutive,
                    incident_started_at.isoformat() if incident_started_at else None,
                    last_notification_ts.isoformat() if last_notification_ts else None,
                ),
            )
            await db.commit()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
