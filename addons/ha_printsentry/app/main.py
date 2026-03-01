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
from .models import HistoryResponse, LatestStatusResponse, PrinterStubResponse, Status
from .worker import PrintSentryWorker

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


db = Database(settings.db_path)
worker = PrintSentryWorker(settings, db)
worker_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    await db.init()
    worker_task = asyncio.create_task(worker.run())
    yield
    worker.stop()
    if worker_task:
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task


app = FastAPI(title="ha_printsentry", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/api/status", response_model=LatestStatusResponse)
async def get_status():
    latest = await db.get_latest()
    state = await db.get_incident_state()
    if not latest:
        return LatestStatusResponse(
            ts=None,
            status=Status.UNKNOWN,
            confidence=0.0,
            reason="No inferences yet",
            incident_active=bool(state["active"]),
            unhealthy_consecutive=int(state["unhealthy_consecutive"]),
            last_notification_ts=datetime.fromisoformat(state["last_notification_ts"]) if state["last_notification_ts"] else None,
        )

    return LatestStatusResponse(
        ts=latest.ts,
        status=latest.status,
        confidence=latest.confidence,
        reason=latest.reason,
        incident_active=bool(state["active"]),
        unhealthy_consecutive=int(state["unhealthy_consecutive"]),
        last_notification_ts=datetime.fromisoformat(state["last_notification_ts"]) if state["last_notification_ts"] else None,
    )


@app.get("/api/history", response_model=HistoryResponse)
async def get_history(limit: int = Query(default=50, ge=1)):
    limit = min(limit, settings.history_size)
    items = await db.get_history(limit)
    return HistoryResponse(items=items)


@app.get("/api/frame")
async def get_frame():
    frame = Path(settings.latest_frame_path)
    if not frame.exists():
        raise HTTPException(status_code=404, detail="No frame captured yet")
    return FileResponse(frame, media_type="image/jpeg")


@app.post("/api/printer/pause", response_model=PrinterStubResponse, status_code=501)
async def pause_printer():
    return PrinterStubResponse(message="Printer pause integration is not implemented in ha_printsentry.")


@app.post("/api/printer/cancel", response_model=PrinterStubResponse, status_code=501)
async def cancel_printer():
    return PrinterStubResponse(message="Printer cancel integration is not implemented in ha_printsentry.")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    latest = await db.get_latest()
    history = await db.get_history(20)
    state = await db.get_incident_state()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "latest": latest,
            "history": history,
            "incident_active": bool(state["active"]),
            "unhealthy_consecutive": int(state["unhealthy_consecutive"]),
            "last_notification_ts": state["last_notification_ts"],
        },
    )
