from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ha_printsentry"
    rtsp_url: str = "rtsp://example"
    check_interval_sec: int = 2
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llava"
    ollama_timeout_sec: int = 30
    history_size: int = 200
    unhealthy_consecutive_threshold: int = 3
    log_level: str = "INFO"

    data_dir: str = "/data"
    latest_frame_path: str = "/data/latest.jpg"
    db_path: str = "/data/ha_printsentry.db"
    dashboard_url: str = "http://localhost:8000"


settings = Settings()
