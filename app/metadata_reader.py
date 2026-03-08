from __future__ import annotations

from pathlib import Path
from typing import Callable

from .exiftool_runner import ExifToolRunner
from .metadata_fields import FIELD_DEFS
from .metadata_mapper import MetadataMapper
from .models import FileMetadataSnapshot


ProgressCallback = Callable[[str, int, int], None]


class MetadataReader:
    def __init__(self, exiftool: ExifToolRunner, mapper: MetadataMapper) -> None:
        self.exiftool = exiftool
        self.mapper = mapper

    @staticmethod
    def _parse_keywords(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str):
            parts = value.replace(";", ",").split(",")
            return [p.strip() for p in parts if p.strip()]
        return [str(value).strip()]

    @staticmethod
    def _parse_text(value: object | None) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            for item in value:
                text = str(item).strip()
                if text:
                    return text
            return ""
        return str(value).strip()

    def _normalize_row(self, file_path: Path, raw: dict[str, object]) -> FileMetadataSnapshot:
        normalized: dict[str, str | list[str]] = {}
        for key, field in FIELD_DEFS.items():
            found: object | None = None
            for tag in field.targets:
                if tag in raw and raw[tag] not in (None, ""):
                    found = raw[tag]
                    break
            if field.keywords:
                normalized[key] = self._parse_keywords(found)
            else:
                normalized[key] = self._parse_text(found)
        return FileMetadataSnapshot(file_path=file_path, values=normalized)

    def read_normalized(self, file_path: Path) -> FileMetadataSnapshot:
        rows, errors = self.exiftool.read_tags_many([file_path], self.mapper.all_target_tags())
        if errors:
            raise RuntimeError(errors[0])
        raw = rows.get(file_path, {})
        return self._normalize_row(file_path, raw)

    def read_many_normalized(
        self,
        files: list[Path],
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[dict[Path, FileMetadataSnapshot], list[str]]:
        def _on_progress(done: int, total: int) -> None:
            if progress_callback is not None:
                progress_callback("Reading metadata", done, total)

        rows_by_file, errors = self.exiftool.read_tags_many(
            files,
            self.mapper.all_target_tags(),
            progress_callback=_on_progress,
        )

        snapshots: dict[Path, FileMetadataSnapshot] = {}
        for file_path in files:
            row = rows_by_file.get(file_path)
            if row is None:
                if not any(err.startswith(f"{file_path}:") for err in errors):
                    errors.append(f"{file_path}: No metadata returned")
                continue
            snapshots[file_path] = self._normalize_row(file_path, row)
        return snapshots, errors
