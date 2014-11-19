"""
A verified fake implementation of go-contacts for use in tests.

This implementation is tested in the go-contacts package alongside the API it
is faking, to ensure that the behaviour is the same for both.
"""


import json
from uuid import uuid4
from urlparse import urlparse, parse_qs
import itertools
import urllib


class Request(object):
    """
    Representation of an HTTP request.
    """

    def __init__(self, method, path, body=None, headers=None):
        self.method = method
        self.path = path
        self.body = body
        self.headers = headers if headers is not None else {}


class Response(object):
    """
    Representation of an HTTP response.
    """

    def __init__(self, code, headers, data):
        self.code = code
        self.headers = headers if headers is not None else {}
        self.data = data
        self.body = json.dumps(data)


class FakeContactsError(Exception):
    """
    Error we can use to craft a different HTTP response.
    """

    def __init__(self, code, reason):
        super(FakeContactsError, self).__init__()
        self.code = code
        self.reason = reason
        self.data = {
            u"status_code": code,
            u"reason": reason,
        }


def _data_to_json(data):
    if not isinstance(data, basestring):
        # If we don't already have JSON, we want to make some to guarantee
        # encoding succeeds.
        data = json.dumps(data)
    return json.loads(data)

previous_cursors = []


def _paginate(contact_list, cursor, max_results):
    contact_list.sort(key=lambda contact: contact['key'])
    if cursor is not None:
        if cursor not in previous_cursors:
            raise FakeContactsError(
                400,
                u"Riak error, possible invalid cursor: %r" % (cursor,))
        # Encoding and decoding are the same operation
        cursor = _encode_cursor(cursor)
        contact_list = list(itertools.dropwhile(
            lambda contact: contact['key'] <= cursor, contact_list))
    new_cursor = None
    if len(contact_list) > max_results:
        contact_list = contact_list[:max_results]
        new_cursor = contact_list[-1]['key']
        new_cursor = _encode_cursor(new_cursor)
    previous_cursors.append(new_cursor)
    return (contact_list, new_cursor)


def _encode_cursor(cursor):
    if cursor is not None:
        cursor = cursor.encode('rot13')
    return cursor


class FakeContacts(object):
    """
    Fake implementation of the Contacts part of the Contacts API
    """
    def __init__(self, contacts_data={}, max_contacts_per_page=10):
        self.contacts_data = contacts_data
        self.max_contacts_per_page = max_contacts_per_page

    @staticmethod
    def make_contact_dict(fields):
        contact = {
            # Always generate a key. It can be overridden by `fields`.
            u'key': uuid4().hex,

            # Some constant-for-our-purposes fields.
            u'$VERSION': 2,
            u'user_account': u'owner-1',
            u'created_at': u'2014-07-25 12:44:11.159151',

            # Everything else.
            u'name': None,
            u'surname': None,
            u'groups': [],
            u'msisdn': None,
            u'twitter_handle': None,
            u'bbm_pin': None,
            u'mxit_id': None,
            u'dob': None,
            u'facebook_id': None,
            u'wechat_id': None,
            u'email_address': None,
            u'gtalk_id': None,
            u'extra': {},
            u'subscription': {},
        }
        contact.update(fields)
        return contact

    def _check_fields(self, contact_data):
        allowed_fields = set(self.make_contact_dict({}).keys())
        allowed_fields.discard(u"key")

        bad_fields = set(contact_data.keys()) - allowed_fields
        if bad_fields:
            raise FakeContactsError(
                400, "Invalid contact fields: %s" % ", ".join(
                    sorted(bad_fields)))

    def create_contact(self, contact_data):
        contact_data = _data_to_json(contact_data)
        self._check_fields(contact_data)

        contact = self.make_contact_dict(contact_data)
        self.contacts_data[contact[u"key"]] = contact
        return contact

    def get_contact(self, contact_key):
        contact = self.contacts_data.get(contact_key)
        if contact is None:
            raise FakeContactsError(
                404, u"Contact %r not found." % (contact_key,))
        return contact

    def get_all_contacts(self, query):
        if query is not None:
            raise FakeContactsError(400, "query parameter not supported")
        return self.contacts_data.values()

    def get_all(self, query):
        stream = query.get('stream', None)
        stream = stream and stream[0]
        q = query.get('query', None)
        q = q and q[0]
        if stream == 'true':
            return self.get_all_contacts(q)
        else:
            cursor = query.get('cursor', None)
            cursor = cursor and cursor[0]
            max_results = query.get('max_results', None)
            max_results = max_results and max_results[0]
            return self.get_page_contacts(q, cursor, max_results)

    def get_page_contacts(self, query, cursor, max_results):
        contacts = self.get_all_contacts(query)

        max_results = (max_results and int(max_results)) or float('inf')
        max_results = min(max_results, self.max_contacts_per_page)

        contacts, cursor = _paginate(contacts, cursor, max_results)

        return {u'cursor': cursor, u'data': contacts}

    def update_contact(self, contact_key, contact_data):
        contact = self.get_contact(contact_key)
        contact_data = _data_to_json(contact_data)
        self._check_fields(contact_data)
        for k, v in contact_data.iteritems():
            contact[k] = v
        return contact

    def delete_contact(self, contact_key):
        contact = self.get_contact(contact_key)
        self.contacts_data.pop(contact_key)
        return contact

    def request(self, request, contact_key, query, contact_store):
        if request.method == "POST":
            if contact_key is None or contact_key is "":
                return self.create_contact(request.body)
            else:
                raise FakeContactsError(405, "")
        if request.method == "GET":
            if contact_key is None or contact_key is "":
                return self.get_all(query)
            else:
                return self.get_contact(contact_key)
        elif request.method == "PUT":
            # NOTE: This is an incorrect use of the PUT method, but
            # it's what we have for now.
            return self.update_contact(contact_key, request.body)
        elif request.method == "DELETE":
            return self.delete_contact(contact_key)
        else:
            raise FakeContactsError(405, "")


class FakeGroups(object):
    """
    Fake implementation of the Groups part of the Contacts API
    """
    dynamic_cursor_keyword = 'dynamicgroup'
    static_cursor_keyword = 'staticgroup'

    def __init__(self, groups_data={}, max_groups_per_page=10):
        self.groups_data = groups_data
        self.max_groups_per_page = max_groups_per_page

    @staticmethod
    def make_group_dict(fields):
        group = {
            # Always generate a key. It can be overridden by `fields`.
            u'key': uuid4().hex,

            # Some constant-for-our-purposes fields.
            u'$VERSION': None,
            u'user_account': u'owner-1',
            u'created_at': u'2014-07-25 12:44:11.159151',

            # Everything else.
            u'name': None,
            u'query': None,
        }
        group.update(fields)
        return group

    def _check_fields(self, group_data):
        allowed_fields = set(self.make_group_dict({}).keys())
        allowed_fields.discard(u"key")

        bad_fields = set(group_data.keys()) - allowed_fields
        if bad_fields:
            raise FakeContactsError(
                400, "Invalid group fields: %s" % ", ".join(
                    sorted(bad_fields)))

    def create_group(self, group_data):
        group_data = _data_to_json(group_data)
        self._check_fields(group_data)
        group = self.make_group_dict(group_data)
        self.groups_data[group[u"key"]] = group
        return group

    def get_group(self, group_key):
        group = self.groups_data.get(group_key)
        if group is None:
            raise FakeContactsError(
                404, u"Group %r not found." % (group_key,))
        return group

    def get_all_groups(self, query):
        if query is not None:
            raise FakeContactsError(400, "query parameter not supported")
        return self.groups_data.values()

    def get_page_groups(self, query, cursor, max_results):
        groups = self.get_all_groups(query)

        max_results = (max_results and int(max_results)) or float('inf')
        max_results = min(max_results, self.max_groups_per_page)

        groups, cursor = _paginate(groups, cursor, max_results)

        return {u'cursor': cursor, u'data': groups}

    def get_contacts_for_group(self, key, query):
        stream = query.get('stream', None)
        stream = stream and stream[0]
        q = query.get('query', None)
        q = q and q[0]
        if stream == 'true':
            return self.get_contacts_for_group_stream(q, key)
        else:
            cursor = query.get('cursor', None)
            cursor = cursor and cursor[0]
            max_results = query.get('max_results', None)
            max_results = max_results and max_results[0]
            return self.get_contacts_for_group_page(
                q, key, cursor, max_results)

    def _filter_contacts(self, contacts, group_key):
        filtered = []
        for contact in contacts:
            if group_key in contact.get('groups'):
                filtered.append(contact)
        return filtered

    def _query_contacts(self, contacts, query):
        try:
            field, _, value = query.partition(':')
            results = []
            for contact in contacts:
                if contact[field] == value:
                    results.append(contact)
            return results
        except KeyError:
            raise FakeContactsError(
                400, "Invalid query, FakeContacts only supports queries of " +
                "the form 'field:value'")

    def get_contacts_for_group_stream(self, query, key):
        if query is not None:
            raise FakeContactsError(400, "query parameter not supported")
        all_contacts = self.fake_contacts.get_all_contacts(None)
        contacts = self._filter_contacts(all_contacts, key)
        group = self.groups_data.get(key)
        if group and group['query'] is not None:
            contacts.extend(self._query_contacts(all_contacts, group['query']))
        return contacts

    def get_contacts_for_group_page(self, query, key, cursor, max_results):
        if query is not None:
            raise FakeContactsError(400, "query parameter not supported")

        all_contacts = self.fake_contacts.get_all_contacts(None)
        max_results = (max_results and int(max_results)) or float('inf')
        max_results = min(
            max_results, self.fake_contacts.max_contacts_per_page)

        if cursor is not None:
            decoded_cursor = cursor.decode('rot13')
        else:
            decoded_cursor = self.static_cursor_keyword

        if decoded_cursor.startswith(self.dynamic_cursor_keyword):
            group = self.groups_data.get(key)
            decoded_cursor = decoded_cursor[len(self.dynamic_cursor_keyword):]
            if decoded_cursor == '':
                decoded_cursor = None
            contacts = self._query_contacts(all_contacts, group['query'])
            contacts, cursor = _paginate(
                contacts, decoded_cursor, max_results)
            if cursor is not None:
                cursor = (self.dynamic_cursor_keyword + cursor).encode('rot13')
        elif decoded_cursor.startswith(self.static_cursor_keyword):
            decoded_cursor = decoded_cursor[len(self.static_cursor_keyword):]
            decoded_cursor = None if decoded_cursor == '' else decoded_cursor
            contacts = self._filter_contacts(all_contacts, key)
            contacts, cursor = _paginate(contacts, decoded_cursor, max_results)

            if cursor is None:
                group = self.groups_data.get(key)
                if group and group.get('query'):
                    cursor = self.dynamic_cursor_keyword.encode('rot13')
            else:
                cursor = (self.static_cursor_keyword + cursor).encode('rot13')
        else:
            raise FakeContactsError(400, "Invalid cursor: %r" % cursor)

        return {u'cursor': cursor, u'data': contacts}

    def update_group(self, group_key, group_data):
        group_data = _data_to_json(group_data)
        group = self.get_group(group_key)
        self._check_fields(group_data)
        group.update(group_data)
        return group

    def delete_group(self, group_key):
        group = self.get_group(group_key)
        self.groups_data.pop(group_key)
        return group

    def get_all(self, query):
        stream = query.get('stream', None)
        stream = stream and stream[0]
        q = query.get('query', None)
        q = q and q[0]
        if stream == 'true':
            return self.get_all_groups(q)
        else:
            cursor = query.get('cursor', None)
            cursor = cursor and cursor[0]
            max_results = query.get('max_results', None)
            max_results = max_results and max_results[0]
            return self.get_page_groups(q, cursor, max_results)

    def request(self, request, contact_key, query, contact_store):
        self.fake_contacts = contact_store
        if request.method == "POST":
            if contact_key is None or contact_key is "":
                return self.create_group(request.body)
            else:
                raise FakeContactsError(405, "Method Not Allowed")
        elif request.method == "GET":
            if contact_key is None or contact_key == "":
                return self.get_all(query)
            elif contact_key.endswith('contacts'):
                key = contact_key[:contact_key.find('/')]
                return self.get_contacts_for_group(key, query)
            else:
                return self.get_group(contact_key)
        elif request.method == "PUT":
            # NOTE: This is an incorrect use of the PUT method, but
            # it's what we have for now.
            return self.update_group(contact_key, request.body)
        elif request.method == "DELETE":
            return self.delete_group(contact_key)
        else:
            raise FakeContactsError(405, "Method Not Allowed")


class FakeContactsApi(object):
    """
    Fake implementation of the Vumi Go contacts API.
    """
    def __init__(self, url_path_prefix, auth_token, contacts_data={},
                 groups_data={}, group_limit=10, contacts_limit=10):
        self.url_path_prefix = url_path_prefix
        self.auth_token = auth_token
        self.contacts = FakeContacts(contacts_data, contacts_limit)
        self.groups = FakeGroups(groups_data, group_limit)

    make_contact_dict = staticmethod(FakeContacts.make_contact_dict)
    make_group_dict = staticmethod(FakeGroups.make_group_dict)

    # The methods below are part of the external API.

    def handle_request(self, request):
        if not self.check_auth(request):
            return self.build_response("", 403)

        url = urlparse(request.path)
        request.path = url.path
        request_type = request.path.replace(
            self.url_path_prefix, '').lstrip('/')
        request_type = request_type[:request_type.find('/')]
        prefix = "/".join([self.url_path_prefix.rstrip("/"), request_type])
        contact_key = request.path.replace(prefix, "").lstrip("/")

        handler = {
            'contacts': self.contacts,
            'groups': self.groups,
        }.get(request_type, None)

        if handler is None:
            self.build_response("", 404)

        try:
            query_string = parse_qs(urllib.unquote(url.query).decode('utf8'))
            return self.build_response(
                handler.request(
                    request, contact_key, query_string, self.contacts))
        except FakeContactsError as err:
            return self.build_response(err.data, err.code)

    def check_auth(self, request):
        auth_header = request.headers.get("Authorization")
        return auth_header == "Bearer %s" % (self.auth_token,)

    def build_response(self, content, code=200, headers=None):
        return Response(code, headers, content)
