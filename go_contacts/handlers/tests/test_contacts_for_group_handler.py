from twisted.internet.defer import inlineCallbacks, returnValue

from go_api.cyclone.helpers import HandlerHelper, AppHelper
from vumi.tests.helpers import VumiTestCase, PersistenceHelper
from go.vumitools.contact import ContactStore

from go_contacts.handlers import ContactsForGroupHandler
from go_contacts.backends.riak import RiakContactsForGroupModel


class TestContactsForGroupHandler(VumiTestCase):
    @inlineCallbacks
    def setUp(self):
        self.persistence_helper = self.add_helper(
            PersistenceHelper(use_riak=True, is_sync=False))
        self.collection = yield self.mk_collection('owner-1')
        self.model_factory = lambda req: self.collection
        self.handler_helper = HandlerHelper(
            ContactsForGroupHandler,
            handler_kwargs={'model_factory': self.model_factory})
        self.app_helper = AppHelper(
            urlspec=ContactsForGroupHandler.mk_urlspec(
                '/root', self.model_factory))

    @inlineCallbacks
    def mk_collection(self, owner_id):
        manager = yield self.persistence_helper.get_riak_manager()
        contact_store = ContactStore(manager, owner_id)
        collection = RiakContactsForGroupModel(contact_store, 10)
        returnValue(collection)

    @inlineCallbacks
    def test_get_stream_with_query(self):
        data = yield self.app_helper.get(
            '/root/1/contacts?stream=true&query=foo', parser='json')
        self.assertEqual(data[u'status_code'], 400)
        self.assertEqual(data[u'reason'], 'query parameter not supported')
