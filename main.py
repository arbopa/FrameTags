from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.exiftool_runner import ExifToolRunner, find_exiftool
from app.logger import configure_logging
from app.main_window import MainWindow
from app.preset_manager import PresetManager
from app.settings_manager import SettingsManager


def main() -> int:
    project_root = Path(__file__).resolve().parent
    data_dir = project_root / "data"

    configure_logging(data_dir / "frametags.log")

    app = QApplication(sys.argv)
    app.setApplicationName("FrameTags")

    exiftool_runner = ExifToolRunner(executable=find_exiftool())
    preset_manager = PresetManager(data_dir / "presets.json")
    settings_manager = SettingsManager(data_dir / "settings.json")

    window = MainWindow(
        project_root=project_root,
        exiftool_runner=exiftool_runner,
        preset_manager=preset_manager,
        settings_manager=settings_manager,
    )
    window.resize(1200, 900)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
