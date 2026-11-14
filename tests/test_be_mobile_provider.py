"""Tests for the Be-Mobile map-layer provider."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import unittest

from custom_components.map_layer_be_mobile.provider import (
    BE_MOBILE_ATTRIBUTION,
    BE_MOBILE_BASEMAP_ATTRIBUTION,
    BE_MOBILE_BASEMAP_CACHE_SECONDS,
    BE_MOBILE_PROVIDER_ID,
    BE_MOBILE_TRAFFIC_CACHE_SECONDS,
    BeMobileProvider,
    be_mobile_layer,
    be_mobile_tile_url,
)

_MANIFEST = json.loads(
    (
        Path(__file__).parents[1]
        / "custom_components"
        / "map_layer_be_mobile"
        / "manifest.json"
    ).read_text()
)


class FakeResponse:
    """Async context manager response for provider tests."""

    def __init__(
        self,
        *,
        status: int = 200,
        body: bytes = b"tile",
        content_type: str = "image/png",
    ) -> None:
        self.status = status
        self._body = body
        self.headers = {"Content-Type": content_type}

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def read(self) -> bytes:
        return self._body


class FakeSession:
    """Fake client session that records requested URLs."""

    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.urls: list[str] = []
        self.headers: list[dict[str, str]] = []

    def get(self, url: str, **kwargs: object) -> FakeResponse:
        self.urls.append(url)
        self.headers.append(dict(kwargs.get("headers", {})))
        return self.response


class RaisingSession:
    """Fake client session whose requests raise."""

    def get(self, url: str, **kwargs: object) -> object:
        raise RuntimeError("connection failed")


class BeMobileProviderTest(unittest.TestCase):
    """Be-Mobile provider behavior."""

    def test_metadata_exposes_four_xyz_layers(self) -> None:
        provider = BeMobileProvider(FakeSession(FakeResponse()))

        layers = asyncio.run(provider.async_list_layers())

        self.assertEqual(len(layers), 4)
        by_id = {layer.layer_id: layer for layer in layers}
        self.assertEqual(set(by_id), {"speed", "jams", "delay", "basemap"})
        for layer in layers:
            self.assertEqual(layer.provider_id, BE_MOBILE_PROVIDER_ID)
            self.assertEqual(layer.kind, "xyz_tile")
            self.assertEqual(layer.projection, "EPSG:3857")
            self.assertEqual(layer.tile_scheme, "xyz")
            self.assertEqual(layer.tile_size, 256)
            self.assertEqual(layer.min_zoom, 0)
            self.assertEqual(layer.max_zoom, 19)
            self.assertEqual(layer.content_type, "image/png")
            self.assertIsNone(layer.dimensions)
        self.assertEqual(by_id["speed"].title, "Be-Mobile Traffic Speed")
        self.assertEqual(by_id["jams"].title, "Be-Mobile Traffic Jams")
        self.assertEqual(by_id["delay"].title, "Be-Mobile Traffic Delay")
        self.assertEqual(by_id["basemap"].title, "Be-Mobile Basemap")
        self.assertEqual(by_id["speed"].max_native_zoom, 15)
        self.assertEqual(by_id["jams"].max_native_zoom, 15)
        self.assertEqual(by_id["delay"].max_native_zoom, 15)
        self.assertEqual(by_id["basemap"].max_native_zoom, 19)
        self.assertEqual(by_id["speed"].attribution, BE_MOBILE_ATTRIBUTION)
        self.assertEqual(by_id["jams"].attribution, BE_MOBILE_ATTRIBUTION)
        self.assertEqual(by_id["delay"].attribution, BE_MOBILE_ATTRIBUTION)
        self.assertEqual(by_id["basemap"].attribution, BE_MOBILE_BASEMAP_ATTRIBUTION)

    def test_fetches_speed_tile_from_the_traffic_tile_server(self) -> None:
        session = FakeSession(FakeResponse(body=b"\x89PNG\r\n\x1a\n"))
        provider = BeMobileProvider(session)

        tile = asyncio.run(
            provider.async_get_tile(
                "speed", z=8, x=131, y=85, dimensions={}, options={}
            )
        )

        self.assertEqual(
            session.urls,
            ["https://map.be-mobile.biz/d/public/vrtnws/SPD/8/131/85.png"],
        )
        self.assertEqual(
            session.headers[0]["User-Agent"],
            f"homeassistant-map-layer-be-mobile/{_MANIFEST['version']}",
        )
        self.assertEqual(tile.status, 200)
        self.assertEqual(tile.content, b"\x89PNG\r\n\x1a\n")
        self.assertEqual(tile.content_type, "image/png")
        self.assertEqual(tile.cache_seconds, BE_MOBILE_TRAFFIC_CACHE_SECONDS)

    def test_strips_parameters_from_upstream_content_type(self) -> None:
        session = FakeSession(FakeResponse(content_type="image/png; charset=utf-8"))
        provider = BeMobileProvider(session)

        tile = asyncio.run(
            provider.async_get_tile(
                "speed", z=8, x=131, y=85, dimensions={}, options={}
            )
        )

        self.assertEqual(tile.content_type, "image/png")

    def test_fetches_basemap_tile_from_the_bgtiles_server(self) -> None:
        session = FakeSession(FakeResponse(body=b"\x89PNG\r\n\x1a\n"))
        provider = BeMobileProvider(session)

        tile = asyncio.run(
            provider.async_get_tile(
                "basemap", z=8, x=131, y=85, dimensions={}, options={}
            )
        )

        self.assertEqual(
            session.urls,
            [
                "https://bgtiles.be-mobile.biz/bg/raster/generic/local/8/131/85.png"
            ],
        )
        self.assertEqual(tile.status, 200)
        self.assertEqual(tile.cache_seconds, BE_MOBILE_BASEMAP_CACHE_SECONDS)

    def test_unknown_layer_returns_not_found(self) -> None:
        provider = BeMobileProvider(FakeSession(FakeResponse()))

        tile = asyncio.run(
            provider.async_get_tile(
                "unknown", z=8, x=131, y=85, dimensions={}, options={}
            )
        )

        self.assertEqual(tile.status, 404)

    def test_upstream_404_returns_empty_tile_response(self) -> None:
        provider = BeMobileProvider(FakeSession(FakeResponse(status=404)))

        tile = asyncio.run(
            provider.async_get_tile(
                "speed", z=8, x=131, y=85, dimensions={}, options={}
            )
        )

        self.assertEqual(tile.status, 204)

    def test_upstream_error_returns_bad_gateway(self) -> None:
        provider = BeMobileProvider(FakeSession(FakeResponse(status=500)))

        tile = asyncio.run(
            provider.async_get_tile(
                "speed", z=8, x=131, y=85, dimensions={}, options={}
            )
        )

        self.assertEqual(tile.status, 502)

    def test_request_error_returns_bad_gateway(self) -> None:
        provider = BeMobileProvider(RaisingSession())

        tile = asyncio.run(
            provider.async_get_tile(
                "speed", z=8, x=131, y=85, dimensions={}, options={}
            )
        )

        self.assertEqual(tile.status, 502)


class BeMobileTileUrlTest(unittest.TestCase):
    """URL construction behavior."""

    def test_uses_be_mobile_xyz_templates(self) -> None:
        expected = {
            "speed": "https://map.be-mobile.biz/d/public/vrtnws/SPD/8/131/85.png",
            "jams": "https://map.be-mobile.biz/d/public/vrtnws/SPD-JAM/8/131/85.png",
            "delay": "https://map.be-mobile.biz/d/public/vrtnws/LOS-NEW/8/131/85.png",
            "basemap": (
                "https://bgtiles.be-mobile.biz/bg/raster/generic/local/8/131/85.png"
            ),
        }
        for layer_id, url in expected.items():
            layer = be_mobile_layer(layer_id)
            self.assertIsNotNone(layer)
            self.assertEqual(
                be_mobile_tile_url(layer, z=8, x=131, y=85),
                url,
            )


if __name__ == "__main__":
    unittest.main()
