# Changelog

All notable changes to this project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Option 2: monkey-patch `RackElevationSVG` so carrier-host devices render their cabinet layout SVG inside the rack elevation at their U slot (letterboxed for ≥2U, falls back to stock `front_image` for 1U).
- Expanded demo dataset: marshalling cabinet, MCC with withdrawable buckets, VFD control cabinet, Wago remote I/O station, industrial Ethernet switch panel, safety relay panel, substation protection panel.
- Vertical DIN rail rendering + test coverage.
- Grid-view carrier type (discrete-cell 2D matrix for panel-grid layouts).

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

[Unreleased]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/releases/tag/v0.1.0
