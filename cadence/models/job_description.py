from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cadence.models.base import BaseModel, new_id, now_utc


@dataclass
class JobDescription(BaseModel):
    company_id: str
    title: str
    id: str = field(default_factory=new_id)
    url: Optional[str] = None
    body: str = ""
    source: Optional[str] = None   # e.g. "linkedin", "hacker_news", "referral"
    captured_at: str = field(default_factory=now_utc)
    closes_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> JobDescription:
        return cls(
            id=data["id"],
            company_id=data["company_id"],
            title=data["title"],
            url=data.get("url"),
            body=data.get("body", ""),
            source=data.get("source"),
            captured_at=data["captured_at"],
            closes_at=data.get("closes_at"),
        )
