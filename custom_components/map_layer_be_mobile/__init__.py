"""Be-Mobile map-layer provider integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .provider import BeMobileProvider


async def async_setup(hass: Any, config: Mapping[str, Any]) -> bool:
    """Set up the Be-Mobile map-layer provider package."""

    return True


async def async_setup_entry(hass: Any, entry: Any) -> bool:
    """Register the Be-Mobile map-layer provider."""

    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from custom_components.map_layer import async_get_registry

    session = async_get_clientsession(hass)
    unregister = async_get_registry(hass).async_register_provider(
        BeMobileProvider(session)
    )
    entry.async_on_unload(unregister)
    return True


async def async_unload_entry(hass: Any, entry: Any) -> bool:
    """Unload the Be-Mobile map-layer provider config entry."""

    return True
