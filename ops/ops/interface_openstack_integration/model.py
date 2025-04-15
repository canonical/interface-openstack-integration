# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""pydantic model of the databag read by the requires side."""

import base64
import binascii
import configparser
import contextlib
import io
from typing import Dict, Optional

from pydantic import BaseModel, Json, SecretStr, validator


class Data(BaseModel):
    """Databag for information shared over the relation."""

    # Required config
    auth_url: Json[str]
    password: Json[SecretStr]
    project_domain_name: Json[str]
    project_name: Json[str]
    region: Json[str]
    username: Json[str]
    user_domain_name: Json[str]

    # Optional config
    bs_version: Json[Optional[str]]
    domain_id: Json[Optional[str]] = None
    domain_name: Json[Optional[str]] = None
    endpoint_tls_ca: Json[Optional[str]]
    floating_network_id: Json[Optional[str]]
    has_octavia: Json[Optional[bool]]
    ignore_volume_az: Json[Optional[bool]]
    internal_lb: Json[Optional[bool]]
    lb_enabled: Json[Optional[bool]]
    lb_method: Json[Optional[str]]
    project_id: Json[Optional[str]] = None
    project_domain_id: Json[Optional[str]] = None
    proxy_config: Json[Optional[Dict[str, str]]] = None
    manage_security_groups: Json[Optional[bool]]
    subnet_id: Json[Optional[str]]
    trust_device_path: Json[Optional[bool]]
    user_domain_id: Json[Optional[str]] = None
    version: Json[Optional[int]] = None

    @validator("endpoint_tls_ca")
    def must_be_b64_cert(cls, s: Json[str]):
        """Validate endpoint_tls_ca is base64 encoded str."""
        try:
            base64.b64decode(s, validate=True)
        except binascii.Error:
            raise ValueError("Couldn't find base64 data")
        return s

    @property
    def cloud_config(self) -> str:  # noqa: C901
        """Render as an openstack cloud config ini.

        https://github.com/kubernetes/cloud-provider-openstack/blob/75b1fbb91a2566a869b8922ad62e1c03ab5e6eac/docs/openstack-cloud-controller-manager/using-openstack-cloud-controller-manager.md#global

        """
        _global, _loadbalancer, _blockstorage = {}, {}, {}
        if self.auth_url:
            _global["auth-url"] = self.auth_url
        if self.endpoint_tls_ca:
            _global["ca-file"] = "/etc/config/endpoint-ca.cert"
        if self.username:
            _global["username"] = self.username
        if self.password:
            _global["password"] = self.password.get_secret_value()
        if self.region:
            _global["region"] = self.region
        if self.domain_id:
            _global["domain-id"] = self.domain_id
        if self.domain_name:
            _global["domain-name"] = self.domain_name
        if self.project_id:
            _global["tenant-id"] = self.project_id
        if self.project_name:
            _global["tenant-name"] = self.project_name
        if self.project_domain_id:
            _global["tenant-domain-id"] = self.project_domain_id
        if self.project_domain_name:
            _global["tenant-domain-name"] = self.project_domain_name
        if self.user_domain_id:
            _global["user-domain-id"] = self.user_domain_id
        if self.user_domain_name:
            _global["user-domain-name"] = self.user_domain_name

        if not self.lb_enabled:
            _loadbalancer["enabled"] = "false"
        if self.has_octavia in (True, None):
            # Newer integrator charm will detect whether underlying OpenStack has
            # Octavia enabled so we can set this intelligently. If we're still
            # related to an older integrator, though, default to assuming Octavia
            # is available.
            _loadbalancer["use-octavia"] = "true"
        else:
            _loadbalancer["use-octavia"] = "false"
            _loadbalancer["lb-provider"] = "haproxy"
        if _s := self.subnet_id:
            _loadbalancer["subnet-id"] = _s
        if _s := self.floating_network_id:
            _loadbalancer["floating-network-id"] = _s
        if _s := self.lb_method:
            _loadbalancer["lb-method"] = _s
        if self.internal_lb:
            _loadbalancer["internal-lb"] = "true"
        if self.manage_security_groups:
            _loadbalancer["manage-security-groups"] = "true"

        if _os := self.bs_version:
            _blockstorage["bs-version"] = _os
        if self.trust_device_path:
            _blockstorage["trust-device-path"] = "true"
        if self.ignore_volume_az:
            _blockstorage["ignore-volume-az"] = "true"

        config = configparser.ConfigParser()
        config["Global"] = _global
        config["LoadBalancer"] = _loadbalancer
        config["BlockStorage"] = _blockstorage
        with contextlib.closing(io.StringIO()) as sio:
            config.write(sio)
            output_text = sio.getvalue()

        return output_text
