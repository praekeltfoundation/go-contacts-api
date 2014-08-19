import json
from uuid import uuid4

from fake_errors import FakeContactsError

class FakeGroups(object):
    """
    Fake implementation of the Groups part of the Contacts API
    """
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

    def _data_to_json(self, data):
        if not isinstance(data, basestring):
            # If we don't already have JSON, we want to make some to guarantee
            # encoding succeeds.
            data = json.dumps(data)
        return json.loads(data)

    def _check_group_fields(self, group_data):
        allowed_fields = set(self.make_group_dict({}).keys())
        allowed_fields.discard(u"key")

        bad_fields = set(group_data.keys()) - allowed_fields
        if bad_fields:
            raise FakeContactsError(
                400, "Invalid group fields: %s" % ", ".join(
                    sorted(bad_fields)))

    def create_group(self, group_data):
        group_data = self._data_to_json(group_data)
        self._check_group_fields(group_data)
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
        group_data = self._data_to_json(group_data)
        group = self.get_group(group_key)
        self._check_group_fields(group_data)
        group.update(group_data)
        return group

    def delete_group(self, group_key):
        group = self.get_group(group_key)
        self.groups_data.pop(group_key)
        return group
