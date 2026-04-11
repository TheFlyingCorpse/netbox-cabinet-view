# Changelog

All notable changes to this project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Option 2: monkey-patch `RackElevationSVG` so carrier-host devices render their cabinet layout SVG inside the rack elevation at their U slot (letterboxed for ≥2U, falls back to stock `front_image` for 1U).
- Vertical DIN rail rendering + test coverage.
- Grid-view carrier type (discrete-cell 2D matrix for panel-grid layouts).
- Multi-depth / swing-frame rack support.

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

[Unreleased]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/releases/tag/v0.1.0
