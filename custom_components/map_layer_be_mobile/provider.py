"""Be-Mobile map-layer provider."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from custom_components.map_layer import MapLayerMetadata, TileResponse


class ClientSession(Protocol):
    """Small subset of the aiohttp client session used by this provider."""

    def get(self, url: str, **kwargs: Any) -> Any:
        """Return an async context manager for an HTTP GET request."""


_LOGGER = logging.getLogger(__name__)

_MANIFEST = json.loads((Path(__file__).parent / "manifest.json").read_text())

BE_MOBILE_PROVIDER_ID = "be_mobile"
BE_MOBILE_ATTRIBUTION = "Be-Mobile"
BE_MOBILE_BASEMAP_ATTRIBUTION = "Be-Mobile; OpenStreetMap contributors"
BE_MOBILE_USER_AGENT = f"homeassistant-map-layer-be-mobile/{_MANIFEST['version']}"
BE_MOBILE_TRAFFIC_TILES_URL = "https://map.be-mobile.biz/d/public/vrtnws"
BE_MOBILE_BASEMAP_TILES_URL = "https://bgtiles.be-mobile.biz/bg/raster/generic/local"
BE_MOBILE_TILE_SIZE = 256
BE_MOBILE_MIN_ZOOM = 0
BE_MOBILE_MAX_ZOOM = 19
BE_MOBILE_TRAFFIC_MAX_NATIVE_ZOOM = 15
BE_MOBILE_BASEMAP_MAX_NATIVE_ZOOM = 19
BE_MOBILE_TRAFFIC_CACHE_SECONDS = 60
BE_MOBILE_BASEMAP_CACHE_SECONDS = 86400
BE_MOBILE_REQUEST_TIMEOUT_SECONDS = 30


@dataclass(frozen=True, slots=True)
class BeMobileLayer:
    """Static public Be-Mobile layer definition."""

    layer_id: str
    title: str
    url_prefix: str
    attribution: str
    max_native_zoom: int
    cache_seconds: int


BE_MOBILE_LAYERS: tuple[BeMobileLayer, ...] = (
    BeMobileLayer(
        layer_id="speed",
        title="Be-Mobile Traffic Speed",
        url_prefix=f"{BE_MOBILE_TRAFFIC_TILES_URL}/SPD",
        attribution=BE_MOBILE_ATTRIBUTION,
        max_native_zoom=BE_MOBILE_TRAFFIC_MAX_NATIVE_ZOOM,
        cache_seconds=BE_MOBILE_TRAFFIC_CACHE_SECONDS,
    ),
    BeMobileLayer(
        layer_id="jams",
        title="Be-Mobile Traffic Jams",
        url_prefix=f"{BE_MOBILE_TRAFFIC_TILES_URL}/SPD-JAM",
        attribution=BE_MOBILE_ATTRIBUTION,
        max_native_zoom=BE_MOBILE_TRAFFIC_MAX_NATIVE_ZOOM,
        cache_seconds=BE_MOBILE_TRAFFIC_CACHE_SECONDS,
    ),
    BeMobileLayer(
        layer_id="delay",
        title="Be-Mobile Traffic Delay",
        url_prefix=f"{BE_MOBILE_TRAFFIC_TILES_URL}/LOS-NEW",
        attribution=BE_MOBILE_ATTRIBUTION,
        max_native_zoom=BE_MOBILE_TRAFFIC_MAX_NATIVE_ZOOM,
        cache_seconds=BE_MOBILE_TRAFFIC_CACHE_SECONDS,
    ),
    BeMobileLayer(
        layer_id="basemap",
        title="Be-Mobile Basemap",
        url_prefix=BE_MOBILE_BASEMAP_TILES_URL,
        attribution=BE_MOBILE_BASEMAP_ATTRIBUTION,
        max_native_zoom=BE_MOBILE_BASEMAP_MAX_NATIVE_ZOOM,
        cache_seconds=BE_MOBILE_BASEMAP_CACHE_SECONDS,
    ),
)


class BeMobileProvider:
    """Provider for public Be-Mobile traffic and basemap raster tiles."""

    provider_id = BE_MOBILE_PROVIDER_ID

    def __init__(self, session: ClientSession) -> None:
        """Initialize the provider with a Home Assistant HTTP client session."""

        self._session = session

    async def async_list_layers(self) -> list[MapLayerMetadata]:
        """Return public Be-Mobile layer metadata."""

        return [
            MapLayerMetadata(
                provider_id=self.provider_id,
                layer_id=layer.layer_id,
                title=layer.title,
                kind="xyz_tile",
                projection="EPSG:3857",
                tile_scheme="xyz",
                tile_size=BE_MOBILE_TILE_SIZE,
                min_zoom=BE_MOBILE_MIN_ZOOM,
                max_zoom=BE_MOBILE_MAX_ZOOM,
                max_native_zoom=layer.max_native_zoom,
                attribution=layer.attribution,
                content_type="image/png",
            )
            for layer in BE_MOBILE_LAYERS
        ]

    async def async_get_tile(
        self,
        layer_id: str,
        *,
        z: int,
        x: int,
        y: int,
        dimensions: Mapping[str, Any],
        options: Mapping[str, Any],
    ) -> TileResponse:
        """Fetch one upstream Be-Mobile raster tile."""

        layer = be_mobile_layer(layer_id)
        if layer is None:
            return TileResponse(status=404)

        url = be_mobile_tile_url(layer, z=z, x=x, y=y)
        try:
            async with self._session.get(
                url,
                headers={"User-Agent": BE_MOBILE_USER_AGENT},
                timeout=_client_timeout(BE_MOBILE_REQUEST_TIMEOUT_SECONDS),
            ) as response:
                if response.status == 404:
                    return TileResponse(status=204)
                if response.status != 200:
                    return TileResponse(status=502)

                content = await response.read()
                content_type = response.headers.get("Content-Type", "image/png").split(
                    ";", 1
                )[0]
                return TileResponse(
                    content=content,
                    content_type=content_type or "image/png",
                    cache_seconds=layer.cache_seconds,
                )
        except Exception:
            _LOGGER.debug("Be-Mobile tile request failed", exc_info=True)
            return TileResponse(status=502)


def _client_timeout(total_seconds: int) -> Any:
    try:
        from aiohttp import ClientTimeout
    except ImportError:
        return total_seconds
    return ClientTimeout(total=total_seconds)


def be_mobile_layer(layer_id: str) -> BeMobileLayer | None:
    """Return a known Be-Mobile layer definition by public layer id."""

    for layer in BE_MOBILE_LAYERS:
        if layer.layer_id == layer_id:
            return layer
    return None


def be_mobile_tile_url(layer: BeMobileLayer, *, z: int, x: int, y: int) -> str:
    """Return the upstream Be-Mobile tile URL for XYZ coordinates."""

    return f"{layer.url_prefix}/{z}/{x}/{y}.png"
