"""
Tests for riak contacts backend and collection.
"""

from datetime import datetime

from twisted.internet.defer import inlineCallbacks, returnValue
from zope.interface.verify import verifyObject

from vumi.tests.helpers import VumiTestCase
from vumi.persist.txriak_manager import TxRiakManager

from go.vumitools.contact import ContactStore

from go_api.collections import ICollection

from go_contacts.backends.riak import (
    RiakContactsBackend, RiakContactsCollection)


@inlineCallbacks
def create_riak_manager(config, add_cleanup):
    manager = TxRiakManager.from_config(config)
    add_cleanup(manager.purge_all)
    yield manager.purge_all()
    returnValue(manager)


class TestRiakContactsBackend(VumiTestCase):
    @inlineCallbacks
    def mk_backend(self):
        manager = yield create_riak_manager(
            {'bucket_prefix': 'test.'}, self.add_cleanup)
        backend = RiakContactsBackend(manager)
        returnValue(backend)

    @inlineCallbacks
    def test_get_contacts_collection(self):
        backend = yield self.mk_backend()
        collection = backend.get_contact_collection("owner-1")
        self.assertEqual(collection.contact_store.user_account_key, "owner-1")
        self.assertTrue(isinstance(collection, RiakContactsCollection))


class TestRiakContactsCollection(VumiTestCase):
    @inlineCallbacks
    def mk_collection(self, owner_id):
        manager = yield create_riak_manager(
            {'bucket_prefix': 'test.'}, self.add_cleanup)
        contact_store = ContactStore(manager, owner_id)
        collection = RiakContactsCollection(contact_store)
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
    }

    def assert_contact(self, contact, expected_partial):
        expected = self.CONTACT_FIELD_DEFAULTS.copy()
        expected.update(expected_partial)
        if isinstance(expected.get("created_at"), datetime):
            expected["created_at"] = expected["created_at"].strftime(
                self.EXPECTED_DATE_FORMAT)
        self.assertEqual(contact, expected)

    @inlineCallbacks
    def test_collection_provides_ICollection(self):
        """
        The return value of .get_row_collection() is an object that provides
        ICollection.
        """
        collection = yield self.mk_collection("owner-1")
        verifyObject(ICollection, collection)

    @inlineCallbacks
    def test_init(self):
        collection = yield self.mk_collection("owner-1")
        self.assertEqual(collection.contact_store.user_account_key, "owner-1")

    @inlineCallbacks
    def test_get(self):
        collection = yield self.mk_collection("owner-1")
        new_contact = yield collection.contact_store.new_contact(
            name=u"Bob", msisdn=u"+12345")
        contact = yield collection.get(new_contact.key)
        self.assert_contact(contact, {
            u'key': new_contact.key,
            u'created_at': new_contact.created_at,
            u'msisdn': u'+12345',
            u'name': u'Bob',
            u'user_account': u'owner-1',
        })

    @inlineCallbacks
    def test_get_non_existent_contact(self):
        collection = yield self.mk_collection("owner-1")
        contact = yield collection.get("bad-contact-id")
        self.assertEqual(contact, None)
