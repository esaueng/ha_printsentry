# ha_printsentry

`ha_printsentry` monitors a 3D printer RTSP camera stream and classifies print health as `HEALTHY` or `UNHEALTHY` using a **remote Ollama vision model** over HTTP.

This repository now supports both:
- Docker Compose deployment.
- **Home Assistant Supervisor custom add-on deployment**.

## Home Assistant Add-on Deployment (Supervisor)

This repo is a valid custom add-on repository with add-on files under:

- `repository.yaml`
- `ha_printsentry/config.yaml`
- `ha_printsentry/Dockerfile`
- `ha_printsentry/run.sh`

### Install steps

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**.
2. Click menu (⋮) → **Repositories**.
3. Add this repository URL.
4. Open **ha_printsentry** add-on and click **Install**.
5. Configure options:
   - `rtsp_url`
   - `ollama_base_url`
   - `ollama_model`
   - optional Pushover settings
6. Start add-on and open via **Ingress**.

> This add-on does **not** include Ollama. Your remote Ollama server must already be running and reachable from Home Assistant.


### Add-on repository URL appears as `example`

If Home Assistant shows your repository as `https://github.com/example/ha_printsentry`, it is reading the `url` field from `repository.yaml` and/or add-on `config.yaml`.
This repository now sets both to the real GitHub URL (`https://github.com/esaueng/ha_printsentry`).
After pulling latest changes, remove and re-add the repository in Home Assistant to refresh metadata.

5. Verify host architecture compatibility. Add-ons are filtered by `arch` in `ha_printsentry/config.yaml`; this repo supports `amd64`, `aarch64`, `armv7`, `armhf`, and `i386`.

## Docker Compose Deployment

### Prerequisites

1. Docker + Docker Compose installed.
2. A reachable remote Ollama server with a vision-capable model installed.
   - Configure `OLLAMA_BASE_URL` in `.env`.
   - On Ollama host, ensure model exists: `ollama pull <model>`

### Quick Start

1. Copy environment config:

```bash
cp .env.example .env
```

2. Edit `.env` and set:
   - `RTSP_URL=rtsp://...`
   - `OLLAMA_BASE_URL=http://<ollama-host>:11434`
   - `OLLAMA_MODEL=llava` (or your installed vision model)

3. Start the app:

```bash
docker compose up -d --build
```

4. Open:
   - Dashboard: http://localhost:8000/
   - API status: http://localhost:8000/api/status

5. After updating `RTSP_URL`, restart app:

```bash
docker compose restart app
```

## Features

- RTSP frame capture using `ffmpeg`
- Vision inference through remote Ollama (`OLLAMA_BASE_URL`)
- Strict JSON parsing with schema validation (Pydantic)
- Exponential-backoff retries for RTSP disconnects and Ollama network failures
- Incident logic based on consecutive UNHEALTHY checks
- Optional Pushover notifications with rate limiting
- FastAPI REST API + simple dashboard UI
- SQLite-backed history + incident state persistence

## API Endpoints

- `GET /api/status` latest status payload
- `GET /api/history?limit=N` recent history (capped by `HISTORY_SIZE`)
- `GET /api/frame` latest captured frame JPEG
- `POST /api/printer/pause` stub (501)
- `POST /api/printer/cancel` stub (501)

## Troubleshooting

### Home Assistant Supervisor schema error for `pushover_priority`

If Supervisor logs include:

```
... data['schema']['pushover_priority'] ... Got 'int(-2,2)'
```

this causes Home Assistant to skip loading the add-on config. The add-on schema has been updated to use:

- `pushover_priority: list(-2|-1|0|1|2)`

which is compatible with current Supervisor schema validation.


### RTSP Connectivity

- Check RTSP URL validity and auth.
- Confirm stream is reachable from Docker host/Home Assistant network.
- Inspect logs for ffmpeg errors:

```bash
docker compose logs -f app
```

### Ollama Connectivity

- Verify `OLLAMA_BASE_URL` is reachable from the app container/add-on.
- Confirm model is installed on remote host:

```bash
ollama pull <model>
```

- Check app logs for timeout/retry errors.

### Logs

- Docker Compose:

```bash
docker compose logs -f app
```

- Home Assistant add-on logs are available in the add-on UI.

## Tests

Run locally:

```bash
pytest
```
