from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.exiftool_runner import ExifToolRunner, find_exiftool
from app.logger import configure_logging
from app.main_window import MainWindow
from app.preset_manager import PresetManager
from app.settings_manager import SettingsManager


def resolve_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resolve_user_data_dir(app_name: str = "FrameTags") -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / app_name
    return Path.home() / f".{app_name.lower()}"


def main() -> int:
    app_root = resolve_app_root()
    data_dir = resolve_user_data_dir("FrameTags")
    data_dir.mkdir(parents=True, exist_ok=True)

    configure_logging(data_dir / "frametags.log")

    app = QApplication(sys.argv)
    app.setApplicationName("FrameTags")

    exiftool_runner = ExifToolRunner(executable=find_exiftool())
    preset_manager = PresetManager(data_dir / "presets.json")
    settings_manager = SettingsManager(data_dir / "settings.json")

    window = MainWindow(
        project_root=app_root,
        exiftool_runner=exiftool_runner,
        preset_manager=preset_manager,
        settings_manager=settings_manager,
    )
    window.resize(1200, 900)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
