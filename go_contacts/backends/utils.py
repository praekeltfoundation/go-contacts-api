from vumi.persist.model import VumiRiakError
from go_api.collections.errors import CollectionUsageError
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
