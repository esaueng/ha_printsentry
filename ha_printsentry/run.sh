#!/bin/bash
set -euo pipefail

OPTIONS_FILE="/data/options.json"
if [ -f "$OPTIONS_FILE" ]; then
  eval "$(python3 - <<'PY'
import json
from pathlib import Path

options_path = Path('/data/options.json')
opts = json.loads(options_path.read_text()) if options_path.exists() else {}

mapping = {
    'rtsp_url': 'RTSP_URL',
    'printers': 'PRINTERS',
    'check_interval_sec': 'CHECK_INTERVAL_SEC',
    'ollama_base_url': 'OLLAMA_BASE_URL',
    'ollama_model': 'OLLAMA_MODEL',
    'ollama_timeout_sec': 'OLLAMA_TIMEOUT_SEC',
    'history_size': 'HISTORY_SIZE',
    'unhealthy_consecutive_threshold': 'UNHEALTHY_CONSECUTIVE_THRESHOLD',
    'log_level': 'LOG_LEVEL',
    'dashboard_url': 'DASHBOARD_URL',
    'pushover_user_key': 'PUSHOVER_USER_KEY',
    'pushover_app_token': 'PUSHOVER_APP_TOKEN',
    'pushover_priority': 'PUSHOVER_PRIORITY',
    'pushover_sound': 'PUSHOVER_SOUND',
    'pushover_device': 'PUSHOVER_DEVICE',
    'pushover_retry_sec': 'PUSHOVER_RETRY_SEC',
    'pushover_expire_sec': 'PUSHOVER_EXPIRE_SEC',
    'pushover_min_notification_interval_sec': 'PUSHOVER_MIN_NOTIFICATION_INTERVAL_SEC',
}

for k, env in mapping.items():
    val = opts.get(k)
    if val is None:
        continue
    if isinstance(val, bool):
        sval = 'true' if val else 'false'
    else:
        sval = str(val)
    print(f'export {env}={json.dumps(sval)}')
PY
)"
fi

mkdir -p /data
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
