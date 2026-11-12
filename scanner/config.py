from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    base_url: str
    model: str
    api_key_env: str
    timeout_seconds: int = 300

    def api_key(self) -> str:
        value = os.getenv(self.api_key_env)
        if not value:
            raise RuntimeError(f"Set the {self.api_key_env} environment variable before calling {self.model}.")
        return value


@dataclass(frozen=True)
class AppConfig:
    apk_path: Path
    workspace: Path


@dataclass(frozen=True)
class ScanConfig:
    max_chunk_chars: int
    max_chunks_per_request: int
    max_request_chars: int
    max_scan_chunks: int
    severity_threshold: str


@dataclass(frozen=True)
class Settings:
    app: AppConfig
    scan: ScanConfig
    teacher: ModelConfig
    student: ModelConfig


def _model_config(data: dict[str, str]) -> ModelConfig:
    return ModelConfig(
        provider=data["provider"],
        base_url=data["base_url"].rstrip("/"),
        model=data["model"],
        api_key_env=data["api_key_env"],
        timeout_seconds=int(data.get("timeout_seconds", 300)),
    )


def load_settings(path: Path) -> Settings:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    root = path.parent
    app = data["app"]
    scan = data["scan"]
    return Settings(
        app=AppConfig(apk_path=(root / app["apk_path"]).resolve(), workspace=(root / app["workspace"]).resolve()),
        scan=ScanConfig(**scan),
        teacher=_model_config(data["models"]["teacher"]),
        student=_model_config(data["models"]["student"]),
    )
