# Offline-first — zero runtime network dependencies

OT/ICS, air-gapped substation networks, segregated utility networks, shipboard systems, and classified facilities all need to run NetBox without any outbound internet access at all. This plugin is **fully offline-safe at runtime**:

- **No CDN references** in any template, stylesheet, or rendered SVG. Zero `<link>` or `<script>` tags pointing at `cdn.jsdelivr.net`, `cdnjs.cloudflare.com`, `fonts.googleapis.com`, `unpkg.com`, `bootstrapcdn.com` or similar.
- **No external font dependencies.** The embedded SVG stylesheet uses generic `font: ... sans-serif` declarations only — browsers resolve these against the local system font, never fetching Google Fonts or similar. No `@font-face`, no `@import url(https://…)`.
- **No runtime HTTP calls** from the plugin code. Everything the Layout tab renders comes from the local NetBox database. The `svgwrite` runtime dependency is a pure-Python SVG generator with no network calls.
- **All plugin assets bundled in the wheel.** The plugin's static CSS, templates, and SVG renderer are packaged inside the wheel under `netbox_cabinet_view/static/` and `netbox_cabinet_view/templates/`. No external asset resolution.
- **Committed `docs/screenshots/*.svg` use relative hrefs only** (`/dcim/devices/N/` rather than `http://…/dcim/devices/N/`). They're portable across any NetBox instance and don't leak the dev environment they were generated from.
- **The `RackElevationSVG` monkey-patch** embeds cabinet-layout SVG URLs at the **same origin** as the rack elevation itself (same NetBox host) — no cross-origin fetches.

The only network traffic this plugin generates at runtime is the browser fetching `/dcim/devices/<pk>/cabinet-layout/svg/?w=…&h=…&v=…` as a sub-resource of whichever NetBox page it's viewing, which is identical in scope to NetBox core fetching `/media/devicetype-images/…`. If NetBox works in your air gap, the plugin works in your air gap.

The one external reference in the entire repo is the **Mermaid schema diagram** in [`architecture.md`](architecture.md), which GitHub renders server-side when you view the doc on github.com. That's GitHub's rendering, not the plugin's runtime — the live plugin never touches Mermaid. Offline git clones of the repo show the diagram as a code block, which is still readable.
