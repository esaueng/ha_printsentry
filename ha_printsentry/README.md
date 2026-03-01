# ha_printsentry Home Assistant Add-on

This add-on runs `ha_printsentry` inside Home Assistant Supervisor.

## Configuration

Set options in the add-on UI:

- `rtsp_url` for single-printer mode
- `printers` JSON for multi-printer mode
- `ollama_base_url`
- `ollama_model`
- `check_interval_sec`
- Optional Pushover keys/tuning fields

Example `printers` value:

```json
[
  {"id":"mk4","name":"Prusa MK4","rtsp_url":"rtsp://mk4/stream"},
  {"id":"p1s","name":"Bambu P1S","rtsp_url":"rtsp://p1s/stream"}
]
```

## Notes

- This add-on does **not** run Ollama locally.
- Ensure your remote Ollama host is reachable from Home Assistant.
- Open the ingress panel (or optional mapped port 8000) to view the dashboard.
