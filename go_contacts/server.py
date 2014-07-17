"""
Cyclone application for Vumi Go contacts API.
"""

from go_api.cyclone.handlers import ApiApplication
from go_contacts.backends.riak import RiakContactsBackend


class ContactsApi(ApiApplication):
    """
    :param IContactsBackend backend:
        A backend that provides a contact collection factory.
    """

    def __init__(self, config_file=None, **settings):
        config_dict = self.get_config_settings(config_file)
        self.backend = RiakContactsBackend(config_dict.pop('riak_config'))
        ApiApplication.__init__(self, **settings)

    @property
    def collections(self):
        return (
            ('/', self.backend.get_contact_collection),
        )
