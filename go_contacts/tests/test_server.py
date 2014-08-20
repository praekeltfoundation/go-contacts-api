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

from go_contacts.backends.riak import (
    RiakContactsBackend, contact_to_dict, group_to_dict, RiakGroupsBackend)
from go_contacts.server import ContactsApi
from go_contacts.tests.server_groups_test_mixin import GroupsApiTestMixin
from go_contacts.tests.server_contacts_test_mixin import ContactsApiTestMixin
from go_api.collections.errors import CollectionObjectNotFound


class TestApiServer(object):
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
            ('/contacts', api.contact_backend.get_contact_collection),
            ('/groups', api.group_backend.get_group_collection),
        ))

    @inlineCallbacks
    def test_route(self):
        api = self.mk_api()
        collection = api.contact_backend.get_contact_collection(
            self.OWNER_ID.encode("utf-8"))
        key, data = yield collection.create(None, {
            "msisdn": u"+12345",
        })
        contact = yield collection.contact_store.get_contact_by_key(key)
        code, data = yield self.request(
            api, "GET", '/contacts/%s' % (key,))
        self.assertEqual(code, 200)
        self.assertEqual(data, contact_to_dict(contact))


class TestContactsApi(VumiTestCase, ContactsApiTestMixin,
                      TestApiServer):
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
        return api.contact_backend.get_contact_collection(owner).contact_store

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
        self.assertTrue(isinstance(api.contact_backend, RiakContactsBackend))
        self.assertTrue(isinstance(api.contact_backend.riak_manager,
                                   TxRiakManager))


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
        return api.contacts.create_contact(contact_data)

    def get_contact(self, api, contact_key):
        return api.contacts.get_contact(contact_key)

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
        return api.group_backend.get_group_collection(owner).contact_store

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


class TestFakeGroupsApi(VumiTestCase, GroupsApiTestMixin):
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
        return self.api_class("", "token-1")

    def request(self, api, method, path, body=None, headers=None, auth=True):
        if headers is None:
            headers = {}
        if auth:
            headers["Authorization"] = "Bearer token-1"
        resp = api.handle_request(self.req_class(
            method, path, body=body, headers=headers))
        return resp.code, json.loads(resp.body)

    def create_group(self, api, **group_data):
        return api.groups.create_group(group_data)

    def get_group(self, api, group_key):
        return api.groups.get_group(group_key)

    def group_exists(self, api, group_key):
        from fake_go_contacts import FakeContactsError
        try:
            self.get_group(api, group_key)
        except FakeContactsError:
            return False
        else:
            return True
