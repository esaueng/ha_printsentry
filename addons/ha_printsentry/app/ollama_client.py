from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import httpx
from pydantic import ValidationError

from .models import VisionResult

LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a vision inspector for FDM 3D printing. Your job is to evaluate a single camera image of an active 3D print and decide whether it is HEALTHY or UNHEALTHY. Unhealthy means something went wrong or is likely to fail soon (e.g., loss of bed adhesion, part detached, spaghetti, major layer shift, blob, severe under/over-extrusion, collapsed supports, missing print, nozzle digging into print). Be conservative: if you are unsure, output UNHEALTHY with lower confidence and explain uncertainty. Output MUST be valid JSON ONLY with this schema:
{
"status": "HEALTHY" | "UNHEALTHY",
"confidence": number (0.0 to 1.0),
"reason": string,
"signals": {
"bed_adhesion_ok": boolean,
"spaghetti_detected": boolean,
"layer_shift_detected": boolean,
"detached_part_detected": boolean,
"blob_detected": boolean,
"supports_failed_detected": boolean,
"print_missing_detected": boolean
}
}"""

USER_PROMPT = "Analyze this printer camera frame and return JSON only."


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_sec: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout_sec

    async def infer(self, frame_path: Path) -> VisionResult:
        image_bytes = frame_path.read_bytes()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": USER_PROMPT,
                    "images": [image_b64],
                },
            ],
            "options": {"temperature": 0},
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            body = resp.json()
            content = body.get("message", {}).get("content", "")
            return parse_vision_json(content)


def extract_json_block(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found")
    return cleaned[start : end + 1]


def parse_vision_json(text: str) -> VisionResult:
    try:
        parsed = json.loads(extract_json_block(text))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON returned: {exc}") from exc

    try:
        return VisionResult.model_validate(parsed)
    except ValidationError as exc:
        LOGGER.debug("Vision response schema validation failed: %s", exc)
        raise ValueError(f"Schema validation failed: {exc}") from exc
