"""
Tests for riak contacts backend and collection.
"""

from twisted.internet.defer import inlineCallbacks, returnValue

from vumi.tests.helpers import VumiTestCase
from vumi.tests.helpers import PersistenceHelper

from go_api.queue import PausingQueueCloseMarker
from go.vumitools.contact import ContactStore

from go_contacts.backends.riak import (
    ContactsForGroupBackend, RiakContactsForGroupModel, group_to_dict,
    contact_to_dict)


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
        self.assertTrue(isinstance(collection, RiakContactsForGroupModel))


class TestRiakContactsForGroupModel(VumiTestCase):
    def setUp(self):
        self.persistence_helper = self.add_helper(
            PersistenceHelper(use_riak=True, is_sync=False))

    @inlineCallbacks
    def mk_collection(self, owner_id):
        manager = yield self.persistence_helper.get_riak_manager()
        contact_store = ContactStore(manager, owner_id)
        yield contact_store.contacts.enable_search()
        collection = RiakContactsForGroupModel(contact_store, 10)
        returnValue(collection)

    @inlineCallbacks
    def create_group(self, collection, name, query=None):
        if query is None:
            group = yield collection.contact_store.new_group(name)
        else:
            group = yield collection.contact_store.new_smart_group(name, query)
        returnValue(group_to_dict(group))

    @inlineCallbacks
    def create_contact(self, collection, **contact_data):
        contact = yield collection.contact_store.new_contact(**contact_data)
        returnValue(contact_to_dict(contact))

    @inlineCallbacks
    def collect_queue(self, queue):
        contacts = []
        while True:
            item = yield queue.get()
            if isinstance(item, PausingQueueCloseMarker):
                break
            contacts.append(item)
        returnValue(contacts)

    @inlineCallbacks
    def test_init(self):
        collection = yield self.mk_collection("owner-1")
        self.assertEqual(collection.contact_store.user_account_key, "owner-1")

    @inlineCallbacks
    def test_stream(self):
        collection = yield self.mk_collection("owner-1")
        group = yield self.create_group(collection, name=u'Foo')
        group_false = yield self.create_group(collection, name=u'Wally')

        contact1 = yield self.create_contact(
            collection, name=u'Bar', msisdn=u'+12345',
            groups=[group.get('key')])
        contact2 = yield self.create_contact(
            collection, name=u'Baz', msisdn=u'+54321',
            groups=[group.get('key')])
        contact3 = yield self.create_contact(
            collection, name=u'Qux', msisdn=u'+31415',
            groups=[group.get('key'), group_false.get('key')])
        contact4 = yield self.create_contact(
            collection, name=u'Quux', msisdn=u'+27172',
            groups=[group_false.get('key')])

        queue = yield collection.stream(group.get('key'), None)
        contacts = yield self.collect_queue(queue)

        self.assertTrue(contact1 in contacts)
        self.assertTrue(contact2 in contacts)
        self.assertTrue(contact3 in contacts)
        self.assertFalse(contact4 in contacts)

    @inlineCallbacks
    def test_page(self):
        collection = yield self.mk_collection("owner-1")
        group = yield self.create_group(collection, name=u'Foo')
        group_false = yield self.create_group(collection, name=u'Wally')

        contact1 = yield self.create_contact(
            collection, name=u'Bar', msisdn=u'+12345',
            groups=[group.get('key')])
        contact2 = yield self.create_contact(
            collection, name=u'Baz', msisdn=u'+54321',
            groups=[group.get('key')])
        contact3 = yield self.create_contact(
            collection, name=u'Qux', msisdn=u'+31415',
            groups=[group.get('key'), group_false.get('key')])
        contact4 = yield self.create_contact(
            collection, name=u'Quux', msisdn=u'+27172',
            groups=[group_false.get('key')])

        cursor, contacts = yield collection.page(
            group.get('key'), None, 2, None)
        self.assertFalse(cursor is None)

        cursor, data = yield collection.page(group.get('key'), cursor, 2, None)
        self.assertEqual(cursor, None)
        contacts += data

        self.assertTrue(contact1 in contacts)
        self.assertTrue(contact2 in contacts)
        self.assertTrue(contact3 in contacts)
        self.assertFalse(contact4 in contacts)

    @inlineCallbacks
    def test_page_dynamic_group(self):
        collection = yield self.mk_collection("owner-1")

        group_false = yield self.create_group(collection, name=u'Wally')
        group = yield self.create_group(
            collection, name=u'Foo', query=u'msisdn:\+12345')

        contact1 = yield self.create_contact(
            collection, name=u'Bar', msisdn=u'+12345'
            )
        contact2 = yield self.create_contact(
            collection, name=u'Baz', msisdn=u'+54321',
            groups=[group.get('key')])
        contact3 = yield self.create_contact(
            collection, name=u'Qux', msisdn=u'+12345'
            )
        contact4 = yield self.create_contact(
            collection, name=u'Quux', msisdn=u'+27172',
            groups=[group_false.get('key')])

        cursor, contacts = yield collection.page(
            group.get('key'), None, 2, None)
        self.assertFalse(cursor is None)

        while cursor is not None:
            cursor, data = yield collection.page(group['key'], cursor, 2, None)
            contacts += data

        self.assertTrue(contact1 in contacts)
        self.assertTrue(contact2 in contacts)
        self.assertTrue(contact3 in contacts)
        self.assertFalse(contact4 in contacts)

    @inlineCallbacks
    def test_stream_dynamic_group(self):
        collection = yield self.mk_collection("owner-1")

        group_false = yield self.create_group(collection, name=u'Wally')
        group = yield self.create_group(
            collection, name=u'Foo', query=u'msisdn:\+12345')

        contact1 = yield self.create_contact(
            collection, name=u'Bar', msisdn=u'+12345'
            )
        contact2 = yield self.create_contact(
            collection, name=u'Baz', msisdn=u'+54321',
            groups=[group.get('key')])
        contact3 = yield self.create_contact(
            collection, name=u'Qux', msisdn=u'+12345'
            )
        contact4 = yield self.create_contact(
            collection, name=u'Quux', msisdn=u'+27172',
            groups=[group_false.get('key')])

        queue = yield collection.stream(group.get('key'), None)
        contacts = yield self.collect_queue(queue)

        self.assertTrue(contact1 in contacts)
        self.assertTrue(contact2 in contacts)
        self.assertTrue(contact3 in contacts)
        self.assertFalse(contact4 in contacts)
