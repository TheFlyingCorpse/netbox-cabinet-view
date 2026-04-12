# Roadmap — deferred features and future work

## Carrier types still deferred

- **Strut channel** (Unistrut, similar) — adjacent to DIN rail but with different spacing and clip semantics. Would work as a new `MountTypeChoices` entry. Not blocking anyone today, so deferred.
- **Keystone frames** — RJ45 / fibre / coax keystone patch fields in ISP street cabinets and telco huts.
- **Krone LSA / 110-block terminal frames** — copper cross-connect terminal frames in telco / ISP copper distribution rooms. Distinct enough from DIN that it wants its own carrier type, not a subtype of `din_rail`.
- **HMI panel cutouts** — flush-mounted HMIs in machine cabinets.
- **Pneumatic / hydraulic manifolds** — different physics, but the same "here's a block with N ports at known positions" shape.

None of these are in the current release because they'd need their own carrier-type enum values and their own validation rules, and v0.4.0 already had a large scope. They're tracked under "Planned" in [CHANGELOG.md](../CHANGELOG.md).

## Bundled placeholder line-art (v0.6.0 exploration)

When a DeviceType or ModuleType has no uploaded `front_image`, the renderer falls back to a plain colored rectangle with a text label. A future release should bundle **generic line-art SVGs** that ship with the plugin as fallback images, so out-of-the-box rendering looks realistic without requiring users to upload manufacturer photos.

Explored art families (prototyped in `/tmp/module-art/` during the v0.5.0 cycle, OpSec-cleared for the GE-inspired set):

- **IED backplane modules** — PSU, CPU (two form factors), binary I/O, analog I/O (CT/PT), comms (ETH + SFP + serial). Narrow vertical cards with backplane connectors. GE UR-inspired and Siemens SIPROTEC-inspired variants.
- **RTU/PLC DIN-mount modules** — CPU/gateway (wider body), 8×DI 24VDC, 4×DO relay, 4×AI 4-20mA. Light-body with color-coded top bands and spring-cage terminals. WAGO/Sprecher/Netcontrol/ABB RTU inspired.
- **Transceiver face plates** — SFP fibre (LC duplex), SFP RJ45 (copper), QSFP28 (MPO/MTP), empty cage. Front-face-only views (the body is inside the cage; you only see the face plate when plugged in).
- **IED/RTU chassis** — 2-row backplane enclosure with dashed slot positions.

Still to explore:
- **Rack-mount shelves** — 1U/2U/4U front panels with blank plates, DIN rail cutouts visible, or fibre patch panel faceplates
- **DIN-rail mounted devices** — generic relay, MCB, contactor, terminal block, PSU, fieldbus coupler (light/dark body variants)
- **Mounting plate devices** — VFD drive, safety relay, IPC, generic panel instrument
- **WDM/OLT line cards** — wider subrack cards with fibre ports
- **Siemens SIPROTEC plug-in modules** — ETH-BB, BIN-IO, and similar proprietary slot form factors that aren't SFP-shaped
- **Front panel overlays** — LCD displays, keypads, indicator lamp clusters, HMI cutouts

Implementation path: add `ModuleMountProfile.front_image` ImageField (decided, migration ready) + optionally `DeviceMountProfile.default_front_image` for a profile-level fallback. Bundle the SVGs under `static/netbox_cabinet_view/module-art/`. The renderer checks `module_type.cabinet_profile.front_image` → bundled fallback → colored rectangle, in that order.

Related: **management IP easter egg** — render `device.primary_ip4` on the CPU module's LCD area as an SVG text overlay on top of the composited front_image. Cute and genuinely useful for ops engineers glancing at the Layout tab.

## UX features deferred

- **Per-face mounting (front + rear positions)** — today a `Mount` has a single `offset_x_mm`/`offset_y_mm` + geometry, and the whole layout renders on whichever face(s) the host `Device` is drawn on. Real cabinets often have **different stuff on the front and rear of the same shelf**: an industrial switch mounted on the front rail, PSUs or fuse blocks on a rear rail, or line cards in the front of a modular chassis with cooling modules in the rear. Need a `Mount.face` field (or a per-`Placement` face override) plus SVG renderer logic that draws different layouts depending on which face the parent rack elevation is painting. Also affects the `is_full_depth` decision: a cabinet with distinct front + rear mount layouts is naturally full-depth. See `seed: mark front-only DeviceTypes as is_full_depth=False` (commit 88bc44a) for the v0.4.0 workaround.
- **Nested SVG recursion** — a hosted device's own interior rendered inline inside its rectangle on the parent mount. Think "click into an MCC bucket from the cabinet view and see the DIN rail inside, with its contactors and auxiliary relays rendered in place." Visual equivalent of the existing rack-elevation monkey-patch but pointed inward. Beautiful feature, wants its own release cycle.
- **Okabe-Ito colorblind-safe palette** and a monochrome/pattern fallback for print. The v0.4.0 high-contrast mode (`@media (prefers-contrast: more)`) handles the substation-sunlight case but not colorblindness explicitly. Deferred until a user speaks up.
- ~~**Port / interface overlay on device images**~~ — **shipped in v0.7.0** as port_map JSONField with zone/pin/module_bay entries + two-level overlay + protruding connectors. Health indicators (from external REST/GraphQL sources) deferred to a future release.
- ~~**Drag-to-place UI**~~ — **shipped in v0.7.0** with ghost rect + grid snap + PATCH to API.
- ~~**GraphQL**~~ — **shipped in v0.6.0** via Strawberry.
- **Auto-provisioning Mounts from existing DeviceBay/ModuleBay templates** on a DeviceType — a one-click path from "I have a DeviceType with 8 ModuleBays" to "and here's a Mount with 8 slots ready to receive placements."
- **Port health indicators from external sources** — extend the port overlay with live health data (link state, error counters, traffic stats) pulled from an external REST or GraphQL endpoint. Needs a configurable data-source integration pattern. Deferred from v0.7.0.
- **Auto-scrape port_map coordinates from netbox-devicetype-library** — scrape front-panel images and component positions from the community DeviceType library (https://github.com/netbox-community/devicetype-library) to auto-generate port_map entries for common device types. Could process the YAML definitions + front panel images to derive pin positions. Large scope but would give out-of-the-box overlay coverage for hundreds of device types.

## What is NOT on the roadmap, ever

- **Environmental / certification metadata** (IP, NEMA, Ex, temperature, RF shielding, EMP/HEMP, SIL, seismic, fire, impact, etc.) — handled via NetBox custom fields on `dcim.rack` and `dcim.devicetype`. See [certification-ratings.md](certification-ratings.md) for the recommended baseline. The plugin will not grow first-class fields for these.
- **Standard 19″ patch panel cabling** — already handled by NetBox core (front/rear port tracking). The plugin doesn't need to duplicate it.
- **A parallel "Cabinet" model** separate from `dcim.Device` — a cabinet is a device with `hosts_mounts=True` on its profile, and that's the whole architectural decision. See [architecture.md](architecture.md) for why.
