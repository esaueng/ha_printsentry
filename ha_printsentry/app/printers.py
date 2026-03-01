from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel

PRINTER_ID_PATTERN = re.compile(r"[^a-z0-9]+")
DEFAULT_PRINTER_ID = "printer-1"
DEFAULT_PRINTER_NAME = "Printer 1"


class PrinterTarget(BaseModel):
    id: str
    name: str
    rtsp_url: str


def _normalize_printer_id(value: str) -> str:
    cleaned = PRINTER_ID_PATTERN.sub("-", value.strip().lower()).strip("-")
    return cleaned or DEFAULT_PRINTER_ID


def parse_printers_config(printers: str, fallback_rtsp_url: str) -> list[PrinterTarget]:
    items: list[dict[str, Any]]
    printers = printers.strip()
    fallback_rtsp_url = fallback_rtsp_url.strip()

    if printers:
        try:
            loaded = json.loads(printers)
        except json.JSONDecodeError as exc:
            raise ValueError("PRINTERS must be valid JSON") from exc
        if not isinstance(loaded, list):
            raise ValueError("PRINTERS must be a JSON array")
        if not loaded:
            raise ValueError("PRINTERS cannot be an empty array")
        items = loaded
    elif fallback_rtsp_url:
        items = [{"id": DEFAULT_PRINTER_ID, "name": DEFAULT_PRINTER_NAME, "rtsp_url": fallback_rtsp_url}]
    else:
        raise ValueError("Configure RTSP_URL or PRINTERS")

    targets: list[PrinterTarget] = []
    used_ids: set[str] = set()
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError("Each PRINTERS entry must be an object")
        rtsp_url = str(item.get("rtsp_url", "")).strip()
        if not rtsp_url:
            raise ValueError("Each PRINTERS entry must include rtsp_url")

        name = str(item.get("name") or item.get("id") or f"Printer {idx}").strip()
        if not name:
            name = f"Printer {idx}"

        printer_id = _normalize_printer_id(str(item.get("id") or name))
        suffix = 2
        base_id = printer_id
        while printer_id in used_ids:
            printer_id = f"{base_id}-{suffix}"
            suffix += 1
        used_ids.add(printer_id)

        targets.append(PrinterTarget(id=printer_id, name=name, rtsp_url=rtsp_url))
    return targets

