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

## Troubleshooting: repository shows `example` URL or add-on missing

If Home Assistant displays this repository as `https://github.com/example/ha_printsentry` or the add-on does not appear:

1. Make sure your repository contains `repository.yaml` at root and `ha_printsentry/config.yaml` as a top-level add-on directory.
2. Confirm both metadata URLs point to your real repo (`https://github.com/esaueng/ha_printsentry`).
3. In Home Assistant Add-on Store, remove the repository and add it again.
4. Reload the Add-on Store UI.
5. Confirm your GitHub default branch includes this fix commit (add-on version `0.2.1`).

6. Confirm your Home Assistant CPU architecture is supported by the add-on (`amd64`, `aarch64`, `armv7`, `armhf`, `i386`).


## Supervisor schema parse error (`pushover_priority`)

If Supervisor logs show:

```
... data['schema']['pushover_priority'] ... Got 'int(-2,2)'
```

then the add-on schema is invalid for current Supervisor regex rules. This repository now uses:

- `pushover_priority: list(-2|-1|0|1|2)`

which accepts valid Pushover priority values and is compatible with Supervisor schema validation.
