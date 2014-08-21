"""
Tests for contacts API cyclone server.
"""
from twisted.internet.defer import inlineCallbacks
import json


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
        if u'created_at' in data:
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
