# Roadmap — what's not in v0.4 (and why)

## Carrier types still deferred

- **Strut channel** (Unistrut, similar) — adjacent to DIN rail but with different spacing and clip semantics. Would work as a new `MountTypeChoices` entry. Not blocking anyone today, so deferred.
- **Keystone frames** — RJ45 / fibre / coax keystone patch fields in ISP street cabinets and telco huts.
- **Krone LSA / 110-block terminal frames** — copper cross-connect terminal frames in telco / ISP copper distribution rooms. Distinct enough from DIN that it wants its own carrier type, not a subtype of `din_rail`.
- **HMI panel cutouts** — flush-mounted HMIs in machine cabinets.
- **Pneumatic / hydraulic manifolds** — different physics, but the same "here's a block with N ports at known positions" shape.

None of these are in the current release because they'd need their own carrier-type enum values and their own validation rules, and v0.4.0 already had a large scope. They're tracked under "Planned" in [CHANGELOG.md](../CHANGELOG.md).

## UX features deferred

- **Per-face mounting (front + rear positions)** — today a `Mount` has a single `offset_x_mm`/`offset_y_mm` + geometry, and the whole layout renders on whichever face(s) the host `Device` is drawn on. Real cabinets often have **different stuff on the front and rear of the same shelf**: an industrial switch mounted on the front rail, PSUs or fuse blocks on a rear rail, or line cards in the front of a modular chassis with cooling modules in the rear. Need a `Mount.face` field (or a per-`Placement` face override) plus SVG renderer logic that draws different layouts depending on which face the parent rack elevation is painting. Also affects the `is_full_depth` decision: a cabinet with distinct front + rear mount layouts is naturally full-depth. See `seed: mark front-only DeviceTypes as is_full_depth=False` (commit 88bc44a) for the v0.4.0 workaround.
- **Nested SVG recursion** — a hosted device's own interior rendered inline inside its rectangle on the parent mount. Think "click into an MCC bucket from the cabinet view and see the DIN rail inside, with its contactors and auxiliary relays rendered in place." Visual equivalent of the existing rack-elevation monkey-patch but pointed inward. Beautiful feature, wants its own release cycle.
- **Okabe-Ito colorblind-safe palette** and a monochrome/pattern fallback for print. The v0.4.0 high-contrast mode (`@media (prefers-contrast: more)`) handles the substation-sunlight case but not colorblindness explicitly. Deferred until a user speaks up.
- **Drag-to-place UI** in the Placement form. v0.4.0 ships an HTMX-driven dynamic form with compatibility-filtered dropdowns and click-to-add from empty slots; drag-and-drop is a further step.
- **Auto-provisioning Mounts from existing DeviceBay/ModuleBay templates** on a DeviceType — a one-click path from "I have a DeviceType with 8 ModuleBays" to "and here's a Mount with 8 slots ready to receive placements."
- **GraphQL** — v0.4.0 ships minimal read-only DRF serializers (only because NetBox's detail templates require them for autocomplete). GraphQL support for full plugin object graphs is a deferred item.

## What is NOT on the roadmap, ever

- **Environmental / certification metadata** (IP, NEMA, Ex, temperature, RF shielding, EMP/HEMP, SIL, seismic, fire, impact, etc.) — handled via NetBox custom fields on `dcim.rack` and `dcim.devicetype`. See [certification-ratings.md](certification-ratings.md) for the recommended baseline. The plugin will not grow first-class fields for these.
- **Standard 19″ patch panel cabling** — already handled by NetBox core (front/rear port tracking). The plugin doesn't need to duplicate it.
- **A parallel "Cabinet" model** separate from `dcim.Device` — a cabinet is a device with `hosts_mounts=True` on its profile, and that's the whole architectural decision. See [architecture.md](architecture.md) for why.
