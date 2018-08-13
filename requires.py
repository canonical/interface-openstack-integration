"""
This is the requires side of the interface layer, for use in charms that wish
to request integration with OpenStack native features.  The integration will be
provided by the OpenStack integration charm, which allows the requiring charm
to not require cloud credentials itself and not have a lot of OpenStack
specific API code.

The flags that are set by the requires side of this interface are:

* **`endpoint.{endpoint_name}.joined`** This flag is set when the relation
  has been joined, and the charm should then use the methods documented below
  to request specific OpenStack features.  This flag is automatically removed
  if the relation is broken.  It should not be removed by the charm.

* **`endpoint.{endpoint_name}.ready`** This flag is set once the requested
  features have been enabled for the OpenStack instance on which the charm is
  running.  This flag is automatically removed if new integration features are
  requested.  It should not be removed by the charm.
"""


from charms.reactive import Endpoint
from charms.reactive import when, when_not
from charms.reactive import clear_flag, toggle_flag


class OpenStackIntegrationRequires(Endpoint):
    """
    Interface to request integration access.

    Note that due to resource limits and permissions granularity, policies are
    limited to being applied at the charm level.  That means that, if any
    permissions are requested (i.e., any of the enable methods are called),
    what is granted will be the sum of those ever requested by any instance of
    the charm on this cloud.

    Labels, on the other hand, will be instance specific.

    Example usage:

    ```python
    from charms.reactive import when, endpoint_from_flag

    @when('endpoint.openstack.ready')
    def openstack_integration_ready():
        openstack = endpoint_from_flag('endpoint.openstack.joined')
        credentials = openstack.get_credentials()
        update_config_enable_openstack(credentials)
    ```
    """

    @property
    def _received(self):
        """
        Helper to streamline access to received data since we expect to only
        ever be connected to a single OpenStack integration application with a
        single unit.
        """
        return self.relations[0].joined_units.received

    @property
    def _to_publish(self):
        """
        Helper to streamline access to received data since we expect to only
        ever be connected to a single OpenStack integration application with a
        single unit.
        """
        return self.relations[0].to_publish

    @when('endpoint.{endpoint_name}.changed')
    def check_ready(self):
        # My middle name is ready. No, that doesn't sound right.
        # I eat ready for breakfast.
        toggle_flag(self.expand_name('ready'), self.is_ready)
        clear_flag(self.expand_name('changed'))

    @when_not('endpoint.{endpoint_name}.joined')
    def remove_ready(self):
        clear_flag(self.expand_name('ready'))

    @property
    def is_ready(self):
        """
        Whether or not the request for this instance has been completed.
        """
        return bool(self._received)

    @property
    def auth_url(self):
        return self._received['auth_url']

    @property
    def username(self):
        return self._received['username']

    @property
    def password(self):
        return self._received['password']

    @property
    def user_domain_name(self):
        return self._received['user_domain_name']

    @property
    def project_domain_name(self):
        return self._received['project_domain_name']

    @property
    def project_name(self):
        return self._received['project_name']
