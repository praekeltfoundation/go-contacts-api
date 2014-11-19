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
        api = yield self.mk_api()
        code, data = yield self.request(
            api, 'GET', '/groups/1/contacts?stream=true&query=foo',
            parser='json')
        self.assertEqual(code, 400)
        self.assertEqual(data['status_code'], 400)
        self.assertEqual(data['reason'], 'query parameter not supported')

    @inlineCallbacks
    def test_stream_all_contacts_for_group_empty(self):
        """
        An empty list of data is streamed if there are no contacts in the
        contact group.
        """
        api = yield self.mk_api()
        group = yield self.create_group(api, name=u'Bob')
        code, data = yield self.request(
            api, 'GET', '/groups/%s/contacts?stream=true' % group.get('key'),
            parser='json_lines')
        self.assertEqual(code, 200)
        self.assertEqual(data, [])

    @inlineCallbacks
    def test_stream_all_contacts_for_group(self):
        """
        All the contacts should be streamed if there are contacts in the
        contact group
        """
        api = yield self.mk_api(limit=2)
        group = yield self.create_group(api, name=u'Foo')
        group_false = yield self.create_group(api, name=u'Wally')

        contact1 = yield self.create_contact(
            api, name=u'Bar', msisdn=u'+12345', groups=[group.get('key')])
        contact2 = yield self.create_contact(
            api, name=u'Baz', msisdn=u'+54321', groups=[group.get('key')])
        contact3 = yield self.create_contact(
            api, name=u'Qux', msisdn=u'+31415',
            groups=[group.get('key'), group_false.get('key')])
        contact4 = yield self.create_contact(
            api, name=u'Quux', msisdn=u'+27172',
            groups=[group_false.get('key')])

        code, data = yield self.request(
            api, 'GET', '/groups/%s/contacts?stream=true' % group.get('key'),
            parser='json_lines')

        self.assertEqual(code, 200)
        self.assertTrue(contact1 in data)
        self.assertTrue(contact2 in data)
        self.assertTrue(contact3 in data)
        self.assertFalse(contact4 in data)

    @inlineCallbacks
    def test_stream_contacts_for_smart_group(self):
        """
        All the static as well as dynamic contacts for a group should be
        streamed
        """
        api = yield self.mk_api(limit=2)
        group = yield self.create_group(
            api, name=u'Foo', query=u'msisdn:12345')
        group_false = yield self.create_group(api, name=u'Wally')

        contact1 = yield self.create_contact(
            api, name=u'Bar', msisdn=u'12345', groups=[group.get('key')])
        contact2 = yield self.create_contact(
            api, name=u'Baz', msisdn=u'54321', groups=[group.get('key')])
        contact3 = yield self.create_contact(
            api, name=u'Qux', msisdn=u'31415',
            groups=[group_false.get('key')])
        contact4 = yield self.create_contact(
            api, name=u'Quux', msisdn=u'12345')

        code, data = yield self.request(
            api, 'GET', '/groups/%s/contacts?stream=true' % group.get('key'),
            parser='json_lines')

        self.assertEqual(code, 200)
        self.assertTrue(contact1 in data)
        self.assertTrue(contact2 in data)
        self.assertFalse(contact3 in data)
        self.assertTrue(contact4 in data)

    @inlineCallbacks
    def test_stream_bad_id(self):
        """
        If the contacts of an invalid group id is requested, an empty stream
        should be returned.
        """
        api = yield self.mk_api()

        code, data = yield self.request(
            api, 'GET', '/groups/foo/contacts?stream=true', parser='json_lines')

        self.assertEqual(code, 200)
        self.assertEqual(data, [])

    @inlineCallbacks
    def test_get_page_empty(self):
        """
        An empty page with None continuation cursor is sent if there are no
        contacts in the contact group
        """
        api = yield self.mk_api()
        group = yield self.create_group(api, name=u'Foo')
        code, data = yield self.request(
            api, 'GET', '/groups/%s/contacts' % group.get('key'),
            parser='json')
        self.assertEqual(code, 200)
        self.assertEqual(data[u'cursor'], None)
        self.assertEqual(data[u'data'], [])

    @inlineCallbacks
    def test_get_page(self):
        """
        If all of the contacts fit on a page, it should return that page with
        a None continuation cursor.
        """
        api = yield self.mk_api(limit=3)
        group = yield self.create_group(api, name=u'Foo')
        group2 = yield self.create_group(api, name=u'Waldo')
        contact1 = yield self.create_contact(
            api, name=u'Bar', msisdn=u'+12345', groups=[group.get('key')])
        contact2 = yield self.create_contact(
            api, name=u'Baz', msisdn=u'+54321', groups=[group.get('key')])
        contact3 = yield self.create_contact(
            api, name=u'Qux', msisdn=u'+31415', groups=[group2.get('key')])
        code, data = yield self.request(
            api, 'GET', '/groups/%s/contacts' % group.get('key'),
            parser='json')
        self.assertEqual(code, 200)
        self.assertEqual(data.get('cursor'), None)
        self.assertTrue(contact1 in data.get('data'))
        self.assertTrue(contact2 in data.get('data'))
        self.assertFalse(contact3 in data.get('data'))

    @inlineCallbacks
    def test_get_page_multiple(self):
        """
        If all of the contacts don't fit on a single page, they should be
        spread across multiple pages. (default page size limit)
        """
        api = yield self.mk_api(limit=2)
        group = yield self.create_group(api, name=u'Foo')
        group2 = yield self.create_group(api, name=u'Waldo')
        contact1 = yield self.create_contact(
            api, name=u'Bar', msisdn=u'+12345', groups=[group.get('key')])
        contact2 = yield self.create_contact(
            api, name=u'Baz', msisdn=u'+54321', groups=[group.get('key')])
        contact3 = yield self.create_contact(
            api, name=u'Qux', msisdn=u'+31415', groups=[group.get('key')])
        contact4 = yield self.create_contact(
            api, name=u'Quux', msisdn=u'+27172', groups=[group2.get('key')])

        code, data = yield self.request(
            api, 'GET', '/groups/%s/contacts' % group.get('key'),
            parser='json')

        self.assertEqual(code, 200)
        self.assertFalse(data.get('cursor') is None)

        contacts = data.get('data')

        code, data = yield self.request(
            api, 'GET', '/groups/%s/contacts?cursor=%s' % (
                group.get('key'), data.get('cursor').encode()), parser='json')

        self.assertEqual(code, 200)
        self.assertTrue(data.get('cursor') is None)

        contacts += data.get('data')
        self.assertTrue(contact1 in contacts)
        self.assertTrue(contact2 in contacts)
        self.assertTrue(contact3 in contacts)
        self.assertFalse(contact4 in contacts)

    @inlineCallbacks
    def test_get_page_multiple_with_limit(self):
        """
        If all of the contacts don't fit on a single page, they should be
        spread across multiple pages. (url parameter page size limit)
        """
        api = yield self.mk_api()
        group = yield self.create_group(api, name=u'Foo')
        group2 = yield self.create_group(api, name=u'Waldo')
        contact1 = yield self.create_contact(
            api, name=u'Bar', msisdn=u'+12345', groups=[group.get('key')])
        contact2 = yield self.create_contact(
            api, name=u'Baz', msisdn=u'+54321', groups=[group.get('key')])
        contact3 = yield self.create_contact(
            api, name=u'Qux', msisdn=u'+31415',
            groups=[group.get('key'), group2.get('key')])
        contact4 = yield self.create_contact(
            api, name=u'Qux', msisdn=u'+27172', groups=[group2.get('key')])

        code, data = yield self.request(
            api, 'GET', '/groups/%s/contacts?max_results=2' % group.get('key'),
            parser='json')

        self.assertEqual(code, 200)
        self.assertFalse(data.get('cursor') is None)

        contacts = data.get('data')

        code, data = yield self.request(
            api, 'GET', '/groups/%s/contacts?cursor=%s&max_results=2' % (
                group.get('key'), data.get('cursor').encode()), parser='json')

        self.assertEqual(code, 200)
        self.assertTrue(data.get('cursor') is None)

        contacts += data.get('data')
        self.assertTrue(contact1 in contacts)
        self.assertTrue(contact2 in contacts)
        self.assertTrue(contact3 in contacts)
        self.assertFalse(contact4 in contacts)

    @inlineCallbacks
    def test_get_page_bad_cursor(self):
        """
        If a bad cursor is supplied, an error message should be returned.
        """
        api = yield self.mk_api()
        group = yield self.create_group(api, name=u'Foo')
        yield self.create_contact(
            api, name=u'Bar', msisdn=u'+12345', groups=[group.get('key')])

        code, data = yield self.request(
            api, 'GET', '/groups/%s/contacts?cursor=foo' % group.get('key'),
            parser='json')

        self.assertEqual(code, 400)
        self.assertEqual(data.get('status_code'), 400)
        self.assertEqual(
            data.get('reason'), u"Invalid cursor: u'foo'")

    @inlineCallbacks
    def test_get_page_invalid_group_id(self):
        """
        If the contacts of an invalid group id is requested, an empty page
        should be returned.
        """
        api = yield self.mk_api()

        code, data = yield self.request(
            api, 'GET', '/groups/foo/contacts', parser='json')

        self.assertEqual(code, 200)
        self.assertEqual(data.get('cursor'), None)
        self.assertEqual(data.get('data'), [])

    @inlineCallbacks
    def test_get_page_with_query(self):
        """
        If a query is specified, an error should be returned, as queries are
        not yet supported
        """
        api = yield self.mk_api()

        code, data = yield self.request(
            api, 'GET', '/groups/foo/contacts?query=bar', parser='json')

        self.assertEqual(code, 400)
        self.assertEqual(data.get('status_code'), 400)
        self.assertEqual(data.get('reason'), 'query parameter not supported')

    @inlineCallbacks
    def test_page_dynamic_group_contacts(self):
        """
        Getting a page of contacts should return both the static and dynamic
        contacts for a group.
        """
        api = yield self.mk_api()

        group_false = yield self.create_group(api, name=u'Wally')
        group = yield self.create_group(
            api, name=u'Foo', query=u'msisdn:12345')

        contact1 = yield self.create_contact(
            api, name=u'Bar', msisdn=u'12345'
            )
        contact2 = yield self.create_contact(
            api, name=u'Baz', msisdn=u'54321',
            groups=[group.get('key')])
        contact3 = yield self.create_contact(
            api, name=u'Qux', msisdn=u'12345'
            )
        contact4 = yield self.create_contact(
            api, name=u'Quux', msisdn=u'27172',
            groups=[group_false.get('key')])

        code, data = yield self.request(
            api, 'GET', '/groups/%s/contacts?max_results=2' % group.get('key'))
        self.assertEqual(code, 200)
        cursor = data.get('cursor').encode()
        contacts = data.get('data')
        self.assertFalse(cursor is None)

        while cursor is not None:
            code, data = yield self.request(
                api, 'GET', '/groups/%s/contacts?max_results=2&cursor=%s' % (
                    group.get('key'), cursor.encode()))
            self.assertEqual(code, 200)
            cursor = data.get('cursor')
            contacts += data.get('data')

        self.assertTrue(contact1 in contacts)
        self.assertTrue(contact2 in contacts)
        self.assertTrue(contact3 in contacts)
        self.assertFalse(contact4 in contacts)
