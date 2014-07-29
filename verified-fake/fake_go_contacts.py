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


class FakeContactsApi(object):
    """
    Fake implementation of the Vumi Go contacts API.
    """

    def __init__(self, url_path_prefix, auth_token, contacts_data):
        self.url_path_prefix = url_path_prefix
        self.auth_token = auth_token
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
        }
        contact.update(fields)
        return contact

    def handle_request(self, request):
        if not self.check_auth(request):
            return self.build_response("", 403)

        # TODO: Improve this as our server implementation grows.

        prefix = "/".join([self.url_path_prefix.rstrip("/"), "contacts"])
        contact_key = request.path.replace(prefix, "").lstrip("/")

        try:
            if not contact_key:
                if request.method == "POST":
                    return self.create_contact(request)
                else:
                    return self.build_response("", 405)

            if request.method == "GET":
                return self.get_contact(contact_key, request)
            elif request.method == "PUT":
                # NOTE: This is an incorrect use of the PUT method, but it's
                # what we have for now.
                return self.update_contact(contact_key, request)
            elif request.method == "DELETE":
                return self.delete_contact(contact_key, request)
            else:
                return self.build_response("", 405)

        except FakeContactsError as err:
            return self.build_response(err.data, err.code)

    def check_auth(self, request):
        auth_header = request.headers.get("Authorization")
        return auth_header == "Bearer %s" % (self.auth_token,)

    def build_response(self, content, code=200, headers=None):
        return Response(code, headers, content)

    def _get_contact(self, contact_key):
        contact = self.contacts_data.get(contact_key)
        if contact is None:
            raise FakeContactsError(
                404, u"Contact %r not found." % (contact_key,))
        return contact

    def create_contact(self, request):
        # TODO: Confirm this behaviour against the real API.
        contact_data = json.loads(request.body)
        if u"key" in contact_data:
            raise FakeContactsError(400, "")
        contact = self.make_contact_dict(contact_data)
        self.contacts_data[contact[u"key"]] = contact
        return self.build_response(contact)

    def get_contact(self, contact_key, request):
        # TODO: Confirm this behaviour against the real API.
        contact = self._get_contact(contact_key)
        return self.build_response(contact)

    def update_contact(self, contact_key, request):
        # TODO: Confirm this behaviour against the real API.
        contact = self._get_contact(contact_key)
        update_data = json.loads(request.body)
        for k, v in update_data.iteritems():
            # TODO: Reject changes to key?
            contact[k] = v
        return self.build_response(contact)

    def delete_contact(self, contact_key, request):
        # TODO: Confirm this behaviour against the real API.
        contact = self._get_contact(contact_key)
        self.contacts_data.pop(contact_key)
        return self.build_response(contact)