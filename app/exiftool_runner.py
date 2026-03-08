from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

try:
    from exiftool import ExifToolHelper
except ImportError:  # pragma: no cover - handled at runtime
    ExifToolHelper = None  # type: ignore[assignment]


ProgressCallback = Callable[[int, int], None]


def find_exiftool() -> str:
    app_dir = Path(sys.argv[0]).resolve().parent
    candidates: list[Path] = [app_dir / "exiftool.exe", app_dir / "_internal" / "exiftool.exe"]

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(str(meipass)) / "exiftool.exe")

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "exiftool"


class ExifToolRunner:
    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or find_exiftool()
        self._helper: ExifToolHelper | None = None

    def is_available(self) -> bool:
        try:
            proc = subprocess.run(
                [self.executable, "-ver"],
                capture_output=True,
                text=True,
                check=False,
            )
            return proc.returncode == 0
        except FileNotFoundError:
            return False

    def start(self) -> None:
        if self._helper is not None:
            return
        if ExifToolHelper is None:
            raise RuntimeError("PyExifTool is not installed. Install dependencies from requirements.txt.")
        self._helper = ExifToolHelper(executable=self.executable)
        self._helper.__enter__()

    def stop(self) -> None:
        if self._helper is None:
            return
        helper = self._helper
        self._helper = None
        helper.__exit__(None, None, None)

    def _ensure_started(self) -> ExifToolHelper:
        self.start()
        if self._helper is None:
            raise RuntimeError("Failed to start ExifTool helper.")
        return self._helper

    def read_tags_many(
        self,
        files: list[Path],
        tags: list[str],
        batch_size: int = 200,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[dict[Path, dict[str, object]], list[str]]:
        helper = self._ensure_started()
        rows_by_file: dict[Path, dict[str, object]] = {}
        errors: list[str] = []

        total = len(files)
        processed = 0

        for start in range(0, total, batch_size):
            chunk = files[start : start + batch_size]
            chunk_paths = [str(p) for p in chunk]
            try:
                rows = helper.get_tags(chunk_paths, tags=tags, params=["-n"])
                for row in rows:
                    source = row.get("SourceFile")
                    if not source:
                        continue
                    path = Path(str(source))
                    copy = {k: v for k, v in row.items() if k != "SourceFile"}
                    rows_by_file[path] = copy
            except Exception:
                for file_path in chunk:
                    try:
                        row = helper.get_tags(str(file_path), tags=tags, params=["-n"])[0]
                        copy = {k: v for k, v in row.items() if k != "SourceFile"}
                        rows_by_file[file_path] = copy
                    except Exception as exc:
                        errors.append(f"{file_path}: {exc}")
            processed += len(chunk)
            if progress_callback is not None:
                progress_callback(processed, total)

        return rows_by_file, errors

    def write_with_args(self, file_path: Path, args: list[str]) -> None:
        cmd = [self.executable, "-overwrite_original"] + args + [str(file_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "ExifTool write failed")
