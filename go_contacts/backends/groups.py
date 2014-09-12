"""
Riak groups backend and collection
"""

from twisted.internet.defer import inlineCallbacks, returnValue
from zope.interface import implementer

from vumi.persist.fields import ValidationError
from vumi.persist.model import VumiRiakError
from go.vumitools.contact import (
    ContactStore, ContactGroup)

from go_api.collections import ICollection
from go_api.collections.errors import (
    CollectionObjectNotFound, CollectionUsageError)

from go_contacts.backends.riak import RiakContactsCollection


def group_to_dict(group):
    """
    Turn  a group into a dict we can return.
    """
    group_dict = {}
    for key, value in group.get_data().iteritems():
        group_dict[key] = value
    return group_dict

NONSETTABLE_GROUP_FIELDS = ['$VERSION', 'user_account']


def settable_group_fields(**fields):
    return dict((k, v) for k, v in fields.iteritems()
                if k not in NONSETTABLE_GROUP_FIELDS)


class RiakGroupsBackend(object):
    def __init__(self, riak_manager, max_groups_per_page):
        self.riak_manager = riak_manager
        self.max_groups_per_page = max_groups_per_page

    def get_group_collection(self, owner_id):
        contact_store = ContactStore(self.riak_manager, owner_id)
        return RiakGroupsCollection(contact_store, self.max_groups_per_page)


@implementer(ICollection)
class RiakGroupsCollection(object):

    def __init__(self, contact_store, max_groups_per_page):
        self.contact_store = contact_store
        self.max_groups_per_page = max_groups_per_page

    @classmethod
    def _pick_group_fields(cls, data):
        """
        Return a sub-dictionary of the items from ``data`` that are valid
        group fields.
        """
        return RiakContactsCollection._pick_fields(
            data, ContactGroup.field_descriptors.keys())

    @classmethod
    def _check_group_fields(cls, data):
        """
        Return a sub-dictionary of the items from ``data`` that are valid
        and raise a :class:`CollectionUsageError` if any fields are not.
        """
        fields = cls._pick_group_fields(data)
        given_keys = set(data.keys())
        valid_keys = set(fields.keys())
        if given_keys != valid_keys:
            raise CollectionUsageError(
                'Invalid group fields: %s' % ', '.join(
                    sorted(given_keys - valid_keys)))
        return fields

    def all_keys(self):
        """
        Return an iterable over all keys in the collection. May return a
        deferred instead of the iterable.
        """
        raise NotImplementedError()

    @inlineCallbacks
    def stream(self, query):
        """
        Return an iterable over all objects in the collection. The iterable may
        contain deferreds instead of objects. May return a deferred instead of
        the iterable.

        :param unicode query:
            Search term requested through the API. Defaults to ``None`` if no
            search term was requested. Currently not implemented and will raise
            a CollectionUsageError if not ``None``.
        """
        if query is not None:
            raise CollectionUsageError("query parameter not supported")

        group_keys = yield self.contact_store.list_keys(
            self.contact_store.groups)
        group_list = []
        for key in group_keys:
            group = self.contact_store.get_group(key)
            group.addCallback(group_to_dict)
            group_list.append(group)
        returnValue(group_list)

    @inlineCallbacks
    def page(self, cursor, max_results, query):
        """
        Generages a page which contains a subset of the objects in the
        collection.

        :param unicode cursor:
            Used to determine the start point of the page. Defaults to ``None``
            if no cursor was supplied.
        :param int max_results:
            Used to limit the number of results presented in a page. Defaults
            to ``None`` if no limit was specified.
        :param unicode query:
            Search term requested through the API. Defaults to ``None`` if no
            search term was requested. Currently not implemented and will raise
            a CollectionUsageError if not ``None``.

        :return:
            (cursor, data). ``cursor`` is an opaque string that refers to the
            next page, and is ``None`` if this is the last page. ``data`` is a
            list of all the objects within the page.
        :rtype: tuple
        """
        # TODO: Use riak pagination instead of fake pagination
        if query is not None:
            raise CollectionUsageError("query parameter not supported")

        max_results = max_results or float('inf')
        max_results = min(max_results, self.max_groups_per_page)

        model_proxy = self.contact_store.groups
        user_account_key = self.contact_store.user_account_key
        try:
            group_keys = yield model_proxy.index_keys_page(
                'user_account', user_account_key, max_results=max_results,
                continuation=cursor)
        except VumiRiakError:
            raise CollectionUsageError(
                "Riak error, possible invalid cursor: %r" % cursor)

        group_list = []
        for key in group_keys:
            group = yield self.contact_store.get_group(key)
            group = group_to_dict(group)
            group_list.append(group)
        cursor = group_keys.continuation
        returnValue((cursor, group_list))

    @inlineCallbacks
    def get(self, object_id):
        """
        Return a single object from the collection. May return a deferred
        instead of the object.
        """
        group = yield self.contact_store.get_group(object_id)
        if not isinstance(group, ContactGroup):
            raise CollectionObjectNotFound(object_id, u'Group')
        returnValue(group_to_dict(group))

    @inlineCallbacks
    def create(self, object_id, data):
        """
        Create an object within the collection. May return a deferred.

        If ``object_id`` is ``None``, an identifier will be generated.
        """
        fields = self._check_group_fields(data)
        if object_id is not None:
            raise CollectionUsageError(
                u'A group key may not be specified in group creation')
        if u'name' not in fields:
            raise CollectionUsageError(
                u'The group name must be specified in group creation')
        try:
            if u'query' in fields and fields[u'query'] is not None:
                group = yield self.contact_store.new_smart_group(
                    fields[u'name'], fields[u'query'])
            else:
                group = yield self.contact_store.new_group(fields[u'name'])
        except ValidationError, e:
            raise CollectionUsageError(str(e))
        returnValue((group.key, group_to_dict(group)))

    @inlineCallbacks
    def update(self, object_id, data):
        """
        Update an object. May return a deferred.

        ``object_id`` may not be ``None``.
        """
        fields = self._check_group_fields(data)
        fields = settable_group_fields(**fields)

        group = yield self.contact_store.get_group(object_id)
        if not isinstance(group, ContactGroup):
            raise CollectionObjectNotFound(object_id, u'Group')
        try:
            for field_name, field_value in fields.iteritems():
                setattr(group, field_name, field_value)
        except ValidationError, e:
            raise CollectionUsageError(str(e))
        yield group.save()
        returnValue(group_to_dict(group))

    @inlineCallbacks
    def delete(self, object_id):
        """
        Delete an object. May return a deferred.
        """
        group = yield self.contact_store.get_group(object_id)
        if not isinstance(group, ContactGroup):
            raise CollectionObjectNotFound(object_id, u'Group')
        group_data = group_to_dict(group)
        yield group.delete()
        returnValue(group_data)
