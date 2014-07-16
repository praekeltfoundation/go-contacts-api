"""
Tests for riak contacts backend and collection.
"""

from twisted.trial.unittest import TestCase
from zope.interface.verify import verifyObject

from go_api.collections import ICollection

from go_contacts.backends.riak import (
    RiakContactsBackend, RiakContactsCollection)


class TestRiakContactsBackend(TestCase):
    def test_get_contacts_collection(self):
        backend = RiakContactsBackend()
        collection = backend.get_contact_collection("owner-1")
        self.assertEqual(collection.owner_id, "owner-1")
        self.assertTrue(isinstance(collection, RiakContactsCollection))


class TestRiakContactsCollection(TestCase):
    def test_collection_provides_ICollection(self):
        """
        The return value of .get_row_collection() is an object that provides
        ICollection.
        """
        collection = RiakContactsCollection("owner-1")
        verifyObject(ICollection, collection)

    def test_init(self):
        collection = RiakContactsCollection("owner-1")
        self.assertEqual(collection.owner_id, "owner-1")

    def test_get(self):
        collection = RiakContactsCollection("owner-1")
        self.assertEqual(collection.get("contact-1"), {})
