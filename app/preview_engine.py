from __future__ import annotations

from pathlib import Path
from typing import Callable

from .metadata_fields import FIELD_DEFS, WRITE_STRATEGY
from .metadata_mapper import MetadataMapper
from .metadata_reader import MetadataReader
from .models import FileChangeAction, FileChangeSet


ProgressCallback = Callable[[str, int, int], None]


class PreviewEngine:
    def __init__(self, reader: MetadataReader, mapper: MetadataMapper) -> None:
        self.reader = reader
        self.mapper = mapper
        self.last_errors: list[str] = []

    @staticmethod
    def _split_keywords(text: str) -> list[str]:
        parts = text.replace(";", ",").split(",")
        return [p.strip() for p in parts if p.strip()]

    def build_changes(
        self,
        files: list[Path],
        selected_values: dict[str, str],
        write_mode: str,
        include_unchanged: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> list[FileChangeSet]:
        changes: list[FileChangeSet] = []
        snapshots, errors = self.reader.read_many_normalized(files, progress_callback=progress_callback)
        self.last_errors = list(errors)

        total = len(files)
        for idx, file_path in enumerate(files, start=1):
            snapshot = snapshots.get(file_path)
            if snapshot is None:
                continue

            existing = snapshot.values
            proposed = dict(existing)
            actions: list[FileChangeAction] = []

            for field_key, input_value in selected_values.items():
                field_def = FIELD_DEFS[field_key]
                from_value = existing.get(field_key, "")

                if field_def.keywords:
                    incoming_keywords = self._split_keywords(input_value)
                    current_keywords = from_value if isinstance(from_value, list) else []
                    if write_mode == "append_keywords":
                        lowered = {k.lower() for k in current_keywords}
                        appended = [k for k in incoming_keywords if k.lower() not in lowered]
                        if appended:
                            merged = current_keywords + appended
                            proposed[field_key] = merged
                            actions.append(
                                FileChangeAction(
                                    field=field_key,
                                    mode="append_keywords",
                                    from_value=current_keywords,
                                    to_value=merged,
                                    targets=self.mapper.field_targets(field_key),
                                )
                            )
                    elif write_mode == "write_if_empty":
                        if not current_keywords and incoming_keywords:
                            proposed[field_key] = incoming_keywords
                            actions.append(
                                FileChangeAction(
                                    field=field_key,
                                    mode="write_if_empty",
                                    from_value=current_keywords,
                                    to_value=incoming_keywords,
                                    targets=self.mapper.field_targets(field_key),
                                )
                            )
                    else:
                        if incoming_keywords != current_keywords:
                            proposed[field_key] = incoming_keywords
                            actions.append(
                                FileChangeAction(
                                    field=field_key,
                                    mode="overwrite",
                                    from_value=current_keywords,
                                    to_value=incoming_keywords,
                                    targets=self.mapper.field_targets(field_key),
                                )
                            )
                    continue

                incoming_text = input_value.strip()
                current_text = str(from_value).strip()
                if write_mode == "write_if_empty":
                    if current_text == "" and incoming_text:
                        proposed[field_key] = incoming_text
                        actions.append(
                            FileChangeAction(
                                field=field_key,
                                mode="write_if_empty",
                                from_value=current_text,
                                to_value=incoming_text,
                                targets=self.mapper.field_targets(field_key),
                            )
                        )
                else:
                    if incoming_text != current_text:
                        proposed[field_key] = incoming_text
                        actions.append(
                            FileChangeAction(
                                field=field_key,
                                mode="overwrite",
                                from_value=current_text,
                                to_value=incoming_text,
                                targets=self.mapper.field_targets(field_key),
                            )
                        )

            strategy = WRITE_STRATEGY.get(file_path.suffix.lower(), "embedded")
            if actions or include_unchanged:
                changes.append(
                    FileChangeSet(
                        file_path=file_path,
                        existing=existing,
                        proposed=proposed,
                        actions=actions,
                        write_strategy=strategy,
                    )
                )

            if progress_callback is not None:
                progress_callback("Building change sets", idx, total)

        return changes
