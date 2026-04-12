#!/usr/bin/env python3
"""
Fetch a rack elevation SVG from a running NetBox instance and flatten
every embedded cabinet-layout ``<image>`` into an inlined nested
``<svg>`` element, so the resulting file is self-contained and renders
correctly on github.com / README.md / any other static viewer.

Why this exists
---------------
NetBox's core rack elevation emits ``<image href="/dcim/devices/N/
cabinet-layout/svg/?...">`` pointing at the plugin's SVG endpoint (via
the ``RackElevationSVG`` monkey-patch this plugin installs). Those
hrefs only resolve against a live NetBox server. When the SVG is
committed to the repo as a doc screenshot and rendered by GitHub,
GitHub can't fetch sub-resources from localhost, so the cabinet
interiors never appear - the viewer sees empty coloured U slots
instead of the rails + mounts + modules the plugin is supposed to
show off.

What this tool does
-------------------
1. Fetch the rack elevation SVG from ``/api/dcim/racks/<N>/elevation/
   ?face=<front|rear>&render=svg``
2. For every ``<image xlink:href="/dcim/devices/<pk>/cabinet-layout/
   svg/?...">``, fetch the referenced sub-SVG with the same query
   params.
3. Rewrite class names in both the sub-SVG's ``<defs><style>`` block
   and the elements that use them with a unique ``-dev<pk>-`` prefix,
   so CSS rules from different embedded cabinets don't collide when
   they all live in the same outer document.
4. Replace the ``<image>`` element with a nested ``<svg>`` carrying
   the sub-SVG's contents, positioned at the ``<image>``'s x/y/width/
   height and using the sub-SVG's viewBox with
   ``preserveAspectRatio='xMidYMid meet'``.
5. Strip the whole-document background fill from the sub-SVG's style
   block so the rack elevation's own background shows through.
6. Fold the prefixed ``<style>`` contents into the outer ``<defs>``,
   so CSS scoping actually works (SVG does NOT scope ``<style>``
   inside nested ``<svg>``).
7. Write the flattened result to ``docs/screenshots/rack-<face>.svg``.

Usage
-----
    python3 tools/flatten_rack_svg.py

Prereqs:
- The dev NetBox stack is running on http://localhost:7543
- You can log in with admin/admin
- The ``cabinetview_seed`` command has been run so there are actual
  scenarios to render

Re-run this any time the seed data changes or the SVG renderer
changes in a way that affects the rendered output, then commit the
regenerated files.
"""
import re
import sys
import urllib.parse
import urllib.request
import http.cookiejar


NETBOX_URL = 'http://localhost:7543'
RACK_PK = 2  # Test Rack A
USER = 'admin'
PASSWORD = 'admin'
OUT_DIR = 'docs/screenshots'


def login(session):
    """Perform the CSRF-protected session login dance and return the opener."""
    req = urllib.request.Request(f'{NETBOX_URL}/login/')
    with session.open(req) as r:
        body = r.read().decode()
    m = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', body)
    if not m:
        raise RuntimeError('could not find csrfmiddlewaretoken on /login/')
    csrf = m.group(1)

    data = urllib.parse.urlencode({
        'csrfmiddlewaretoken': csrf,
        'username': USER,
        'password': PASSWORD,
        'next': '/',
    }).encode()
    req = urllib.request.Request(
        f'{NETBOX_URL}/login/',
        data=data,
        headers={'Referer': f'{NETBOX_URL}/login/'},
    )
    with session.open(req) as r:
        r.read()


def fetch(session, path):
    """Fetch `path` relative to NETBOX_URL, return body as str."""
    req = urllib.request.Request(f'{NETBOX_URL}{path}')
    with session.open(req) as r:
        return r.read().decode()


def fetch_bytes(session, path):
    """Fetch `path` relative to NETBOX_URL, return raw bytes."""
    req = urllib.request.Request(f'{NETBOX_URL}{path}')
    with session.open(req) as r:
        return r.read()


# ---------------------------------------------------------------------------
# SVG surgery
# ---------------------------------------------------------------------------

# Matches one <image ...> self-closing element that references a
# cabinet-layout/svg URL. Captures: full tag, x, y, width, height,
# and the href query string we can fetch directly.
IMAGE_RE = re.compile(
    r'<image\b[^>]*?'
    r'(?:xlink:href|href)="((?:/dcim/devices/\d+/cabinet-layout/svg/)[^"]*)"'
    r'[^>]*?/>'
)

# Helpers to extract attrs from a matched <image> tag.
_ATTR_RE_CACHE = {}
def get_attr(tag, name):
    rx = _ATTR_RE_CACHE.get(name)
    if rx is None:
        rx = re.compile(rf'\b{re.escape(name)}="([^"]*)"')
        _ATTR_RE_CACHE[name] = rx
    m = rx.search(tag)
    return m.group(1) if m else None


def parse_sub_svg(sub_body: str, dev_pk: int):
    """
    Return (viewbox, prefixed_style_css, inner_body) for a cabinet-
    layout sub-SVG. The outer ``<svg>`` wrapper is stripped; the CDATA
    style block is pulled out, prefixed with ``-devN-`` on every class
    name, and returned separately so the caller can fold it into the
    outer document's ``<defs>``.
    """
    # Extract viewBox off the outer <svg>.
    m = re.search(r'<svg\b[^>]*\bviewBox="([^"]+)"', sub_body)
    viewbox = m.group(1) if m else '0 0 100 100'

    # Extract and strip just the <style>...</style> element. The
    # enclosing <defs> also contains <clipPath> elements emitted by
    # svgwrite which we want to keep in the inlined output, so we
    # can't just strip the whole <defs>.
    style_m = re.search(
        r'<style[^>]*>\s*<!\[CDATA\[(.*?)\]\]>\s*</style>',
        sub_body, re.DOTALL,
    )
    css = style_m.group(1) if style_m else ''
    sub_body = sub_body.replace(style_m.group(0), '', 1) if style_m else sub_body

    # Drop the .svg-bg rule so the outer rack elevation's background
    # shows through the U slot instead of a solid dark-mode fill.
    # Do this both in the default block and inside the @media
    # (prefers-color-scheme: dark) block.
    css = re.sub(r'\.svg-bg\s*\{[^}]*\}', '', css)

    # Strip the outer <svg> wrapper, leaving just the inner elements.
    inner = re.sub(r'^.*?<svg\b[^>]*>', '', sub_body, count=1, flags=re.DOTALL)
    inner = re.sub(r'</svg>\s*$', '', inner, count=1, flags=re.DOTALL)

    # Prefix all CSS class selectors AND class attributes in the inner
    # body so sibling cabinet embeds don't cross-contaminate.
    prefix = f'd{dev_pk}-'

    # Collect all class names actually used in the CSS.
    class_names = set(re.findall(r'\.([A-Za-z][\w-]*)', css))

    # Rewrite CSS: `.foo` -> `.d<pk>-foo`
    def _css_sub(match):
        name = match.group(1)
        return f'.{prefix}{name}'
    prefixed_css = re.sub(r'\.([A-Za-z][\w-]*)', _css_sub, css)

    # Rewrite element class attributes: class="foo bar" -> class="d<pk>-foo d<pk>-bar"
    # Only rewrite class names that actually appear in the CSS so we
    # don't touch class attributes that aren't styled (there shouldn't
    # be any, but safer).
    def _elem_class_sub(match):
        raw = match.group(1)
        parts = raw.split()
        new = []
        for p in parts:
            if p in class_names:
                new.append(f'{prefix}{p}')
            else:
                new.append(p)
        return f'class="{" ".join(new)}"'
    inner = re.sub(r'class="([^"]*)"', _elem_class_sub, inner)

    # Namespace clipPath IDs (and any other element IDs) with a
    # dev-pk prefix so sibling embeds in the same outer document
    # don't collide. Two passes:
    #   1. id="clip-foo" -> id="d<pk>-clip-foo"
    #   2. clip-path="url(#clip-foo)" -> clip-path="url(#d<pk>-clip-foo)"
    inner = re.sub(
        r'\bid="([^"]*)"',
        lambda m: f'id="d{dev_pk}-{m.group(1)}"',
        inner,
    )
    inner = re.sub(
        r'\bclip-path="url\(#([^)]*)\)"',
        lambda m: f'clip-path="url(#d{dev_pk}-{m.group(1)})"',
        inner,
    )

    return viewbox, prefixed_css, inner


def flatten(session, face: str) -> str:
    """Return the flattened rack elevation SVG for `face` as a str."""
    rack_svg = fetch(
        session,
        f'/api/dcim/racks/{RACK_PK}/elevation/?face={face}&render=svg',
    )
    # Strip any absolute-URL prefixes so the committed file stays portable.
    rack_svg = rack_svg.replace(f'{NETBOX_URL}/', '/')

    all_css = []
    replacements = []

    for m in IMAGE_RE.finditer(rack_svg):
        tag = m.group(0)
        href = m.group(1)
        # Only inline hrefs that point at our cabinet-layout endpoint.
        if '/cabinet-layout/svg/' not in href:
            continue

        x = get_attr(tag, 'x') or '0'
        y = get_attr(tag, 'y') or '0'
        w = get_attr(tag, 'width') or '0'
        h = get_attr(tag, 'height') or '0'

        pk_match = re.search(r'/dcim/devices/(\d+)/', href)
        if not pk_match:
            continue
        dev_pk = int(pk_match.group(1))

        sub_body = fetch(session, href)
        sub_body = sub_body.replace(f'{NETBOX_URL}/', '/')
        viewbox, css, inner = parse_sub_svg(sub_body, dev_pk)
        all_css.append(css)

        # Build the replacement: a nested <svg> with its own viewBox.
        replacement = (
            f'<svg x="{x}" y="{y}" width="{w}" height="{h}" '
            f'viewBox="{viewbox}" preserveAspectRatio="xMidYMid meet" '
            f'overflow="hidden">{inner}</svg>'
        )
        replacements.append((tag, replacement))

    # Apply replacements (one at a time — classes are unique so
    # ``str.replace(..., count=1)`` is fine).
    out = rack_svg
    for old, new in replacements:
        out = out.replace(old, new, 1)

    # v0.6.1: Also inline any /media/ image refs as base64 data URIs.
    # These are module/device front_image files that the cabinet SVGs
    # reference. Without inlining, GitHub can't render them.
    import base64
    MEDIA_IMAGE_RE = re.compile(
        r'(?:xlink:href|href)="(/media/[^"]+\.(?:svg|png|jpg|jpeg|gif))"'
    )
    media_matches = list(MEDIA_IMAGE_RE.finditer(out))
    inlined_count = 0
    for m in media_matches:
        media_path = m.group(1)
        try:
            img_bytes = fetch_bytes(session, media_path)
            if media_path.endswith('.svg'):
                data_uri = 'data:image/svg+xml;base64,' + base64.b64encode(img_bytes).decode()
            elif media_path.endswith('.png'):
                data_uri = 'data:image/png;base64,' + base64.b64encode(img_bytes).decode()
            else:
                data_uri = 'data:image/jpeg;base64,' + base64.b64encode(img_bytes).decode()
            out = out.replace(media_path, data_uri, 1)
            inlined_count += 1
        except Exception:
            pass  # skip unresolvable images
    if inlined_count:
        print(f'  inlined {inlined_count} media image(s) as base64 data URIs')

    # Fold the collected inner-SVG CSS into the outer rack <defs>.
    if all_css:
        combined = '\n'.join(all_css)
        # The rack SVG already has a <defs>...<style>...</style>...</defs>
        # block at the top. Inject our combined CSS just before </style>.
        out = re.sub(
            r'(<style[^>]*>\s*<!\[CDATA\[)',
            r'\1\n' + combined + '\n',
            out,
            count=1,
        )

    return out


def main():
    cj = http.cookiejar.CookieJar()
    session = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj)
    )
    login(session)

    for face in ('front', 'rear'):
        print(f'flattening {face} face...')
        flat = flatten(session, face)
        out_path = f'{OUT_DIR}/rack-{face}.svg'
        with open(out_path, 'w') as f:
            f.write(flat)
        print(f'  wrote {out_path} ({len(flat):,} bytes)')

    print('done.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
