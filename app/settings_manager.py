from __future__ import annotations

import base64
import json
from dataclasses import asdict
from pathlib import Path

from .models import AppSettings


class SettingsManager:
    def __init__(self, settings_path: Path) -> None:
        self.settings_path = settings_path

    def load(self) -> AppSettings:
        if not self.settings_path.exists():
            return AppSettings()
        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return AppSettings(**payload)
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps(asdict(settings), indent=2),
            encoding="utf-8",
        )


def encode_geometry(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def decode_geometry(raw: str) -> bytes:
    return base64.b64decode(raw.encode("ascii"))
