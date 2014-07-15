"""
Riak contacts backend and collection.
"""

from zope.interface import implementer

from go_api.interfaces import ICollection


class RiakContactsBackend(object):
    def get_contact_collection(self, owner_id):
        pass


@implementer(ICollection)
class RiakContactsCollection(object):
    def all_keys(self):
        """
        Return an iterable over all keys in the collection. May return a
        deferred instead of the iterable.
        """
        raise NotImplementedError()

    def all():
        """
        Return an iterable over all objects in the collection. The iterable may
        contain deferreds instead of objects. May return a deferred instead of
        the iterable.
        """
        raise NotImplementedError()

    def get(object_id):
        """
        Return a single object from the collection. May return a deferred
        instead of the object.
        """
        return {}

    def create(object_id, data):
        """
        Create an object within the collection. May return a deferred.

        If ``object_id`` is ``None``, an identifier will be generated.
        """
        raise NotImplementedError()

    def update(object_id, data):
        """
        Update an object. May return a deferred.

        ``object_id`` may not be ``None``.
        """
        raise NotImplementedError()

    def delete(object_id):
        """
        Delete an object. May return a deferred.
        """
        raise NotImplementedError()
