import pytest

from app.models import Status
from app.ollama_client import parse_vision_json


def test_parse_valid_json():
    text = '{"status":"HEALTHY","confidence":0.92,"reason":"Looks stable","signals":{"bed_adhesion_ok":true,"spaghetti_detected":false,"layer_shift_detected":false,"detached_part_detected":false,"blob_detected":false,"supports_failed_detected":false,"print_missing_detected":false}}'
    result = parse_vision_json(text)
    assert result.status == Status.HEALTHY
    assert result.confidence == pytest.approx(0.92)


def test_parse_rejects_invalid_schema():
    text = '{"status":"BAD","confidence":2,"reason":"x","signals":{}}'
    with pytest.raises(ValueError):
        parse_vision_json(text)
