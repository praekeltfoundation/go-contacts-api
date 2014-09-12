"""
Tests for riak groups backend and collection.
"""

from datetime import datetime

from twisted.internet.defer import inlineCallbacks, returnValue
from zope.interface.verify import verifyObject

from vumi.tests.helpers import VumiTestCase
from vumi.tests.helpers import PersistenceHelper

from go.vumitools.contact import ContactStore

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
        backend = RiakGroupsBackend(manager, 10)
        returnValue(backend)

    @inlineCallbacks
    def test_get_group_collection(self):
        backend = yield self.mk_backend()
        collection = backend.get_group_collection(u'owner-1')
        self.assertEqual(collection.contact_store.user_account_key, u'owner-1')
        self.assertTrue(isinstance(collection, RiakGroupsCollection))


class TestRiakGroupsCollection(VumiTestCase):
    def setUp(self):
        self.persistence_helper = self.add_helper(
            PersistenceHelper(use_riak=True, is_sync=False))

    @inlineCallbacks
    def mk_collection(self, owner_id):
        manager = yield self.persistence_helper.get_riak_manager()
        contact_store = ContactStore(manager, owner_id)
        collection = RiakGroupsCollection(contact_store, 10)
        returnValue(collection)

    EXPECTED_DATE_FORMAT = '%Y-%m-%d %H:%M:%S.%f'

    GROUP_FIELD_DEFAULTS = {
        u'name': None,
        u'query': None,
        u'$VERSION': None,
    }

    def assert_group(self, group, expected_partial):
        expected = self.GROUP_FIELD_DEFAULTS.copy()
        expected.update(expected_partial)
        if isinstance(expected.get(u'created_at'), datetime):
            expected[u'created_at'] = expected[u'created_at'].strftime(
                self.EXPECTED_DATE_FORMAT)
        self.assertEqual(group, expected)

    def test_pick_group_fields(self):
        pick_group_fields = RiakGroupsCollection._pick_group_fields
        self.assertEqual(
            pick_group_fields({u'name': u'Bob', u'notfield': u'xyz'}),
            {u'name': u'Bob'})

    def test_check_group_fields_success(self):
        self.assertEqual(
            RiakGroupsCollection._check_group_fields({u'name': u'Bob'}),
            {u'name': u'Bob'})

    def test_check_group_fields_fail(self):
        err = self.assertRaises(
            CollectionUsageError, RiakGroupsCollection._check_group_fields,
            {u'name': u'Bob', u'notfield': u'xyz'})
        self.assertEqual(str(err), u'Invalid group fields: notfield')

    def test_check_group_fields_fail_multiple_fields(self):
        err = self.assertRaises(
            CollectionUsageError, RiakGroupsCollection._check_group_fields,
            {u'name': u'Bob', u'notfield': u'xyz', u'badfield': u'foo'})
        self.assertEqual(
            str(err), u'Invalid group fields: badfield, notfield')

    @inlineCallbacks
    def test_collection_provides_ICollection(self):
        """
        The return value of .get_row_collection() is an object that provides
        ICollection.
        """
        collection = yield self.mk_collection(u'owner-1')
        verifyObject(ICollection, collection)

    @inlineCallbacks
    def test_init(self):
        collection = yield self.mk_collection(u'owner-1')
        self.assertEqual(collection.contact_store.user_account_key, u'owner-1')

    @inlineCallbacks
    def test_get(self):
        collection = yield self.mk_collection(u'owner-1')
        new_group = yield collection.contact_store.new_group(u'Bob')
        group = yield collection.get(new_group.key)
        self.assert_group(group, {
            u'key': new_group.key,
            u'created_at': new_group.created_at,
            u'name': u'Bob',
            u'user_account': u'owner-1',
        })

    @inlineCallbacks
    def test_get_fail(self):
        collection = yield self.mk_collection(u'owner-1')
        e = yield self.failUnlessFailure(collection.get(u'bad-key'),
                                         CollectionObjectNotFound)
        self.assertEqual(str(e), u"Group u'bad-key' not found.")

    @inlineCallbacks
    def test_create_group(self):
        collection = yield self.mk_collection(u'owner-1')
        key, group = yield collection.create(None, {
            u'name': u'Bob',
        })
        new_group = yield collection.contact_store.get_group(key)
        self.assert_group(group, {
            u'key': new_group.key,
            u'created_at': new_group.created_at,
            u'name': u'Bob',
            u'user_account': u'owner-1',
        })

    @inlineCallbacks
    def test_create_smart_group(self):
        collection = yield self.mk_collection(u'owner-1')
        key, group = yield collection.create(None, {
            u'name': u'Bob',
            u'query': u'test_query',
        })
        new_group = yield collection.contact_store.get_group(key)
        self.assert_group(group, {
            u'key': new_group.key,
            u'created_at': new_group.created_at,
            u'query': u'test_query',
            u'name': u'Bob',
            u'user_account': u'owner-1',
        })

    @inlineCallbacks
    def test_create_with_id_fails(self):
        collection = yield self.mk_collection(u'owner-1')
        d = collection.create(u'foo', {
            u'name': u'Bob',
        })
        err = yield self.failUnlessFailure(d, CollectionUsageError)
        self.assertEqual(
            str(err), u'A group key may not be specified in group creation')

    @inlineCallbacks
    def test_create_invalid_fields(self):
        collection = yield self.mk_collection(u'owner-1')
        d = collection.create(None, {
            u'unknown_field': u'foo',
            u'not_the_field': u'bar',
        })
        err = yield self.failUnlessFailure(d, CollectionUsageError)
        self.assertEqual(
            str(err), u'Invalid group fields: not_the_field, unknown_field')

    @inlineCallbacks
    def test_create_invalid_field_value(self):
        collection = yield self.mk_collection(u'owner-1')
        d = collection.create(None, {
            u'name': 5,
        })
        err = yield self.failUnlessFailure(d, CollectionUsageError)
        self.assertEqual(
            str(err), u'Value 5 is not a unicode string.')

    @inlineCallbacks
    def test_create_missing_name_field(self):
        collection = yield self.mk_collection(u'owner-1')
        d = collection.create(None, {})
        err = yield self.failUnlessFailure(d, CollectionUsageError)
        self.assertEqual(
            str(err), u'The group name must be specified in group creation')

    @inlineCallbacks
    def test_update(self):
        collection = yield self.mk_collection(u'owner-1')
        new_group = yield collection.contact_store.new_group(u'Bob')
        group = yield collection.update(new_group.key, {
            u'name': u'Susan',
        })
        self.assert_group(group, {
            u'key': new_group.key,
            u'created_at': new_group.created_at,
            u'name': u'Susan',
            u'user_account': u'owner-1',
        })

    @inlineCallbacks
    def test_update_query(self):
        collection = yield self.mk_collection(u'owner-1')
        new_group = yield collection.contact_store.new_smart_group(
            u'Bob', u'testquery')
        group = yield collection.update(new_group.key, {
            u'name': u'Susan',
            u'query': u'differenttestquery',
        })
        self.assert_group(group, {
            u'key': new_group.key,
            u'created_at': new_group.created_at,
            u'name': u'Susan',
            u'query': u'differenttestquery',
            u'user_account': u'owner-1',
        })

    @inlineCallbacks
    def test_update_non_existent_group(self):
        collection = yield self.mk_collection(u'owner-1')
        d = collection.update(u'bad-group-id', {})
        err = yield self.failUnlessFailure(d, CollectionObjectNotFound)
        self.assertEqual(
            str(err), u"Group u'bad-group-id' not found.")

    @inlineCallbacks
    def test_update_invalid_fields(self):
        collection = yield self.mk_collection(u'owner-1')
        new_group = yield collection.contact_store.new_group(u'Bob')
        d = collection.update(new_group.key, {
            u'unknown_field': u'foo',
            u'not_the_field': u'bar',
        })
        err = yield self.failUnlessFailure(d, CollectionUsageError)
        self.assertEqual(
            str(err), u'Invalid group fields: not_the_field, unknown_field')

    @inlineCallbacks
    def test_update_invalid_field_value(self):
        collection = yield self.mk_collection(u'owner-1')
        new_group = yield collection.contact_store.new_group(u'Bob')
        d = collection.update(new_group.key, {
            u'name': None,
        })
        err = yield self.failUnlessFailure(d, CollectionUsageError)
        self.assertEqual(
            str(err), u'None is not allowed as a value for non-null fields.')

    @inlineCallbacks
    def test_delete(self):
        collection = yield self.mk_collection(u'owner-1')
        new_group = yield collection.contact_store.new_group(name=u'Bob')
        group = yield collection.delete(new_group.key)
        self.assert_group(group, {
            u'key': new_group.key,
            u'created_at': new_group.created_at,
            u'name': u'Bob',
            u'user_account': u'owner-1',
        })
        d = yield collection.contact_store.get_group(u'owner-1')
        self.assertEqual(d, None)

    @inlineCallbacks
    def test_delete_non_existent_contact(self):
        collection = yield self.mk_collection(u'owner-1')
        d = collection.delete(u'bad-group-id')
        err = yield self.failUnlessFailure(d, CollectionObjectNotFound)
        self.assertEqual(str(err), u"Group u'bad-group-id' not found.")
