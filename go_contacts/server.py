"""
Cyclone application for Vumi Go contacts API.
"""

from vumi.persist.txriak_manager import TxRiakManager

from go_api.cyclone.handlers import ApiApplication
from go_contacts.backends.riak import RiakContactsBackend


class ContactsApi(ApiApplication):
    """
    :param IContactsBackend backend:
        A backend that provides a contact collection factory.
    """

    config_required = True

    def initialize(self, settings, config):
        self.backend = self._setup_backend(config)

    def _setup_backend(self, config):
        if "riak_manager" not in config:
            raise ValueError(
                "Config file must contain a riak_manager entry.")
        riak_manager = TxRiakManager.from_config(config['riak_manager'])
        backend = RiakContactsBackend(riak_manager)
        return backend

    @property
    def collections(self):
        return (
            ('/contacts', self.backend.get_contact_collection),
        )
