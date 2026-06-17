"""Project-scoped key-value memory. Stub for Phase 0."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(slots=True)
class MemoryEntry:
    key: str
    value: str
    source: str | None
    created_at: datetime
    updated_at: datetime


class ProjectMemory:
    """In-memory project memory. SQLite-backed in Phase 1.

    Thread-safety: not thread-safe. Wrap in a lock if shared.
    """

    def __init__(self, project_id: str) -> None:
        self._project_id = project_id
        self._entries: dict[str, MemoryEntry] = {}

    @property
    def project_id(self) -> str:
        return self._project_id

    def get(self, key: str) -> str | None:
        entry = self._entries.get(key)
        return entry.value if entry is not None else None

    def set(self, key: str, value: str, *, source: str | None = None) -> None:
        now = datetime.now(UTC)
        existing = self._entries.get(key)
        if existing is not None:
            existing.value = value
            existing.updated_at = now
            if source is not None:
                existing.source = source
        else:
            self._entries[key] = MemoryEntry(
                key=key, value=value, source=source, created_at=now, updated_at=now
            )

    def delete(self, key: str) -> bool:
        return self._entries.pop(key, None) is not None

    def all(self) -> dict[str, str]:
        return {k: v.value for k, v in self._entries.items()}

    def group_by_prefix(self) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = defaultdict(dict)
        for k, v in self._entries.items():
            prefix, _, rest = k.partition(".")
            out[prefix][rest] = v.value
        return dict(out)
