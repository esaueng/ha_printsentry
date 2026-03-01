from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from .printers import PrinterTarget, parse_printers_config


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ha_printsentry"
    rtsp_url: str = "rtsp://example"
    printers: str = ""
    check_interval_sec: int = 2
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llava"
    ollama_timeout_sec: int = 30
    history_size: int = 200
    unhealthy_consecutive_threshold: int = 3
    log_level: str = "INFO"

    pushover_user_key: str = ""
    pushover_app_token: str = ""
    pushover_priority: int = 0
    pushover_sound: str = "pushover"
    pushover_device: str = ""
    pushover_retry_sec: int | None = None
    pushover_expire_sec: int | None = None
    pushover_min_notification_interval_sec: int = 300

    data_dir: str = "/data"
    latest_frame_path: str = "/data/latest.jpg"
    frames_dir: str = "/data/frames"
    db_path: str = "/data/ha_printsentry.db"
    dashboard_url: str = "http://localhost:8000"

    def configured_printers(self) -> list[PrinterTarget]:
        return parse_printers_config(self.printers, self.rtsp_url)


settings = Settings()
