"""Config-flow and setup tests using Home Assistant."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

try:
    from custom_components.map_layer_be_mobile import async_setup_entry
    from custom_components.map_layer_be_mobile.config_flow import ConfigFlow
except ModuleNotFoundError as exc:
    if exc.name not in {"homeassistant", "custom_components.map_layer"}:
        raise
    raise unittest.SkipTest(
        "Install Home Assistant and the map_layer repo to run config-flow tests"
    ) from exc


class ConfigFlowTest(unittest.IsolatedAsyncioTestCase):
    """Exercise the real flow methods without making external tile requests."""

    async def asyncSetUp(self) -> None:
        self.flow = ConfigFlow()
        self.flow.hass = MagicMock()

    async def test_user_creates_entry_without_input(self) -> None:
        with (
            patch.object(self.flow, "_async_current_entries", return_value=[]),
            patch.object(self.flow, "async_create_entry", return_value={}) as create,
        ):
            await self.flow.async_step_user(None)
        create.assert_called_once_with(title="Map Layer Be-Mobile", data={})

    async def test_duplicate_setup_aborts(self) -> None:
        with patch.object(self.flow, "_async_current_entries", return_value=[object()]):
            result = await self.flow.async_step_user(None)
        self.assertEqual(result["reason"], "single_instance_allowed")


class SetupEntryTest(unittest.IsolatedAsyncioTestCase):
    """Provider registration during setup."""

    async def test_setup_registers_provider_and_unload_hook(self) -> None:
        entry = MagicMock()
        session = MagicMock()
        registry = MagicMock()
        with (
            patch(
                "homeassistant.helpers.aiohttp_client.async_get_clientsession",
                return_value=session,
            ),
            patch(
                "custom_components.map_layer.async_get_registry", return_value=registry
            ),
            patch(
                "custom_components.map_layer_be_mobile.BeMobileProvider"
            ) as provider,
        ):
            self.assertTrue(await async_setup_entry(MagicMock(), entry))
        provider.assert_called_once_with(session)
        registry.async_register_provider.assert_called_once_with(provider.return_value)
        entry.async_on_unload.assert_called_once_with(
            registry.async_register_provider.return_value
        )


if __name__ == "__main__":
    unittest.main()
