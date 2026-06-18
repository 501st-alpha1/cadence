from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cadence.models.base import BaseModel, new_id, now_utc


@dataclass
class TakeHome(BaseModel):
    application_id: str
    description: str
    id: str = field(default_factory=new_id)
    repo_url: Optional[str] = None
    due_at: Optional[str] = None
    submitted_at: Optional[str] = None
    notes: str = ""
    created_at: str = field(default_factory=now_utc)

    @property
    def is_submitted(self) -> bool:
        return self.submitted_at is not None

    @classmethod
    def from_dict(cls, data: dict) -> TakeHome:
        return cls(
            id=data["id"],
            application_id=data["application_id"],
            description=data["description"],
            repo_url=data.get("repo_url"),
            due_at=data.get("due_at"),
            submitted_at=data.get("submitted_at"),
            notes=data.get("notes", ""),
            created_at=data["created_at"],
        )
