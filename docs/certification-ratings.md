# Environmental & certification ratings — use NetBox custom fields

This plugin's job is **geometric visualization** of what's inside a physical enclosure. Textual certification attributes (IP rating, Ex rating, temperature range, RF shielding, EMP/HEMP hardening, SIL rating, seismic zone, fire rating, etc.) are a different axis — they're not about where things are, they're about what the enclosure or equipment is certified to withstand. These belong in NetBox's first-class **custom fields** system, not in the plugin's models.

To add them, go to NetBox → Customization → Custom Fields → Add and create fields on the `dcim.rack` and/or `dcim.devicetype` content types. A reasonable baseline covering most industrial / utility / telco / ISP use cases:

| Field | Type | Example | Applies to | Category |
|---|---|---|---|---|
| `ip_rating` | Text | `IP54` | Rack + DeviceType | Ingress protection (IEC 60529) |
| `nema_rating` | Text | `NEMA 4X` | Rack + DeviceType | Ingress protection (North America) |
| `operating_temp_min_c` / `_max_c` | Integer | `-40` / `70` | DeviceType | Thermal operating range |
| `ex_rating` | Text | `II 2 G Ex d IIB T4 Gb` | Rack + DeviceType | Hazardous area (ATEX / IECEx) |
| `nec_class_division` | Text | `Class I Div 1 Group D` | Rack + DeviceType | Hazardous area (NEC, North America) |
| `emc_class` | Selection | `Class A` / `Class B` | DeviceType | EMC emissions (CISPR 22 / FCC Part 15) |
| `surge_withstand_kv` | Decimal | `4.0` | DeviceType | Transient immunity (IEC 61000-4-5) |
| `rf_shielding_db` | Integer | `80` | Rack + DeviceType | RF shielding effectiveness at frequency |
| `tempest_zone` | Selection | `Zone 0` / `1` / `2` / `3` | Rack + DeviceType | TEMPEST emanation security |
| `hemp_protected` | Boolean | `true` | Rack + DeviceType | HEMP hardening (IEC 61000-5-10 / MIL-STD-188-125) |
| `fire_rating` | Text | `UL 94 V-0` or `FR60` | Rack + DeviceType | Flame retardance |
| `seismic_zone` | Text | `Bellcore GR-63 Zone 4` | Rack | Seismic qualification |
| `vibration_grade` | Text | `IEC 60068-2-6 Fc` | DeviceType | Vibration withstand |
| `ik_rating` | Text | `IK10` | Rack + DeviceType | Mechanical impact (IEC 62262) |
| `sccr_ka` | Integer | `65` | DeviceType | Short-circuit current rating |
| `sil_rating` | Selection | `SIL 1` / `2` / `3` / `4` | DeviceType | Functional safety (IEC 61508/61511) |
| `pl_rating` | Selection | `PLa`…`PLe` | DeviceType | Machine safety (ISO 13849) |
| `certifications` | Text (multiline) | `CE, UKCA, UL, CSA, IEC 61439, IEC 61850, EN 50155` | Rack + DeviceType | Regulatory / compliance |

**Recommended split:** put the ratings on **Rack** when you care about "as-installed" (an individual rack might have been modified in the field) and on **DeviceType** when you maintain a device-type library with design-value ratings. NetBox custom fields don't inherit, so if you want both, fill in both — or pick the one your workflow actually queries. For most ISP / OT / utility operators, **Rack is the more load-bearing location** because that's where field modifications happen.

## Why these aren't first-class plugin fields

Adding them would:

1. **Duplicate NetBox's built-in custom-fields system** — which already handles everything in the table above.
2. **Commit the plugin to maintaining a taxonomy of every rating scheme across every region** — and every region has its own local variants of IP / NEMA / Ex / fire / seismic standards, most of which update on a rolling basis.
3. **Dilute the "this is a geometry plugin" narrative** without giving operators anything they can't already do in the NetBox UI in 30 seconds.

Custom fields also give you free filtering, search, sort, and bulk-edit support — which the plugin would have to re-implement for its own first-class fields. The cost/benefit is firmly on the "use what NetBox already provides" side.
