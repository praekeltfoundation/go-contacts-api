"""
Tests for riak contacts backend and collection.
"""

from twisted.internet.defer import inlineCallbacks, returnValue

from vumi.tests.helpers import VumiTestCase
from vumi.tests.helpers import PersistenceHelper

from go.vumitools.contact import ContactStore

from go_contacts.backends.riak import (
    ContactsForGroupBackend, RiakContactsForGroupCollection)


class TestRiakContactsForGroupBackend(VumiTestCase):
    def setUp(self):
        self.persistence_helper = self.add_helper(
            PersistenceHelper(use_riak=True, is_sync=False))

    @inlineCallbacks
    def mk_backend(self):
        manager = yield self.persistence_helper.get_riak_manager()
        backend = ContactsForGroupBackend(manager, 10)
        returnValue(backend)

    @inlineCallbacks
    def test_get_contacts_collection(self):
        backend = yield self.mk_backend()
        collection = backend.get_model("owner-1")
        self.assertEqual(collection.contact_store.user_account_key, "owner-1")
        self.assertTrue(isinstance(collection, RiakContactsForGroupCollection))


class TestRiakContactsForGroupCollection(VumiTestCase):
    def setUp(self):
        self.persistence_helper = self.add_helper(
            PersistenceHelper(use_riak=True, is_sync=False))

    @inlineCallbacks
    def mk_collection(self, owner_id):
        manager = yield self.persistence_helper.get_riak_manager()
        contact_store = ContactStore(manager, owner_id)
        collection = RiakContactsForGroupCollection(contact_store, 10)
        returnValue(collection)

    @inlineCallbacks
    def test_init(self):
        collection = yield self.mk_collection("owner-1")
        self.assertEqual(collection.contact_store.user_account_key, "owner-1")
