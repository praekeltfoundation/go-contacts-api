"""
Tests for groups API cyclone server.
"""
from twisted.internet.defer import inlineCallbacks
import json


class GroupsApiTestMixin(object):
    def mk_api(self):
        raise NotImplementedError()

    def request(self, api, method, path, body=None, headers=None, auth=True):
        raise NotImplementedError()

    def create_group(self, api, **group_data):
        raise NotImplementedError()

    def get_group(self, api, group_key):
        raise NotImplementedError()

    def group_exists(self, api, group_key):
        raise NotImplementedError()

    EXPECTED_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

    OWNER_ID = u'owner-1'

    GROUP_FIELD_DEFAULTS = {
        u'$VERSION': None,
        u'name': None,
        u'query': None,
    }

    def assert_group_response(self, response, expected_partial):
        expected = self.GROUP_FIELD_DEFAULTS.copy()
        expected.update(expected_partial)
        expected[u'user_account'] = self.OWNER_ID
        data = response[1]
        if u'key' in data:
            expected.setdefault(u'key', data[u'key'])
        if u'created_at' in data:
            expected.setdefault(u'created_at', data[u'created_at'])
        self.assertEqual(response, (200, expected))
        return data

    def assert_group(self, group, expected_partial):
        expected = self.GROUP_FIELD_DEFAULTS.copy()
        expected.update(expected_partial)
        expected[u'user_account'] = self.OWNER_ID
        self.assertEqual(group, expected)

    @inlineCallbacks
    def test_get(self):
        api = self.mk_api()
        group = yield self.create_group(api, name=u'Bob')
        group_key = group[u'key']
        resp = yield self.request(api, 'GET', '/groups/%s' % group_key)
        self.assert_group_response(resp, group)

    @inlineCallbacks
    def test_get_non_existent_group(self):
        api = self.mk_api()
        (code, data) = yield self.request(api, 'GET', '/groups/bad-key')
        self.assertEqual(code, 404)
        self.assertEqual(data, {
            u'reason': u"Group 'bad-key' not found.",
            u'status_code': 404,
        })

    @inlineCallbacks
    def test_create(self):
        api = self.mk_api()
        resp = yield self.request(api, 'POST', '/groups/', json.dumps({
            u'name': u'Bob',
        }))
        group = self.assert_group_response(resp, {
            u'name': u'Bob'
        })
        group_key = group[u'key']
        stored_group = yield self.get_group(api, group_key)
        self.assert_group(stored_group, group)

    @inlineCallbacks
    def test_create_smart(self):
        api = self.mk_api()
        resp = yield self.request(api, 'POST', '/groups/', json.dumps({
            u'name': u'Bob',
            u'query': u'test_query',
        }))
        group = self.assert_group_response(resp, {
            u'name': u'Bob',
            u'query': u'test_query',
        })
        group_key = group[u'key']
        stored_group = yield self.get_group(api, group_key)
        self.assert_group(stored_group, group)

    @inlineCallbacks
    def test_create_invalid_fields(self):
        api = self.mk_api()
        (code, data) = yield self.request(api, 'POST', '/groups/', json.dumps({
            u'unknown_field': u'foo',
            u'not_the_field': u'bar',
        }))
        self.assertEqual(code, 400)
        self.assertEqual(data, {
            u'status_code': 400,
            u'reason': u'Invalid group fields: not_the_field, unknown_field',
        })

    @inlineCallbacks
    def test_create_with_id(self):
        api = self.mk_api()
        (code, data) = yield self.request(api, 'POST', '/groups/key')
        self.assertEqual(code, 405)
        self.assertEqual(data, {
            u'reason': u'Method Not Allowed',
            u'status_code': 405,
        })

    @inlineCallbacks
    def test_delete(self):
        api = self.mk_api()
        group = yield self.create_group(api, name=u'Bob')
        group_key = group[u'key']
        resp = yield self.request(api, 'DELETE', '/groups/%s' % group_key)
        self.assert_group_response(resp, group)
        exists = yield self.group_exists(api, group_key)
        self.assertFalse(exists)

    @inlineCallbacks
    def test_delete_non_existent_group(self):
        api = self.mk_api()
        (code, data) = yield self.request(api, 'DELETE', '/groups/bad-id')
        self.assertEqual(code, 404)
        self.assertEqual(data, {
            u'reason': u"Group 'bad-id' not found.",
            u'status_code': 404,
        })

    @inlineCallbacks
    def test_update(self):
        api = self.mk_api()
        group = yield self.create_group(api, name=u'Bob')
        group_key = group[u'key']
        resp = yield self.request(api, 'PUT', '/groups/%s' % group_key,
                                  json.dumps({u'name': u'Susan'}))
        self.assert_group_response(resp, {
            u'key': group_key,
            u'created_at': group[u'created_at'],
            u'name': 'Susan',
        })
        updated_group = yield self.get_group(api, group_key)
        self.assertEqual(updated_group[u'name'], u'Susan')

    @inlineCallbacks
    def test_update_query(self):
        api = self.mk_api()
        group = yield self.create_group(api, name=u'Bob', query=u'test_query')
        group_key = group[u'key']
        resp = yield self.request(api, 'PUT', '/groups/%s' % group_key,
                                  json.dumps({u'query': u'new_query'}))
        self.assert_group_response(resp, {
            u'key': group_key,
            u'created_at': group[u'created_at'],
            u'name': 'Bob',
            u'query': 'new_query',
        })
        updated_group = yield self.get_group(api, group_key)
        self.assertEqual(updated_group[u'query'], u'new_query')

    @inlineCallbacks
    def test_update_invalid_fields(self):
        api = self.mk_api()
        group = yield self.create_group(api, name=u'Bob')
        group_key = group[u'key']
        (code, data) = yield self.request(api, 'PUT', '/groups/%s' % group_key,
                                          json.dumps({u'foo': 'bar'}))
        self.assertEqual(code, 400)
        self.assertEqual(data, {
            u'reason': u'Invalid group fields: foo',
            u'status_code': 400,
        })

    @inlineCallbacks
    def test_update_non_existant_contact(self):
        api = self.mk_api()
        (code, data) = yield self.request(api, 'PUT', '/groups/bad-id',
                                          json.dumps({u'name': u'Bob'}))
        self.assertEqual(code, 404)
        self.assertEqual(data, {
            u'reason': u"Group 'bad-id' not found.",
            u'status_code': 404,
            })
