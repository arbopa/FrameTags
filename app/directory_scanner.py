from __future__ import annotations

from pathlib import Path

from .metadata_fields import SUPPORTED_EXTENSIONS


class DirectoryScanner:
    def scan(self, roots: list[Path], recurse: bool) -> list[Path]:
        results: list[Path] = []
        for root in roots:
            if not root.exists() or not root.is_dir():
                continue
            if recurse:
                for file_path in root.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        results.append(file_path)
            else:
                for file_path in root.glob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        results.append(file_path)
        return sorted(set(results))
