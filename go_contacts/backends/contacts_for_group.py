"""
Riak contacts for group handler and collection.
"""
from twisted.internet.defer import inlineCallbacks, returnValue, succeed

from go.vumitools.contact import ContactStore

from go_api.collections.errors import CollectionUsageError
from go_api.queue import PausingDeferredQueue

from .contacts import contact_to_dict
from .utils import _get_page_of_keys, _fill_queue, _get_smart_page_of_keys


class ContactsForGroupBackend(object):
    def __init__(self, riak_manager, max_contacts_per_page):
        self.riak_manager = riak_manager
        self.max_contacts_per_page = max_contacts_per_page

    def get_model(self, owner_id):
        contact_store = ContactStore(self.riak_manager, owner_id)
        return RiakContactsForGroupModel(
            contact_store, self.max_contacts_per_page)


class RiakContactsForGroupModel(object):

    DYNAMIC_CURSOR = 'dynamicgroup'
    STATIC_CURSOR = 'staticgroup'

    def __init__(self, contact_store, max_contacts_per_page):
        self.contact_store = contact_store
        self.max_contacts_per_page = max_contacts_per_page

    def _get_contact_dict(self, key):
        """
        Returns a dictionary representation of a contact.
        """
        d = self.contact_store.get_contact_by_key(key)
        d.addCallback(contact_to_dict)
        return d

    def _encode_cursor(self, cursor_type, value):
        """
        Encode a cursor.
        """
        if cursor_type == self.STATIC_CURSOR:
            encoded_value = value if value is not None else ''
            encoded = self.STATIC_CURSOR + encoded_value
        elif cursor_type == self.DYNAMIC_CURSOR:
            encoded_value = str(value) if value is not None else ''
            encoded = self.DYNAMIC_CURSOR + encoded_value
        else:
            raise ValueError("Invalid cursor type %r" % (cursor_type,))
        return encoded.encode("rot13")

    def _decode_cursor(self, encoded_cursor):
        """
        Decode a cursor.
        """
        if encoded_cursor is None:
            return self.STATIC_CURSOR, None
        decoded = encoded_cursor.encode("rot13")
        if decoded.startswith(self.STATIC_CURSOR):
            value = decoded[len(self.STATIC_CURSOR):]
            if not value:
                value = None
            return self.STATIC_CURSOR, value
        elif decoded.startswith(self.DYNAMIC_CURSOR):
            value = decoded[len(self.DYNAMIC_CURSOR):]
            if not value:
                value = 0
            else:
                value = int(value)
            return self.DYNAMIC_CURSOR, value
        raise ValueError("Invalid cursor %r" % (encoded_cursor,))

    @inlineCallbacks
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
        group = yield self.contact_store.get_group(group_id)

        def get_page(cursor):
            return _get_page_of_keys(
                model_proxy, group_id, max_results, cursor,
                field_name='groups')

        def get_page_smart(cursor):
            if group and group.is_smart_group():
                keys_d = _get_smart_page_of_keys(
                    model_proxy, max_results, cursor, group.query)
            else:
                keys_d = succeed((None, []))
            return keys_d

        q = PausingDeferredQueue(backlog=1, size=max_results)
        # Static contacts
        q.fill_d = _fill_queue(
            q, get_page, self._get_contact_dict, close_queue=False)
        # Dynamic contacts
        q.fill_d.addCallback(lambda _: _fill_queue(
            q, get_page_smart, self._get_contact_dict, close_queue=True))

        returnValue(q)

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
        try:
            cursor_type, decoded_cursor = self._decode_cursor(cursor)
        except ValueError:
            cursor_type = None

        if cursor_type == self.STATIC_CURSOR:
            cursor, contact_keys = yield _get_page_of_keys(
                model_proxy, group_id, max_results, decoded_cursor, 'groups')
            # If it's the end of static, move to dynamic
            if cursor is None:
                group = yield self.contact_store.get_group(group_id)
                if group and group.is_smart_group():
                    cursor = self._encode_cursor(self.DYNAMIC_CURSOR, None)
            else:
                cursor = self._encode_cursor(self.STATIC_CURSOR, cursor)

        elif cursor_type == self.DYNAMIC_CURSOR:
            group = yield self.contact_store.get_group(group_id)
            cursor, contact_keys = yield _get_smart_page_of_keys(
                model_proxy, max_results, decoded_cursor, group.query)
            if cursor is not None:
                cursor = self._encode_cursor(self.DYNAMIC_CURSOR, cursor)

        else:
            raise CollectionUsageError(
                'Invalid cursor: %r' % cursor)

        contact_list = [
            (yield self._get_contact_dict(key)) for key in contact_keys]

        returnValue((cursor, contact_list))
