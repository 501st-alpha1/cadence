from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize(obj: Any) -> Any:
    """JSON serialization helper for types dataclasses don't handle."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Cannot serialize {type(obj)}")


@dataclass
class BaseModel:
    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=_serialize)

    @classmethod
    def from_dict(cls, data: dict) -> "BaseModel":
        raise NotImplementedError

    @classmethod
    def from_json(cls, text: str) -> "BaseModel":
        return cls.from_dict(json.loads(text))
