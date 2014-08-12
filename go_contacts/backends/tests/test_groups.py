"""
Tests for riak groups backend and collection.
"""

from datetime import datetime

from twisted.internet.defer import inlineCallbacks, returnValue
from zope.interface.verify import verifyObject

from vumi.tests.helpers import VumiTestCase
from vumi.tests.helpers import PersistenceHelper

from go.vumitools.contact import ContactStore, ContactNotFoundError

from go_api.collections import ICollection
from go_api.collections.errors import (
    CollectionObjectNotFound, CollectionUsageError)

from go_contacts.backends.riak import (
    RiakGroupsBackend, RiakGroupsCollection)


class TestRiakGroupsBackend(VumiTestCase):
    def setUp(self):
        self.persistence_helper = self.add_helper(
            PersistenceHelper(use_riak=True, is_sync=False))

    @inlineCallbacks
    def mk_backend(self):
        manager = yield self.persistence_helper.get_riak_manager()
        backend = RiakGroupsBackend(manager)
        returnValue(backend)

    @inlineCallbacks
    def test_get_groups_collection(self):
        backend = yield self.mk_backend()
        collection = backend.get_contact_collection("owner-1")
        self.assertEqual(collection.contact_store.user_account_key, "owner-1")
        self.assertTrue(isinstance(collection, RiakGroupsCollection))


class TestRiakGroupsCollection(VumiTestCase):
    def setUp(self):
        self.persistence_helper = self.add_helper(
            PersistenceHelper(use_riak=True, is_sync=False))

    @inlineCallbacks
    def mk_collection(self, owner_id):
        manager = yield self.persistence_helper.get_riak_manager()
        contact_store = ContactStore(manager, owner_id)
        collection = RiakGroupsCollection(contact_store)
        returnValue(collection)

    EXPECTED_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

    GROUP_FIELD_DEFAULTS = {
        u'name': None,
        u'query': None,
        u'$VERSION': None,
    }

    def assert_group(self, group, expected_partial):
        expected = self.GROUP_FIELD_DEFAULTS.copy()
        expected.update(expected_partial)
        if isinstance(expected.get("created_at"), datetime):
            expected["created_at"] = expected["created_at"].strftime(
                self.EXPECTED_DATE_FORMAT)
        self.assertEqual(group, expected)

    @inlineCallbacks
    def test_get(self):
        collection = yield self.mk_collection("owner-1")
        new_group = yield collection.contact_store.new_group(name=u"Bob")
        group = yield collection.get(new_group.key)
        self.assert_group(group, {
            u'key': new_group.key,
            u'created_at': new_group.created_at,
            u'name': u'Bob',
            u'user_account': u'owner-1',
        })

    @inlineCallbacks
    def test_get_bad_key(self):
        collection = yield self.mk_collection("owner-1")
        error = ""
        try:
            group = yield collection.get('bad-key')
        except CollectionObjectNotFound, e:
            error = e
        self.assertEqual(str(e), "Group 'bad-key' not found.")
