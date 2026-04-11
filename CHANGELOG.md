# Changelog

All notable changes to this project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- **Per-face mounting** — different mount layouts on the front vs rear of the same cabinet-host device. Models the common case where e.g. a rack shelf has a network switch clipped to a front rail and standalone PSUs clipped to a rear rail. Needs a `Mount.face` field or per-`Placement` face override, plus renderer logic to pick which subset of mounts draws on which face. Related to (but distinct from) this release's `is_full_depth` seed fix: that change removed spurious rear-face rendering for devices that have no rear layout at all; per-face mounting would enable cabinets with genuine-but-different rear layouts.
- Multi-depth / swing-frame rack support.
- Krone LSA / 110-block terminal frame modelling for copper cross-connect installs.
- Auto-provisioning of Mounts from existing DeviceBay / ModuleBay templates on a DeviceType.
- Nested SVG recursion (a hosted device's own interior rendered inline inside its rectangle on the parent Mount — e.g. click into an MCC bucket from the cabinet view and see the DIN rail inside).
- Okabe-Ito colorblind-safe palette + monochrome/pattern fallback for print.

## [0.4.1] — 2026-04-12

### Fixed

- **Seed command incorrectly marked front-only rack shelves as `is_full_depth=True`**, causing NetBox's core rack elevation (and by extension the plugin's rack-elevation monkey-patch) to draw their cabinet interiors on BOTH front and rear faces. Real DIN shelves, WDM shelves, marshalling shelves, and fieldbus shelves terminate well short of the rear rails, so they should only render on the face they're installed on. Fixed by setting `is_full_depth=False` on the relevant DeviceTypes in `cabinetview_seed`:
  - `wdm-shelf-1u-8-slot`, `wdm-shelf-1u-2-slot`
  - `rack-din-shelf-2u-single-rail`, `rack-din-shelf-4u-dual-rail`, `rack-din-shelf-4u-single-rail`
  - `marshalling-rack-shelf-4u`
  - `fieldbus-rack-shelf-2u`
  - `ODF Frame 1U` stays `is_full_depth=True` — ODFs ARE genuinely full-depth, with cassette geometry on both faces. That's why the ODF scenario was chosen to exercise the rear-face rack elevation patch in v0.3.0 in the first place.
  - User-visible effect: on users who re-run `manage.py cabinetview_seed` after upgrading, the rear face of `Test Rack A` now correctly shows only the ODF Frame plus empty slots, matching real-world physics.

### Notes

v0.4.1 is a seed-data fix; no model, view, or renderer code changed. Users who don't run the demo seed will see no difference.

## [0.4.0] — 2026-04-12

**v0.4.0 is a large consolidated release** addressing eight concrete UX findings from a v0.3.0 review plus an architectural naming rename. Eleven focused commits on the `v0.4.0-rename-and-ux` branch. All changes verified end-to-end against NetBox 4.5.7-Docker-4.0.2 with the plugin's 20 demo scenarios.

### BREAKING

- **Models renamed** for symmetry and to match how users actually talk about the domain:
  - `Carrier` → **`Mount`**
  - `Mount` → **`Placement`**
  - `DeviceTypeProfile` → **`DeviceMountProfile`** (also dodges a naming clash with NetBox 4.5's core `dcim.ModuleTypeProfile`)
- **Field renamed:** `Carrier.carrier_type` → `Mount.mount_type`; `DeviceTypeProfile.hosts_carriers` → `DeviceMountProfile.hosts_mounts`.
- **Choice classes renamed:** `CarrierTypeChoices` → `MountTypeChoices`; `CarrierSubtypeChoices` → `MountSubtypeChoices`; constants `*_CARRIER_TYPES` → `*_MOUNT_TYPES`.
- **URL paths moved:**
  - `/plugins/cabinet-view/carriers/` → `/plugins/cabinet-view/mounts/`
  - `/plugins/cabinet-view/mounts/` → `/plugins/cabinet-view/placements/`
  - `/plugins/cabinet-view/device-type-profiles/` → `/plugins/cabinet-view/device-mount-profiles/`
  - New: `/plugins/cabinet-view/module-mount-profiles/`
  - **No redirect shims.** Update your bookmarks.
- **API endpoints moved:** `carriers/` → `mounts/`, `mounts/` → `placements/`, `device-type-profiles/` → `device-mount-profiles/`; new `module-mount-profiles/`. API client libraries must be updated.
- **SVG CSS classes** inside the embedded stylesheet: `.carrier*` → `.mount*`, `.carrier-label` → `.mount-label`. Downstream tools that parse the SVG for style must update.

The migrations (`0003_rename_carrier_to_mount` + `0004_mount_profiles`) are hand-written and data-safe — zero rows are rewritten, every FK stays pointing at the same row, and both forward and rollback were verified against a seeded database (26 Mounts, 114 Placements, 39 DeviceMountProfiles preserved through the full round-trip). Users upgrade with a single `./manage.py migrate netbox_cabinet_view`.

### Added

- **`ModuleMountProfile`** — new model mirroring `DeviceMountProfile`'s mountable role for `dcim.ModuleType`. Modules placed via `Placement.module_bay` now render at their real width instead of defaulting to 1 unit. A single RTU/IED chassis with mixed I/O cards shows correct geometry. Nine seed ModuleMountProfile rows cover the PLC backplane + IED chassis + ODF cassette scenarios. Not to be confused with NetBox 4.5's unrelated core `dcim.ModuleTypeProfile` (attribute schema).
- **Empty-state CTA on the Layout tab** (Finding B): the tab is now visible whenever the DeviceMountProfile has `hosts_mounts=True`, *even when there are zero mounts yet*. The empty state renders a dashed scale-reference canvas sized to the device's internal `width_mm × height_mm` with a centered "+ Add the first mount" CTA. Users see the cabinet's proportions before picking a mount type. Replaces v0.3.0's `hide_if_empty=True` which actively hid the plugin from new users.
- **Inline click-to-add placement affordance** (Finding C): every unoccupied slot range on a 1D or grid mount becomes a click target with a pre-filled placement form URL (`?mount=N&position=M`). 2D mounting plates accept click-anywhere coordinates via a small JavaScript handler that converts pointer clicks to mm. Green hover outline so the affordance is discoverable.
- **Carrier-driven dynamic Placement form** (Finding G): HTMX-powered form that reshapes when the user picks a Mount. 1D mounts show only `position` + `size`; grid mounts add `row` + `row_span`; 2D plates switch to `position_x/y` + `size_x/y`. Uses NetBox's native `hx-get='.' / hx-include='#form_fields' / hx-target='#form_fields'` convention — no custom view, no fragment endpoint. Target dropdowns (`device`/`device_bay`/`module_bay`) are compatibility-filtered to valid unoccupied options based on the mount's type + subtype. Numeric fields get computed "Range: 1 – N" help text.
- **Discovery hint card** (Finding H): a `PluginTemplateExtension.right_page()` that injects a soft CTA on Device detail pages whose DeviceType is cabinet-shaped (`u_height == 0`) but has no `DeviceMountProfile` yet. Green-bordered card with a "Set up cabinet layout" primary CTA + dismiss link. Per-user dismissal stored in `UserConfig`. Heuristic: `u_height == 0 AND no profile AND user has add_devicemountprofile perm AND not dismissed`. The hint vanishes the moment the user creates a profile.
- **`@media (prefers-contrast: more)` high-contrast mode** (Finding F): automatic high-contrast rendering for OT/ICS field tablets in bright substation sunlight. Triggers via macOS "Increase Contrast", Windows 11 "Contrast themes", or iOS/iPadOS "Increase Contrast". Pure-black background, 2 – 3 px white strokes, saturated role colors ≥ 8.5:1 contrast. CSS-only, no user-preference plumbing.
- **Thumbnail mode for rack elevation embeds** (Finding E): the cabinet-layout SVG embedded inside the rack elevation `<image>` now renders in a diminished form (55% opacity, no labels, desaturated role colors) via a new `CabinetLayoutSVG(thumbnail=True)` kwarg and `svg.thumbnail` CSS block. Reads as "preview — zoom in to interact" instead of pretending each placement rectangle is a live click target. Full-fidelity rendering is preserved on the Layout tab and the Rack detail "Cabinet Layouts" panel below.
- **Opt-in slot ledger table** (Finding D): spreadsheet-style view of every slot on every mount, rendered above the SVG on the Layout tab when `PLUGINS_CONFIG['netbox_cabinet_view']['SLOT_LEDGER_ENABLED'] = True`. Sortable per-mount sections with occupancy mini-bar + percentage, populated rows with linked device/module names, empty slot rows with "+ mount" actions, and **indented β-ledger sub-rows under hosted devices** for their populated `ModuleBay`s. Natural-sort on `ModuleBay.position` so "Slot 2" sorts before "Slot 10". Bay-empty rows are informational (muted italic), not warnings. Standalone `ledger.py` module with no svgwrite dependency.

### Fixed

- **Marshalling cabinet rendered as 2-pixel hairlines** (Finding A, root cause). `Placement.save()` now calls `full_clean()` unconditionally so the profile-driven size auto-fill fires on every code path — not just form submits. The seed command's `ensure_placement()` was also rewritten away from Django's `update_or_create()` (which silently drops fields touched by `clean()` via its `update_fields=set(defaults)` optimization, causing the auto-filled `size` to never reach the DB). Every v0.3.0 marshalling-cabinet placement that had `size=NULL` now auto-fills to the terminal block's profile footprint.
- **"Terminal rail" label hidden behind placements** (also Finding A). The SVG renderer now does a three-pass render: (1) mount geometry + all placements, (2) empty-slot click targets, (3) mount name labels. Labels are painted on top of everything else so they stay legible on dense 1D mounts like the 48-slot marshalling cabinet.
- **MCB-on-DIN-rail compatibility bug** in the 4U DIN shelf seed scenario. Clip-on MCBs had `mountable_on=busbar` but the seed placed them on a `din_rail` mount. v0.3.0 never noticed because `full_clean()` wasn't running. Fixed by adding a separate `din-mount-mcb-1p` DeviceType with `mountable_on=din_rail` and pointing the 4U shelf seed at it.
- **Null-guards on sibling overlap checks** in `Placement.clean()`. Pre-v0.4.0 placements with `NULL` size fields tripped a `TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'` when the overlap loop tried to compute `other.size_x + other.position_x`. Legacy siblings with incomplete geometry are now skipped (they'll fail their own validation on the next save).

### Changed

- **Layout tab visibility** uses a `visible=` callable on `ViewTab` instead of `hide_if_empty=True`. The tab appears whenever the DeviceMountProfile declares `hosts_mounts=True`, regardless of whether mounts exist yet.
- **`PlacementForm`** is now dynamic per Section G above — irrelevant placement fields are removed from the form entirely based on the selected mount's type.
- **README** rewritten for the new model names, new Mermaid ER diagram, v0.4.0 feature additions, and a "Not in v0.4" section that replaces "Not in v0.3".

### Migration

- **Migration 0003** (`0003_rename_carrier_to_mount`) — hand-written mutual rename. Operation order matters: `RenameField('carrier', 'carrier_type', 'mount_type')` first, then `RenameModel('Mount' → 'Placement')` (to free the name), then `RenameModel('Carrier' → 'Mount')`, then `RenameField('placement', 'carrier', 'mount')`, then `AlterField` for every FK to update `related_name`, then `RemoveConstraint` + `AddConstraint` for the three unique constraints whose names embedded `mount_`, finally `AlterModelOptions` for the new `verbose_name`.
- **Migration 0004** (`0004_mount_profiles`) — `RenameModel('DeviceTypeProfile' → 'DeviceMountProfile')` + `CreateModel('ModuleMountProfile')`.

Both migrations are metadata-only (zero rows rewritten). Data preservation verified: 26 → 26 Mounts, 114 → 114 Placements, 39 → 39 DeviceMountProfiles round-trip through forward + rollback with zero loss.

### Upgrade instructions

```bash
git pull
./manage.py migrate netbox_cabinet_view
./manage.py cabinetview_seed  # optional, idempotent, re-seeds demo data with new names
```

Then update any custom code / scripts that reference the renamed Python classes, DB fields, URL paths, or API endpoints. No redirects are provided for old URLs — they 404 cleanly.

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

[Unreleased]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/TheFlyingCorpse/netbox-cabinet-view/releases/tag/v0.1.0
