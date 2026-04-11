# Changelog

All notable changes to this project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Multi-depth / swing-frame rack support.
- Krone LSA / 110-block terminal frame modelling for copper cross-connect installs.
- Auto-provisioning of Carriers from existing DeviceBay / ModuleBay templates on a DeviceType.

## [0.3.0] — 2026-04-11

### Added
- **Grid carrier type.** New `carrier_type='grid'` for multi-row ("multi-bar") backplanes — think modular protection IEDs with 2 rows of 12 module slots, ODF chassis with fibre cassette grids, large BCU backplanes. A grid carrier has `rows`, `row_height_mm`, and a per-row `length_mm`.
- **Multi-row `Mount.row_span`.** A single Mount can span multiple grid rows, modelling oversized cards that physically occupy more than one bar (common on ABB / GE / Siemens protection IED chassis for comms or differential input modules). `Mount.clean()` does proper rectangle-intersection overlap detection across `(row, row_span, position, size)`.
- **Vertical orientation for all 1D carrier types.** DIN rails, subracks, and busbars can now all be `orientation='vertical'`. The SVG renderer was refactored to centralise `_carrier_visual_width_px` / `_mount_visual_thickness_px` helpers so horizontal and vertical paths share one code path. Previously only DIN rails rendered cleanly in vertical.
- **Rack elevation rear-face patch.** `RackElevationSVG.draw_device_rear` is now monkey-patched alongside `draw_device_front` with identical logic. Fibre patch panels and ODF chassis — where the interesting equipment faces backward — now render their cabinet layout SVG inside the rear column of the rack elevation, not just the front. The 2U threshold and letterboxing behaviour are unchanged. Same opt-out flag (`PATCH_RACK_ELEVATION`).
- **Four new seed scenarios (H–K):**
  - **H. Vertical DIN wall box** — standalone wall-mounted cabinet with one vertical TS35 rail holding 6 stacked relays.
  - **I. Vertical Eurocard subrack** — rotated 6U subrack with 4 cards stacked along its vertical axis.
  - **J. Grid-mounted protection IED** — single host `Device` with 24 `ModuleBay`s across 2 rows × 12 slots, populated with a mix of PSU / CPU / binary I/O / analog / high-speed I/O / Ethernet and fibre comms modules. The fibre comms module spans **both** rows via `row_span=2`, exercising the multi-row mount case. Demonstrates the "one Device, many carrier positions via its ModuleBays" pattern end-to-end.
  - **K. ISP ODF chassis** — 1U fibre patch frame with a 2×6 grid of splice cassettes backed by ModuleBays. Rack-mounted at U21 so the rear-face rack patch is directly exercisable.

### Changed
- **`cabinetview_seed` idempotency hardened.** The command now uses a new `ensure_device_type(mfr, slug, model, ...)` helper that performs `update_or_create` keyed on `(manufacturer, slug)` alone, with the display `model` name in defaults. This fixes an `IntegrityError` when the command was re-run after an upgrade had renamed a DeviceType's `model` string but kept its `slug`. `ensure_mount` similarly switched to `update_or_create` keyed on the target (`device` / `device_bay` / `module_bay`) alone, so a mount can be re-homed onto a new carrier on re-run without tripping `unique_mount_*` constraints. The rack placement pass also now clears ALL devices currently in the managed rack before reassigning, so stale occupants from earlier seed versions can't block the canonical layout.
- **Seed DeviceType / ModuleType / Device names made generic.** Previous seed versions used real vendor part numbers (e.g. "Phoenix UT 2.5", "Pilz PNOZ X3", "ABB REL670", "Wago 750-362", "Rittal TS8 800x2000"). These are withheld as an operational-security hygiene measure — the public repo should not help adversaries fingerprint which specific equipment lives at which OT/ICS site. All seed names are now category-based ("Protection IED chassis 2-row (24-slot)", "Fieldbus Ethernet coupler", "Safety relay (E-Stop)", etc.).
- **Busbar subtypes renamed** in `CarrierSubtypeChoices`: `BB_RILINE_60` → `BB_60MM_PITCH`, `BB_SIEMENS_8US` → `BB_40MM_PITCH`, `BB_ABB_SMISSLINE` → `BB_CLIP_ON`. The taxonomy is now keyed on mechanical pitch and modularity rather than vendor product lines.
- **README expanded** with a gallery of all 20 scenarios (up from 16), an explicit ISP-support section, and an environmental / certification rating guide pointing users at NetBox custom fields rather than asking the plugin to grow first-class fields for them.

### Migration
- **New migration `0002_grid_carrier`** adds `Carrier.rows`, `Carrier.row_height_mm`, `Mount.row`, `Mount.row_span`, and relaxes `Mount.size` from `default=1` to nullable (the auto-default already comes from `DeviceTypeProfile.footprint_primary`). Upgraders run `python manage.py migrate netbox_cabinet_view` after upgrading the plugin.

## [0.2.0] — 2026-04-11

### Added
- **Rack elevation integration.** The plugin now patches `dcim.svg.racks.RackElevationSVG.draw_device_front` at startup so that devices of type `hosts_carriers=True` with `u_height >= 2` render their cabinet layout SVG **inside the rack elevation at their U slot**, instead of the stock `DeviceType.front_image`. This is done as a best-effort, opt-out monkey-patch because the core rack elevation has no plugin hook for per-device image substitution.
  - 1U devices keep the stock behaviour (230×22 px is too narrow for a useful layout).
  - Layout is letterboxed with `preserveAspectRatio="xMidYMid meet"` so it never distorts.
  - URL is cache-busted with a SHA-256 hash of each carrier and mount in the device, so the rack elevation invalidates automatically when anyone edits the host's content.
  - Graceful degradation: patch failures are logged at WARNING and fall through to the stock rendering; they never prevent the plugin from loading.
  - Controlled by `PLUGINS_CONFIG['netbox_cabinet_view']['PATCH_RACK_ELEVATION']`, default `True`.
- **`CabinetLayoutSVG.fit_width` / `fit_height`** parameters for requesting a pixel-dimensioned render that letterboxes the natural drawing inside a target box. Used by the rack elevation patch.
- **`?w=&h=&v=` query parameters** on `/dcim/devices/<pk>/cabinet-layout/svg/` — the first two forward to `CabinetLayoutSVG.fit_width` / `fit_height`, the third is an opaque cache-buster.

### Notes for upgraders
- If a future NetBox version changes the `RackElevationSVG.draw_device_front` signature, the patch will log a warning and the plugin will continue to work without the rack-elevation integration. Set `PATCH_RACK_ELEVATION=False` to silence the warning while still using the Layout tab and rack detail panel.

## [0.1.2] — 2026-04-11

### Added
- **Schema diagram** in the README — a Mermaid ER diagram showing the three plugin models (`DeviceTypeProfile`, `Carrier`, `Mount`) and how they relate to the NetBox core models they attach to (`Device`, `DeviceType`, `DeviceBay`, `ModuleBay`). Documents the Mount three-way XOR constraint explicitly.
- **Supply-chain documents** under `security/`:
  - `security/sbom.cdx.json` — CycloneDX 1.6 Software Bill of Materials, generated reproducibly from a clean Python 3.12 venv containing just the built wheel. Includes purl identifiers for `grype` / `trivy` / `osv-scanner` / Dependency-Track / GitHub dependency-graph consumption.
  - `security/openvex.json` — OpenVEX 0.2.0 Vulnerability Exploitability eXchange document declaring no known CVEs at release time, as a floor statement for downstream compliance scanning.
  - `security/README.md` — regeneration commands and a summary of current contents.
- **Security section** in the main README pointing at the above and explaining the reporting flow via GitHub Security Advisories.

## [0.1.1] — 2026-04-11

### Added
- Seven classic OT/ICS demo scenarios added to `manage.py cabinetview_seed`:
  - **A. Marshalling cabinet** — 4U rack shelf with 20 Phoenix UT 2.5 terminal blocks at 6 mm pitch, stress-testing narrow-slot label fitting.
  - **B. MCC with withdrawable buckets** — standalone 800 × 2200 cabinet with a vertical Rittal RiLine 60 busbar carrying three bucket devices, each hosting its own DIN rail with a contactor and an auxiliary relay inside. Exercises Device-in-Device recursion on a busbar.
  - **C. VFD control cabinet** — Rittal 600 × 1800 enclosure with a back plate holding an ATV630 VFD and a nested DIN rail strip device that carries its own 24 V PSU and motor contactors. Exercises rail-on-plate nesting.
  - **D. Wago remote I/O** — 2U fieldbus shelf with a DIN rail carrying a Wago 750-362 coupler plus four DI and three DO modules chained along the rail.
  - **E. Industrial Ethernet switch** — 2U shelf with a DIN rail carrying a Hirschmann MACH1000 switch.
  - **F. Safety relay panel** — 600 × 800 enclosure with a back plate holding four Pilz PNOZ X3 safety relays.
  - **G. Substation protection panel** — 800 × 2200 protection cabinet with a back plate holding two Siemens SIPROTEC 7SJ82 IEDs, one ABB REL670, and a nested test block rail device with four ABB RTXF test blocks.
- `Test Rack A` resized from 16U to 24U to accommodate the new rack-mounted scenarios (A, D, E) alongside the existing DIN/WDM variety.
- Rack placement in the seed command now runs in two passes (clear, then assign) so re-runs never collide on a used U slot.
- More mounts now rely on `Mount.size` auto-defaulting from `DeviceTypeProfile.footprint_primary` / `footprint_secondary` rather than specifying it explicitly.

### Changed
- `Rittal 2U/4U 19" DIN rail shelf` profiles updated with realistic internal depths.

## [0.1.0] — 2026-04-11

Initial public release.

### Added
- Three models (`DeviceTypeProfile`, `Carrier`, `Mount`), all based on NetBox's `NetBoxModel`.
- Four carrier types: `din_rail`, `subrack`, `mounting_plate`, `busbar`.
- Three mount targets: `dcim.Device`, `dcim.DeviceBay`, `dcim.ModuleBay` (XOR — exactly one populated).
- Carrier units: `mm`, `module_17_5` (DIN module = 17.5 mm), `hp_5_08` (Eurocard HP = 5.08 mm).
- SVG renderer (`svg/cabinets.py`) using `svgwrite`, mirroring the core NetBox rack elevation pattern. Theme-aware via `prefers-color-scheme`.
- Label fitting: `_fit_label()` char-width heuristic + per-mount `<clipPath>` so labels never overflow their slot.
- Carrier label positioning with 3-tier fallback (above carrier / inside carrier / suppressed) so labels can never clip the cabinet outline.
- Host-device name label rendered above the outline, not inside.
- **Layout** tab on every `dcim.Device` detail page (hidden when the device has no carriers), served via `@register_model_view(Device, 'cabinet_layout')` + `ViewTab(hide_if_empty=True)`.
- **Cabinet Layouts** panel on every `dcim.Rack` detail page, embedding each carrier-host's SVG inline via `<object type="image/svg+xml">`.
- `Mount.size` / `size_x` / `size_y` auto-default from the mounted device's `DeviceTypeProfile.footprint_primary` / `footprint_secondary` when left blank — slots are fixed-width, only carriers stretch.
- Minimal REST API (one `ModelViewSet` per model) — required by NetBox's detail templates even when no public API is intended.
- `manage.py cabinetview_seed` management command that creates a realistic OT/ICS demo dataset for visually testing the plugin. Not run automatically on install.

[Unreleased]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/releases/tag/v0.1.0
