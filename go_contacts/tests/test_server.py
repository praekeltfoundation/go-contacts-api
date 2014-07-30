"""
Tests for contacts API cyclone server.
"""

from datetime import datetime
import json

import yaml

from twisted.internet.defer import inlineCallbacks, returnValue

from vumi.persist.txriak_manager import TxRiakManager
from vumi.tests.helpers import VumiTestCase
from vumi.tests.helpers import PersistenceHelper

from go_api.cyclone.helpers import AppHelper

from go_contacts.backends.riak import RiakContactsBackend
from go_contacts.server import ContactsApi


class ContactsApiTestMixin(object):
    def mk_api(self):
        raise NotImplementedError()

    def request(self, api, method, path, body=None, headers=None, auth=True):
        raise NotImplementedError()

    EXPECTED_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

    CONTACT_FIELD_DEFAULTS = {
        u'$VERSION': 2,
        u'bbm_pin': None,
        u'dob': None,
        u'email_address': None,
        u'facebook_id': None,
        u'groups': [],
        u'gtalk_id': None,
        u'mxit_id': None,
        u'name': None,
        u'surname': None,
        u'twitter_handle': None,
        u'wechat_id': None,
    }

    def assert_contact(self, contact, expected_partial):
        expected = self.CONTACT_FIELD_DEFAULTS.copy()
        expected.update(expected_partial)
        if isinstance(expected.get("created_at"), datetime):
            expected["created_at"] = expected["created_at"].strftime(
                self.EXPECTED_DATE_FORMAT)
        self.assertEqual(contact, expected)

    @inlineCallbacks
    def test_get_non_existent_contact(self):
        api = self.mk_api()
        (code, data) = yield self.request(api, "GET", "/contacts/bad-id")
        self.assertEqual(code, 404)
        self.assertEqual(data, {
            u"status_code": 404,
            u"reason": u"Contact 'bad-id' not found.",
        })


class TestContactsApi(VumiTestCase, ContactsApiTestMixin):
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

    @inlineCallbacks
    def request(self, api, method, path, body=None, headers=None, auth=True):
        if headers is None:
            headers = {}
        if auth:
            headers["X-Owner-ID"] = "owner-1"
        app_helper = AppHelper(app=api)
        resp = yield app_helper.request(method, path, headers=headers)
        data = yield resp.json()
        returnValue((resp.code, data))

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
        code, data = yield self.request(
            api, "GET", '/contacts/%s' % (key,))
        self.assertEqual(code, 200)
        self.assertEqual(data, contact.get_data())


class TestFakeContactsApi(VumiTestCase, ContactsApiTestMixin):
    def setUp(self):
        try:
            from fake_go_contacts import Request, FakeContactsApi
        except ImportError as err:
            if "fake_go_contacts" not in err.args[0]:
                raise
            raise ImportError(" ".join([
                err.args[0],
                "(install from pypi or the 'verified-fake' directory)"]))

        self.req_class = Request
        self.api_class = FakeContactsApi

    def mk_api(self):
        return self.api_class("", "token-1", {})

    def request(self, api, method, path, body=None, headers=None, auth=True):
        if headers is None:
            headers = {}
        if auth:
            headers["Authorization"] = "Bearer token-1"
        resp = api.handle_request(self.req_class(
            method, path, headers=headers))
        return resp.code, json.loads(resp.body)
