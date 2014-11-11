"""
Tests for riak contacts backend and collection.
"""

from datetime import datetime

from twisted.internet.defer import inlineCallbacks, returnValue

from vumi.tests.helpers import VumiTestCase
from vumi.tests.helpers import PersistenceHelper

from go.vumitools.contact import ContactStore

from go_api.cyclone.helpers import HandlerHelper, AppHelper

from go_contacts.backends.riak import (
    ContactsForGroupBackend, RiakContactsForGroupCollection,
    ContactsForGroupHandler)


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

    EXPECTED_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

    CONTACT_FIELD_DEFAULTS = {
        u'$VERSION': 2,
        u'bbm_pin': None,
        u'dob': None,
        u'email_address': None,
        u'facebook_id': None,
        u'groups': [],
        u'gtalk_id': None,
        u'mxit_id': None,
        u'name': None,
        u'surname': None,
        u'twitter_handle': None,
        u'wechat_id': None,
        u'extra': {},
        u'subscription': {},
    }

    def assert_contact(self, contact, expected_partial):
        expected = self.CONTACT_FIELD_DEFAULTS.copy()
        expected.update(expected_partial)
        if isinstance(expected.get("created_at"), datetime):
            expected["created_at"] = expected["created_at"].strftime(
                self.EXPECTED_DATE_FORMAT)
        self.assertEqual(contact, expected)

    @inlineCallbacks
    def test_init(self):
        collection = yield self.mk_collection("owner-1")
        self.assertEqual(collection.contact_store.user_account_key, "owner-1")


class TestContactsForGroupHandler(VumiTestCase):
    @inlineCallbacks
    def setUp(self):
        self.persistence_helper = self.add_helper(
            PersistenceHelper(use_riak=True, is_sync=False))
        self.collection = yield self.mk_collection('owner-1')
        self.model_factory = lambda req: self.collection
        self.handler_helper = HandlerHelper(
            ContactsForGroupHandler,
            handler_kwargs={'model_factory': self.model_factory})
        self.app_helper = AppHelper(
            urlspec=ContactsForGroupHandler.mk_urlspec(
                '/root', self.model_factory))

    @inlineCallbacks
    def mk_collection(self, owner_id):
        manager = yield self.persistence_helper.get_riak_manager()
        contact_store = ContactStore(manager, owner_id)
        collection = RiakContactsForGroupCollection(contact_store, 10)
        returnValue(collection)

    @inlineCallbacks
    def test_get_stream_with_query(self):
        data = yield self.app_helper.get(
            '/root/1/contacts?stream=true&query=foo', parser='json')
        self.assertEqual(data[u'status_code'], 500)
        self.assertEqual(data[u'reason'], 'query parameter not supported')
