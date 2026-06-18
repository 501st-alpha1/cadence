from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from cadence.models.base import BaseModel, new_id, now_utc


class OfferStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPLODED = "exploded"   # offer expired before decision


@dataclass
class OfferVersion(BaseModel):
    compensation: str
    at: str = field(default_factory=now_utc)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> OfferVersion:
        return cls(
            compensation=data["compensation"],
            at=data["at"],
            notes=data.get("notes", ""),
        )


@dataclass
class Offer(BaseModel):
    application_id: str
    id: str = field(default_factory=new_id)
    versions: list[OfferVersion] = field(default_factory=list)
    status: str = OfferStatus.PENDING
    expires_at: Optional[str] = None
    received_at: str = field(default_factory=now_utc)
    notes: str = ""

    @property
    def current_terms(self) -> Optional[OfferVersion]:
        if not self.versions:
            return None
        return self.versions[-1]

    @classmethod
    def from_dict(cls, data: dict) -> Offer:
        return cls(
            id=data["id"],
            application_id=data["application_id"],
            versions=[OfferVersion.from_dict(v) for v in data.get("versions", [])],
            status=data.get("status", OfferStatus.PENDING),
            expires_at=data.get("expires_at"),
            received_at=data["received_at"],
            notes=data.get("notes", ""),
        )
