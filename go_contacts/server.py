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

    def __init__(self, config_file=None, **settings):
        if config_file is None:
            raise ValueError(
                "Please specify a config file using --appopts=<config.yaml>")
        self.config = self.get_config_settings(config_file)
        self.backend = self._setup_backend()
        ApiApplication.__init__(self, **settings)

    def _setup_backend(self):
        if "riak_manager" not in self.config:
            raise ValueError(
                "Config file must contain a riak_manager entry.")
        riak_manager = TxRiakManager.from_config(self.config['riak_manager'])
        backend = RiakContactsBackend(riak_manager)
        return backend

    @property
    def collections(self):
        return (
            ('/contacts', self.backend.get_contact_collection),
        )
