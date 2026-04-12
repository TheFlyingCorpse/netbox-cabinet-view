# Bundled placeholder line-art

The plugin ships with a library of generic front-panel SVGs -- ready-to-use
placeholder images for the cabinet-view renderer.  Upload them to
`ModuleMountProfile.front_image` (for modules that slot into a modular chassis)
or `DeviceType.front_image` (for host devices that occupy rack space or
standalone mounts) via the NetBox admin UI.

> **De-branded by design.**  Every SVG is free of logos, model numbers, and
> vendor markings.  The library deliberately spans multiple form-factor families
> so that no single vendor is identifiable from the art alone.

---

## Categories

### IED Type A -- large horizontal-slot IED form factor

Inspired by large horizontal-slot protection-relay chassis (UR-series form
factor).

| Mount type | Upload to |
|---|---|
| `slot_horizontal` | `ModuleMountProfile.front_image` |

| File | Description |
|---|---|
| `ied-type-a/cpu.svg` | CPU / main processor module |
| `ied-type-a/psu.svg` | Power supply module |
| `ied-type-a/analog-io.svg` | Analog I/O module (CT/PT inputs, mA outputs) |
| `ied-type-a/binary-io.svg` | Binary (digital) I/O module |
| `ied-type-a/comms-2slot.svg` | Double-wide communications module (2 slots) |

### IED Type B -- compact vertical-slot IED form factor

Inspired by compact vertical-slot protection relays.

| Mount type | Upload to |
|---|---|
| `slot_vertical` | `ModuleMountProfile.front_image` |

| File | Description |
|---|---|
| `ied-type-b/cpu.svg` | CPU / main processor module |
| `ied-type-b/analog-io.svg` | Analog I/O module |
| `ied-type-b/binary-io.svg` | Binary (digital) I/O module |
| `ied-type-b/eth-plugin.svg` | Ethernet communications plug-in |

### IED Type C -- fixed-I/O protection relay

Inspired by fixed-I/O protection relays with a small expansion bay.

| Mount type | Upload to |
|---|---|
| `slot_vertical` | `ModuleMountProfile.front_image` |

| File | Description |
|---|---|
| `ied-type-c/cpu.svg` | CPU / main processor module |
| `ied-type-c/comms.svg` | Communications expansion module |
| `ied-type-c/ct-pt.svg` | CT/PT measurement input module |

### IED Type D -- compact single-function relay

Inspired by compact single-function relays with one or two expansion slots.

| Mount type | Upload to |
|---|---|
| `slot_vertical` | `ModuleMountProfile.front_image` |

| File | Description |
|---|---|
| `ied-type-d/cpu.svg` | CPU / main processor module |
| `ied-type-d/io.svg` | Combined I/O expansion module |

### RTU Type A -- modular DIN-rail RTU

Inspired by modular DIN-rail-mounted RTUs with clip-on I/O.

| Mount type | Upload to |
|---|---|
| `din_rail` | `ModuleMountProfile.front_image` |

| File | Description |
|---|---|
| `rtu-type-a/cpu.svg` | CPU / head-end processor |
| `rtu-type-a/ai-4ch.svg` | 4-channel analog input module |
| `rtu-type-a/di-8ch.svg` | 8-channel digital input module |
| `rtu-type-a/do-4ch.svg` | 4-channel digital output module |

### RTU Type B -- rack-slot RTU

Inspired by rack-mounted modular RTU backplanes.

| Mount type | Upload to |
|---|---|
| `slot_vertical` | `ModuleMountProfile.front_image` |

| File | Description |
|---|---|
| `rtu-type-b/cpu.svg` | CPU / main processor card |
| `rtu-type-b/comms.svg` | Communications card |
| `rtu-type-b/di.svg` | Digital input card |
| `rtu-type-b/do.svg` | Digital output card |

### RTU Type C -- compact RTU with expansion

Inspired by compact RTUs with side-mount expansion modules.

| Mount type | Upload to |
|---|---|
| `slot_vertical` | `ModuleMountProfile.front_image` |

| File | Description |
|---|---|
| `rtu-type-c/cpu.svg` | CPU / main processor module |
| `rtu-type-c/comms.svg` | Communications module |
| `rtu-type-c/ao.svg` | Analog output module |
| `rtu-type-c/di.svg` | Digital input module |

### RTU Type D -- field RTU

Inspired by ruggedized field RTUs with plug-in I/O.

| Mount type | Upload to |
|---|---|
| `slot_vertical` | `ModuleMountProfile.front_image` |

| File | Description |
|---|---|
| `rtu-type-d/cpu.svg` | CPU / main processor module |
| `rtu-type-d/comms.svg` | Communications module |
| `rtu-type-d/di.svg` | Digital input module |
| `rtu-type-d/do.svg` | Digital output module |

### PLC / Fieldbus I/O -- modular fieldbus I/O system

Inspired by modular fieldbus I/O systems (coupler + slice modules on DIN rail).

| Mount type | Upload to |
|---|---|
| `din_rail` | `ModuleMountProfile.front_image` |

| File | Description |
|---|---|
| `plc-fieldbus/coupler.svg` | Bus coupler / head station |
| `plc-fieldbus/ai-4ch.svg` | 4-channel analog input slice |
| `plc-fieldbus/di-8ch.svg` | 8-channel digital input slice |
| `plc-fieldbus/do-4ch.svg` | 4-channel digital output slice |

### DIN-rail devices -- standalone DIN-rail equipment

Generic DIN-rail-mounted devices that occupy their own placement (not modules
inside a modular chassis).

| Mount type | Upload to |
|---|---|
| `din_rail` | `DeviceType.front_image` |

| File | Description |
|---|---|
| `din-rail-devices/mcb.svg` | Miniature circuit breaker |
| `din-rail-devices/contactor.svg` | Contactor |
| `din-rail-devices/relay.svg` | Relay |
| `din-rail-devices/psu.svg` | DIN-rail power supply |
| `din-rail-devices/terminal.svg` | Terminal block |

### Host chassis -- enclosures and backplanes

Front-panel art for the host devices that contain mounts.  These are the
"parent" devices whose Layout tab the plugin renders.

| Mount type | Upload to |
|---|---|
| n/a (these ARE the hosts) | `DeviceType.front_image` |

| File | Description |
|---|---|
| `host-chassis/din-shelf-2u.svg` | 2U DIN-rail shelf |
| `host-chassis/din-shelf-4u.svg` | 4U DIN-rail shelf |
| `host-chassis/ied-2row.svg` | 2-row modular IED chassis |
| `host-chassis/mcc-panel.svg` | Motor control center panel / bucket |
| `host-chassis/odf-1u.svg` | 1U optical distribution frame |
| `host-chassis/rtu-din.svg` | DIN-rail RTU backplane enclosure |
| `host-chassis/vfd-cabinet.svg` | Variable-frequency drive cabinet |
| `host-chassis/wdm-1u.svg` | 1U WDM / DWDM shelf |

### Transceivers -- pluggable optics and cages

Small-form-factor pluggable modules and empty transceiver cages.

| Mount type | Upload to |
|---|---|
| `slot_horizontal` | `ModuleMountProfile.front_image` |

| File | Description |
|---|---|
| `transceivers/sfp-fibre.svg` | SFP fibre transceiver |
| `transceivers/sfp-rj45.svg` | SFP RJ45 (copper) transceiver |
| `transceivers/qsfp28-fibre.svg` | QSFP28 fibre transceiver |
| `transceivers/empty-cage.svg` | Empty transceiver cage (no optic installed) |

### Network switches and routers

DIN-mount and rack-mount network gear with visible port cutouts.  Useful for
demonstrating the port/connector overlay feature.

| Mount type | Upload to |
|---|---|
| `din_rail` / rack-mount | `DeviceMountProfile.front_image` |

| File | Description |
|---|---|
| `network-switches/managed-switch-8port.svg` | DIN-mount 8-port managed switch with 2x SFP cages |
| `network-switches/router-4port.svg` | DIN-mount industrial router with 4x ETH + 2x SFP + serial |
| `network-switches/rack-switch-24port.svg` | 1U rack-mount 24-port managed switch with 4x SFP+ uplinks |

### Busbar components

Generic busbar segments, supports, and distribution blocks.

| Mount type | Upload to |
|---|---|
| `busbar` | `DeviceMountProfile.front_image` |

| File | Description |
|---|---|
| `busbar-components/segment.svg` | Busbar segment |
| `busbar-components/support.svg` | Busbar insulating support |
| `busbar-components/tap.svg` | Busbar tap-off point |
| `busbar-components/distribution-block.svg` | Distribution block |

### Cable management

Ancillary cable management items.

| File | Description |
|---|---|
| `cable-management/cable-gland.svg` | Top-view cable gland |
| `cable-management/cable-duct.svg` | Slotted cable duct cross-section |

---

## How to upload

### For modules (ModuleMountProfile)

1. Navigate to **Cabinet View > Module Mount Profiles** in the NetBox sidebar.
2. Select (or create) the profile for your module type.
3. Upload the SVG to the **Front-panel image** field.
4. Save.

### For host devices (DeviceType)

1. Navigate to **DCIM > Device Types** in the NetBox sidebar.
2. Select the device type.
3. Upload the SVG to the **Front Image** field.
4. Save.

---

## Creating your own

If your equipment doesn't match any of the bundled art, create your own SVG.
Any SVG or PNG image works -- the renderer composites it into the placement
rectangle via `<image>` with `preserveAspectRatio`.  Use a `viewBox` that
matches the module's physical proportions for best results.
