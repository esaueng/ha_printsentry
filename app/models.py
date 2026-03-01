from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Status(str, Enum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class Signals(BaseModel):
    bed_adhesion_ok: bool
    spaghetti_detected: bool
    layer_shift_detected: bool
    detached_part_detected: bool
    blob_detected: bool
    supports_failed_detected: bool
    print_missing_detected: bool


class VisionResult(BaseModel):
    status: Status
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    signals: Signals


class InferenceRecord(BaseModel):
    id: int | None = None
    printer_id: str = "printer-1"
    printer_name: str = "Printer 1"
    frame_path: str | None = None
    ts: datetime
    status: Status
    confidence: float
    reason: str
    raw_json: str
    incident_active: bool


class LatestStatusResponse(BaseModel):
    printer_id: str
    printer_name: str
    ts: datetime | None
    status: Status
    confidence: float
    reason: str
    incident_active: bool
    unhealthy_consecutive: int
    last_notification_ts: datetime | None


class HistoryResponse(BaseModel):
    printer_id: str
    printer_name: str
    items: list[InferenceRecord]


class PrinterStatusResponse(BaseModel):
    printer_id: str
    printer_name: str
    ts: datetime | None
    status: Status
    confidence: float
    reason: str
    incident_active: bool
    unhealthy_consecutive: int
    last_notification_ts: datetime | None
    frame_url: str


class PrintersResponse(BaseModel):
    items: list[PrinterStatusResponse]


class IncidentState(BaseModel):
    active: bool = False
    unhealthy_consecutive: int = 0
    incident_started_at: datetime | None = None
    last_notification_ts: datetime | None = None


class PrinterStubResponse(BaseModel):
    message: str


def unknown_result(reason: str) -> VisionResult:
    return VisionResult(
        status=Status.UNKNOWN,
        confidence=0.0,
        reason=reason,
        signals=Signals(
            bed_adhesion_ok=False,
            spaghetti_detected=False,
            layer_shift_detected=False,
            detached_part_detected=False,
            blob_detected=False,
            supports_failed_detected=False,
            print_missing_detected=False,
        ),
    )


def to_json_dict(result: VisionResult) -> dict[str, Any]:
    return result.model_dump()
