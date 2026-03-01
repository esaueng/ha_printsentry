from __future__ import annotations

import asyncio
import logging
import contextlib
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from .config import settings
from .db import Database
from .models import (
    HistoryResponse,
    LatestStatusResponse,
    PrinterStatusResponse,
    PrinterStubResponse,
    PrintersResponse,
    Status,
)
from .worker import PrintSentryWorker

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


db = Database(settings.db_path)
printers = settings.configured_printers()
printer_by_id = {printer.id: printer for printer in printers}
workers = [PrintSentryWorker(settings, db, printer) for printer in printers]
worker_tasks: list[asyncio.Task] = []


def _resolve_printer(printer_id: str | None):
    if printer_id:
        printer = printer_by_id.get(printer_id)
        if not printer:
            raise HTTPException(status_code=404, detail=f"Unknown printer_id '{printer_id}'")
        return printer
    return printers[0]


def _frame_path(printer_id: str) -> Path:
    return Path(settings.frames_dir) / f"{printer_id}.jpg"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_tasks
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.frames_dir).mkdir(parents=True, exist_ok=True)
    await db.init()
    worker_tasks = [asyncio.create_task(worker.run()) for worker in workers]
    yield
    for worker in workers:
        worker.stop()
    for worker_task in worker_tasks:
        worker_task.cancel()
    for worker_task in worker_tasks:
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task


app = FastAPI(title="ha_printsentry", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/api/status", response_model=LatestStatusResponse)
async def get_status(printer_id: str | None = Query(default=None)):
    printer = _resolve_printer(printer_id)
    latest = await db.get_latest(printer.id)
    state = await db.get_incident_state(printer.id, printer.name)
    if not latest:
        return LatestStatusResponse(
            printer_id=printer.id,
            printer_name=printer.name,
            ts=None,
            status=Status.UNKNOWN,
            confidence=0.0,
            reason="No inferences yet",
            incident_active=bool(state["active"]),
            unhealthy_consecutive=int(state["unhealthy_consecutive"]),
            last_notification_ts=datetime.fromisoformat(state["last_notification_ts"]) if state["last_notification_ts"] else None,
        )

    return LatestStatusResponse(
        printer_id=printer.id,
        printer_name=printer.name,
        ts=latest.ts,
        status=latest.status,
        confidence=latest.confidence,
        reason=latest.reason,
        incident_active=bool(state["active"]),
        unhealthy_consecutive=int(state["unhealthy_consecutive"]),
        last_notification_ts=datetime.fromisoformat(state["last_notification_ts"]) if state["last_notification_ts"] else None,
    )


@app.get("/api/history", response_model=HistoryResponse)
async def get_history(limit: int = Query(default=50, ge=1), printer_id: str | None = Query(default=None)):
    printer = _resolve_printer(printer_id)
    limit = min(limit, settings.history_size)
    items = await db.get_history(limit, printer.id)
    return HistoryResponse(printer_id=printer.id, printer_name=printer.name, items=items)


@app.get("/api/frame")
async def get_frame(printer_id: str | None = Query(default=None)):
    printer = _resolve_printer(printer_id)
    frame = _frame_path(printer.id)
    if not frame.exists():
        raise HTTPException(status_code=404, detail="No frame captured yet")
    return FileResponse(frame, media_type="image/jpeg")


@app.get("/api/frame/{printer_id}")
async def get_frame_by_printer(printer_id: str):
    printer = _resolve_printer(printer_id)
    frame = _frame_path(printer.id)
    if not frame.exists():
        raise HTTPException(status_code=404, detail="No frame captured yet")
    return FileResponse(frame, media_type="image/jpeg")


@app.get("/api/printers", response_model=PrintersResponse)
async def get_printers():
    items: list[PrinterStatusResponse] = []
    for printer in printers:
        latest = await db.get_latest(printer.id)
        state = await db.get_incident_state(printer.id, printer.name)
        items.append(
            PrinterStatusResponse(
                printer_id=printer.id,
                printer_name=printer.name,
                ts=latest.ts if latest else None,
                status=latest.status if latest else Status.UNKNOWN,
                confidence=latest.confidence if latest else 0.0,
                reason=latest.reason if latest else "No inferences yet",
                incident_active=bool(state["active"]),
                unhealthy_consecutive=int(state["unhealthy_consecutive"]),
                last_notification_ts=(
                    datetime.fromisoformat(state["last_notification_ts"])
                    if state["last_notification_ts"]
                    else None
                ),
                frame_url=f"/api/frame/{printer.id}",
            )
        )
    return PrintersResponse(items=items)


@app.post("/api/printer/pause", response_model=PrinterStubResponse, status_code=501)
async def pause_printer():
    return PrinterStubResponse(message="Printer pause integration is not implemented in ha_printsentry.")


@app.post("/api/printer/cancel", response_model=PrinterStubResponse, status_code=501)
async def cancel_printer():
    return PrinterStubResponse(message="Printer cancel integration is not implemented in ha_printsentry.")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    printer_cards = []
    for printer in printers:
        latest = await db.get_latest(printer.id)
        history = await db.get_history(8, printer.id)
        state = await db.get_incident_state(printer.id, printer.name)
        status = latest.status.value if latest else Status.UNKNOWN.value
        printer_cards.append(
            {
                "id": printer.id,
                "name": printer.name,
                "latest": latest,
                "history": history,
                "incident_active": bool(state["active"]),
                "unhealthy_consecutive": int(state["unhealthy_consecutive"]),
                "last_notification_ts": state["last_notification_ts"],
                "status": status,
                "frame_url": f"/api/frame/{printer.id}",
            }
        )

    status_counts = {
        "healthy": sum(1 for card in printer_cards if card["status"] == Status.HEALTHY.value),
        "unhealthy": sum(1 for card in printer_cards if card["status"] == Status.UNHEALTHY.value),
        "unknown": sum(1 for card in printer_cards if card["status"] == Status.UNKNOWN.value),
    }
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "printer_cards": printer_cards,
            "status_counts": status_counts,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        },
    )
