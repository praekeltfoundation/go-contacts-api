"""
Cyclone application for Vumi Go contacts API.
"""

from vumi.persist.txriak_manager import TxRiakManager

from go_api.cyclone.handlers import ApiApplication
from go_contacts.backends.riak import RiakContactsBackend
from go_contacts.backends.riak import RiakGroupsBackend

from confmodel import Config
from confmodel.fields import ConfigInt, ConfigDict


class ContactsApiConfig(Config):
    """
    This is the configuration for the Contacts API.
    """
    max_groups_per_page = ConfigInt(
        "Maximum number of groups returned per page", required=True)
    max_contacts_per_page = ConfigInt(
        "Maximum number of contacts returned per page", required=True)
    riak_manager = ConfigDict(
        "The configuration parameters for the Riak Manager", required=True)


class ContactsApi(ApiApplication):
    """
    :param IContactsBackend backend:
        A backend that provides a contact collection factory.
    """

    config_required = True

    def initialize(self, settings, config):
        config = ContactsApiConfig(config)
        self.contact_backend = self._setup_contacts_backend(config)
        self.group_backend = self._setup_groups_backend(config)

    def _get_riak_manager(self, config):
        try:
            return self.riak_manager
        except AttributeError:
            self.riak_manager = TxRiakManager.from_config(config.riak_manager)
            return self.riak_manager

    def _setup_contacts_backend(self, config):
        riak_manager = self._get_riak_manager(config)
        backend = RiakContactsBackend(
            riak_manager, config.max_contacts_per_page)
        return backend

    def _setup_groups_backend(self, config):
        riak_manager = self._get_riak_manager(config)
        backend = RiakGroupsBackend(riak_manager, config.max_groups_per_page)
        return backend

    @property
    def collections(self):
        return (
            ('/contacts', self.contact_backend.get_contact_collection),
            ('/groups', self.group_backend.get_group_collection),
        )
