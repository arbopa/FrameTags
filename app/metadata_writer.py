from __future__ import annotations

from pathlib import Path
from typing import Callable

from .exiftool_runner import ExifToolRunner
from .metadata_fields import RAW_EXTENSIONS
from .metadata_mapper import MetadataMapper
from .models import FileChangeSet


ProgressCallback = Callable[[int, int], None]


class MetadataWriter:
    def __init__(self, exiftool: ExifToolRunner, mapper: MetadataMapper) -> None:
        self.exiftool = exiftool
        self.mapper = mapper

    @staticmethod
    def _target_path(file_path: Path, strategy: str, raw_pref: str) -> tuple[Path, bool]:
        ext = file_path.suffix.lower()
        if ext in RAW_EXTENSIONS and strategy in {"sidecar_or_embedded", "embedded_or_sidecar"}:
            if raw_pref == "prefer_sidecar":
                return file_path.with_suffix(".xmp"), True
        return file_path, False

    def _action_args(self, action, sidecar_only: bool) -> list[str]:
        targets = self.mapper.field_targets(action.field, sidecar_only=sidecar_only)
        if not targets:
            return []

        args: list[str] = []
        if action.field == "keywords":
            values = action.to_value if isinstance(action.to_value, list) else []
            for tag in targets:
                if tag.upper().endswith("XPKEYWORDS"):
                    joined = "; ".join(values)
                    args.append(f"-{tag}={joined}")
                    continue
                args.append(f"-{tag}=")
                for keyword in values:
                    args.append(f"-{tag}+={keyword}")
            return args

        value = str(action.to_value)
        for tag in targets:
            args.append(f"-{tag}={value}")
        return args

    def apply(
        self,
        change_sets: list[FileChangeSet],
        raw_write_preference: str,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[int, int]:
        changed_files = 0
        changed_actions = 0

        actionable = [c for c in change_sets if c.actions]
        total = len(actionable)
        processed = 0

        for change_set in actionable:
            target_path, sidecar_only = self._target_path(
                change_set.file_path,
                change_set.write_strategy,
                raw_write_preference,
            )

            cmd_args: list[str] = []
            for action in change_set.actions:
                cmd_args.extend(self._action_args(action, sidecar_only=sidecar_only))

            if cmd_args:
                self.exiftool.write_with_args(target_path, cmd_args)
                changed_files += 1
                changed_actions += len(change_set.actions)

            processed += 1
            if progress_callback is not None:
                progress_callback(processed, total)

        return changed_files, changed_actions
