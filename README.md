# netbox-cabinet-view

A NetBox plugin that models physical mounting that doesn't fit a 19″ rack — DIN rails, Eurocard subracks, mounting plates, and busbars — and renders each cabinet as an SVG drawing with real device images.

## Compatibility

| NetBox version | Supported | Tested | Notes |
|---|:---:|:---:|---|
| **4.5.x** | ✅ | ✅ | Actively developed against 4.5.7 — this is the version all screenshots and smoke tests run against |
| **4.4.x** | ✅ | ⚠️ | Untested but all APIs used (`NetBoxModel`, `ViewTab`, `register_model_view`, `get_model_urls`, `PluginTemplateExtension.models`) are present in 4.4.0; no code changes expected |
| 4.3.x and older | ❌ | ❌ | Not supported — some helpers we rely on may not exist or have different signatures |
| 4.6.x (when released) | ❓ | ❓ | To be verified when released |

Python 3.10+ required (matches NetBox 4.4 / 4.5's own Python support).

## What it adds

Three models:

- **DeviceTypeProfile** — per-DeviceType declaration of whether the device hosts carriers (i.e. it's a cabinet or enclosure) and/or mounts on carriers (it's a DIN-mounted relay, a 4-HP Eurocard, a clip-on MCB). Internal dimensions and footprints live here.
- **Carrier** — a geometric mounting structure attached to a host `Device`. Four types ship in v1: `din_rail`, `subrack`, `mounting_plate`, `busbar`. Each has offset, orientation, length (1D) or width/height (2D), and a unit (mm, DIN module 17.5 mm, Eurocard HP 5.08 mm).
- **Mount** — a placement on a carrier. Points at exactly one of:
  - a standalone `dcim.Device` (bare DIN rail mounts)
  - a `dcim.DeviceBay` (chassis with child devices — e.g. a WDM shelf with two filter modules)
  - a `dcim.ModuleBay` (modular PLC / line-card chassis)

And one view:

- A **Layout** tab on every `dcim.Device` detail page. Renders the host's carriers and their mounts as an SVG via `svgwrite`, reusing `DeviceType.front_image` and `ModuleType.front_image` from core NetBox. Falls back to colored rectangles with labels when no image is available.

## OT/ICS coverage

v1 covers the common OT/ICS cabinet types:

| Cabinet kind | Carrier type used |
|---|---|
| PLC cabinets, marshalling/junction boxes, field I/O, IS cabinets, relay panels, small LV distribution | `din_rail` |
| Rittal/Hoffman enclosures with back-mounted VSDs, UPS, contactors, IPCs | `mounting_plate` |
| VME/cPCI/MTCA measurement and controller racks, 3U/6U industrial computing | `subrack` |
| MCCs, LV panelboards, withdrawable switchgear spines (RiLine, 8US, SMISSLINE) | `busbar` |
| Modular PLCs, OLT/WDM line cards, modular router/switch chassis | `subrack` + `ModuleBay` mounts |
| MCC withdrawable buckets, switchgear compartments | nested Device-in-Device-on-Carrier (no new model) |

## Install

```bash
pip install -e /path/to/netbox-cabinet-view
```

Add to your NetBox `configuration.py`:

```python
PLUGINS = ['netbox_cabinet_view']
```

Then run migrations:

```bash
DEVELOPER=1 python manage.py makemigrations netbox_cabinet_view
python manage.py migrate netbox_cabinet_view
python manage.py collectstatic --no-input
```

Restart NetBox. A **Cabinet View** entry appears in the sidebar, and every `dcim.Device` detail page grows a **Layout** tab (hidden when the device has no carriers).

## Using it

1. Create a `DeviceTypeProfile` for any DeviceType that hosts carriers (set `hosts_carriers=True` and the internal dimensions in mm).
2. Create a `DeviceTypeProfile` for any DeviceType that mounts on carriers (set `mountable_on`, `mountable_subtype`, and `footprint_primary` in carrier units). Mount `size` is optional — if left blank it defaults to the profile's `footprint_primary` (slots are fixed-width; only carriers stretch).
3. Create a `Device` of the host type, place it in a Location or a Rack as normal.
4. Add one or more `Carrier` records to the host device — DIN rail at offset (x, y) with a length, or a mounting plate with width×height, etc.
5. Add `Mount` records to place devices (or device bays, or module bays) on the carriers at specific positions.
6. Visit the host device's detail page → **Layout** tab.

## Demo data

The plugin ships a management command that creates a realistic OT/ICS demo dataset for visually testing every feature. It is **not** run automatically on install. To use it:

```bash
python manage.py cabinetview_seed
```

The command is idempotent — safe to re-run, updates drifted fields back to the canonical values. It creates one `Site` (`OT Test Site`), one `Location`, one `Manufacturer` (`Generic`), nine `DeviceRole`s, twelve `DeviceType`s with matching `DeviceTypeProfile`s, one `Rack` (`Test Rack A`, 12U), and the devices below:

| # | Scenario | Host device | Host DeviceType | Carrier(s) | Mount target | Demonstrates |
|---|---|---|---|---|---|---|
| 1 | Standalone DIN rail | `DIN Rail #1` | DIN TS35 480 mm | 1× DIN rail (480 mm) | 2× Phoenix REL-MR (Device) | Bare rail with no enclosing cabinet |
| 2 | 2D mounting plate | `Enclosure #1` | Rittal TS8 800×2000 | 1× mounting plate (760×1960 mm) | 1× Industrial PC (Device, 220×90 mm) | Back-plate with `(x, y)` mm placement |
| 3 | Chassis with child devices | `WDM Shelf #1` | WDM Shelf 1U 8-slot | 1× subrack (HP 3U, 406 mm) | 2× WDM Mux/Demux (DeviceBay, slots 1 and 5) | `DeviceBay`-backed mounts, parent/child visualization |
| 4 | Small chassis | `WDM Shelf 2-slot #1` | WDM Shelf 1U 2-slot | 1× subrack (HP 3U, 440 mm, full width) | 2× WDM Mux/Demux (DeviceBay, 20 HP each) | Fixed-width slots in a wider carrier |
| 5 | LV panelboard | `LV Panel Busbar` | Rittal RiLine 60 1 m | 1× busbar (1000 mm) | 3× MCB 1P 45 mm (Device, at mm positions) | Copper busbar with clip-on modules |
| 6 | Modular PLC | `PLC Backplane #1` | Test PLC Backplane 8-slot | 1× subrack (HP 3U, 400 mm) | 2× DI 16×24 VDC (ModuleBay) | `ModuleBay`-backed mounts, modular chassis |
| 7 | Rack-mounted DIN shelf (2U) | `DIN Shelf 2U #1` | Rittal 2U 19″ DIN rail shelf | 1× DIN rail (420 mm, centered) | 3× Phoenix REL-MR (Device) | Realistic 2U DIN shelf for rack-elevation testing |
| 8 | Rack-mounted DIN shelf (4U) | `DIN Shelf 4U #1` | Rittal 4U 19″ DIN rail shelf | 2× stacked DIN rails (upper + lower) | 2× Relay + 3× MCB (Device) | Multi-carrier host device, stacked rails |

The eight scenarios populate `Test Rack A` with the 1U / 2U / 4U DIN shelves and the two WDM shelves at various U positions, so the rack detail page and rack elevation both show a realistic mix.

## Not in v1

## Not in v1

Strut channel, keystone frames, Krone LSA/110-block frames, fiber cassettes, HMI panel cutouts, pneumatic manifolds, auto-provisioning carriers from existing bay templates, drag-to-place UI, REST API, GraphQL.
