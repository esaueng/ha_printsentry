# ha_printsentry Home Assistant Add-on

This add-on runs `ha_printsentry` inside Home Assistant Supervisor.

## Configuration

Set options in the add-on UI:

- `rtsp_url`
- `ollama_base_url`
- `ollama_model`
- `check_interval_sec`
- Optional Pushover keys/tuning fields

## Notes

- This add-on does **not** run Ollama locally.
- Ensure your remote Ollama host is reachable from Home Assistant.
- Open the ingress panel (or optional mapped port 8000) to view the dashboard.
