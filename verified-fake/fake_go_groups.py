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


class FakeGroupsError(Exception):
    """
    Error we can use to craft a different HTTP response.
    """

    def __init__(self, code, reason):
        super(FakeGroupsError, self).__init__()
        self.code = code
        self.reason = reason
        self.data = {
            u"status_code": code,
            u"reason": reason,
        }


class FakeGroupsApi(object):
    """
    Fake implementation of the Vumi Go groups API.
    """

    def __init__(self, url_path_prefix, auth_token, group_data):
        self.url_path_prefix = url_path_prefix
        self.auth_token = auth_token
        self.groups_data = group_data

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
            raise FakeGroupsError(
                400, "Invalid group fields: %s" % ", ".join(
                    sorted(bad_fields)))

    def _data_to_json(self, group_data):
        if not isinstance(group_data, basestring):
            # If we don't already have JSON, we want to make some to guarantee
            # encoding succeeds.
            group_data = json.dumps(group_data)
        return json.loads(group_data)

    def create_group(self, group_data):
        group_data = self._data_to_json(group_data)
        self._check_fields(group_data)
        group = self.make_group_dict(group_data)
        self.groups_data[group[u"key"]] = group
        return group

    def get_group(self, group_key):
        group = self.groups_data.get(group_key)
        if group is None:
            raise FakeGroupsError(
                404, u"Group %r not found." % (group_key,))
        return group

    def update_group(self, group_key, group_data):
        group_data = self._data_to_json(group_data)
        group = self.get_group(group_key)
        self._check_fields(group_data)
        group.update(group_data)
        return group

    def delete_group(self, group_key):
        group = self.get_group(group_key)
        self.groups_data.pop(group_key)
        return group

    # The methods below are part of the external API.

    def handle_request(self, request):
        if not self.check_auth(request):
            return self.build_response("", 403)

        prefix = "/".join([self.url_path_prefix.rstrip("/"), "groups"])
        group_key = request.path.replace(prefix, "").lstrip("/")

        try:
            if request.method == "POST":
                if group_key is None or group_key is "":
                    return self.handle_create_group(request)
                else:
                    raise FakeGroupsError(405, "Method Not Allowed")
            elif request.method == "GET":
                return self.handle_get_group(group_key, request)
            elif request.method == "PUT":
                # NOTE: This is an incorrect use of the PUT method, but it's
                # what we have for now.
                return self.handle_update_group(group_key, request)
            elif request.method == "DELETE":
                return self.handle_delete_group(group_key, request)
            else:
                raise FakeGroupsError(405, "Method Not Allowed")

        except FakeGroupsError as err:
            return self.build_response(err.data, err.code)

    def check_auth(self, request):
        auth_header = request.headers.get("Authorization")
        return auth_header == "Bearer %s" % (self.auth_token,)

    def build_response(self, content, code=200, headers=None):
        return Response(code, headers, content)

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
