from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cadence.models.base import BaseModel, new_id, now_utc


@dataclass
class Company(BaseModel):
    display_name: str
    id: str = field(default_factory=new_id)
    domain: Optional[str] = None
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_utc)

    @classmethod
    def from_dict(cls, data: dict) -> Company:
        return cls(
            id=data["id"],
            display_name=data["display_name"],
            domain=data.get("domain"),
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
            created_at=data["created_at"],
        )
