# Map Layer Be-Mobile

Home Assistant custom integration that registers Be-Mobile traffic raster
layers with the generic `map_layer` integration.

This provider exposes Be-Mobile traffic speed, traffic jams, traffic delay,
and basemap XYZ tiles through the `map_layer` tile proxy. It does not store
private coordinates, dashboard configuration, provider secrets, or upstream
URLs in client-visible tokens.

## Installation

1. Install the `Map Layer` integration first.
2. In HACS, add this repository as a custom repository with category
   `Integration`.
3. Install `Map Layer Be-Mobile`.
4. Restart Home Assistant.
5. Add `Map Layer Be-Mobile` from Settings > Devices & services.

No API key is required. The traffic layers cover the Belgian road network.
Tiles outside the covered area or without data render as transparent tiles,
so overlays stay usable at every zoom level.

## Layers

| Layer | Description |
|---|---|
| `speed` | Current driving speeds on the road network |
| `jams` | Slow and stationary traffic |
| `delay` | Roads running slower than usual |
| `basemap` | Full base map built from OpenStreetMap data |

The traffic layers exist up to zoom 15 and are upscaled up to the card's
zoom 19 ceiling. The basemap exists up to zoom 19.

## Development

Run tests with the core map-layer repo on `PYTHONPATH`:

```sh
PYTHONPATH=/path/to/homeassistant-map-layer:/path/to/homeassistant-map-layer-be-mobile \
  python -m unittest discover -s tests
```

To include config-flow and setup tests against Home Assistant:

```sh
PYTHONPATH=../homeassistant-map-layer:. \
  uv run --with homeassistant python -m unittest discover -s tests
```
