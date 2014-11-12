"""
Riak contacts for group handler and collection.
"""
from twisted.internet.defer import inlineCallbacks, returnValue

from go.vumitools.contact import ContactStore

from go_api.collections.errors import CollectionUsageError
from go_api.queue import PausingDeferredQueue

from .contacts import contact_to_dict
from .utils import _get_page_of_keys, _fill_queue


class ContactsForGroupBackend(object):
    def __init__(self, riak_manager, max_contacts_per_page):
        self.riak_manager = riak_manager
        self.max_contacts_per_page = max_contacts_per_page

    def get_model(self, owner_id):
        contact_store = ContactStore(self.riak_manager, owner_id)
        return RiakContactsForGroupCollection(
            contact_store, self.max_contacts_per_page)


class RiakContactsForGroupCollection(object):
    def __init__(self, contact_store, max_contacts_per_page):
        self.contact_store = contact_store
        self.max_contacts_per_page = max_contacts_per_page

    def stream(self, group_id, query):
        """
        Returns a :class:`PausingDeferredQueue` of all the contacts in the
        group. May return a deferred instead of the
        :class:`PausingDeferredQueue`. A queue item that is an instance of
        :class:`PausingQueueCloseMarker` indicates the end of the queue.

        :param unicode group_id:
            The ID of the group to fetch the contacts for.
        :param unicode query:
            Search term requested through the API. Defaults to ``None`` if no
            search term was requested. Currently not implemented and will raise
            a CollectionUsageError if not ``None``.
        """
        if query is not None:
            raise CollectionUsageError("query parameter not supported")

        max_results = self.max_contacts_per_page
        model_proxy = self.contact_store.contacts

        def get_page(cursor):
            return _get_page_of_keys(
                model_proxy, group_id, max_results, cursor,
                field_name='groups')

        def get_dict(key):
            d = self.contact_store.get_contact_by_key(key)
            d.addCallback(contact_to_dict)
            return d

        q = PausingDeferredQueue(backlog=1, size=max_results)
        q.fill_d = _fill_queue(q, get_page, get_dict)
        return q

    @inlineCallbacks
    def page(self, group_id, cursor, max_results, query):
        """
        Generages a page which contains a subset of the contact objects
        belonging to a specific group.

        :param unicode group_id:
            Used to determine which group to fetch the contacts for.
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
        if query is not None:
            raise CollectionUsageError("query parameter not supported")

        max_results = max_results or float('inf')
        max_results = min(max_results, self.max_contacts_per_page)

        model_proxy = self.contact_store.contacts
        cursor, contact_keys = yield _get_page_of_keys(
            model_proxy, group_id, max_results, cursor, field_name='groups')

        contact_list = []
        for key in contact_keys:
            contact = yield self.contact_store.get_contact_by_key(key)
            contact = contact_to_dict(contact)
            contact_list.append(contact)

        returnValue((cursor, contact_list))
