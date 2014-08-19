import json
from uuid import uuid4

from fake_go_contacts_contacts import FakeContacts
from fake_go_contacts_groups import FakeGroups
from fake_errors import FakeContactsError


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


class FakeContactsApi(FakeContacts, FakeGroups):
    """
    Fake implementation of the Vumi Go contacts API.
    """

    def __init__(self, url_path_prefix, auth_token, contacts_data={},
                 groups_data={}):
        self.url_path_prefix = url_path_prefix
        self.auth_token = auth_token
        self.contacts_data = contacts_data
        self.groups_data = groups_data

    # The methods below are part of the external API.

    def handle_request(self, request):
        if not self.check_auth(request):
            return self.build_response("", 403)

        request_type = request.path.replace(
            self.url_path_prefix, '').lstrip('/')
        request_type = request_type[:request_type.find('/')]
        prefix = "/".join([self.url_path_prefix.rstrip("/"), request_type])
        contact_key = request.path.replace(prefix, "").lstrip("/")

        if request_type == 'contacts':
            try:
                if not contact_key:
                    if request.method == "POST":
                        return self.handle_create_contact(request)
                    else:
                        return self.build_response("", 405)

                if request.method == "GET":
                    return self.handle_get_contact(contact_key, request)
                elif request.method == "PUT":
                    # NOTE: This is an incorrect use of the PUT method, but
                    # it's what we have for now.
                    return self.handle_update_contact(contact_key, request)
                elif request.method == "DELETE":
                    return self.handle_delete_contact(contact_key, request)
                else:
                    return self.build_response("", 405)

            except FakeContactsError as err:
                return self.build_response(err.data, err.code)

        elif request_type == 'groups':
            try:
                if request.method == "POST":
                    if contact_key is None or contact_key is "":
                        return self.handle_create_group(request)
                    else:
                        raise FakeContactsError(405, "Method Not Allowed")
                elif request.method == "GET":
                    return self.handle_get_group(contact_key, request)
                elif request.method == "PUT":
                    # NOTE: This is an incorrect use of the PUT method, but
                    # it's what we have for now.
                    return self.handle_update_group(contact_key, request)
                elif request.method == "DELETE":
                    return self.handle_delete_group(contact_key, request)
                else:
                    raise FakeContactsError(405, "Method Not Allowed")

            except FakeContactsError as err:
                return self.build_response(err.data, err.code)

    def check_auth(self, request):
        auth_header = request.headers.get("Authorization")
        return auth_header == "Bearer %s" % (self.auth_token,)

    def build_response(self, content, code=200, headers=None):
        return Response(code, headers, content)

    def handle_create_contact(self, request):
        contact = self.create_contact(request.body)
        return self.build_response(contact)

    def handle_get_contact(self, contact_key, request):
        contact = self.get_contact(contact_key)
        return self.build_response(contact)

    def handle_update_contact(self, contact_key, request):
        contact = self.update_contact(contact_key, request.body)
        return self.build_response(contact)

    def handle_delete_contact(self, contact_key, request):
        contact = self.delete_contact(contact_key)
        return self.build_response(contact)

    def handle_create_group(self, request):
        group = self.create_group(request.body)
        return self.build_response(group)

    def handle_get_group(self, group_key, request):
        group = self.get_group(group_key)
        return self.build_response(group)

    def handle_update_group(self, group_key, request):
        group = self.update_group(group_key, request.body)
        return self.build_response(group)

    def handle_delete_group(self, group_key, request):
        group = self.delete_group(group_key)
        return self.build_response(group)
