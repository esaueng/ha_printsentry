from pathlib import Path


def test_addon_schema_uses_supervisor_compatible_pushover_priority() -> None:
    config_text = Path("ha_printsentry/config.yaml").read_text(encoding="utf-8")
    assert "pushover_priority: int(-2,2)" not in config_text
    assert "pushover_priority: list(-2|-1|0|1|2)" in config_text
