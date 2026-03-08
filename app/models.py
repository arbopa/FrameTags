from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Preset:
    name: str
    fields: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class FileMetadataSnapshot:
    file_path: Path
    values: dict[str, str | list[str]]


@dataclass(slots=True)
class FileChangeAction:
    field: str
    mode: str
    from_value: str | list[str]
    to_value: str | list[str]
    targets: list[str]


@dataclass(slots=True)
class FileChangeSet:
    file_path: Path
    existing: dict[str, str | list[str]]
    proposed: dict[str, str | list[str]]
    actions: list[FileChangeAction]
    write_strategy: str

    @property
    def changed_field_count(self) -> int:
        return len(self.actions)


@dataclass(slots=True)
class AppSettings:
    last_selected_preset: str = ""
    last_used_directories: list[str] = field(default_factory=list)
    recurse: bool = True
    write_mode: str = "overwrite"
    raw_write_preference: str = "prefer_sidecar"
    window_geometry: str = ""
