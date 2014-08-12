"""
Riak groups backend and collection
"""

from twisted.internet.defer import inlineCallbacks, returnValue
from zope.interface import implementer

from vumi.persist.fields import ValidationError
from go.vumitools.contact import (
    ContactStore, ContactNotFoundError, ContactGroup)

from go_api.collections import ICollection
from go_api.collections.errors import (
    CollectionObjectNotFound, CollectionUsageError)


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
