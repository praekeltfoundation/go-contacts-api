"""
Riak contacts backend and collection.
"""

from twisted.internet.defer import inlineCallbacks, returnValue
from zope.interface import implementer

from go.vumitools.contact import (
    ContactStore, ContactNotFoundError, ContactError)

from go_api.collections import ICollection


class RiakContactsBackend(object):
    def __init__(self, riak_manager):
        self.riak_manager = riak_manager

    def get_contact_collection(self, owner_id):
        contact_store = ContactStore(self.riak_manager, owner_id)
        return RiakContactsCollection(contact_store)


@implementer(ICollection)
class RiakContactsCollection(object):
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
        try:
            contact = yield self.contact_store.get_contact_by_key(object_id)
        except (ContactNotFoundError, ContactError):
            returnValue(None)
        returnValue(contact.get_data())

    def create(self, object_id, data):
        """
        Create an object within the collection. May return a deferred.

        If ``object_id`` is ``None``, an identifier will be generated.
        """
        raise NotImplementedError()

    def update(self, object_id, data):
        """
        Update an object. May return a deferred.

        ``object_id`` may not be ``None``.
        """
        raise NotImplementedError()

    def delete(self, object_id):
        """
        Delete an object. May return a deferred.
        """
        raise NotImplementedError()
