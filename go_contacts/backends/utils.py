from vumi.persist.model import VumiRiakError
from go_api.collections.errors import CollectionUsageError
from go_api.queue import PausingQueueCloseMarker
from twisted.internet.defer import inlineCallbacks, returnValue


@inlineCallbacks
def _get_page_of_keys(model_proxy, user_account_key, max_results, cursor):
    try:
        contact_keys = yield model_proxy.index_keys_page(
            'user_account', user_account_key, max_results=max_results,
            continuation=cursor)
    except VumiRiakError:
        raise CollectionUsageError(
            "Riak error, possible invalid cursor: %r" % (cursor,))

    cursor = contact_keys.continuation
    returnValue((cursor, contact_keys))


@inlineCallbacks
def _fill_queue(q, get_page, get_dict):
    keys_deferred = get_page(None)

    while True:
        cursor, keys = yield keys_deferred
        if cursor is not None:
            # Get the next page of keys while we fetch the objects
            keys_deferred = get_page(cursor)

        for key in keys:
            obj = yield get_dict(key)
            yield q.put(obj)

        if cursor is None:
            break

    q.put(PausingQueueCloseMarker())
