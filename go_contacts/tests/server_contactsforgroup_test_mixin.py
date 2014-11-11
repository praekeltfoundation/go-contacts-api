"""
Tests for contacts API cyclone server.
"""
from twisted.internet.defer import inlineCallbacks
# import json


class ContactsForGroupApiTestMixin(object):
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

    @inlineCallbacks
    def test_stream_query(self):
        """
        An HTTP error is sent if a request is sent with a query
        """
        api = self.mk_api()
        code, data = yield self.request(
            api, 'GET', '/groups/1/contacts?stream=true&query=foo',
            parser=json)
        self.assertEqual(code, 500)
        self.assertEqual(data['response_code'], 500)
        self.assertEqual(data['reason'], 'query parameter not supported')

    @inlineCallbacks
    def test_stream_all_contacts_for_group_empty(self):
        """
        An empty list of data is streamed if there are no contacts in the 
        contact group.
        """
        api = self.mk_api()
        group = yield self.create_group(api, name=u'Bob')
        code, data = yield self.request(
            api, 'GET', '/groups/%s/contacts?stream=true' % group.get('id'),
            parser='json_lines')
        self.assertEqual(code, 200)
        self.assertEqual(data, [])
