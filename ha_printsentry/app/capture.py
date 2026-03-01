from __future__ import annotations

import asyncio
import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)


async def capture_frame(rtsp_url: str, output_path: Path, timeout_sec: int = 20) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-rtsp_transport",
        "tcp",
        "-i",
        rtsp_url,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        "-y",
        str(output_path),
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError("ffmpeg frame capture timed out")

    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg capture failed: {stderr.decode().strip()}")

    LOGGER.debug("Captured frame to %s", output_path)
