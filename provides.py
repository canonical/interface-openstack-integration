"""
This is the provides side of the interface layer, for use only by the
OpenStack integration charm itself.

The flags that are set by the provides side of this interface are:

* **`endpoint.{endpoint_name}.requested`** This flag is set when there is
  a new or updated request by a remote unit for OpenStack integration
  features.  The OpenStack integration charm should then iterate over each
  request, perform whatever actions are necessary to satisfy those requests,
  and then mark them as complete.
"""

from operator import attrgetter
from typing import Dict

from charms.reactive import Endpoint
from charms.reactive import when
from charms.reactive import toggle_flag, clear_flag


class OpenStackIntegrationProvides(Endpoint):
    """
    Example usage:

    ```python
    from charms.reactive import when, endpoint_from_flag
    from charms import layer

    @when('endpoint.openstack.requests-pending')
    def handle_requests():
        openstack = endpoint_from_flag('endpoint.openstack.requests-pending')
        for request in openstack.requests:
            request.set_credentials(layer.openstack.get_user_credentials())
        openstack.mark_completed()
    ```
    """

    @when('endpoint.{endpoint_name}.changed')
    def check_requests(self):
        toggle_flag(self.expand_name('requests-pending'),
                    len(self.all_requests) > 0)
        clear_flag(self.expand_name('changed'))

    @property
    def all_requests(self):
        """
        A list of all of the #IntegrationRequests that have been made.
        """
        if not hasattr(self, '_all_requests'):
            self._all_requests = [IntegrationRequest(unit)
                                  for unit in self.all_joined_units]
        return self._all_requests

    @property
    def new_requests(self):
        """
        A list of the new or updated #IntegrationRequests that have been made.
        """
        is_changed = attrgetter('is_changed')
        return list(filter(is_changed, self.all_requests))

    def mark_completed(self):
        """
        Mark all requests as completed and remove the `requests-pending` flag.
        """
        clear_flag(self.expand_name('requests-pending'))


class IntegrationRequest:
    """
    A request for integration from a single remote unit.
    """
    def __init__(self, unit):
        self._unit = unit

    @property
    def _to_publish(self):
        return self._unit.relation.to_publish

    @property
    def is_changed(self):
        """
        Whether this request has changed since the last time it was
        marked completed (if ever).
        """
        return not self.has_credentials

    @property
    def unit_name(self):
        return self._unit.unit_name

    def set_credentials(self,
                        auth_url,
                        region,
                        username,
                        password,
                        user_domain_name,
                        project_domain_name,
                        project_name,
                        endpoint_tls_ca,
                        *_,
                        domain_id=None,
                        domain_name=None,
                        project_id=None,
                        project_domain_id=None,
                        user_domain_id=None,
                        version=None,
            ):
        """
        Set the credentials for this request.
        """
        self._to_publish.update({
            'auth_url': auth_url,
            'region': region,
            'username': username,
            'password': password,
            'domain_id': domain_id,
            'domain_name': domain_name,
            'endpoint_tls_ca': endpoint_tls_ca,
            'project_domain_name': project_domain_name,
            'project_domain_id': project_domain_id,
            'project_id': project_id,
            'project_name': project_name,
            'user_domain_id': user_domain_id,
            'user_domain_name': user_domain_name,
            'version': version,
        })

    def set_lbaas_config(self,
                         subnet_id,
                         floating_network_id,
                         lb_method,
                         manage_security_groups,
                         has_octavia=None,
                         lb_enabled=None,
                         internal_lb=False):
        """
        Set the load-balancer-as-a-service config for this request.
        """
        self._to_publish.update({
            'subnet_id': subnet_id,
            'floating_network_id': floating_network_id,
            'lb_method': lb_method,
            'internal_lb': internal_lb,
            'manage_security_groups': manage_security_groups,
            'has_octavia': has_octavia,
            'lb_enabled': lb_enabled,
        })

    def set_block_storage_config(self,
                                 bs_version,
                                 trust_device_path,
                                 ignore_volume_az):
        """
        Set the block storage config for this request.
        """
        self._to_publish.update({
            'bs_version': bs_version,
            'trust_device_path': trust_device_path,
            'ignore_volume_az': ignore_volume_az,
        })

    @property
    def proxy_config(self) -> Dict[str, str]:
        """
        Get the proxy config answered on this request.

        if `proxy_config` is not set, return an empty dict.
        """
        data = self._to_publish.get('proxy_config')
        if not data or not isinstance(data, dict):
            return {}
        return {k: (v or "") for k, v  in data.items()}

    def set_proxy_config(self, proxy_config: Dict[str, str]):
        """
        Set the proxy config for this request.
        """
        self._to_publish.update({
            'proxy_config': proxy_config,
        })

    @property
    def has_credentials(self):
        """
        Whether or not credentials have been set via `set_credentials`.
        """
        return 'credentials' in self._to_publish
