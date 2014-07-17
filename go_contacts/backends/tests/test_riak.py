"""
Tests for riak contacts backend and collection.
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
    RiakContactsBackend, RiakContactsCollection)


class TestRiakContactsBackend(VumiTestCase):
    def setUp(self):
        self.persistence_helper = self.add_helper(
            PersistenceHelper(use_riak=True, is_sync=False))

    @inlineCallbacks
    def mk_backend(self):
        manager = yield self.persistence_helper.get_riak_manager()
        backend = RiakContactsBackend(manager)
        returnValue(backend)

    @inlineCallbacks
    def test_get_contacts_collection(self):
        backend = yield self.mk_backend()
        collection = backend.get_contact_collection("owner-1")
        self.assertEqual(collection.contact_store.user_account_key, "owner-1")
        self.assertTrue(isinstance(collection, RiakContactsCollection))


class TestRiakContactsCollection(VumiTestCase):
    def setUp(self):
        self.persistence_helper = self.add_helper(
            PersistenceHelper(use_riak=True, is_sync=False))

    @inlineCallbacks
    def mk_collection(self, owner_id):
        manager = yield self.persistence_helper.get_riak_manager()
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

    def test_pick_fields(self):
        pick_fields = RiakContactsCollection._pick_fields
        self.assertEqual(
            pick_fields({"a": "1", "b": "2"}, ["a", "c"]),
            {"a": "1"})

    def test_pick_contact_fields(self):
        pick_contact_fields = RiakContactsCollection._pick_contact_fields
        self.assertEqual(
            pick_contact_fields({"msisdn": "+12345", "notfield": "xyz"}),
            {"msisdn": "+12345"})

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
        d = collection.get("bad-contact-id")
        err = yield self.failUnlessFailure(d, CollectionObjectNotFound)
        self.assertEqual(str(err), "Contact 'bad-contact-id' not found.")

    @inlineCallbacks
    def test_create(self):
        collection = yield self.mk_collection("owner-1")
        key, contact = yield collection.create(None, {
            "msisdn": u"+12345",
            "name": u"Arthur",
            "surname": u"of Camelot",
        })
        new_contact = yield collection.contact_store.get_contact_by_key(key)
        self.assert_contact(contact, {
            u'key': new_contact.key,
            u'created_at': new_contact.created_at,
            u'msisdn': u'+12345',
            u'name': u'Arthur',
            u'surname': u'of Camelot',
            u'user_account': u'owner-1',
        })

    @inlineCallbacks
    def test_update(self):
        collection = yield self.mk_collection("owner-1")
        new_contact = yield collection.contact_store.new_contact(
            name=u"Bob", msisdn=u"+12345")
        contact = yield collection.update(new_contact.key, {
            "msisdn": u"+6789",
        })
        self.assert_contact(contact, {
            u'key': new_contact.key,
            u'created_at': new_contact.created_at,
            u'msisdn': u"+6789",
            u'name': u'Bob',
            u'user_account': u'owner-1',
        })

    @inlineCallbacks
    def test_update_non_existent_contact(self):
        collection = yield self.mk_collection("owner-1")
        d = collection.update("bad-contact-id", {})
        err = yield self.failUnlessFailure(d, CollectionObjectNotFound)
        self.assertEqual(str(err), "Contact 'bad-contact-id' not found.")

    @inlineCallbacks
    def test_update_invalid_fields(self):
        collection = yield self.mk_collection("owner-1")
        new_contact = yield collection.contact_store.new_contact(
            name=u"Bob", msisdn=u"+12345")
        d = collection.update(new_contact.key, {
            "unknown_field": u"foo",
            "not_the_field": u"bar",
        })
        err = yield self.failUnlessFailure(d, CollectionUsageError)
        self.assertEqual(
            str(err), "Invalid contact fields: not_the_field, unknown_field")

    @inlineCallbacks
    def test_delete(self):
        collection = yield self.mk_collection("owner-1")
        new_contact = yield collection.contact_store.new_contact(
            name=u"Bob", msisdn=u"+12345")
        contact = yield collection.delete(new_contact.key)
        self.assert_contact(contact, {
            u'key': new_contact.key,
            u'created_at': new_contact.created_at,
            u'msisdn': u'+12345',
            u'name': u'Bob',
            u'user_account': u'owner-1',
        })
        d = collection.contact_store.get_contact_by_key("owner-1")
        yield self.failUnlessFailure(d, ContactNotFoundError)

    @inlineCallbacks
    def test_delete_non_existent_contact(self):
        collection = yield self.mk_collection("owner-1")
        d = collection.delete("bad-contact-id")
        err = yield self.failUnlessFailure(d, CollectionObjectNotFound)
        self.assertEqual(str(err), "Contact 'bad-contact-id' not found.")
