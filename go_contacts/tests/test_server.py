"""
Tests for contacts API cyclone server.
"""

import json

import yaml

from twisted.internet.defer import inlineCallbacks, returnValue

from vumi.persist.txriak_manager import TxRiakManager
from vumi.tests.helpers import VumiTestCase
from vumi.tests.helpers import PersistenceHelper

from go_api.cyclone.helpers import AppHelper

from go_contacts.backends.riak import (RiakContactsBackend, contact_to_dict,
                                       group_to_dict, RiakGroupsBackend)
from go_contacts.server import ContactsApi
from go_contacts.tests.test_server_groups import GroupsApiTestMixin
from go_api.collections.errors import CollectionObjectNotFound


class ContactsApiTestMixin(object):
    def mk_api(self):
        raise NotImplementedError()

    def request(self, api, method, path, body=None, headers=None, auth=True):
        raise NotImplementedError()

    def create_contact(self, api, **contact_data):
        raise NotImplementedError()

    def get_contact(self, api, contact_key):
        raise NotImplementedError()

    def contact_exists(self, api, contact_key):
        raise NotImplementedError()

    EXPECTED_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

    OWNER_ID = u"owner-1"

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
        u'extra': {},
        u'subscription': {},
    }

    def assert_contact(self, contact, expected_partial):
        expected = self.CONTACT_FIELD_DEFAULTS.copy()
        expected.update(expected_partial)
        expected[u"user_account"] = self.OWNER_ID
        self.assertEqual(contact, expected)

    def assert_contact_response(self, response, expected_partial):
        expected = self.CONTACT_FIELD_DEFAULTS.copy()
        expected.update(expected_partial)
        expected[u"user_account"] = self.OWNER_ID
        data = response[1]
        if u"key" in data:
            expected.setdefault(u"key", data[u"key"])
            expected.setdefault(u"created_at", data[u"created_at"])
        self.assertEqual(response, (200, expected))
        return data

    @inlineCallbacks
    def test_get(self):
        api = self.mk_api()
        contact = yield self.create_contact(
            api, name=u"Bob", msisdn=u"+12345")

        contact_key = contact[u"key"]
        resp = yield self.request(
            api, "GET", "/contacts/" + contact_key)
        self.assert_contact_response(resp, {
            u'key': contact[u"key"],
            u'created_at': contact[u"created_at"],
            u'msisdn': u'+12345',
            u'name': u'Bob',
        })

    @inlineCallbacks
    def test_get_non_existent_contact(self):
        api = self.mk_api()
        (code, data) = yield self.request(api, "GET", "/contacts/bad-id")
        self.assertEqual(code, 404)
        self.assertEqual(data, {
            u"status_code": 404,
            u"reason": u"Contact 'bad-id' not found.",
        })

    @inlineCallbacks
    def test_create(self):
        api = self.mk_api()
        resp = yield self.request(
            api, "POST", "/contacts/", json.dumps({
                u"msisdn": u"+12345",
                u"name": u"Arthur",
                u"surname": u"of Camelot",
            }))
        contact = self.assert_contact_response(resp, {
            u"msisdn": u"+12345",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
        })
        contact_key = contact[u"key"]

        stored_contact = yield self.get_contact(api, contact_key)
        self.assert_contact(stored_contact, contact)

    @inlineCallbacks
    def test_create_with_extras(self):
        api = self.mk_api()
        resp = yield self.request(
            api, "POST", "/contacts/", json.dumps({
                u"msisdn": u"+12345",
                u"name": u"Arthur",
                u"surname": u"of Camelot",
                u"extra": {
                    u"quest": u"Grail",
                    u"government": u"monarchy",
                },
            }))
        contact = self.assert_contact_response(resp, {
            u"msisdn": u"+12345",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
            u"extra": {
                u"quest": u"Grail",
                u"government": u"monarchy",
            },
        })
        contact_key = contact[u"key"]

        stored_contact = yield self.get_contact(api, contact_key)
        self.assert_contact(stored_contact, contact)

    @inlineCallbacks
    def test_create_invalid_fields(self):
        api = self.mk_api()
        (code, data) = yield self.request(
            api, "POST", "/contacts/", json.dumps({
                u"unknown_field": u"foo",
                u"not_the_field": u"bar",
            }))
        self.assertEqual(code, 400)
        self.assertEqual(data, {
            u"status_code": 400,
            u"reason": u"Invalid contact fields: not_the_field, unknown_field",
        })

    @inlineCallbacks
    def test_update(self):
        api = self.mk_api()
        contact = yield self.create_contact(
            api, name=u"Bob", msisdn=u"+12345")

        contact_key = contact[u"key"]
        resp = yield self.request(
            api, "PUT", "/contacts/" + contact_key, json.dumps({
                "msisdn": u"+6789",
            }))
        self.assert_contact_response(resp, {
            u"key": contact_key,
            u"created_at": contact[u"created_at"],
            u"msisdn": u"+6789",
            u"name": u"Bob",
        })

    @inlineCallbacks
    def test_update_extras(self):
        api = self.mk_api()
        contact = yield self.create_contact(
            api, name=u"Arthur", msisdn=u"+12345")

        contact_key = contact[u"key"]
        resp = yield self.request(
            api, "PUT", "/contacts/" + contact_key, json.dumps({
                u"msisdn": u"+6789",
                u"extra": {
                    u"quest": u"Grail",
                    u"government": u"monarchy",
                },
            }))
        self.assert_contact_response(resp, {
            u"key": contact_key,
            u"created_at": contact[u"created_at"],
            u"msisdn": u"+6789",
            u"name": u"Arthur",
            u"extra": {
                u"quest": u"Grail",
                u"government": u"monarchy",
            },
        })

        resp = yield self.request(
            api, "PUT", "/contacts/" + contact_key, json.dumps({
                u"extra": {
                    u"government": u"repressive",
                    u"assistant": u"Patsy",
                },
            }))
        self.assert_contact_response(resp, {
            u"key": contact_key,
            u"created_at": contact[u"created_at"],
            u"msisdn": u"+6789",
            u"name": u"Arthur",
            u"extra": {
                u"government": u"repressive",
                u"assistant": u"Patsy",
            },
        })

    @inlineCallbacks
    def test_update_non_existent_contact(self):
        api = self.mk_api()
        resp = yield self.request(
            api, "PUT", "/contacts/bad-id", json.dumps({
                "msisdn": u"+6789",
            }))
        self.assertEqual(resp, (404, {
            u"status_code": 404,
            u"reason": u"Contact 'bad-id' not found.",
        }))

    @inlineCallbacks
    def test_update_invalid_fields(self):
        api = self.mk_api()
        contact = yield self.create_contact(
            api, name=u"Bob", msisdn=u"+12345")

        contact_key = contact[u"key"]
        resp = yield self.request(
            api, "PUT", "/contacts/" + contact_key, json.dumps({
                u"unknown_field": u"foo",
                u"not_the_field": u"bar",
            }))
        self.assertEqual(resp, (400, {
            u"status_code": 400,
            u"reason": u"Invalid contact fields: not_the_field, unknown_field",
        }))

    @inlineCallbacks
    def test_delete(self):
        api = self.mk_api()
        contact = yield self.create_contact(
            api, name=u"Bob", msisdn=u"+12345")

        contact_key = contact[u"key"]
        resp = yield self.request(
            api, "DELETE", "/contacts/" + contact_key)
        self.assert_contact_response(resp, contact)

        exists = yield self.contact_exists(api, contact_key)
        self.assertFalse(exists)

    @inlineCallbacks
    def test_delete_non_existent_contact(self):
        api = self.mk_api()
        resp = yield self.request(api, "DELETE", "/contacts/bad-id")
        self.assertEqual(resp, (404, {
            u"status_code": 404,
            u"reason": u"Contact 'bad-id' not found.",
        }))


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
            headers["X-Owner-ID"] = self.OWNER_ID.encode("utf-8")
        app_helper = AppHelper(app=api)
        resp = yield app_helper.request(
            method, path, data=body, headers=headers)
        data = yield resp.json()
        returnValue((resp.code, data))

    def _store(self, api):
        owner = self.OWNER_ID.encode("utf-8")
        return api.backend.get_contact_collection(owner).contact_store

    @inlineCallbacks
    def create_contact(self, api, **contact_data):
        contact = yield self._store(api).new_contact(**contact_data)
        returnValue(contact_to_dict(contact))

    @inlineCallbacks
    def get_contact(self, api, contact_key):
        contact = yield self._store(api).get_contact_by_key(contact_key)
        returnValue(contact_to_dict(contact))

    @inlineCallbacks
    def contact_exists(self, api, contact_key):
        from go.vumitools.contact.models import ContactNotFoundError
        try:
            yield self.get_contact(api, contact_key)
        except ContactNotFoundError:
            returnValue(False)
        else:
            returnValue(True)

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
            ('/groups', api.group_backend.get_group_collection),
        ))

    @inlineCallbacks
    def test_route(self):
        api = self.mk_api()
        collection = api.backend.get_contact_collection(
            self.OWNER_ID.encode("utf-8"))
        key, data = yield collection.create(None, {
            "msisdn": u"+12345",
        })
        contact = yield collection.contact_store.get_contact_by_key(key)
        code, data = yield self.request(
            api, "GET", '/contacts/%s' % (key,))
        self.assertEqual(code, 200)
        self.assertEqual(data, contact_to_dict(contact))


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
            method, path, body=body, headers=headers))
        return resp.code, json.loads(resp.body)

    def create_contact(self, api, **contact_data):
        return api.create_contact(contact_data)

    def get_contact(self, api, contact_key):
        return api.get_contact(contact_key)

    def contact_exists(self, api, contact_key):
        from fake_go_contacts import FakeContactsError
        try:
            self.get_contact(api, contact_key)
        except FakeContactsError:
            return False
        else:
            return True


class TestGroupsApi(VumiTestCase, GroupsApiTestMixin):
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
    def create_group(self, api, name, query=None):
        if query is not None:
            group = yield self._store(api).new_smart_group(name, query)
        else:
            group = yield self._store(api).new_group(name)
        returnValue(group_to_dict(group))

    def _store(self, api):
        owner = self.OWNER_ID.encode("utf-8")
        return api.backend.get_contact_collection(owner).contact_store

    @inlineCallbacks
    def get_group(self, api, key):
        group = yield self._store(api).get_group(key)
        if group is None:
            raise CollectionObjectNotFound(key, u'Group')
        returnValue(group_to_dict(group))

    @inlineCallbacks
    def request(self, api, method, path, body=None, headers=None, auth=True):
        if headers is None:
            headers = {}
        if auth:
            headers["X-Owner-ID"] = self.OWNER_ID.encode("utf-8")
        app_helper = AppHelper(app=api)
        resp = yield app_helper.request(
            method, path, data=body, headers=headers)
        data = yield resp.json()
        returnValue((resp.code, data))

    @inlineCallbacks
    def group_exists(self, api, group_key):
        try:
            yield self.get_group(api, group_key)
        except CollectionObjectNotFound:
            returnValue(False)
        else:
            returnValue(True)

    def test_init(self):
        configfile = self.mk_config({
            "riak_manager": {
                "bucket_prefix": "test",
            },
        })
        api = ContactsApi(configfile)
        self.assertTrue(isinstance(api.group_backend, RiakGroupsBackend))
        self.assertTrue(isinstance(api.group_backend.riak_manager,
                                   TxRiakManager))
