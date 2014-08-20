import json
from uuid import uuid4


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


class FakeContacts(object):
    """
    Fake implementation of the Contacts part of the Contacts API
    """
    def __init__(self, contacts_data={}):
        self.contacts_data = contacts_data

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

    def request(self, request, contact_key):
        if not contact_key:
            if request.method == "POST":
                return self.create_contact(request.body)
            else:
                raise FakeContactsError(405, "")
        if request.method == "GET":
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
    def __init__(self, groups_data={}):
        self.groups_data = groups_data

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

    def request(self, request, contact_key):
        if request.method == "POST":
            if contact_key is None or contact_key is "":
                return self.create_group(request.body)
            else:
                raise FakeContactsError(405, "Method Not Allowed")
        elif request.method == "GET":
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
                 groups_data={}):
        self.url_path_prefix = url_path_prefix
        self.auth_token = auth_token
        self.contacts = FakeContacts(contacts_data)
        self.groups = FakeGroups(groups_data)

    make_contact_dict = staticmethod(FakeContacts.make_contact_dict)
    make_group_dict = staticmethod(FakeGroups.make_group_dict)

    # The methods below are part of the external API.

    def handle_request(self, request):
        if not self.check_auth(request):
            return self.build_response("", 403)

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
            return self.build_response(handler.request(request, contact_key))
        except FakeContactsError as err:
            return self.build_response(err.data, err.code)

    def check_auth(self, request):
        auth_header = request.headers.get("Authorization")
        return auth_header == "Bearer %s" % (self.auth_token,)

    def build_response(self, content, code=200, headers=None):
        return Response(code, headers, content)
