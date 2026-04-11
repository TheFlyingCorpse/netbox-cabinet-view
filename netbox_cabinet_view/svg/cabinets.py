"""
SVG renderer for cabinet layouts.

Mirrors the structure and image-embedding pattern of
``netbox/dcim/svg/racks.py`` — same svgwrite primitives, same Hyperlink →
Rect → (optional Image) composition, same fallback chain when an image is
absent.
"""

from dataclasses import dataclass

import svgwrite
from django.conf import settings
from svgwrite.container import Hyperlink
from svgwrite.image import Image
from svgwrite.masking import ClipPath
from svgwrite.shapes import Rect
from svgwrite.text import Text

from utilities.html import foreground_color


def _fit_label(text: str, width_px: float, font_size: int = 11) -> str:
    """
    Return a version of ``text`` that fits horizontally in ``width_px``.

    Rough char-width heuristic — same approximation the core rack renderer
    uses (``truncate_text`` in dcim/svg/racks.py). Returns '' when the box
    is too narrow to show even a single character plus an ellipsis.
    """
    if not text:
        return ''
    char_w = font_size * 0.6
    # Leave ~2 px of padding on each side.
    usable = max(0.0, width_px - 4)
    max_chars = int(usable / char_w)
    if max_chars <= 0:
        return ''
    if max_chars >= len(text):
        return text
    if max_chars < 2:
        return ''
    return text[: max_chars - 1] + '…'

from ..choices import CarrierTypeChoices, OrientationChoices


# SVG scale factor — 1 mm of carrier geometry = this many SVG pixels.
# Overridable via PLUGINS_CONFIG['netbox_cabinet_view']['MM_TO_PX'].
DEFAULT_MM_TO_PX = 2

# Padding around the drawing, in px.
DRAWING_PADDING = 20

# How tall a DIN rail is drawn, in px (visual only — the rail has no real height).
DIN_RAIL_PX = 14

# Busbar visual thickness, in px.
BUSBAR_PX = 24

# Subrack visual height when the host has no internal_height_mm, in px.
SUBRACK_DEFAULT_HEIGHT_PX = 120

# Minimum drawing dimensions.
MIN_WIDTH_PX = 400
MIN_HEIGHT_PX = 120


@dataclass
class MountTarget:
    """Resolved render data for a single Mount, independent of backing FK type."""
    name: str
    image: object        # Django FieldFile or None
    url: str             # absolute-ish URL for the hyperlink
    color: str           # hex color without leading '#', or ''
    description: str
    empty: bool = False  # True for unpopulated device/module bays


class CabinetLayoutSVG:
    """
    Render the interior layout of a host device as an SVG drawing.

    Parameters
    ----------
    host_device : dcim.models.Device
        The carrier-hosting device.
    user : django.contrib.auth.models.AbstractUser | None
        Used to filter mounts by view permission.
    base_url : str
        Absolute URL prefix for image hrefs (e.g. ``https://netbox.example.com``).
    include_images : bool
        If False, only colored rectangles are drawn (useful for debugging).
    """

    def __init__(self, host_device, user=None, base_url='', include_images=True,
                 fit_width=None, fit_height=None):
        self.host_device = host_device
        self.user = user
        self.base_url = base_url.rstrip('/') if base_url else ''
        self.include_images = include_images
        # Optional target display dimensions. When both are set, the outer
        # <svg> root is emitted at these pixel dimensions with a viewBox at
        # the drawing's natural size and `preserveAspectRatio="xMidYMid meet"`,
        # letterboxing the layout inside the target. This is how the rack
        # elevation patch requests a "fit into this U slot" rendering.
        self.fit_width = fit_width
        self.fit_height = fit_height

        plugin_settings = getattr(settings, 'PLUGINS_CONFIG', {}).get('netbox_cabinet_view', {})
        self.mm_to_px = plugin_settings.get('MM_TO_PX', DEFAULT_MM_TO_PX)

        self.profile = getattr(host_device.device_type, 'cabinet_profile', None)

        self.carriers = list(
            host_device.cabinet_carriers.all().prefetch_related(
                'mounts__device__device_type',
                'mounts__device__role',
                'mounts__device_bay__installed_device__device_type',
                'mounts__device_bay__installed_device__role',
                'mounts__module_bay__installed_module__module_type',
                'mounts__module_bay__device__role',
            )
        )

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def _mm(self, mm) -> float:
        return float(mm or 0) * self.mm_to_px

    def _drawing_size(self):
        """Compute outer drawing dimensions."""
        if self.profile and self.profile.internal_width_mm and self.profile.internal_height_mm:
            w = self._mm(self.profile.internal_width_mm)
            h = self._mm(self.profile.internal_height_mm)
        else:
            # No outer frame — fit the bounding box of all carriers.
            max_x = 0.0
            max_y = 0.0
            for carrier in self.carriers:
                cw, ch = self._carrier_extent_mm(carrier)
                max_x = max(max_x, carrier.offset_x_mm + cw)
                max_y = max(max_y, carrier.offset_y_mm + ch)
            w = self._mm(max_x)
            h = self._mm(max_y)

        w = max(w + 2 * DRAWING_PADDING, MIN_WIDTH_PX)
        h = max(h + 2 * DRAWING_PADDING, MIN_HEIGHT_PX)
        return w, h

    def _carrier_extent_mm(self, carrier):
        """Return (width_mm, height_mm) a carrier occupies visually."""
        if carrier.is_two_d:
            return (carrier.width_mm or 0, carrier.height_mm or 0)

        length = carrier.length_mm or 0
        # 1D carriers get a nominal visual height.
        if carrier.carrier_type == CarrierTypeChoices.TYPE_BUSBAR:
            thickness_mm = BUSBAR_PX / self.mm_to_px
        elif carrier.carrier_type == CarrierTypeChoices.TYPE_SUBRACK:
            thickness_mm = SUBRACK_DEFAULT_HEIGHT_PX / self.mm_to_px
        else:  # DIN rail
            thickness_mm = DIN_RAIL_PX / self.mm_to_px

        if carrier.orientation == OrientationChoices.VERTICAL:
            return (thickness_mm, length)
        return (length, thickness_mm)

    def _carrier_origin_px(self, carrier):
        """Top-left SVG px coordinates of a carrier within the drawing."""
        return (
            DRAWING_PADDING + self._mm(carrier.offset_x_mm),
            DRAWING_PADDING + self._mm(carrier.offset_y_mm),
        )

    # ------------------------------------------------------------------
    # Target resolution
    # ------------------------------------------------------------------

    def _resolve_target(self, mount) -> MountTarget:
        if mount.device_id:
            dev = mount.device
            return MountTarget(
                name=dev.name or str(dev.device_type),
                image=(dev.device_type.front_image if self.include_images else None) or None,
                url=dev.get_absolute_url(),
                color=getattr(dev.role, 'color', '') or '',
                description=self._device_description(dev),
            )

        if mount.device_bay_id:
            bay = mount.device_bay
            child = bay.installed_device
            if child is None:
                return MountTarget(
                    name=f'(empty) {bay.name}',
                    image=None,
                    url=bay.get_absolute_url(),
                    color='',
                    description=f'Empty device bay: {bay.name}',
                    empty=True,
                )
            return MountTarget(
                name=child.name or str(child.device_type),
                image=(child.device_type.front_image if self.include_images else None) or None,
                url=child.get_absolute_url(),
                color=getattr(child.role, 'color', '') or '',
                description=self._device_description(child),
            )

        if mount.module_bay_id:
            bay = mount.module_bay
            module = getattr(bay, 'installed_module', None)
            parent = bay.device
            parent_color = getattr(parent.role, 'color', '') or '' if parent else ''
            if module is None:
                return MountTarget(
                    name=f'(empty) {bay.name}',
                    image=None,
                    url=bay.get_absolute_url(),
                    color='',
                    description=f'Empty module bay: {bay.name}',
                    empty=True,
                )
            mt = module.module_type
            # ModuleType in NetBox 4.5 does not expose a front_image field,
            # so we use getattr() with a None fallback. When/if a later NetBox
            # version adds one, this picks it up automatically.
            mt_image = getattr(mt, 'front_image', None) if self.include_images else None
            return MountTarget(
                name=str(mt),
                image=mt_image or None,
                url=module.get_absolute_url(),
                color=parent_color,
                description=f'{mt} in {bay.name}',
            )

        return MountTarget(name='?', image=None, url='#', color='', description='Unresolved mount')

    @staticmethod
    def _device_description(device):
        bits = [f'Name: {device.name}']
        if device.role_id:
            bits.append(f'Role: {device.role}')
        bits.append(f'Type: {device.device_type}')
        if device.asset_tag:
            bits.append(f'Asset: {device.asset_tag}')
        return '\n'.join(bits)

    # ------------------------------------------------------------------
    # Mount geometry (1D / 2D)
    # ------------------------------------------------------------------

    def _mount_box_px(self, mount, carrier):
        """
        Return ((x, y), (w, h)) in SVG px for a mount on the given carrier.
        """
        ox, oy = self._carrier_origin_px(carrier)

        if carrier.is_two_d:
            return (
                (ox + self._mm(mount.position_x), oy + self._mm(mount.position_y)),
                (self._mm(mount.size_x), self._mm(mount.size_y)),
            )

        # 1D
        start_mm = (mount.position - 1) * carrier.mm_per_unit if mount.position else 0
        size_mm = (mount.size or 1) * carrier.mm_per_unit

        if carrier.carrier_type == CarrierTypeChoices.TYPE_BUSBAR:
            thickness_px = BUSBAR_PX
        elif carrier.carrier_type == CarrierTypeChoices.TYPE_SUBRACK:
            # Let the mount visually occupy most of the subrack height.
            thickness_px = SUBRACK_DEFAULT_HEIGHT_PX - 8
        else:  # DIN rail
            thickness_px = 70  # typical DIN module height ~90 mm — give it real presence

        if carrier.orientation == OrientationChoices.VERTICAL:
            # y axis runs along the rail
            x_center = ox + (DIN_RAIL_PX / 2 if carrier.carrier_type == CarrierTypeChoices.TYPE_DIN_RAIL
                             else 0)
            return (
                (x_center - thickness_px / 2, oy + self._mm(start_mm)),
                (thickness_px, self._mm(size_mm)),
            )
        # horizontal
        y_center = oy + (DIN_RAIL_PX / 2 if carrier.carrier_type == CarrierTypeChoices.TYPE_DIN_RAIL
                         else BUSBAR_PX / 2 if carrier.carrier_type == CarrierTypeChoices.TYPE_BUSBAR
                         else SUBRACK_DEFAULT_HEIGHT_PX / 2)
        return (
            (ox + self._mm(start_mm), y_center - thickness_px / 2),
            (self._mm(size_mm), thickness_px),
        )

    # ------------------------------------------------------------------
    # Drawing primitives
    # ------------------------------------------------------------------

    def _setup_drawing(self):
        width, height = self._drawing_size()
        if self.fit_width and self.fit_height:
            # Render at natural size internally (viewBox), but tell the
            # browser to display the SVG at the caller-supplied dimensions
            # with `xMidYMid meet` so the layout keeps its aspect ratio and
            # any spare space gets letterboxed with the theme background.
            dwg = svgwrite.Drawing(size=(self.fit_width, self.fit_height))
            dwg.viewbox(width=width, height=height)
            dwg['preserveAspectRatio'] = 'xMidYMid meet'
        else:
            dwg = svgwrite.Drawing(size=(width, height))
            dwg.viewbox(width=width, height=height)
        dwg.defs.add(dwg.style(_EMBEDDED_CSS))

        # Theme-aware background rect. This is painted as the very first
        # element so it sits under every carrier / mount. Styled via CSS
        # (`rect.svg-bg`) so it flips colour for light/dark automatically.
        dwg.add(Rect(insert=(0, 0), size=(width, height), class_='svg-bg'))
        return dwg, width, height

    def _draw_host_outline(self, dwg, width, height):
        if not self.profile or not self.profile.internal_width_mm or not self.profile.internal_height_mm:
            return
        outline = Rect(
            insert=(DRAWING_PADDING, DRAWING_PADDING),
            size=(self._mm(self.profile.internal_width_mm), self._mm(self.profile.internal_height_mm)),
            class_='cabinet-outline',
        )
        dwg.add(outline)

        # Label with the host device name — placed ABOVE the outline so it
        # never collides with carriers or mounts inside the enclosure.
        label = Text(
            self.host_device.name or str(self.host_device.device_type),
            insert=(DRAWING_PADDING + 2, DRAWING_PADDING - 5),
            class_='cabinet-label',
        )
        dwg.add(label)

    def _draw_carrier(self, dwg, carrier):
        ox, oy = self._carrier_origin_px(carrier)
        ctype = carrier.carrier_type

        if ctype == CarrierTypeChoices.TYPE_MOUNTING_PLATE:
            cw = self._mm(carrier.width_mm or 0)
            ch = self._mm(carrier.height_mm or 0)
            rect = Rect(
                insert=(ox, oy),
                size=(cw, ch),
                class_='carrier mounting-plate',
            )
            dwg.add(rect)
            self._draw_carrier_label(dwg, carrier, ox, oy, cw, ch)
            return

        length_px = self._mm(carrier.length_mm or 0)

        if carrier.orientation == OrientationChoices.VERTICAL:
            width_px = {
                CarrierTypeChoices.TYPE_DIN_RAIL: DIN_RAIL_PX,
                CarrierTypeChoices.TYPE_SUBRACK:  SUBRACK_DEFAULT_HEIGHT_PX,
                CarrierTypeChoices.TYPE_BUSBAR:   BUSBAR_PX,
            }[ctype]
            cw, ch = width_px, length_px
        else:
            height_px = {
                CarrierTypeChoices.TYPE_DIN_RAIL: DIN_RAIL_PX,
                CarrierTypeChoices.TYPE_SUBRACK:  SUBRACK_DEFAULT_HEIGHT_PX,
                CarrierTypeChoices.TYPE_BUSBAR:   BUSBAR_PX,
            }[ctype]
            cw, ch = length_px, height_px

        rect = Rect(
            insert=(ox, oy),
            size=(cw, ch),
            class_=f'carrier {ctype.replace("_", "-")}',
        )
        dwg.add(rect)
        self._draw_carrier_label(dwg, carrier, ox, oy, cw, ch)

    def _draw_carrier_label(self, dwg, carrier, ox, oy, cw, ch):
        """
        Position the carrier name label so it never crosses the cabinet
        outline border and never overlaps the host-name label above the
        outline.

        Strategy, in order:
        1. If there is >= 18 px of clear space above the carrier AND that
           space is also below the top of the outline (so the label can sit
           *inside* the cabinet, between outline border and carrier top),
           draw it there.
        2. Otherwise, if the carrier visual has enough internal height
           (>= 18 px), draw the label inside the carrier's top-left corner,
           clipped to the carrier rectangle.
        3. Otherwise (thin DIN rail / busbar pressed against the outline
           top), suppress the label — the carrier name is still visible in
           the Carriers table underneath the SVG.
        """
        label_offset_px = 14  # text baseline distance from the anchor edge

        # Space above this carrier that is inside the outline.
        space_above = oy - DRAWING_PADDING

        if space_above >= 18:
            # Plenty of room above the carrier but below the outline top.
            dwg.add(Text(
                carrier.name,
                insert=(ox + 4, oy - 4),
                class_='carrier-label',
            ))
            return

        if ch >= 18:
            # Room inside the carrier — put the label top-left, clipped so
            # it can't spill over the carrier rect.
            clip_id = f'clip-carrier-{carrier.pk or id(carrier)}-lbl'
            clip = ClipPath(id_=clip_id)
            clip.add(Rect(insert=(ox, oy), size=(cw, ch)))
            dwg.defs.add(clip)
            dwg.add(Text(
                carrier.name,
                insert=(ox + 4, oy + label_offset_px),
                clip_path=f'url(#{clip_id})',
                class_='carrier-label',
            ))
            return

        # Too thin to label safely — suppress. The Carriers table under the
        # SVG still lists the name, so nothing is actually lost.

    def _draw_mount(self, dwg, carrier, mount):
        target = self._resolve_target(mount)
        (x, y), (w, h) = self._mount_box_px(mount, carrier)

        href = (f'{self.base_url}{target.url}') if target.url.startswith('/') else target.url
        link = Hyperlink(href=href, target='_parent')
        link.set_desc(target.description)

        color = target.color or '999999'
        text_color = f'#{foreground_color(color)}' if color else '#000000'

        # Per-mount clipPath — every label/image is hard-clipped to the
        # mount's bounding box so narrow carriers never show overflowing
        # text or stray pixels from images.
        clip_id = f'clip-mount-{mount.pk or id(mount)}'
        clip = ClipPath(id_=clip_id)
        clip.add(Rect(insert=(x, y), size=(w, h)))
        dwg.defs.add(clip)
        clip_ref = f'url(#{clip_id})'

        label_text = _fit_label(target.name, w)
        text_center = (x + w / 2, y + h / 2)

        if target.empty:
            link.add(Rect(insert=(x, y), size=(w, h), class_='slot empty'))
            if label_text:
                link.add(Text(
                    label_text,
                    insert=text_center,
                    text_anchor='middle',
                    dominant_baseline='central',
                    clip_path=clip_ref,
                    class_='label empty',
                ))
            dwg.add(link)
            return

        link.add(Rect(
            insert=(x, y),
            size=(w, h),
            style=f'fill: #{color}',
            class_='slot',
        ))

        if self.include_images and target.image:
            try:
                url = target.image.url
            except ValueError:
                url = ''
            if url:
                if url.startswith('/'):
                    url = f'{self.base_url}{url}'
                img = Image(
                    href=url, insert=(x, y), size=(w, h),
                    class_='device-image',
                    clip_path=clip_ref,
                )
                img.fit(scale='slice')
                link.add(img)
                if label_text:
                    # Outlined label for readability on top of the image.
                    link.add(Text(
                        label_text,
                        insert=text_center,
                        text_anchor='middle',
                        dominant_baseline='central',
                        stroke='black',
                        stroke_width='0.2em',
                        stroke_linejoin='round',
                        clip_path=clip_ref,
                        class_='device-image-label',
                    ))
                    link.add(Text(
                        label_text,
                        insert=text_center,
                        text_anchor='middle',
                        dominant_baseline='central',
                        fill='white',
                        clip_path=clip_ref,
                        class_='device-image-label',
                    ))
                dwg.add(link)
                return

        # No image — draw a plain label on the colored rect (if it fits).
        if label_text:
            link.add(Text(
                label_text,
                insert=text_center,
                text_anchor='middle',
                dominant_baseline='central',
                fill=text_color,
                clip_path=clip_ref,
                class_='label',
            ))
        dwg.add(link)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def render(self) -> str:
        dwg, width, height = self._setup_drawing()
        self._draw_host_outline(dwg, width, height)
        for carrier in self.carriers:
            self._draw_carrier(dwg, carrier)
            mounts = carrier.mounts.all()
            if self.user is not None:
                mounts = mounts.restrict(self.user, 'view')
            for mount in mounts:
                self._draw_mount(dwg, carrier, mount)
        return dwg.tostring()


# Stylesheet inlined into the SVG. The SVG is loaded via <object> so it renders
# in its own document context — `prefers-color-scheme` flips the palette
# automatically when NetBox is in dark mode.
_EMBEDDED_CSS = """
/* Light theme (default) */
.svg-bg { fill: #f8f9fc; }
.cabinet-outline { fill: none; stroke: #8a8f9a; stroke-width: 2; stroke-dasharray: 4 3; }
.cabinet-label   { font: 600 13px sans-serif; fill: #555; }

.carrier { stroke: #333; stroke-width: 1; }
.carrier.din-rail       { fill: #c0c7d1; }
.carrier.subrack        { fill: #e3ebf1; stroke: #456; }
.carrier.mounting-plate { fill: #f7f6ef; stroke: #a99; stroke-dasharray: 6 3; }
.carrier.busbar         { fill: #c47a2c; stroke: #6a3c10; stroke-width: 1.5; }
.carrier-label          { font: 500 11px sans-serif; fill: #444; }

.slot        { stroke: #222; stroke-width: 0.6; }
.slot.empty  { fill: none; stroke: #aaa; stroke-dasharray: 3 2; }
.label       { font: 500 11px sans-serif; pointer-events: none; fill: #111; }
.label.empty { fill: #888; font-style: italic; }
.device-image-label { font: 600 11px sans-serif; pointer-events: none; }

/* Dark theme — follows NetBox's Bootstrap dark mode via prefers-color-scheme,
 * which the embedding page propagates to <object> documents. */
@media (prefers-color-scheme: dark) {
  .svg-bg          { fill: #141619; }
  .cabinet-outline { stroke: #6c7078; }
  .cabinet-label   { fill: #c8ccd4; }

  .carrier                { stroke: #9aa2ad; }
  .carrier.din-rail       { fill: #4b5460; }
  .carrier.subrack        { fill: #3b4451; stroke: #7a8696; }
  .carrier.mounting-plate { fill: #2a2a26; stroke: #8a7a74; }
  .carrier.busbar         { fill: #a0661f; stroke: #f5b06a; }
  .carrier-label          { fill: #c8ccd4; }

  .slot        { stroke: #101114; }
  .slot.empty  { fill: none; stroke: #5a6070; }
  .label       { fill: #f3f3f3; }
  .label.empty { fill: #7a8696; }
}
"""
