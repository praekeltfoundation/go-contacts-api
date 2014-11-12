from cyclone.web import HTTPError

from go_api.cyclone.handlers import BaseHandler
from go_api.collections.errors import (
    CollectionUsageError, CollectionObjectNotFound)

from twisted.internet.defer import maybeDeferred


class ContactsForGroupHandler(BaseHandler):
    """
    Handler for getting all contacts for a group

    Methods supported:

    * ``GET /:group_id/contacts`` - retrieve all contacts of a group.
    """
    route_suffix = ":group_id/contacts"
    model_alias = "collection"

    def get(self, group_id):
        query = self.get_argument('query', default=None)
        stream = self.get_argument('stream', default='false')
        if stream == 'true':
            d = maybeDeferred(self.collection.stream, group_id, query)
            d.addCallback(self.write_queue)
        else:
            cursor = self.get_argument('cursor', default=None)
            max_results = self.get_argument('max_results', default=None)
            try:
                max_results = max_results and int(max_results)
            except ValueError:
                raise HTTPError(400, "max_results must be an integer")
            d = maybeDeferred(
                self.collection.page, group_id, cursor=cursor,
                max_results=max_results, query=query)
            d.addCallback(self.write_page)
        d.addErrback(self.catch_err, 404, CollectionObjectNotFound)
        d.addErrback(self.catch_err, 400, CollectionUsageError)
        d.addErrback(
            self.raise_err, 500,
            "Failed to retrieve contacts for group %r." % group_id)
        return d
