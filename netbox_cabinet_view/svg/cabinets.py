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
from django.urls import NoReverseMatch, reverse
from svgwrite.container import Hyperlink
from svgwrite.image import Image
from svgwrite.masking import ClipPath
from svgwrite.shapes import Rect
from svgwrite.text import Text

from utilities.html import foreground_color

from ..choices import MountTypeChoices, OrientationChoices


class _RawSVGElement:
    """
    Wrapper that satisfies svgwrite's ``Drawing.add()`` interface
    (which requires a ``get_xml()`` method returning an ElementTree
    element) for raw XML strings. Used by Feature 2 (v0.5.0) to
    embed a pre-rendered nested SVG string into the parent drawing
    without parsing it through svgwrite's object model.
    """

    __slots__ = ('_xml_str',)

    def __init__(self, xml_str):
        self._xml_str = xml_str

    def get_xml(self):
        from xml.etree.ElementTree import fromstring
        return fromstring(self._xml_str)


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


# SVG scale factor — 1 mm of mount geometry = this many SVG pixels.
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
class PlacementTarget:
    """Resolved render data for a single Placement, independent of backing FK type."""
    name: str
    image: object        # Django FieldFile or None
    url: str             # absolute-ish URL for the hyperlink
    color: str           # hex color without leading '#', or ''
    description: str
    empty: bool = False  # True for unpopulated device/module bays
    # Feature 2 (v0.5.0): nested SVG recursion.
    hosts_mounts: bool = False   # True if the resolved device itself hosts mounts
    resolved_device: object = None  # The Device that is itself a mount-host (for recursion)


@dataclass
class _PlacementStub:
    """
    Duck-typed Placement used by ``_draw_empty_slots_*``.

    ``_placement_box_px`` reads a small set of fields off its
    placement argument; this dataclass exposes exactly those fields
    without needing a DB row. Used to reuse the existing geometry
    code when drawing click-to-add affordances over empty slot ranges
    for Finding C (v0.4.0).
    """
    mount: object
    position: object
    size: object
    row: object
    row_span: object
    position_x: object
    position_y: object
    size_x: object
    size_y: object


class CabinetLayoutSVG:
    """
    Render the interior layout of a host device as an SVG drawing.

    Parameters
    ----------
    host_device : dcim.models.Device
        The mount-hosting device.
    user : django.contrib.auth.models.AbstractUser | None
        Used to filter placements by view permission.
    base_url : str
        Absolute URL prefix for image hrefs (e.g. ``https://netbox.example.com``).
    include_images : bool
        If False, only colored rectangles are drawn (useful for debugging).
    """

    # Feature 2 (v0.5.0): max nesting depth for recursive cabinet-in-
    # cabinet rendering. 3 levels covers the deepest real-world OT/ICS
    # case: MCC cabinet → withdrawable bucket → DIN rail → (device
    # that itself hosts something).
    MAX_NESTING_DEPTH = 3

    def __init__(self, host_device, user=None, base_url='', include_images=True,
                 fit_width=None, fit_height=None, thumbnail=False, face=None,
                 _depth=0, _visited=None,
                 mount_only_pk=None, highlight=None):
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
        # Finding E (v0.4.0): when True, the root <svg> element gets a
        # `thumbnail` class so the embedded CSS can paint everything at
        # reduced opacity, suppress labels, and desaturate role colours.
        # Used by the rack elevation patch so the inline-embedded cabinet
        # interior reads as "preview — zoom in to interact" instead of
        # pretending each module is a live click target.
        self.thumbnail = thumbnail
        # Feature 1 (v0.5.0): per-face filtering. When set to 'front' or
        # 'rear', only mounts with face=='' (both) or face==face_value are
        # included. Used by the rack elevation patch so front-face rendering
        # only draws front-face mounts, and rear only draws rear mounts.
        self.face = face
        # Feature 2 (v0.5.0): recursion depth tracking. The top-level
        # renderer has _depth=0. Each nested renderer increments by 1.
        # Rendering stops when _depth >= MAX_NESTING_DEPTH.
        self._depth = _depth
        self._visited = _visited if _visited is not None else set()
        self._visited.add(host_device.pk)

        plugin_settings = getattr(settings, 'PLUGINS_CONFIG', {}).get('netbox_cabinet_view', {})
        self.mm_to_px = plugin_settings.get('MM_TO_PX', DEFAULT_MM_TO_PX)

        self.profile = getattr(host_device.device_type, 'cabinet_profile', None)

        mounts_qs = host_device.cabinet_mounts.all().prefetch_related(
            'placements__device__device_type',
            'placements__device__role',
            'placements__device_bay__installed_device__device_type',
            'placements__device_bay__installed_device__role',
            'placements__module_bay__installed_module__module_type',
            'placements__module_bay__device__role',
        )
        # Feature 1: filter mounts by face when requested.
        if face:
            from django.db.models import Q
            mounts_qs = mounts_qs.filter(Q(face='') | Q(face=face))
        # Feature 6: filter to a single mount for preview rendering.
        if mount_only_pk:
            mounts_qs = mounts_qs.filter(pk=mount_only_pk)
        self.mounts = list(mounts_qs)
        # Feature 6: highlight dict for the live preview chip.
        self.highlight = highlight

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
            # No outer frame — fit the bounding box of all mounts.
            max_x = 0.0
            max_y = 0.0
            for mount in self.mounts:
                cw, ch = self._mount_extent_mm(mount)
                max_x = max(max_x, mount.offset_x_mm + cw)
                max_y = max(max_y, mount.offset_y_mm + ch)
            w = self._mm(max_x)
            h = self._mm(max_y)

        w = max(w + 2 * DRAWING_PADDING, MIN_WIDTH_PX)
        h = max(h + 2 * DRAWING_PADDING, MIN_HEIGHT_PX)
        return w, h

    def _mount_extent_mm(self, mount):
        """Return (width_mm, height_mm) a mount occupies visually."""
        if mount.is_two_d:
            return (mount.width_mm or 0, mount.height_mm or 0)

        if mount.is_grid:
            # Grid: rows × (row_height × rows) perpendicular to length_mm.
            length = mount.length_mm or 0
            rows = max(1, mount.rows or 1)
            row_h = mount.row_height_mm or 0
            perp = rows * row_h
            if mount.orientation == OrientationChoices.VERTICAL:
                # Rows sit side-by-side along x; mount's length runs down y.
                return (perp, length)
            # Horizontal: rows stack along y; mount's length runs across x.
            return (length, perp)

        length = mount.length_mm or 0
        # 1D mounts get a nominal visual height.
        thickness_mm = self._mount_visual_width_px(mount) / self.mm_to_px

        if mount.orientation == OrientationChoices.VERTICAL:
            return (thickness_mm, length)
        return (length, thickness_mm)

    def _mount_origin_px(self, mount):
        """Top-left SVG px coordinates of a mount within the drawing."""
        return (
            DRAWING_PADDING + self._mm(mount.offset_x_mm),
            DRAWING_PADDING + self._mm(mount.offset_y_mm),
        )

    # ------------------------------------------------------------------
    # Target resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _is_mount_host(device):
        """Return True if the device itself hosts cabinet mounts."""
        if device is None:
            return False
        profile = getattr(device.device_type, 'cabinet_profile', None)
        return bool(profile and profile.hosts_mounts and device.cabinet_mounts.exists())

    def _resolve_target(self, placement) -> PlacementTarget:
        if placement.device_id:
            dev = placement.device
            return PlacementTarget(
                name=dev.name or str(dev.device_type),
                image=(dev.device_type.front_image if self.include_images else None) or None,
                url=dev.get_absolute_url(),
                color=getattr(dev.role, 'color', '') or '',
                description=self._device_description(dev),
                hosts_mounts=self._is_mount_host(dev),
                resolved_device=dev,
            )

        if placement.device_bay_id:
            bay = placement.device_bay
            child = bay.installed_device
            if child is None:
                return PlacementTarget(
                    name=f'(empty) {bay.name}',
                    image=None,
                    url=bay.get_absolute_url(),
                    color='',
                    description=f'Empty device bay: {bay.name}',
                    empty=True,
                )
            return PlacementTarget(
                name=child.name or str(child.device_type),
                image=(child.device_type.front_image if self.include_images else None) or None,
                url=child.get_absolute_url(),
                color=getattr(child.role, 'color', '') or '',
                description=self._device_description(child),
                hosts_mounts=self._is_mount_host(child),
                resolved_device=child,
            )

        if placement.module_bay_id:
            bay = placement.module_bay
            module = getattr(bay, 'installed_module', None)
            parent = bay.device
            parent_color = getattr(parent.role, 'color', '') or '' if parent else ''
            if module is None:
                return PlacementTarget(
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
            return PlacementTarget(
                name=str(mt),
                image=mt_image or None,
                url=module.get_absolute_url(),
                color=parent_color,
                description=f'{mt} in {bay.name}',
            )

        return PlacementTarget(name='?', image=None, url='#', color='', description='Unresolved placement')

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
    # Placement geometry (1D / 2D / grid)
    # ------------------------------------------------------------------

    def _mount_visual_width_px(self, mount):
        """
        Thickness in px of a single-row 1D mount drawn perpendicular to
        its axis (rail line, busbar, subrack body, or grid row). For a
        horizontal mount this is its height; for a vertical one, its
        width. Used to center placements on the mount regardless of orientation.
        """
        ctype = mount.mount_type
        if ctype == MountTypeChoices.TYPE_DIN_RAIL:
            return DIN_RAIL_PX
        if ctype == MountTypeChoices.TYPE_BUSBAR:
            return BUSBAR_PX
        if ctype == MountTypeChoices.TYPE_SUBRACK:
            return SUBRACK_DEFAULT_HEIGHT_PX
        if ctype == MountTypeChoices.TYPE_GRID:
            # Grid row strip thickness = row_height_mm in px, capped
            # at a minimum of DIN_RAIL_PX so very thin rows still
            # render visibly. This fixes the ODF bug where 14px strips
            # were much thinner than the 44px row_height, causing
            # placements to overflow.
            return max(DIN_RAIL_PX, self._mm(mount.row_height_mm or 0))
        return DIN_RAIL_PX

    def _placement_visual_thickness_px(self, mount):
        """
        Thickness in px of a placement (how much it protrudes from its
        mount perpendicular to the mount's axis). Larger than the mount's
        own line so placements "overhang" the rail visually.
        """
        ctype = mount.mount_type
        if ctype == MountTypeChoices.TYPE_BUSBAR:
            return BUSBAR_PX
        if ctype == MountTypeChoices.TYPE_SUBRACK:
            # Let the placement visually occupy most of the subrack height.
            return SUBRACK_DEFAULT_HEIGHT_PX - 8
        if ctype == MountTypeChoices.TYPE_GRID:
            # Placement fills the row_height minus a small gap so the
            # row strip border is still visible. Fixes the ODF bug
            # where fixed 56px placements overflowed 44px rows and
            # extended outside the cabinet outline.
            row_h_px = self._mm(mount.row_height_mm or 0)
            return max(DIN_RAIL_PX, row_h_px - 4)
        # DIN rail
        return 70  # typical DIN module height ~90 mm — give it real presence

    def _row_origin_px(self, mount, row: int):
        """
        Return the (x, y) SVG px origin of one row of a grid mount, or of
        a single-row 1D mount. Row numbering is 1-indexed.

        For horizontal grids, rows stack vertically with `row_height_mm` spacing.
        For vertical grids, rows sit side-by-side along the x-axis, same spacing.
        """
        ox, oy = self._mount_origin_px(mount)
        if mount.mount_type != MountTypeChoices.TYPE_GRID:
            return (ox, oy)
        step = self._mm(mount.row_height_mm or 0)
        offset = max(0, row - 1) * step
        if mount.orientation == OrientationChoices.VERTICAL:
            return (ox + offset, oy)
        return (ox, oy + offset)

    def _placement_box_px(self, placement, mount):
        """
        Return ((x, y), (w, h)) in SVG px for a placement on the given mount.
        Handles 1D (din_rail / subrack / busbar), 2D (mounting_plate), and
        grid (1-N rows of slotted strips).
        """
        if mount.is_two_d:
            ox, oy = self._mount_origin_px(mount)
            return (
                (ox + self._mm(placement.position_x), oy + self._mm(placement.position_y)),
                (self._mm(placement.size_x), self._mm(placement.size_y)),
            )

        # 1D or grid — compute (start, length) along the mount's axis,
        # then thicken perpendicular to it.
        start_units = (placement.position - 1) if placement.position else 0
        start_mm = start_units * mount.mm_per_unit
        size_mm = (placement.size or 1) * mount.mm_per_unit

        placement_thickness = self._placement_visual_thickness_px(mount)
        mount_width = self._mount_visual_width_px(mount)

        if mount.is_grid:
            # A placement in a grid sits in a specific row, and may span
            # multiple rows (row_span). Find the origin of the first row
            # and extend thickness across the spanned rows.
            base_x, base_y = self._row_origin_px(mount, placement.row or 1)
            row_span = max(1, placement.row_span or 1)
            if row_span > 1:
                step = self._mm(mount.row_height_mm or 0)
                span_thickness = (row_span - 1) * step + placement_thickness
            else:
                span_thickness = placement_thickness

            if mount.orientation == OrientationChoices.VERTICAL:
                # Rows run side by side along x; placement extends down along y.
                x_center = base_x + mount_width / 2
                x = x_center - placement_thickness / 2
                # If multi-row, stretch the box to cover all spanned rows.
                if row_span > 1:
                    step = self._mm(mount.row_height_mm or 0)
                    x = base_x + mount_width / 2 - placement_thickness / 2
                    return (
                        (x, base_y + self._mm(start_mm)),
                        (span_thickness, self._mm(size_mm)),
                    )
                return (
                    (x, base_y + self._mm(start_mm)),
                    (placement_thickness, self._mm(size_mm)),
                )
            # horizontal grid: rows stack along y; placement extends right along x.
            y_center = base_y + mount_width / 2
            y = y_center - placement_thickness / 2
            if row_span > 1:
                y = base_y + mount_width / 2 - placement_thickness / 2
                return (
                    (base_x + self._mm(start_mm), y),
                    (self._mm(size_mm), span_thickness),
                )
            return (
                (base_x + self._mm(start_mm), y),
                (self._mm(size_mm), placement_thickness),
            )

        # Plain 1D mount
        ox, oy = self._mount_origin_px(mount)
        if mount.orientation == OrientationChoices.VERTICAL:
            x_center = ox + mount_width / 2
            return (
                (x_center - placement_thickness / 2, oy + self._mm(start_mm)),
                (placement_thickness, self._mm(size_mm)),
            )
        # horizontal
        y_center = oy + mount_width / 2
        return (
            (ox + self._mm(start_mm), y_center - placement_thickness / 2),
            (self._mm(size_mm), placement_thickness),
        )

    # ------------------------------------------------------------------
    # Drawing primitives
    # ------------------------------------------------------------------

    def _setup_drawing(self):
        width, height = self._drawing_size()
        # debug=False disables svgwrite's attribute allow-list, so we
        # can emit HTML5 `data-*` attributes on the 2D click-anywhere
        # rect without svgwrite throwing ValueError. svgwrite's
        # validation doesn't know about data-* attrs because they're
        # an HTML thing, not a core SVG thing, even though they're
        # standards-compliant on any SVG element.
        if self.fit_width and self.fit_height:
            # Render at natural size internally (viewBox), but tell the
            # browser to display the SVG at the caller-supplied dimensions
            # with `xMidYMid meet` so the layout keeps its aspect ratio and
            # any spare space gets letterboxed with the theme background.
            dwg = svgwrite.Drawing(size=(self.fit_width, self.fit_height), debug=False)
            dwg.viewbox(width=width, height=height)
            dwg['preserveAspectRatio'] = 'xMidYMid meet'
        else:
            dwg = svgwrite.Drawing(size=(width, height), debug=False)
            dwg.viewbox(width=width, height=height)

        # Finding E (v0.4.0): expose self.thumbnail on the root <svg>
        # element so the embedded stylesheet's `svg.thumbnail` rules
        # take effect.
        if self.thumbnail:
            dwg['class'] = 'thumbnail'

        dwg.defs.add(dwg.style(_EMBEDDED_CSS))

        # Theme-aware background rect. This is painted as the very first
        # element so it sits under every mount / placement. Styled via CSS
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
        # never collides with mounts or placements inside the enclosure.
        label = Text(
            self.host_device.name or str(self.host_device.device_type),
            insert=(DRAWING_PADDING + 2, DRAWING_PADDING - 5),
            class_='cabinet-label',
        )
        dwg.add(label)

    def _draw_mount(self, dwg, mount):
        """
        Draw the mount's geometry (rail/plate/grid strips). The mount's
        label is drawn separately in a second pass by `_label_mount()`
        so it sits on top of the placement rectangles instead of hiding
        behind them (Finding A, v0.4.0).

        Returns ``(ox, oy, cw, ch)`` — the coordinates/extent the label
        pass needs to compute where the label should sit.
        """
        ox, oy = self._mount_origin_px(mount)
        ctype = mount.mount_type

        if ctype == MountTypeChoices.TYPE_MOUNTING_PLATE:
            cw = self._mm(mount.width_mm or 0)
            ch = self._mm(mount.height_mm or 0)
            dwg.add(Rect(
                insert=(ox, oy),
                size=(cw, ch),
                class_='mount mounting-plate',
            ))
            return (ox, oy, cw, ch)

        # Grid: draw one strip per row. Each strip is a DIN-rail-style rect
        # anchored at that row's origin (see _row_origin_px).
        if mount.is_grid:
            rows = max(1, mount.rows or 1)
            length_px = self._mm(mount.length_mm or 0)
            strip_thickness = self._mount_visual_width_px(mount)
            # Compute the full grid bounding box for the label helper.
            full_perp_mm = rows * (mount.row_height_mm or 0)
            full_perp_px = self._mm(full_perp_mm)
            if mount.orientation == OrientationChoices.VERTICAL:
                grid_w_px, grid_h_px = full_perp_px, length_px
            else:
                grid_w_px, grid_h_px = length_px, full_perp_px

            for r in range(1, rows + 1):
                row_x, row_y = self._row_origin_px(mount, r)
                if mount.orientation == OrientationChoices.VERTICAL:
                    dwg.add(Rect(
                        insert=(row_x, row_y),
                        size=(strip_thickness, length_px),
                        class_='mount grid grid-row',
                    ))
                else:
                    dwg.add(Rect(
                        insert=(row_x, row_y),
                        size=(length_px, strip_thickness),
                        class_='mount grid grid-row',
                    ))
            return (ox, oy, grid_w_px, grid_h_px)

        length_px = self._mm(mount.length_mm or 0)
        thickness_px = self._mount_visual_width_px(mount)

        if mount.orientation == OrientationChoices.VERTICAL:
            cw, ch = thickness_px, length_px
        else:
            cw, ch = length_px, thickness_px

        dwg.add(Rect(
            insert=(ox, oy),
            size=(cw, ch),
            class_=f'mount {ctype.replace("_", "-")}',
        ))
        return (ox, oy, cw, ch)

    def _draw_mount_label(self, dwg, mount, ox, oy, cw, ch):
        """
        Position the mount name label so it never crosses the cabinet
        outline border and never overlaps the host-name label above the
        outline.

        Strategy, in order:
        1. If there is >= 18 px of clear space above the mount AND that
           space is also below the top of the outline (so the label can sit
           *inside* the cabinet, between outline border and mount top),
           draw it there.
        2. Otherwise, if the mount visual has enough internal height
           (>= 18 px), draw the label inside the mount's top-left corner,
           clipped to the mount rectangle.
        3. Otherwise (thin DIN rail / busbar pressed against the outline
           top), suppress the label — the mount name is still visible in
           the Mounts table underneath the SVG.
        """
        label_offset_px = 14  # text baseline distance from the anchor edge

        # Space above this mount that is inside the outline.
        space_above = oy - DRAWING_PADDING

        if space_above >= 18:
            # Plenty of room above the mount but below the outline top.
            dwg.add(Text(
                mount.name,
                insert=(ox + 4, oy - 4),
                class_='mount-label',
            ))
            return

        if ch >= 18:
            # Room inside the mount — put the label top-left, clipped so
            # it can't spill over the mount rect.
            clip_id = f'clip-mount-{mount.pk or id(mount)}-lbl'
            clip = ClipPath(id_=clip_id)
            clip.add(Rect(insert=(ox, oy), size=(cw, ch)))
            dwg.defs.add(clip)
            dwg.add(Text(
                mount.name,
                insert=(ox + 4, oy + label_offset_px),
                clip_path=f'url(#{clip_id})',
                class_='mount-label',
            ))
            return

        # Too thin to label safely — suppress. The Mounts table under the
        # SVG still lists the name, so nothing is actually lost.

    def _draw_placement(self, dwg, mount, placement):
        target = self._resolve_target(placement)
        (x, y), (w, h) = self._placement_box_px(placement, mount)

        # Feature 2 (v0.5.0): nested SVG recursion. If the placed device
        # is itself a mount-host with actual placements AND we haven't
        # exceeded the nesting depth AND the device isn't already in
        # our visited-hosts chain (circular-reference guard), render its
        # interior inline as a miniature cabinet layout inside this
        # placement's rectangle.
        if (
            target.hosts_mounts
            and not self.thumbnail
            and self._depth < self.MAX_NESTING_DEPTH
            and target.resolved_device.pk not in self._visited
        ):
            try:
                nested = CabinetLayoutSVG(
                    host_device=target.resolved_device,
                    user=self.user,
                    base_url=self.base_url,
                    include_images=False,     # no images in nested views
                    fit_width=int(w),
                    fit_height=int(h),
                    thumbnail=True,           # visual diminishment
                    face=self.face,
                    _depth=self._depth + 1,
                    _visited=set(self._visited),  # copy to avoid cross-branch pollution
                )
                nested_svg = nested.render()
                # Embed as a nested <svg> element inside the parent drawing,
                # positioned at this placement's bounding box.
                import re as _re
                # Extract the viewBox from the nested SVG.
                vb_m = _re.search(r'viewBox="([^"]+)"', nested_svg)
                vb = vb_m.group(1) if vb_m else f'0 0 {int(w)} {int(h)}'
                # Strip the outer <svg>...</svg> wrapper.
                inner = _re.sub(r'^.*?<svg\b[^>]*>', '', nested_svg, count=1, flags=_re.DOTALL)
                inner = _re.sub(r'</svg>\s*$', '', inner, count=1, flags=_re.DOTALL)
                # Namespace clipPath IDs to avoid collision with the parent.
                dev_pk = target.resolved_device.pk
                prefix = f'n{self._depth + 1}-d{dev_pk}-'
                inner = _re.sub(
                    r'\bid="([^"]*)"',
                    lambda m: f'id="{prefix}{m.group(1)}"',
                    inner,
                )
                inner = _re.sub(
                    r'\bclip-path="url\(#([^)]*)\)"',
                    lambda m: f'clip-path="url(#{prefix}{m.group(1)})"',
                    inner,
                )
                # Build the nested <svg> element manually as raw XML.
                # Must declare xlink namespace because the inner SVG
                # may contain xlink:href attributes on <image> and
                # <a> elements (svgwrite emits these for compatibility).
                nested_tag = (
                    f'<svg x="{x}" y="{y}" width="{w}" height="{h}" '
                    f'viewBox="{vb}" preserveAspectRatio="xMidYMid meet" '
                    f'overflow="hidden" '
                    f'xmlns="http://www.w3.org/2000/svg" '
                    f'xmlns:xlink="http://www.w3.org/1999/xlink" '
                    f'xmlns:ev="http://www.w3.org/2001/xml-events">'
                    f'{inner}</svg>'
                )
                # svgwrite's Drawing.add() requires objects with a
                # get_xml() method; raw ET elements don't have it.
                # _RawSVGElement wraps the XML string to satisfy the
                # interface.
                dwg.add(_RawSVGElement(nested_tag))
                return  # skip the normal image/label drawing
            except Exception:
                pass  # fall through to normal rendering on any error

        href = (f'{self.base_url}{target.url}') if target.url.startswith('/') else target.url
        link = Hyperlink(href=href, target='_parent')
        link.set_desc(target.description)

        color = target.color or '999999'
        text_color = f'#{foreground_color(color)}' if color else '#000000'

        # Per-placement clipPath — every label/image is hard-clipped to the
        # placement's bounding box so narrow mounts never show overflowing
        # text or stray pixels from images.
        clip_id = f'clip-placement-{placement.pk or id(placement)}'
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
    # Finding C (v0.4.0): inline add-placement affordance.
    #
    # Every unoccupied range of slot positions on a 1D or grid mount
    # gets wrapped in an <a> whose href opens the PlacementForm with
    # `mount=<pk>&position=<start>` (and `&row=<row>` for grid rows)
    # pre-filled. 2D mounting plates get a single transparent rect
    # covering the plate area, tagged with data-mount-pk so the Layout
    # tab template can attach a click handler that computes (pos_x,
    # pos_y) in mm and navigates.
    #
    # Skipped entirely in thumbnail mode - the rack elevation embed
    # does not participate in click-to-add because its hyperlinks
    # aren't routable through the parent rack-elevation <image>
    # wrapper.
    # ------------------------------------------------------------------

    def _placement_add_url(self, **params) -> str:
        """
        Return the URL for the PlacementForm with GET params pre-filled.
        Falls back to '#' if the URL namespace is not yet registered
        (e.g. during Django system checks before ready()).
        """
        try:
            base = reverse('plugins:netbox_cabinet_view:placement_add')
        except NoReverseMatch:
            return '#'
        if params:
            qs = '&'.join(f'{k}={v}' for k, v in params.items() if v is not None)
            return f'{base}?{qs}' if qs else base
        return base

    @staticmethod
    def _empty_ranges_1d(occupied, capacity):
        """
        Return a list of ``(start, end)`` tuples (both inclusive,
        1-indexed) for runs of empty slots in ``1..capacity`` given a
        set of occupied positions. Example::

            occupied = {1, 2, 3, 8, 9, 10}
            capacity = 12
            result   = [(4, 7), (11, 12)]
        """
        ranges = []
        start = None
        for pos in range(1, capacity + 1):
            if pos not in occupied:
                if start is None:
                    start = pos
            else:
                if start is not None:
                    ranges.append((start, pos - 1))
                    start = None
        if start is not None:
            ranges.append((start, capacity))
        return ranges

    def _draw_empty_slots_1d(self, dwg, mount):
        """
        For a 1D mount (din_rail / subrack / busbar), wrap each empty
        range of slot positions in an `<a>` with a dashed rect.
        """
        capacity = mount.capacity_units
        if capacity <= 0:
            return
        occupied = set()
        for p in mount.placements.all():
            if p.position is None or p.size is None:
                continue
            occupied.update(range(p.position, p.position + p.size))

        for start, end in self._empty_ranges_1d(occupied, capacity):
            # Build a synthetic placement with the empty range's
            # geometry so we can reuse _placement_box_px().
            stub = _PlacementStub(
                mount=mount, position=start, size=end - start + 1,
                row=None, row_span=None,
                position_x=None, position_y=None, size_x=None, size_y=None,
            )
            (x, y), (w, h) = self._placement_box_px(stub, mount)
            href = self._placement_add_url(mount=mount.pk, position=start)
            link = Hyperlink(href=href, target='_parent')
            link.set_desc(f'Add placement at position {start}')
            link.add(Rect(
                insert=(x, y), size=(w, h),
                class_='slot empty-slot',
            ))
            dwg.add(link)

    def _draw_empty_slots_grid(self, dwg, mount):
        """
        For a grid mount, compute empty ranges row by row and wrap each
        in an `<a>` — so users can drop a placement into "row 2, cols 5-8".
        """
        capacity = mount.capacity_units
        rows = max(1, mount.rows or 1)
        if capacity <= 0:
            return

        # Build per-row occupancy from every placement's (row, row_span,
        # position, size) rectangle. row_span > 1 occupies multiple rows.
        per_row = {r: set() for r in range(1, rows + 1)}
        for p in mount.placements.all():
            if p.row is None or p.position is None or p.size is None:
                continue
            span = max(1, p.row_span or 1)
            for r in range(p.row, min(p.row + span, rows + 1)):
                per_row[r].update(range(p.position, p.position + p.size))

        for r, occupied in per_row.items():
            for start, end in self._empty_ranges_1d(occupied, capacity):
                stub = _PlacementStub(
                    mount=mount, position=start, size=end - start + 1,
                    row=r, row_span=1,
                    position_x=None, position_y=None, size_x=None, size_y=None,
                )
                (x, y), (w, h) = self._placement_box_px(stub, mount)
                href = self._placement_add_url(
                    mount=mount.pk, position=start, row=r,
                )
                link = Hyperlink(href=href, target='_parent')
                link.set_desc(f'Add placement at row {r}, position {start}')
                link.add(Rect(
                    insert=(x, y), size=(w, h),
                    class_='slot empty-slot',
                ))
                dwg.add(link)

    def _draw_empty_slots_2d(self, dwg, mount):
        """
        For a 2D mounting plate, emit a single transparent rect
        covering the whole plate area, tagged with ``data-mount-pk`` so
        the device_layout_tab.html template JS can attach a click
        handler that converts pointer coordinates to mm and navigates
        to the PlacementForm.
        """
        ox, oy = self._mount_origin_px(mount)
        cw = self._mm(mount.width_mm or 0)
        ch = self._mm(mount.height_mm or 0)
        if cw <= 0 or ch <= 0:
            return
        # debug=False bypasses svgwrite's attribute allow-list so we
        # can emit data-* attributes; they're HTML5 extensions and
        # aren't in svgwrite's SVG spec whitelist.
        rect = Rect(
            insert=(ox, oy), size=(cw, ch),
            class_='slot empty-slot mount-2d',
            debug=False,
        )
        rect['fill-opacity'] = 0  # visible only on hover via CSS
        rect['data-mount-pk'] = mount.pk
        # Scale factor embedded so the JS can recover mm from px.
        rect['data-mm-per-px'] = 1.0 / self.mm_to_px
        rect['data-origin-x'] = ox
        rect['data-origin-y'] = oy
        dwg.add(rect)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def render(self) -> str:
        """
        Multi-pass render:

        1. **Pass 1**: draw the mount geometry (rail/plate/grid) AND
           all of each mount's placements (device rectangles + images
           + per-placement labels) inside the mount's footprint.
        2. **Pass 2**: draw empty-slot click targets (Finding C,
           v0.4.0) — unoccupied slot ranges on 1D/grid mounts, plus a
           whole-plate transparent rect on 2D mounts for click-
           anywhere handling. Skipped in thumbnail mode.
        3. **Pass 3**: draw the mount NAME label on top of
           everything else (Finding A, v0.4.0). Previously the label
           was drawn inline inside ``_draw_mount`` before any
           placements, so thick 1D rails labeled inside the rail body
           (e.g. the 48-slot marshalling cabinet) had their "Terminal
           rail" text painted over by the terminal block placements.
           Splitting the passes lets the label sit visibly on top.

        The ``label`` text has ``pointer-events: none`` so it never
        blocks clicks on the placements or empty-slot links
        underneath it.
        """
        dwg, width, height = self._setup_drawing()
        self._draw_host_outline(dwg, width, height)

        # Pass 1: mount geometry + placements.
        mount_bounds = []
        for mount in self.mounts:
            bounds = self._draw_mount(dwg, mount)
            mount_bounds.append((mount, bounds))
            placements = mount.placements.all()
            if self.user is not None:
                placements = placements.restrict(self.user, 'view')
            for placement in placements:
                self._draw_placement(dwg, mount, placement)

        # Pass 2: empty-slot click targets (Finding C). Skipped in
        # thumbnail mode because the rack elevation <image> wrapper
        # swallows mount-level hyperlinks.
        if not self.thumbnail:
            for mount in self.mounts:
                if mount.is_one_d:
                    self._draw_empty_slots_1d(dwg, mount)
                elif mount.is_grid:
                    self._draw_empty_slots_grid(dwg, mount)
                elif mount.is_two_d:
                    self._draw_empty_slots_2d(dwg, mount)

        # Pass 3: mount labels, painted on top of every placement so
        # the text is always legible regardless of how dense the
        # mount is.
        for mount, (ox, oy, cw, ch) in mount_bounds:
            self._draw_mount_label(dwg, mount, ox, oy, cw, ch)

        # Pass 4 (Feature 6, v0.5.0): highlight overlay for the live
        # preview chip on the PlacementForm. Draws a green semi-
        # transparent dashed rectangle at the proposed position.
        if self.highlight and len(self.mounts) >= 1:
            mount = self.mounts[0]
            stub = _PlacementStub(
                mount=mount,
                position=self.highlight.get('position'),
                size=self.highlight.get('size', 1),
                row=self.highlight.get('row'),
                row_span=self.highlight.get('row_span', 1),
                position_x=self.highlight.get('position_x'),
                position_y=self.highlight.get('position_y'),
                size_x=self.highlight.get('size_x'),
                size_y=self.highlight.get('size_y'),
            )
            try:
                (hx, hy), (hw, hh) = self._placement_box_px(stub, mount)
                dwg.add(Rect(
                    insert=(hx, hy), size=(hw, hh),
                    class_='highlight-placement',
                ))
            except (TypeError, ValueError, ZeroDivisionError):
                pass  # invalid highlight params — skip silently

        return dwg.tostring()


# Stylesheet inlined into the SVG. The SVG is loaded via <object> so it renders
# in its own document context — `prefers-color-scheme` flips the palette
# automatically when NetBox is in dark mode.
_EMBEDDED_CSS = """
/* Light theme (default) */
.svg-bg { fill: #f8f9fc; }
.cabinet-outline { fill: none; stroke: #8a8f9a; stroke-width: 2; stroke-dasharray: 4 3; }
.cabinet-label   { font: 600 13px sans-serif; fill: #555; }

.mount { stroke: #333; stroke-width: 1; }
.mount.din-rail       { fill: #c0c7d1; }
.mount.subrack        { fill: #e3ebf1; stroke: #456; }
.mount.mounting-plate { fill: #f7f6ef; stroke: #a99; stroke-dasharray: 6 3; }
.mount.busbar         { fill: #c47a2c; stroke: #6a3c10; stroke-width: 1.5; }
.mount.grid.grid-row  { fill: #d8d5c4; stroke: #6a6655; }
.mount-label          { font: 500 11px sans-serif; fill: #444; }

.slot        { stroke: #222; stroke-width: 0.6; }
.slot.empty  { fill: none; stroke: #aaa; stroke-dasharray: 3 2; }
.label       { font: 500 11px sans-serif; pointer-events: none; fill: #111; }
.label.empty { fill: #888; font-style: italic; }
.device-image-label { font: 600 11px sans-serif; pointer-events: none; }

/* Feature 6 (v0.5.0): highlight overlay for the live preview chip
 * on the PlacementForm. Green dashed rectangle showing where the
 * proposed placement will land relative to existing placements.
 */
.highlight-placement {
  fill: #00c853;
  fill-opacity: 0.35;
  stroke: #00c853;
  stroke-width: 2;
  stroke-dasharray: 4 2;
  pointer-events: none;
}

/* Finding C (v0.4.0): click-to-add affordance over empty slot
 * ranges on 1D/grid mounts and the whole area of 2D mounts.
 * Nearly invisible at rest so it doesn't clutter the normal view;
 * reveals a dashed green outline on hover, matching the
 * "unclaimed / available" aesthetic from the B empty-state
 * canvas. Cursor switches to pointer so the affordance is
 * discoverable by accident.
 */
.slot.empty-slot {
  fill: rgba(129, 199, 132, 0.05);
  stroke: none;
  cursor: pointer;
}
a:hover > .slot.empty-slot,
.slot.empty-slot:hover {
  fill: rgba(129, 199, 132, 0.22);
  stroke: #81c784;
  stroke-width: 1.5;
  stroke-dasharray: 3 2;
}

/* Dark theme — follows NetBox's Bootstrap dark mode via prefers-color-scheme,
 * which the embedding page propagates to <object> documents. */
@media (prefers-color-scheme: dark) {
  .svg-bg          { fill: #141619; }
  .cabinet-outline { stroke: #6c7078; }
  .cabinet-label   { fill: #c8ccd4; }

  .mount                { stroke: #9aa2ad; }
  .mount.din-rail       { fill: #4b5460; }
  .mount.subrack        { fill: #3b4451; stroke: #7a8696; }
  .mount.mounting-plate { fill: #2a2a26; stroke: #8a7a74; }
  .mount.busbar         { fill: #a0661f; stroke: #f5b06a; }
  .mount.grid.grid-row  { fill: #454034; stroke: #a09777; }
  .mount-label          { fill: #c8ccd4; }

  .slot        { stroke: #101114; }
  .slot.empty  { fill: none; stroke: #5a6070; }
  .label       { fill: #f3f3f3; }
  .label.empty { fill: #7a8696; }

  /* Finding C empty-slot affordance, dark-mode contrast. */
  .slot.empty-slot         { fill: rgba(129, 199, 132, 0.08); }
  a:hover > .slot.empty-slot,
  .slot.empty-slot:hover   { fill: rgba(129, 199, 132, 0.3); stroke: #a5d6a7; }
}

/* Thumbnail mode — Finding E, v0.4.0.
 *
 * When CabinetLayoutSVG is constructed with `thumbnail=True`, the root
 * <svg> element gets `class="thumbnail"`. These rules then apply to
 * diminish the rendering so users understand it's a preview, not a
 * live click target.
 *
 * Used by the rack elevation monkey-patch so the embedded cabinet
 * interior inside a rack U slot reads as "zoom in via the Layout tab
 * to interact" instead of tempting users to click on individual
 * placement rectangles (whose hyperlinks are unreachable from inside
 * the core rack-elevation <image> wrapper anyway — clicking them
 * navigates to the HOST device, not the mounted one, and that's a
 * click-target lie).
 *
 * Strategy: drop contrast + opacity, suppress per-placement labels,
 * suppress the mount name label, kill the cabinet outline. The mount
 * geometry is still visible so users can read "here's the shape of
 * the interior" at a glance.
 */
svg.thumbnail .cabinet-outline,
svg.thumbnail .cabinet-label,
svg.thumbnail .mount-label,
svg.thumbnail .label,
svg.thumbnail .device-image-label,
svg.thumbnail .slot.empty-slot {
  display: none;
}
svg.thumbnail .mount,
svg.thumbnail .slot {
  opacity: 0.55;
  filter: saturate(0.6);
}

/* High-contrast mode — Finding F, v0.4.0.
 *
 * Triggers automatically when the OS asks for increased contrast:
 *
 *   * macOS:   System Settings → Accessibility → Display → Increase Contrast
 *   * Windows: Settings → Accessibility → Contrast themes
 *   * iOS/iPadOS: Settings → Accessibility → Display & Text Size → Increase Contrast
 *
 * Designed for OT/ICS field engineers using tablets in bright substation
 * sunlight where the default ~4.1:1 ratio washes out. All strokes go to
 * pure white on pure black, role colors get pulled to saturated primaries
 * at >= 8.5:1 contrast against the black background, and stroke widths
 * bump up one notch so nothing dissolves at glancing angles.
 *
 * CSS-only; no user preference plumbing, no extra runtime cost. Dark-mode
 * also-triggering (`prefers-color-scheme: dark`) falls through to these
 * rules if both media features match, because this block is declared
 * last and has equal specificity.
 */
@media (prefers-contrast: more) {
  .svg-bg          { fill: #000; }
  .cabinet-outline { stroke: #fff; stroke-width: 3; stroke-dasharray: 6 4; }
  .cabinet-label   { fill: #fff; font-weight: 700; }

  .mount                { stroke: #fff; stroke-width: 2; }
  .mount.din-rail       { fill: #3a5a8a; }
  .mount.subrack        { fill: #225566; }
  .mount.mounting-plate { fill: #553366; stroke-dasharray: 6 3; }
  .mount.busbar         { fill: #a04010; stroke-width: 2.5; }
  .mount.grid.grid-row  { fill: #554422; }
  .mount-label          { fill: #fff; font-weight: 700; }

  .slot        { stroke: #fff; stroke-width: 1; }
  .slot.empty  { fill: none; stroke: #bbb; stroke-width: 1; stroke-dasharray: 3 2; }
  .label       { fill: #fff; font-weight: 700; }
  .label.empty { fill: #bbb; }
  .device-image-label { fill: #fff; font-weight: 700; }
}
"""
