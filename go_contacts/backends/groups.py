"""
Riak groups backend and collection
"""

from twisted.internet.defer import inlineCallbacks, returnValue
from zope.interface import implementer

from vumi.persist.fields import ValidationError
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


class RiakGroupsBackend(object):
    def __init__(self, riak_manager):
        self.riak_manager = riak_manager

    def get_contact_collection(self, owner_id):
        contact_store = ContactStore(self.riak_manager, owner_id)
        return RiakGroupsCollection(contact_store)


@implementer(ICollection)
class RiakGroupsCollection(object):
    def __init__(self, contact_store):
        self.contact_store = contact_store

    @classmethod
    def _pick_group_fields(cls, data):
        """
        Return a sub-dictionary of the items from ``data`` that are valid
        contact fields.
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
                "Invalid group fields: %s" % ", ".join(
                    sorted(given_keys - valid_keys)))
        return fields

    def all_keys(self):
        """
        Return an iterable over all keys in the collection. May return a
        deferred instead of the iterable.
        """
        raise NotImplementedError()

    def all(self):
        """
        Return an iterable over all objects in the collection. The iterable may
        contain deferreds instead of objects. May return a deferred instead of
        the iterable.
        """
        raise NotImplementedError()

    @inlineCallbacks
    def get(self, object_id):
        """
        Return a single object from the collection. May return a deferred
        instead of the object.
        """
        group = yield self.contact_store.get_group(object_id)
        if not isinstance(group, ContactGroup):
            raise CollectionObjectNotFound(object_id, "Group")
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
                "A group key may not be specified in group creation")
        if 'name' not in fields:
            raise CollectionUsageError(
                "The group name must be specified in group creation")
        try:
            if 'query' in fields:
                group = yield self.contact_store.new_smart_group(
                    fields['name'], fields['query'])
            else:
                group = yield self.contact_store.new_group(fields['name'])
        except ValidationError, e:
            raise CollectionUsageError(str(e))
        returnValue((group.key, group_to_dict(group)))

    @inlineCallbacks
    def update(self, object_id, data):
        """
        Update an object. May return a deferred.

        ``object_id`` may not be ``None``.
        """
        return NotImplementedError

    @inlineCallbacks
    def delete(self, object_id):
        """
        Delete an object. May return a deferred.
        """
        return NotImplementedError