import pytest

from app.printers import parse_printers_config


def test_parse_printers_uses_rtsp_fallback():
    printers = parse_printers_config("", "rtsp://single-printer/stream")
    assert len(printers) == 1
    assert printers[0].id == "printer-1"
    assert printers[0].name == "Printer 1"
    assert printers[0].rtsp_url == "rtsp://single-printer/stream"


def test_parse_printers_json_multi_stream():
    printers = parse_printers_config(
        '[{"id":"MK4","name":"Prusa MK4","rtsp_url":"rtsp://mk4"},{"name":"Bambu P1S","rtsp_url":"rtsp://p1s"}]',
        "",
    )
    assert [printer.id for printer in printers] == ["mk4", "bambu-p1s"]
    assert [printer.name for printer in printers] == ["Prusa MK4", "Bambu P1S"]


def test_parse_printers_rejects_invalid_json():
    with pytest.raises(ValueError):
        parse_printers_config("not-json", "")
