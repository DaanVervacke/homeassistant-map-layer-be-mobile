"""Config flow for the Be-Mobile map-layer provider."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries

from .const import DOMAIN


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """No-input config flow for the Be-Mobile provider."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create the single Be-Mobile provider config entry."""

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="Map Layer Be-Mobile", data={})
