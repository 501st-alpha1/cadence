from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cadence.models.base import BaseModel, new_id, now_utc


@dataclass
class Person(BaseModel):
    name: str
    id: str = field(default_factory=new_id)
    company_id: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    notes: str = ""
    created_at: str = field(default_factory=now_utc)

    @classmethod
    def from_dict(cls, data: dict) -> Person:
        return cls(
            id=data["id"],
            name=data["name"],
            company_id=data.get("company_id"),
            role=data.get("role"),
            email=data.get("email"),
            linkedin_url=data.get("linkedin_url"),
            notes=data.get("notes", ""),
            created_at=data["created_at"],
        )
