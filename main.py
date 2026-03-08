from __future__ import annotations

import os
import shutil
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


def migrate_legacy_data_if_needed(data_dir: Path, legacy_dirs: list[Path]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)

    for filename in ("presets.json", "settings.json"):
        target = data_dir / filename
        if target.exists():
            continue

        for legacy_dir in legacy_dirs:
            source = legacy_dir / filename
            if source.exists():
                shutil.copy2(source, target)
                break


def main() -> int:
    app_root = resolve_app_root()
    data_dir = resolve_user_data_dir("FrameTags")

    migrate_legacy_data_if_needed(
        data_dir,
        legacy_dirs=[
            app_root / "data",
            app_root / "_internal" / "data",
            Path(__file__).resolve().parent / "data",
        ],
    )

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
