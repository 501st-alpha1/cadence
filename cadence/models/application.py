from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from cadence.models.base import BaseModel, new_id, now_utc


class ApplicationStatus(str, Enum):
    SAVED = "saved"
    APPLIED = "applied"
    PHONE_SCREEN = "phone_screen"
    INTERVIEW = "interview"
    OFFER = "offer"
    ACCEPTED = "accepted"
    WITHDRAWN = "withdrawn"
    REJECTED = "rejected"
    GHOSTED = "ghosted"
    DECLINED_OFFER = "declined_offer"
    POSITION_FILLED = "position_filled"
    PAUSED = "paused"


@dataclass
class StatusTransition(BaseModel):
    status: str
    at: str = field(default_factory=now_utc)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> StatusTransition:
        return cls(
            status=data["status"],
            at=data["at"],
            notes=data.get("notes", ""),
        )


@dataclass
class InterviewSession(BaseModel):
    interviewer_id: str
    id: str = field(default_factory=new_id)
    format: Optional[str] = None   # e.g. "technical", "behavioural", "system_design"
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> InterviewSession:
        return cls(
            id=data.get("id", new_id()),
            interviewer_id=data["interviewer_id"],
            format=data.get("format"),
            notes=data.get("notes", ""),
        )


@dataclass
class Interview(BaseModel):
    round_type: str   # "phone_screen", "technical", "onsite", "final", "other"
    scheduled_at: str
    id: str = field(default_factory=new_id)
    completed_at: Optional[str] = None
    thank_you_sent: bool = False
    sessions: list[InterviewSession] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> Interview:
        return cls(
            id=data.get("id", new_id()),
            round_type=data["round_type"],
            scheduled_at=data["scheduled_at"],
            completed_at=data.get("completed_at"),
            thank_you_sent=data.get("thank_you_sent", False),
            sessions=[InterviewSession.from_dict(s) for s in data.get("sessions", [])],
            notes=data.get("notes", ""),
        )


@dataclass
class ApplicationReference(BaseModel):
    reference_contact_id: str
    used_at: str = field(default_factory=now_utc)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> ApplicationReference:
        return cls(
            reference_contact_id=data["reference_contact_id"],
            used_at=data["used_at"],
            notes=data.get("notes", ""),
        )


@dataclass
class Application(BaseModel):
    company_id: str
    id: str = field(default_factory=new_id)
    job_description_id: Optional[str] = None
    role_title: Optional[str] = None          # fallback when no JD exists
    status_history: list[StatusTransition] = field(default_factory=list)
    follow_up_after_days: Optional[int] = None  # overrides global threshold
    resume_version: Optional[str] = None
    cover_letter: str = ""
    cover_letter_version: Optional[str] = None
    source: Optional[str] = None              # channel when no JD source exists
    notes: str = ""
    applied_at: Optional[str] = None
    interviews: list[Interview] = field(default_factory=list)
    application_references: list[ApplicationReference] = field(default_factory=list)
    created_at: str = field(default_factory=now_utc)

    @property
    def status(self) -> Optional[str]:
        if not self.status_history:
            return None
        return self.status_history[-1].status

    def transition(self, new_status: str, notes: str = "") -> None:
        self.status_history.append(StatusTransition(status=new_status, notes=notes))

    @classmethod
    def from_dict(cls, data: dict) -> Application:
        return cls(
            id=data["id"],
            company_id=data["company_id"],
            job_description_id=data.get("job_description_id"),
            role_title=data.get("role_title"),
            status_history=[StatusTransition.from_dict(s) for s in data.get("status_history", [])],
            follow_up_after_days=data.get("follow_up_after_days"),
            resume_version=data.get("resume_version"),
            cover_letter=data.get("cover_letter", ""),
            cover_letter_version=data.get("cover_letter_version"),
            source=data.get("source"),
            notes=data.get("notes", ""),
            applied_at=data.get("applied_at"),
            interviews=[Interview.from_dict(i) for i in data.get("interviews", [])],
            application_references=[
                ApplicationReference.from_dict(r)
                for r in data.get("application_references", [])
            ],
            created_at=data["created_at"],
        )
