"""Tests for cadence models and storage layer."""

import json
import pathlib
import sys
import tempfile
import unittest
import unittest.mock as mock

# Stub out CLI deps so tests don't require them installed
for mod in ["click", "rich", "rich.console", "rich.table", "rich.rule"]:
    sys.modules.setdefault(mod, mock.MagicMock())

from cadence.config import Config
from cadence.models import (
    Application, Company, JobDescription, Message,
    Offer, Person, ReferenceContact, TakeHome,
)
from cadence.models.application import (
    ApplicationReference, Interview, InterviewSession,
)
from cadence.models.offer import OfferVersion
from cadence.models.message import RequestedDocument
from cadence.storage import Store


def make_store(tmp: str) -> Store:
    pub = pathlib.Path(tmp) / "public"
    priv = pathlib.Path(tmp) / "private"
    pub.mkdir()
    priv.mkdir()
    config = Config({"repos": {"public": str(pub), "private": str(priv)}, "thresholds": {}})
    return Store(config)


class TestCompanyModel(unittest.TestCase):
    def test_roundtrip(self):
        c = Company(display_name="Acme", domain="acme.com", tags=["tech", "startup"])
        c2 = Company.from_dict(c.to_dict())
        self.assertEqual(c.id, c2.id)
        self.assertEqual(c.display_name, c2.display_name)
        self.assertEqual(c.tags, c2.tags)

    def test_json_roundtrip(self):
        c = Company(display_name="Beta")
        c2 = Company.from_json(c.to_json())
        self.assertEqual(c.id, c2.id)


class TestApplicationModel(unittest.TestCase):
    def test_status_history(self):
        a = Application(company_id="co-1", role_title="Engineer")
        self.assertIsNone(a.status)
        a.transition("applied")
        a.transition("phone_screen", notes="went well")
        self.assertEqual(a.status, "phone_screen")
        self.assertEqual(len(a.status_history), 2)

    def test_status_history_roundtrip(self):
        a = Application(company_id="co-1", role_title="Engineer")
        a.transition("applied")
        a.transition("interview")
        a2 = Application.from_dict(a.to_dict())
        self.assertEqual(a2.status, "interview")
        self.assertEqual(len(a2.status_history), 2)

    def test_interviews_embedded(self):
        a = Application(company_id="co-1")
        iv = Interview(round_type="technical", scheduled_at="2026-07-01T10:00:00Z")
        iv.sessions.append(InterviewSession(interviewer_id="person-1", format="technical"))
        a.interviews.append(iv)
        a2 = Application.from_dict(a.to_dict())
        self.assertEqual(len(a2.interviews), 1)
        self.assertEqual(len(a2.interviews[0].sessions), 1)
        self.assertFalse(a2.interviews[0].thank_you_sent)

    def test_application_references_embedded(self):
        a = Application(company_id="co-1")
        a.application_references.append(
            ApplicationReference(reference_contact_id="ref-1")
        )
        a2 = Application.from_dict(a.to_dict())
        self.assertEqual(len(a2.application_references), 1)


class TestOfferModel(unittest.TestCase):
    def test_versions(self):
        o = Offer(
            application_id="app-1",
            versions=[OfferVersion(compensation="100k")],
        )
        o.versions.append(OfferVersion(compensation="110k", notes="after counter"))
        self.assertEqual(o.current_terms.compensation, "110k")
        o2 = Offer.from_dict(o.to_dict())
        self.assertEqual(len(o2.versions), 2)
        self.assertEqual(o2.current_terms.compensation, "110k")


class TestMessageModel(unittest.TestCase):
    def test_requires_context(self):
        with self.assertRaises(ValueError):
            Message(direction="inbound", channel="email", body="hi")

    def test_requested_documents_roundtrip(self):
        msg = Message(
            direction="inbound",
            channel="email",
            body="Please send your resume",
            person_id="p-1",
            requested_documents=[RequestedDocument(type="resume")],
        )
        msg2 = Message.from_dict(msg.to_dict())
        self.assertEqual(len(msg2.requested_documents), 1)
        self.assertIsNone(msg2.requested_documents[0].sent_at)


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = make_store(self.tmp)

    def test_company_crud(self):
        c = Company(display_name="Beta Inc", domain="beta.io")
        self.store.save_company(c)
        c2 = self.store.get_company(c.id)
        self.assertIsNotNone(c2)
        self.assertEqual(c2.display_name, "Beta Inc")

    def test_company_not_found(self):
        result = self.store.get_company("nonexistent-id")
        self.assertIsNone(result)

    def test_find_company_by_prefix(self):
        self.store.save_company(Company(display_name="Alpha Corp"))
        self.store.save_company(Company(display_name="Beta Inc"))
        results = self.store.find_company("alp")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].display_name, "Alpha Corp")

    def test_find_company_ambiguous(self):
        self.store.save_company(Company(display_name="Alpha One"))
        self.store.save_company(Company(display_name="Alpha Two"))
        results = self.store.find_company("alpha")
        self.assertEqual(len(results), 2)

    def test_application_persists_status_history(self):
        a = Application(company_id="co-1", role_title="SWE")
        a.transition("applied")
        a.transition("phone_screen")
        self.store.save_application(a)
        a2 = self.store.get_application(a.id)
        self.assertEqual(a2.status, "phone_screen")
        self.assertEqual(len(a2.status_history), 2)

    def test_messages_for_application(self):
        p = Person(name="Jane")
        self.store.save_person(p)
        a = Application(company_id="co-1")
        a.transition("applied")
        self.store.save_application(a)

        m1 = Message(direction="inbound", channel="email",
                     body="Hi", application_id=a.id, person_id=p.id)
        m2 = Message(direction="outbound", channel="email",
                     body="Thanks", application_id=a.id)
        m_other = Message(direction="inbound", channel="linkedin",
                          body="Other", person_id=p.id)
        for m in [m1, m2, m_other]:
            self.store.save_message(m)

        app_msgs = self.store.messages_for_application(a.id)
        self.assertEqual(len(app_msgs), 2)

    def test_offer_for_application(self):
        a = Application(company_id="co-1")
        a.transition("applied")
        self.store.save_application(a)

        o = Offer(application_id=a.id,
                  versions=[OfferVersion(compensation="120k")])
        self.store.save_offer(o)

        result = self.store.offer_for_application(a.id)
        self.assertIsNotNone(result)
        self.assertEqual(result.current_terms.compensation, "120k")

    def test_find_application_by_prefix(self):
        a = Application(company_id="co-1", role_title="Engineer")
        a.transition("started")
        self.store.save_application(a)

        results = self.store.find_application(a.id[:6])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, a.id)

    def test_find_application_no_match(self):
        results = self.store.find_application("zzzzzzzz")
        self.assertEqual(results, [])

    def test_find_job_description_by_prefix(self):
        jd = JobDescription(company_id="co-1", title="Backend Engineer")
        self.store.save_job_description(jd)
        results = self.store.find_job_description(jd.id[:6])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Backend Engineer")

    def test_find_offer_by_prefix(self):
        a = Application(company_id="co-1")
        self.store.save_application(a)
        o = Offer(application_id=a.id, versions=[OfferVersion(compensation="100k")])
        self.store.save_offer(o)
        results = self.store.find_offer(o.id[:6])
        self.assertEqual(len(results), 1)

    def test_find_reference_contact_by_prefix(self):
        rc = ReferenceContact(person_id="p-1", relationship="former manager")
        self.store.save_reference_contact(rc)
        results = self.store.find_reference_contact(rc.id[:6])
        self.assertEqual(len(results), 1)

    def test_all_companies_empty(self):
        results = list(self.store.all_companies())
        self.assertEqual(results, [])

    def test_dirs_created(self):
        pub = pathlib.Path(self.tmp) / "public"
        priv = pathlib.Path(self.tmp) / "private"
        self.assertTrue((pub / "companies").exists())
        self.assertTrue((priv / "applications").exists())
        self.assertTrue((priv / "references").exists())


if __name__ == "__main__":
    unittest.main()
