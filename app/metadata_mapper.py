from __future__ import annotations

from .metadata_fields import FIELD_DEFS


class MetadataMapper:
    def all_target_tags(self) -> list[str]:
        tags: list[str] = []
        for field in FIELD_DEFS.values():
            tags.extend(field.targets)
        seen: set[str] = set()
        unique: list[str] = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique.append(tag)
        return unique

    def field_targets(self, field_key: str, sidecar_only: bool = False) -> list[str]:
        targets = list(FIELD_DEFS[field_key].targets)
        if sidecar_only:
            targets = [tag for tag in targets if tag.upper().startswith("XMP-")]
        return targets
