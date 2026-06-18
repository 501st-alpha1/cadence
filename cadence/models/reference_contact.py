from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cadence.models.base import BaseModel, new_id, now_utc


@dataclass
class ReferenceContact(BaseModel):
    person_id: str
    id: str = field(default_factory=new_id)
    relationship: Optional[str] = None     # e.g. "former manager", "colleague"
    how_long_known: Optional[str] = None   # e.g. "3 years"
    agreed_at: str = field(default_factory=now_utc)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> ReferenceContact:
        return cls(
            id=data["id"],
            person_id=data["person_id"],
            relationship=data.get("relationship"),
            how_long_known=data.get("how_long_known"),
            agreed_at=data["agreed_at"],
            notes=data.get("notes", ""),
        )
