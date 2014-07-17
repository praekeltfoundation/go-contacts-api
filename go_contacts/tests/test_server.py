"""
Tests for contacts API cyclone server.
"""

import yaml

from twisted.internet.defer import inlineCallbacks

from vumi.persist.txriak_manager import TxRiakManager
from vumi.tests.helpers import VumiTestCase
from vumi.tests.helpers import PersistenceHelper

from go_api.cyclone.helpers import AppHelper

from go_contacts.backends.riak import RiakContactsBackend
from go_contacts.server import ContactsApi


class ContactsApiTestCase(VumiTestCase):
    def setUp(self):
        self.persistence_helper = self.add_helper(
            PersistenceHelper(use_riak=True, is_sync=False))

    def mk_config(self, config_dict):
        tempfile = self.mktemp()
        with open(tempfile, 'wb') as fp:
            yaml.safe_dump(config_dict, fp)
        return tempfile

    def mk_api(self):
        configfile = self.mk_config({
            "riak_manager": {
                "bucket_prefix": "test",
            },
        })
        return ContactsApi(configfile)

    def test_init(self):
        configfile = self.mk_config({
            "riak_manager": {
                "bucket_prefix": "test",
            },
        })
        api = ContactsApi(configfile)
        self.assertTrue(isinstance(api.backend, RiakContactsBackend))
        self.assertTrue(isinstance(api.backend.riak_manager, TxRiakManager))

    def test_init_no_configfile(self):
        err = self.assertRaises(ValueError, ContactsApi)
        self.assertEqual(
            str(err),
            "Please specify a config file using --appopts=<config.yaml>")

    def test_init_no_riak_config(self):
        configfile = self.mk_config({})
        err = self.assertRaises(ValueError, ContactsApi, configfile)
        self.assertEqual(
            str(err),
            "Config file must contain a riak_manager entry.")

    def test_collections(self):
        api = self.mk_api()
        self.assertEqual(api.collections, (
            ('/contacts', api.backend.get_contact_collection),
        ))

    @inlineCallbacks
    def test_route(self):
        api = self.mk_api()
        collection = api.backend.get_contact_collection("owner-1")
        key, data = yield collection.create(None, {
            "msisdn": u"+12345",
        })
        contact = yield collection.contact_store.get_contact_by_key(key)
        app_helper = AppHelper(app=api)
        resp = yield app_helper.get(
            '/contacts/%s' % (key,),
            headers={"X-Owner-ID": "owner-1"})
        self.assertEqual(resp.code, 200)
        resp_data = yield resp.json()
        self.assertEqual(resp_data, contact.get_data())
