# Demo scenarios

The plugin ships a management command that creates a realistic OT/ICS + ISP demo dataset for visually testing every feature. It is **not** run automatically on install. To use it:

```bash
python manage.py cabinetview_seed
```

The command is idempotent — safe to re-run, updates drifted fields back to the canonical values, and re-layouts rack positions cleanly. It creates one `Site` (`OT Test Site`), one `Location`, one `Manufacturer` (`Generic`), nine `DeviceRole`s, around 30 `DeviceType`s with matching `DeviceMountProfile`s, nine `ModuleType`s with matching `ModuleMountProfile`s, one `Rack` (`Test Rack A`, 24U), and **20 scenarios** across four groups.

Device type and model names in the seed are deliberately generic by category (no real vendor part numbers) as an operational-security hygiene measure — the plugin's repo should not help adversaries fingerprint which specific equipment lives at which site.

## Core scenarios (9) — the basic model

| # | Scenario | Host device | Mount(s) | Demonstrates |
|---|---|---|---|---|
| 1 | Standalone DIN rail | `DIN Rail #1` | 1× DIN rail (480 mm) | Bare rail with no enclosing cabinet |
| 2 | 2D mounting plate | `Floor Enclosure #1` | 1× mounting plate (760×1960 mm) | Back-plate with `(x, y)` mm placement |
| 3 | Chassis with child devices | `WDM Shelf #1` | 1× subrack (HP 3U, 406 mm) | `DeviceBay`-backed placements, parent/child |
| 4 | Small chassis, wider mount | `WDM Shelf 2-slot #1` | 1× subrack (HP 3U, 440 mm) | Fixed-width slots in a wider mount |
| 5 | LV panelboard | `LV Distribution Busbar` | 1× busbar (1000 mm) | Copper busbar with clip-on modules |
| 6 | Modular PLC | `PLC Backplane #1` | 1× subrack (HP 3U, 400 mm) | `ModuleBay`-backed placements |
| 7 | Rack-mounted DIN shelf (2U) | `DIN Shelf 2U #1` | 1× DIN rail (420 mm, centered) | Realistic 2U rack-mounted DIN |
| 8 | Rack-mounted DIN shelf (4U, two rails) | `DIN Shelf 4U #1` | 2× stacked DIN rails | Multi-mount host, stacked rails |
| 9 | ISP-style 4U DIN shelf (single rail) | `DIN Shelf 4U ISP #1` | 1× DIN rail (centered vertically) | Single rail with wire-management headroom |

## Classic OT/ICS scenarios (A–G)

| # | Scenario | Host device | Demonstrates |
|---|---|---|---|
| A | **Marshalling cabinet** | `Marshalling Cabinet #1` (4U rack) | 20 terminal blocks at 6 mm pitch — dense narrow-slot rendering stress test |
| B | **MCC with withdrawable buckets** | `MCC Cabinet #1` | **Device-in-Device recursion** on a vertical busbar mount; three bucket devices, each a host with its own DIN rail inside holding a contactor and an auxiliary relay |
| C | **VFD control cabinet** | `VFD Cabinet #1` | Mounting plate holding a VFD + a nested DIN strip device that itself carries a 24 V PSU and two motor contactors — rail-on-plate nesting |
| D | **Fieldbus remote I/O station** | `Fieldbus Remote I/O #1` (2U rack) | Bus-coupler-plus-modules pattern on DIN: 1 coupler + 4 DI + 3 DO cards |
| E | **Industrial Ethernet switch panel** | `Industrial Switch Shelf #1` (2U rack) | Single wider-footprint device on a DIN rail |
| F | **Safety relay panel** | `Safety Panel #1` | Four fixed-size safety relays on a 2D plate |
| G | **Substation protection panel** | `Protection Panel #1` | Two overcurrent IEDs + one line-distance IED on a plate, plus a nested test-block rail device carrying four test blocks |

## v0.3.0 scenarios (H–K) — grid mounts, vertical, and ISP

| # | Scenario | Host device | Demonstrates |
|---|---|---|---|
| H | **Vertical DIN rail wall box** | `Vertical DIN Wall Box #1` | Vertical-orientation DIN rail with 6 relays stacked top-to-bottom |
| I | **Vertical Eurocard subrack** | `Vertical Subrack #1` | Vertical-orientation subrack with 4 cards — proves all 1D mount types support `orientation='vertical'` |
| J | **Grid-mounted protection IED** | `Protection IED L01` | **Grid mount** with 2 rows × 12 slots, ModuleBay-backed placements including a comms module that **spans both rows** via `row_span=2` — the "one device, many mount positions depending on its ModuleBays" story |
| K | **ISP ODF (fibre patch frame)** | `ODF Frame #1` (1U rack) | 12 fibre splice cassettes in a 2×6 grid. The interesting face of an ODF is the **rear**, so this also proves the rear-face `RackElevationSVG` patch — the ODF layout appears inside the rack elevation at U21 on both front and rear columns |

`Test Rack A` (24U) holds the 1U / 2U / 4U rack-mounted scenarios (3, 4, 7, 8, 9, A, D, E, K) at consecutive U positions. The standalone scenarios (1, 2, 5, 6, B, C, F, G, H, I, J) live in `OT Test Site` / `Control Room` without a rack.

## Rendered scenario gallery

The SVGs below are committed at `docs/screenshots/*.svg` and embedded live — every stroke, fill and label you see is exactly what the plugin's `/dcim/devices/<pk>/cabinet-layout/svg/` endpoint returns for that device.

| Scenario | Rendering |
|---|---|
| **1. Standalone DIN rail** | ![](screenshots/01-din-rail.svg) |
| **2. Mounting plate + IPC** | ![](screenshots/02-mounting-plate.svg) |
| **3. WDM 8-slot shelf (DeviceBay)** | ![](screenshots/03-wdm-8slot.svg) |
| **4. WDM 2-slot shelf** | ![](screenshots/04-wdm-2slot.svg) |
| **5. LV distribution busbar** | ![](screenshots/05-busbar.svg) |
| **6. Modular PLC (ModuleBay)** | ![](screenshots/06-modular-plc.svg) |
| **7. 2U rack DIN shelf** | ![](screenshots/07-din-shelf-2u.svg) |
| **8. 4U rack DIN shelf — two stacked rails** | ![](screenshots/08-din-shelf-4u-two-rail.svg) |
| **9. 4U rack DIN shelf — ISP single-rail** | ![](screenshots/09-din-shelf-4u-isp.svg) |
| **A. Marshalling cabinet (20 terminal blocks)** | ![](screenshots/A-marshalling.svg) |
| **B. MCC with withdrawable buckets** | ![](screenshots/B-mcc-cabinet.svg) |
| **C. VFD control cabinet** | ![](screenshots/C-vfd-cabinet.svg) |
| **D. Fieldbus remote I/O station** | ![](screenshots/D-fieldbus-remote-io.svg) |
| **E. Industrial Ethernet switch** | ![](screenshots/E-industrial-switch.svg) |
| **F. Safety relay panel** | ![](screenshots/F-safety-panel.svg) |
| **G. Substation protection panel** | ![](screenshots/G-protection-panel.svg) |
| **H. Vertical DIN wall box** | ![](screenshots/H-vertical-din-wall-box.svg) |
| **I. Vertical Eurocard subrack** | ![](screenshots/I-vertical-subrack.svg) |
| **J. Grid-mounted IED (multi-row span)** | ![](screenshots/J-grid-ied.svg) |
| **K. ISP ODF (12-cassette grid)** | ![](screenshots/K-odf-chassis.svg) |

## OT/ICS coverage

The plugin covers the common OT/ICS cabinet types:

| Cabinet kind | Mount type used |
|---|---|
| PLC cabinets, marshalling/junction boxes, field I/O, IS cabinets, relay panels, small LV distribution | `din_rail` |
| Rittal/Hoffman enclosures with back-mounted VSDs, UPS, contactors, IPCs | `mounting_plate` |
| VME/cPCI/MTCA measurement and controller racks, 3U/6U industrial computing | `subrack` |
| MCCs, LV panelboards, withdrawable switchgear spines (RiLine, 8US, SMISSLINE) | `busbar` |
| Modular PLCs, OLT/WDM line cards, modular router/switch chassis | `subrack` + `ModuleBay` placements (with `ModuleMountProfile` for per-module footprint) |
| MCC withdrawable buckets, switchgear compartments | nested Device-in-Device-on-Mount (no new model) |

## Supporting ISPs

Yes. The plugin covers the main physical-mounting patterns ISPs encounter:

- **Modular OLT / WDM / ROADM shelves** with line cards — `subrack` mounts with `ModuleBay`-backed placements (scenarios 3, 4, 6)
- **ODF / fibre patch chassis** — `grid` mounts with cassette positions, visible on the rack rear face (scenario K)
- **DIN-mounted NIDs, media converters, surge protectors, small fieldbus switches** — `din_rail` mounts (scenarios 1, D, E, H)
- **Telco DC power distribution** — `busbar` mounts + nested DIN for MCBs (scenario 5)
- **Vertical DIN rails in street cabinets / OSP pedestals** — `orientation='vertical'` on any 1D mount (scenario H)
- **Rack elevation showing what's inside each shelf on both faces** — via the `RackElevationSVG` rear-face patch, now rendered in thumbnail mode so users understand the embed is a preview, not a live click target

Gaps for ISPs, called out explicitly: Krone LSA / 110-block copper frames are deferred (see [roadmap](roadmap.md)). Standard 19″ patch panel cabling (front/rear port tracking) is already handled by NetBox core — the plugin doesn't need to duplicate it.
