# ha_printsentry

`ha_printsentry` is a local, Dockerized Home Assistant Add-on–style service that monitors one or more 3D printer RTSP camera streams and classifies print health as `HEALTHY` or `UNHEALTHY` using a **remote Ollama vision model** over HTTP.

## Features

- RTSP frame capture using `ffmpeg` (single or multi-printer)
- Vision inference through remote Ollama (`OLLAMA_BASE_URL`)
- Strict JSON parsing with schema validation (Pydantic)
- Exponential-backoff retries for RTSP disconnects and Ollama network failures
- Incident logic based on consecutive UNHEALTHY checks
- Optional Pushover notifications with rate limiting
- FastAPI REST API + dashboard UI with per-printer cards and live frame refresh
- SQLite-backed per-printer history + incident state persistence

## Prerequisites

1. Docker + Docker Compose installed.
2. A reachable remote Ollama server with a vision-capable model installed.
   - Configure `OLLAMA_BASE_URL` in `.env`.
   - On Ollama host, ensure model exists: `ollama pull <model>`

## Quick Start

1. Copy environment config:

```bash
cp .env.example .env
```

2. Edit `.env` and set one of:
   - Single printer: `RTSP_URL=rtsp://...`
   - Multiple printers:
     - `RTSP_URL=`
     - `PRINTERS=[{"id":"mk4","name":"Prusa MK4","rtsp_url":"rtsp://mk4/stream"},{"id":"p1s","name":"Bambu P1S","rtsp_url":"rtsp://p1s/stream"}]`
   - `OLLAMA_BASE_URL=http://<ollama-host>:11434`
   - `OLLAMA_MODEL=llava` (or your installed vision model)

3. Start the app:

```bash
docker compose up -d --build
```

4. Open:
   - Dashboard: http://localhost:8000/
   - API status: http://localhost:8000/api/status

5. After updating stream config (`RTSP_URL` or `PRINTERS`), restart app:

```bash
docker compose restart app
```

## Pushover Alerts (optional)

Set both values in `.env` to enable notifications:

- `PUSHOVER_USER_KEY`
- `PUSHOVER_APP_TOKEN`

Notification behavior:
- Triggers when UNHEALTHY is seen `UNHEALTHY_CONSECUTIVE_THRESHOLD` times consecutively.
- Sends one notification per incident.
- Additional notifications are blocked until either:
  - `PUSHOVER_MIN_NOTIFICATION_INTERVAL_SEC` has passed, or
  - a HEALTHY result resets/ends the incident and a new incident begins.

## Environment Variables

See `.env.example` for full configuration. Key values:

- `RTSP_URL`
- `PRINTERS` (JSON array for multi-printer mode)
- `CHECK_INTERVAL_SEC`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_TIMEOUT_SEC`
- `HISTORY_SIZE`
- `UNHEALTHY_CONSECUTIVE_THRESHOLD`
- `LOG_LEVEL`

## API Endpoints

- `GET /api/printers` status summary for all configured printers
- `GET /api/status?printer_id=<id>` latest status payload for one printer
- `GET /api/history?printer_id=<id>&limit=N` recent history for one printer (capped by `HISTORY_SIZE`)
- `GET /api/frame/{printer_id}` latest captured frame JPEG for a printer
- `POST /api/printer/pause` stub (501)
- `POST /api/printer/cancel` stub (501)

## Troubleshooting

### RTSP Connectivity

- Check RTSP URL validity and auth.
- Confirm stream is reachable from Docker host/container network.
- Inspect logs for ffmpeg errors:

```bash
docker compose logs -f app
```

### Ollama Connectivity

- Verify `OLLAMA_BASE_URL` is reachable from the app container.
- Confirm model is installed on remote host:

```bash
ollama pull <model>
```

- Check app logs for timeout/retry errors.

### Logs

```bash
docker compose logs -f app
```

## Tests

Run locally:

```bash
pytest
```
