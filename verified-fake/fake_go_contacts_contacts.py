import json
from uuid import uuid4

from fake_errors import FakeContactsError

class FakeContacts(object):
    """
    Fake implementation of the Contacts part of the Contacts API
    """
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

    def _check_contact_fields(self, contact_data):
        allowed_fields = set(self.make_contact_dict({}).keys())
        allowed_fields.discard(u"key")

        bad_fields = set(contact_data.keys()) - allowed_fields
        if bad_fields:
            raise FakeContactsError(
                400, "Invalid contact fields: %s" % ", ".join(
                    sorted(bad_fields)))

    def _data_to_json(self, data):
        if not isinstance(data, basestring):
            # If we don't already have JSON, we want to make some to guarantee
            # encoding succeeds.
            data = json.dumps(data)
        return json.loads(data)

    def create_contact(self, contact_data):
        contact_data = self._data_to_json(contact_data)
        self._check_contact_fields(contact_data)

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
        contact_data = self._data_to_json(contact_data)
        self._check_contact_fields(contact_data)
        for k, v in contact_data.iteritems():
            contact[k] = v
        return contact

    def delete_contact(self, contact_key):
        contact = self.get_contact(contact_key)
        self.contacts_data.pop(contact_key)
        return contact
