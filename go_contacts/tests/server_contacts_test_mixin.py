"""
Tests for contacts API cyclone server.
"""
from twisted.internet.defer import inlineCallbacks
import json


class ContactsApiTestMixin(object):
    def mk_api(self, limit):
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
        code, data = yield self.request(api, "GET", "/contacts/bad-id")
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
        code, data = yield self.request(
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

    @inlineCallbacks
    def test_stream_contacts_query(self):
        """
        If a query parameter is supplied, a CollectionUsageError should be
        thrown, as queries are not yet supported.
        """
        api = self.mk_api()
        code, data = yield self.request(
            api, 'GET', '/contacts/?stream=true&query=foo')
        self.assertEqual(code, 400)
        self.assertEqual(data.get(u'status_code'), 400)
        self.assertEqual(data.get(u'reason'), u'query parameter not supported')

    @inlineCallbacks
    def test_stream_all_contacts_empty(self):
        """
        This test ensures that an empty list of data is streamed if there are
        no contacts in the contact store.
        """
        api = self.mk_api()
        code, data = yield self.request(
            api, 'GET', '/contacts/?stream=true', parser='json_lines')
        self.assertEqual(code, 200)
        self.assertEqual(data, [])

    @inlineCallbacks
    def test_stream_all_contacts(self):
        """
        This test ensures that all the contacts in the contact store are
        streamed when streaming is requested.
        """
        api = self.mk_api()
        contact1 = yield self.create_contact(
            api, name=u"Bob", msisdn=u"+12345")
        contact2 = yield self.create_contact(
            api, name=u"Susan", msisdn=u"+54321")

        code, data = yield self.request(
            api, 'GET', '/contacts/?stream=true', parser='json_lines')
        self.assertEqual(code, 200)
        self.assertTrue(contact1 in data)
        self.assertTrue(contact2 in data)

    @inlineCallbacks
    def test_get_contact_empty_page(self):
        """
        This tests tests that an empty page is returned when there are no
        contacts in the contact store.
        """
        api = self.mk_api()
        code, data = yield self.request(api, 'GET', '/contacts/')
        self.assertEqual(code, 200)
        self.assertEqual(data, {'cursor': None, 'data': []})

    @inlineCallbacks
    def test_get_contact_page_multiple(self):
        """
        This test ensures that contacts are split over multiple pages according
        to the ``max_results`` parameter in the query string. It also tests
        that multiple pages are fetched correctly when using the next page
        cursor
        """
        api = self.mk_api()

        contact1 = yield self.create_contact(
            api, name=u"Bob", msisdn=u"+12345")
        contact2 = yield self.create_contact(
            api, name=u"Susan", msisdn=u"+54321")
        contact3 = yield self.create_contact(
            api, name=u"Foo", msisdn=u"+314159")

        code, data = yield self.request(api, 'GET', '/contacts/?max_results=2')
        self.assertEqual(code, 200)
        cursor = data[u'cursor']
        contacts = data[u'data']
        self.assertEqual(len(contacts), 2)

        code, data = yield self.request(
            api, 'GET',
            '/contacts/?max_results=2&cursor=%s' % cursor.encode('ascii'))
        self.assertEqual(code, 200)
        self.assertEqual(data[u'cursor'], None)
        contacts += data[u'data']

        self.assertTrue(contact1 in contacts)
        self.assertTrue(contact2 in contacts)
        self.assertTrue(contact3 in contacts)

    @inlineCallbacks
    def test_get_contact_page_single(self):
        """
        This test tests that a single page with a None cursor is returned if
        all the contacts in the contact store fit into one page.
        """
        api = self.mk_api()

        contact1 = yield self.create_contact(
            api, name=u"Bob", msisdn=u"+12345")
        contact2 = yield self.create_contact(
            api, name=u"Susan", msisdn=u"+54321")

        code, data = yield self.request(
            api, 'GET', '/contacts/?max_results=3')
        self.assertEqual(code, 200)
        cursor = data[u'cursor']
        contacts = data[u'data']
        self.assertEqual(len(contacts), 2)
        self.assertEqual(cursor, None)
        self.assertTrue(contact1 in contacts)
        self.assertTrue(contact2 in contacts)

    @inlineCallbacks
    def test_page_default_limit_contacts(self):
        """
        For this test, the default limit per page is set to 5. If the user
        requests more than this, `contacts/?max_results=10`, it should only
        return the maximum of 5 results per page.
        """
        api = self.mk_api(limit=5)

        for i in range(10):
            yield self.create_contact(
                api, name=u'%s' % str(i)*5, msisdn=u'+%s' % str(i)*5)

        code, data = yield self.request(
            api, 'GET', '/contacts/?max_results=10')
        self.assertEqual(code, 200)
        self.assertEqual(len(data.get('data')), 5)

    @inlineCallbacks
    def test_page_bad_cursor(self):
        """
        If the user requests a next page cursor that doesn't exist,
        ``contacts/?cursor=bad-id``, an empty page should be returned
        """
        api = self.mk_api()
        yield self.create_contact(api, name=u"Bob", msisdn=u"+12345")

        code, data = yield self.request(
            api, 'GET', '/contacts/?cursor=bad-id')
        self.assertEqual(code, 400)
        self.assertEqual(data.get(u'status_code'), 400)
        self.assertEqual(
            data.get(u'reason'),
            u"Riak error, possible invalid cursor: u'bad-id'")

    @inlineCallbacks
    def test_page_query(self):
        """
        If a query parameter is supplied, a CollectionUsageError should be
        thrown, as querys are not yet supported.
        """
        api = self.mk_api()
        code, data = yield self.request(api, 'GET', '/contacts/?query=foo')
        self.assertEqual(code, 400)
        self.assertEqual(data.get(u'status_code'), 400)
        self.assertEqual(data.get(u'reason'), u'query parameter not supported')
