"""
Riak contacts backend and collection.
"""

from twisted.internet.defer import inlineCallbacks, returnValue
from zope.interface import implementer

from vumi.persist.fields import ValidationError
from go.vumitools.contact import (
    ContactStore, ContactNotFoundError, Contact)

from go_api.collections import ICollection
from go_api.collections.errors import (
    CollectionObjectNotFound, CollectionUsageError)


def contact_to_dict(contact):
    """
    Turn a contact into a dict we can return.

    TODO: Move this into the contact model in vumi-go or something.
    """
    contact_dict = {
        u"extra": dict(contact.extra),
        u"subscription": dict(contact.subscription),
    }
    for key, value in contact.get_data().iteritems():
        if key.startswith(u"extras-") or key.startswith(u"subscription-"):
            # We already have these.
            continue
        contact_dict[key] = value
    return contact_dict


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

    @staticmethod
    def _pick_fields(data, keys):
        """
        Return a sub-dictionary of all the items from ``data`` whose
        keys are listed in ``keys``.
        """
        return dict((k, data[k]) for k in keys if k in data)

    @classmethod
    def _pick_contact_fields(cls, data):
        """
        Return a sub-dictionary of the items from ``data`` that are valid
        contact fields.
        """
        return cls._pick_fields(data, Contact.field_descriptors.keys())

    @classmethod
    def _check_contact_fields(cls, data):
        """
        Return a sub-dictionary of the items from ``data`` that are valid
        and raise a :class:`CollectionUsageError` if any fields are not.
        """
        fields = cls._pick_contact_fields(data)
        given_keys = set(data.keys())
        valid_keys = set(fields.keys())
        if given_keys != valid_keys:
            raise CollectionUsageError(
                "Invalid contact fields: %s" % ", ".join(
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
        try:
            contact = yield self.contact_store.get_contact_by_key(object_id)
        except ContactNotFoundError:
            raise CollectionObjectNotFound(object_id, "Contact")
        returnValue(contact_to_dict(contact))

    @inlineCallbacks
    def create(self, object_id, data):
        """
        Create an object within the collection. May return a deferred.

        If ``object_id`` is ``None``, an identifier will be generated.
        """
        fields = self._check_contact_fields(data)
        if object_id is not None:
            raise CollectionUsageError(
                "A contact key may not be specified in contact creation")
        try:
            contact = yield self.contact_store.new_contact(**fields)
        except ValidationError, e:
            raise CollectionUsageError(str(e))
        returnValue((contact.key, contact_to_dict(contact)))

    @inlineCallbacks
    def update(self, object_id, data):
        """
        Update an object. May return a deferred.

        ``object_id`` may not be ``None``.
        """
        fields = self._check_contact_fields(data)
        try:
            contact = yield self.contact_store.update_contact(
                object_id, **fields)
        except ContactNotFoundError:
            raise CollectionObjectNotFound(object_id, "Contact")
        except ValidationError, e:
            raise CollectionUsageError(str(e))
        returnValue(contact_to_dict(contact))

    @inlineCallbacks
    def delete(self, object_id):
        """
        Delete an object. May return a deferred.
        """
        try:
            contact = yield self.contact_store.get_contact_by_key(object_id)
        except ContactNotFoundError:
            raise CollectionObjectNotFound(object_id, "Contact")
        contact_data = contact_to_dict(contact)
        yield contact.delete()
        returnValue(contact_data)
