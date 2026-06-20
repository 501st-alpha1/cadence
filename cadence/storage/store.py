from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterator, Optional, Type, TypeVar

from cadence.config import Config
from cadence.models.base import BaseModel
from cadence.models.company import Company
from cadence.models.job_description import JobDescription
from cadence.models.person import Person
from cadence.models.application import Application
from cadence.models.message import Message
from cadence.models.offer import Offer
from cadence.models.take_home import TakeHome
from cadence.models.reference_contact import ReferenceContact

T = TypeVar("T", bound=BaseModel)


class Store:
    """
    Thin filesystem abstraction over the two data repos.

    Public repo:  companies/, job_descriptions/
    Private repo: applications/, people/, messages/, offers/,
                  take_homes/, references/
    """

    def __init__(self, config: Config) -> None:
        self._public = config.public_repo
        self._private = config.private_repo
        self._ensure_dirs()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _ensure_dirs(self) -> None:
        for repo, dirs in [
            (self._public, ["companies", "job_descriptions"]),
            (self._private, ["applications", "people", "messages",
                             "offers", "take_homes", "references"]),
        ]:
            for d in dirs:
                (repo / d).mkdir(parents=True, exist_ok=True)

    def _path(self, repo: Path, collection: str, id: str) -> Path:
        return repo / collection / f"{id}.json"

    def _write(self, repo: Path, collection: str, model: BaseModel) -> Path:
        path = self._path(repo, collection, model.id)  # type: ignore[attr-defined]
        path.write_text(model.to_json(), encoding="utf-8")
        return path

    def _read(self, repo: Path, collection: str, id: str,
              factory: Callable[[dict], T]) -> Optional[T]:
        path = self._path(repo, collection, id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return factory(data)

    def _all(self, repo: Path, collection: str,
             factory: Callable[[dict], T]) -> Iterator[T]:
        directory = repo / collection
        if not directory.exists():
            return
        for path in sorted(directory.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            yield factory(data)

    def _delete(self, repo: Path, collection: str, id: str) -> bool:
        path = self._path(repo, collection, id)
        if path.exists():
            path.unlink()
            return True
        return False

    def _find_by_id_prefix(self, items: Iterator[T], query: str) -> list[T]:
        """Match items whose id starts with query (case-insensitive)."""
        q = query.lower()
        return [item for item in items if item.id.lower().startswith(q)]  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # Public repo — Companies
    # ------------------------------------------------------------------ #

    def save_company(self, company: Company) -> Path:
        return self._write(self._public, "companies", company)

    def get_company(self, id: str) -> Optional[Company]:
        return self._read(self._public, "companies", id, Company.from_dict)

    def all_companies(self) -> Iterator[Company]:
        return self._all(self._public, "companies", Company.from_dict)

    def find_company(self, query: str) -> list[Company]:
        """Find companies by ID prefix or name prefix."""
        by_id = self._find_by_id_prefix(self.all_companies(), query)
        if by_id:
            return by_id
        q = query.lower()
        return [c for c in self.all_companies() if c.display_name.lower().startswith(q)]

    # ------------------------------------------------------------------ #
    # Public repo — Job Descriptions
    # ------------------------------------------------------------------ #

    def save_job_description(self, jd: JobDescription) -> Path:
        return self._write(self._public, "job_descriptions", jd)

    def get_job_description(self, id: str) -> Optional[JobDescription]:
        return self._read(self._public, "job_descriptions", id, JobDescription.from_dict)

    def all_job_descriptions(self) -> Iterator[JobDescription]:
        return self._all(self._public, "job_descriptions", JobDescription.from_dict)

    def find_job_description(self, query: str) -> list[JobDescription]:
        """Find job descriptions by ID prefix."""
        return self._find_by_id_prefix(self.all_job_descriptions(), query)

    # ------------------------------------------------------------------ #
    # Private repo — People
    # ------------------------------------------------------------------ #

    def save_person(self, person: Person) -> Path:
        return self._write(self._private, "people", person)

    def get_person(self, id: str) -> Optional[Person]:
        return self._read(self._private, "people", id, Person.from_dict)

    def all_people(self) -> Iterator[Person]:
        return self._all(self._private, "people", Person.from_dict)

    def find_person(self, query: str) -> list[Person]:
        """Find people by ID prefix or name prefix."""
        by_id = self._find_by_id_prefix(self.all_people(), query)
        if by_id:
            return by_id
        q = query.lower()
        return [p for p in self.all_people() if p.name.lower().startswith(q)]

    # ------------------------------------------------------------------ #
    # Private repo — Applications
    # ------------------------------------------------------------------ #

    def save_application(self, app: Application) -> Path:
        return self._write(self._private, "applications", app)

    def get_application(self, id: str) -> Optional[Application]:
        return self._read(self._private, "applications", id, Application.from_dict)

    def all_applications(self) -> Iterator[Application]:
        return self._all(self._private, "applications", Application.from_dict)

    def find_application(self, query: str) -> list[Application]:
        """Find applications by ID prefix."""
        return self._find_by_id_prefix(self.all_applications(), query)

    # ------------------------------------------------------------------ #
    # Private repo — Messages
    # ------------------------------------------------------------------ #

    def save_message(self, message: Message) -> Path:
        return self._write(self._private, "messages", message)

    def get_message(self, id: str) -> Optional[Message]:
        return self._read(self._private, "messages", id, Message.from_dict)

    def all_messages(self) -> Iterator[Message]:
        return self._all(self._private, "messages", Message.from_dict)

    def find_message(self, query: str) -> list[Message]:
        """Find messages by ID prefix."""
        return self._find_by_id_prefix(self.all_messages(), query)

    def messages_for_application(self, application_id: str) -> list[Message]:
        return [m for m in self.all_messages() if m.application_id == application_id]

    def messages_for_person(self, person_id: str) -> list[Message]:
        return [m for m in self.all_messages() if m.person_id == person_id]

    # ------------------------------------------------------------------ #
    # Private repo — Offers
    # ------------------------------------------------------------------ #

    def save_offer(self, offer: Offer) -> Path:
        return self._write(self._private, "offers", offer)

    def get_offer(self, id: str) -> Optional[Offer]:
        return self._read(self._private, "offers", id, Offer.from_dict)

    def all_offers(self) -> Iterator[Offer]:
        return self._all(self._private, "offers", Offer.from_dict)

    def find_offer(self, query: str) -> list[Offer]:
        """Find offers by ID prefix."""
        return self._find_by_id_prefix(self.all_offers(), query)

    def offer_for_application(self, application_id: str) -> Optional[Offer]:
        for offer in self.all_offers():
            if offer.application_id == application_id:
                return offer
        return None

    # ------------------------------------------------------------------ #
    # Private repo — Take-homes
    # ------------------------------------------------------------------ #

    def save_take_home(self, take_home: TakeHome) -> Path:
        return self._write(self._private, "take_homes", take_home)

    def get_take_home(self, id: str) -> Optional[TakeHome]:
        return self._read(self._private, "take_homes", id, TakeHome.from_dict)

    def all_take_homes(self) -> Iterator[TakeHome]:
        return self._all(self._private, "take_homes", TakeHome.from_dict)

    def find_take_home(self, query: str) -> list[TakeHome]:
        """Find take-homes by ID prefix."""
        return self._find_by_id_prefix(self.all_take_homes(), query)

    def take_home_for_application(self, application_id: str) -> Optional[TakeHome]:
        for th in self.all_take_homes():
            if th.application_id == application_id:
                return th
        return None

    # ------------------------------------------------------------------ #
    # Private repo — Reference Contacts
    # ------------------------------------------------------------------ #

    def save_reference_contact(self, ref: ReferenceContact) -> Path:
        return self._write(self._private, "references", ref)

    def get_reference_contact(self, id: str) -> Optional[ReferenceContact]:
        return self._read(self._private, "references", id, ReferenceContact.from_dict)

    def all_reference_contacts(self) -> Iterator[ReferenceContact]:
        return self._all(self._private, "references", ReferenceContact.from_dict)

    def find_reference_contact(self, query: str) -> list[ReferenceContact]:
        """Find reference contacts by ID prefix."""
        return self._find_by_id_prefix(self.all_reference_contacts(), query)
