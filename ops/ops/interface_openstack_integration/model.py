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
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, Json, SecretStr, validator


class LBClassOptions(BaseModel):
    """Options for LoadBalancerClass section in cloud config."""

    floating_network_id: Optional[str] = Field(
        None,
        alias="floating-network-id",
        description="floating-network-id. The same with floating-network-id option above.",
    )
    floating_subnet_id: Optional[str] = Field(
        None,
        alias="floating-subnet-id",
        description="floating-subnet-id. The same with floating-subnet-id option above.",
    )
    floating_subnet: Optional[str] = Field(
        None,
        alias="floating-subnet",
        description="floating-subnet. The same with floating-subnet option above.",
    )
    floating_subnet_tags: Optional[str] = Field(
        None,
        alias="floating-subnet-tags",
        description="floating-subnet-tags. The same with floating-subnet-tags option above.",
    )
    network_id: Optional[str] = Field(
        None, alias="network-id", description="network-id. The same with network-id option above."
    )
    subnet_id: Optional[str] = Field(
        None, alias="subnet-id", description="subnet-id. The same with subnet-id option above."
    )
    member_subnet_id: Optional[str] = Field(
        None,
        alias="member-subnet-id",
        description="member-subnet-id. The same with member-subnet-id option above.",
    )


class Data(BaseModel):
    """Databag for information shared over the relation."""

    # Global Config
    auth_url: Json[str]
    endpoint_tls_ca: Json[Optional[str]]
    username: Json[str]
    password: Json[SecretStr]
    region: Json[str]
    domain_id: Json[Optional[str]] = None
    domain_name: Json[Optional[str]] = None
    project_id: Json[Optional[str]] = None
    project_name: Json[str]
    project_domain_id: Json[Optional[str]] = None
    project_domain_name: Json[str]
    user_domain_id: Json[Optional[str]]
    user_domain_name: Json[str]

    # LoadBalancer config
    has_octavia: Json[Optional[bool]]
    lb_enabled: Json[Optional[bool]]
    floating_network_id: Json[Optional[str]]
    floating_subnet_id: Json[Optional[str]] = None
    floating_subnet: Json[Optional[str]] = None
    floating_subnet_tags: Json[Optional[str]] = None
    lb_provider: Json[Optional[str]] = None
    lb_method: Json[Optional[str]] = None
    subnet_id: Json[Optional[str]] = None
    member_subnet_id: Json[Optional[str]] = None
    network_id: Json[Optional[str]] = None
    manage_security_groups: Json[Optional[bool]] = None
    create_monitor: Json[Optional[bool]] = None
    monitor_delay: Json[Optional[int]] = None
    monitor_max_retries: Json[Optional[int]] = None
    monitor_max_retries_down: Json[Optional[int]] = None
    monitor_timeout: Json[Optional[int]] = None
    internal_lb: Json[Optional[bool]] = None
    node_selector: Json[Optional[str]] = None
    cascade_delete: Json[bool] = Field(default=True)
    flavor_id: Json[Optional[str]] = None
    availability_zone: Json[Optional[str]] = None
    lb_classes: Json[Dict[str, "LBClassOptions"]] = Field(default_factory=dict)
    enable_ingress_hostname: Json[Optional[bool]] = None
    ingress_hostname_suffix: Json[Optional[str]] = None
    default_tls_container_ref: Json[Optional[str]] = None
    container_store: Json[Optional[str]] = None
    max_shared_lb: Json[Optional[int]] = None
    provider_requires_serial_api_calls: Json[Optional[bool]] = None

    bs_version: Json[Optional[str]]
    trust_device_path: Json[Optional[bool]] = None
    ignore_volume_az: Json[Optional[bool]] = None

    proxy_config: Json[Optional[Dict[str, str]]] = None
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

        https://github.com/kubernetes/cloud-provider-openstack/blob/0973c523d13210ca7499ee30ba2b564808b48d54/docs/openstack-cloud-controller-manager/using-openstack-cloud-controller-manager.md#global

        https://github.com/kubernetes/cloud-provider-openstack/blob/0973c523d13210ca7499ee30ba2b564808b48d54/docs/openstack-cloud-controller-manager/using-openstack-cloud-controller-manager.md#load-balancer

        """
        _global, _loadbalancer, _blockstorage = {}, {}, {}
        _s: Any
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
        if _s := self.floating_network_id:
            _loadbalancer["floating-network-id"] = _s
        if _s := self.floating_subnet_id:
            _loadbalancer["floating-subnet-id"] = _s
        if _s := self.floating_subnet:
            _loadbalancer["floating-subnet"] = _s
        if _s := self.floating_subnet_tags:
            _loadbalancer["floating-subnet-tags"] = _s

        octavia_available = self.has_octavia in (True, None)
        _loadbalancer["use-octavia"] = "true" if octavia_available else "false"

        if _s := self.lb_provider:
            _loadbalancer["lb-provider"] = _s
        else:
            default_provider = "amphora" if octavia_available else "haproxy"
            _loadbalancer["lb-provider"] = default_provider

        if _loadbalancer["lb-provider"] == "ovn":
            _loadbalancer["lb-method"] = "SOURCE_IP_PORT"
        elif _s := self.lb_method:
            _loadbalancer["lb-method"] = _s
        elif _loadbalancer["lb-provider"] in ("amphora", "octavia"):
            _loadbalancer["lb-method"] = "ROUND_ROBIN"

        if _s := self.subnet_id:
            _loadbalancer["subnet-id"] = _s
        if _s := self.member_subnet_id:
            _loadbalancer["member-subnet-id"] = _s
        if _s := self.network_id:
            _loadbalancer["network-id"] = _s
        if self.manage_security_groups:
            _loadbalancer["manage-security-groups"] = "true"

        if self.create_monitor:
            _loadbalancer["create-monitor"] = "true"
        if _s := self.monitor_delay:
            _loadbalancer["monitor-delay"] = str(_s)
        if _s := self.monitor_max_retries:
            _loadbalancer["monitor-max-retries"] = str(_s)
        if _s := self.monitor_max_retries_down:
            _loadbalancer["monitor-max-retries-down"] = str(_s)
        if _s := self.monitor_timeout:
            _loadbalancer["monitor-timeout"] = str(_s)

        if self.internal_lb:
            _loadbalancer["internal-lb"] = "true"

        if _s := self.node_selector:
            _loadbalancer["node-selector"] = _s
        if not self.cascade_delete:
            _loadbalancer["cascade-delete"] = "false"
        if _s := self.flavor_id:
            _loadbalancer["flavor-id"] = _s
        if _s := self.availability_zone:
            _loadbalancer["availability-zone"] = _s

        if self.enable_ingress_hostname:
            _loadbalancer["enable-ingress-hostname"] = "true"
        if _s := self.ingress_hostname_suffix:
            _loadbalancer["ingress-hostname-suffix"] = _s
        if octavia_available and (_s := self.default_tls_container_ref):
            _loadbalancer["default-tls-container-ref"] = _s
        if _s := self.container_store:
            _loadbalancer["container-store"] = _s
        if _s := self.max_shared_lb:
            _loadbalancer["max-shared-lb"] = str(_s)
        if self.provider_requires_serial_api_calls:
            _loadbalancer["provider-requires-serial-api-calls"] = "true"

        if _os := self.bs_version:
            _blockstorage["bs-version"] = _os
        if self.trust_device_path:
            _blockstorage["trust-device-path"] = "true"
        if self.ignore_volume_az:
            _blockstorage["ignore-volume-az"] = "true"

        config = configparser.ConfigParser()
        config["Global"] = _global
        config["LoadBalancer"] = _loadbalancer
        for lb_class, lb_class_opts in self.lb_classes.items():
            if as_dict := {k: v for k, v in lb_class_opts.dict(by_alias=True).items() if v}:
                config[f'LoadBalancerClass "{lb_class}"'] = as_dict

        config["BlockStorage"] = _blockstorage

        with contextlib.closing(io.StringIO()) as sio:
            config.write(sio)
            output_text = sio.getvalue()

        return output_text
