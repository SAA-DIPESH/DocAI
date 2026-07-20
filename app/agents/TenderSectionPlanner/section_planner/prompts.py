from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .settings import Settings


@dataclass(frozen=True)
class PromptDocument:
    name: str
    content: str
    sha256: str
    modified_at: str | None


@dataclass(frozen=True)
class PlannerPrompts:
    constitution: PromptDocument
    specification: PromptDocument
    user_prompt: PromptDocument

    @property
    def hashes(self) -> dict[str, str]:
        return {
            "Constitution": self.constitution.sha256,
            "Specification": self.specification.sha256,
            "UserPrompt": self.user_prompt.sha256,
        }


class PromptLoader:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def _read(path: Path) -> PromptDocument:
        content = path.read_text(encoding="utf-8")
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        return PromptDocument(
            name=path.name,
            content=content,
            sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            modified_at=modified,
        )

    def load(self) -> PlannerPrompts:
        self.settings.validate()
        return PlannerPrompts(
            constitution=self._read(self.settings.constitution_path),
            specification=self._read(self.settings.specification_path),
            user_prompt=self._read(self.settings.user_prompt_path),
        )
