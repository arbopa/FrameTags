from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import Preset


class PresetManager:
    def __init__(self, preset_path: Path) -> None:
        self.preset_path = preset_path

    def _load_payload(self) -> dict[str, list[dict[str, object]]]:
        if not self.preset_path.exists():
            return {"presets": []}
        try:
            payload = json.loads(self.preset_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("presets"), list):
                return payload
        except Exception:
            pass
        return {"presets": []}

    def _save_payload(self, payload: dict[str, list[dict[str, object]]]) -> None:
        self.preset_path.parent.mkdir(parents=True, exist_ok=True)
        self.preset_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def list_presets(self) -> list[Preset]:
        payload = self._load_payload()
        presets: list[Preset] = []
        for item in payload["presets"]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            fields = item.get("fields", {})
            if not name or not isinstance(fields, dict):
                continue
            normalized = {
                str(k): str(v)
                for k, v in fields.items()
                if str(v).strip()
            }
            presets.append(Preset(name=name, fields=normalized))
        return presets

    def save_new(self, preset: Preset) -> None:
        payload = self._load_payload()
        presets = [p for p in payload["presets"] if p.get("name") != preset.name]
        presets.append(asdict(preset))
        payload["presets"] = presets
        self._save_payload(payload)

    def update(self, preset: Preset) -> None:
        self.save_new(preset)

    def delete(self, name: str) -> None:
        payload = self._load_payload()
        payload["presets"] = [p for p in payload["presets"] if p.get("name") != name]
        self._save_payload(payload)
