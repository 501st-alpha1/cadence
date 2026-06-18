from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cadence.models.base import BaseModel, new_id, now_utc


@dataclass
class RequestedDocument(BaseModel):
    type: str                        # e.g. "resume", "cover_letter", "references", "portfolio"
    requested_at: str = field(default_factory=now_utc)
    sent_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> RequestedDocument:
        return cls(
            type=data["type"],
            requested_at=data["requested_at"],
            sent_at=data.get("sent_at"),
        )


@dataclass
class Message(BaseModel):
    direction: str                   # "inbound" | "outbound"
    channel: str                     # "email" | "linkedin" | "phone" | "other"
    body: str
    id: str = field(default_factory=new_id)
    application_id: Optional[str] = None
    person_id: Optional[str] = None
    subject: Optional[str] = None
    requested_documents: list[RequestedDocument] = field(default_factory=list)
    sent_at: str = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        if not self.application_id and not self.person_id:
            raise ValueError("Message must have at least one of application_id or person_id")

    @classmethod
    def from_dict(cls, data: dict) -> Message:
        return cls(
            id=data["id"],
            direction=data["direction"],
            channel=data["channel"],
            body=data["body"],
            application_id=data.get("application_id"),
            person_id=data.get("person_id"),
            subject=data.get("subject"),
            requested_documents=[
                RequestedDocument.from_dict(d)
                for d in data.get("requested_documents", [])
            ],
            sent_at=data["sent_at"],
        )
