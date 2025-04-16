# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
"""Implementation of openstack integrator interface.

This only implements the requires side, currently, since the providers
is still using the Reactive Charm framework self.
"""
import base64
import logging
from typing import Dict, Optional

from backports.cached_property import cached_property
from ops.charm import CharmBase, RelationBrokenEvent
from ops.framework import Object
from ops.model import Relation
from pydantic import ValidationError

from .model import Data

log = logging.getLogger(__name__)


class OpenstackIntegrationRequirer(Object):
    """Requires side of openstack relation."""

    def __init__(
        self, charm: CharmBase, endpoint: str = "openstack", relation_id: Optional[int] = None
    ):
        super().__init__(charm, f"relation-{endpoint}")
        self.endpoint = endpoint
        self.relation_id = relation_id
        events = charm.on[endpoint]
        self._unit_name = self.model.unit.name.replace("/", "_")
        self.framework.observe(events.relation_joined, self._joined)

    def _joined(self, event):
        to_publish = self.relation.data[self.model.unit]
        to_publish["charm"] = self.model.app.name

    @cached_property
    def relation(self) -> Optional[Relation]:
        """The relation to the integrator, or None."""
        return self.model.get_relation(self.endpoint, relation_id=self.relation_id)

    @cached_property
    def _raw_data(self):
        if self.relation and self.relation.units:
            return self.relation.data[list(self.relation.units)[0]]
        return None

    @cached_property
    def _data(self) -> Optional[Data]:
        raw = self._raw_data
        return Data(**raw) if raw else None

    def evaluate_relation(self, event) -> Optional[str]:
        """Determine if relation is ready."""
        no_relation = not self.relation or (
            isinstance(event, RelationBrokenEvent) and event.relation is self.relation
        )
        if not self.is_ready:
            if no_relation:
                return f"Missing required {self.endpoint}"
            return f"Waiting for {self.endpoint}"
        return None

    @property
    def is_ready(self):
        """Whether the request for this instance has been completed."""
        try:
            self._data
        except ValidationError as ve:
            log.error(f"{self.endpoint} relation data not yet valid. ({ve}")
            return False
        if self._data is None:
            log.error(f"{self.endpoint} relation data not yet available.")
            return False
        return all(
            field is not None
            for field in [
                self._data.auth_url,
                self._data.username,
                self._data.password,
                self._data.user_domain_name,
                self._data.project_domain_name,
                self._data.project_name,
            ]
        )

    @property
    def cloud_conf(self) -> Optional[str]:
        """Return cloud.conf from integrator relation."""
        if self.is_ready and (data := self._data):
            return data.cloud_config
        return None

    @property
    def cloud_conf_b64(self) -> Optional[bytes]:
        """Return cloud.conf from integrator relation as base64-encoded bytes."""
        if self.is_ready and (data := self.cloud_conf):
            return base64.b64encode(data.encode())
        return None

    @property
    def endpoint_tls_ca(self) -> Optional[bytes]:
        """Return cloud.conf from integrator relation."""
        if self.is_ready and (data := self._data):
            if data.endpoint_tls_ca:
                return data.endpoint_tls_ca.encode()
        return None

    @property
    def proxy_config(self) -> Dict[str, str]:
        """Return proxy_config from integrator relation."""
        config = None
        if self.is_ready and (data := self._data):
            config = data.proxy_config
        return config or {}
