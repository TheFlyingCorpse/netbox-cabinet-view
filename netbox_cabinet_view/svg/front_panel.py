"""
Standalone front-panel SVG renderer for non-host devices with port_map.

Renders the device's front_image at full size with port overlay pins
on top. Used when a device has a DeviceMountProfile with port_map but
no internal mounts (e.g. a 1U rack-mount switch).
"""
import fnmatch

import svgwrite
from django.conf import settings
from svgwrite.container import Hyperlink
from svgwrite.image import Image
from svgwrite.shapes import Rect
from svgwrite.text import Text

from .cabinets import _EMBEDDED_CSS


def render_front_panel(device, base_url='', theme=None):
    """
    Return an SVG string showing the device's front-panel image with
    port overlay pins.
    """
    profile = getattr(device.device_type, 'cabinet_profile', None)
    if not profile:
        return _empty_svg('No profile')

    port_map = profile.port_map or []
    if not port_map:
        return _empty_svg('No port_map')

    # Resolve the front-panel image URL.
    image_url = None
    dt_image = getattr(device.device_type, 'front_image', None)
    if dt_image:
        try:
            image_url = dt_image.url
        except ValueError:
            pass
    if not image_url and profile.front_image:
        try:
            image_url = profile.front_image.url
        except ValueError:
            pass

    # Determine dimensions from the SVG viewBox of the line-art,
    # or fall back to sensible defaults.
    # Use the device type's u_height to guess physical dimensions:
    # 1U = 44mm height, 19" = 483mm width.
    u_height = getattr(device.device_type, 'u_height', 1) or 1
    panel_w = 483  # 19" standard rack width in mm
    panel_h = u_height * 44  # mm per U

    plugin_cfg = getattr(settings, 'PLUGINS_CONFIG', {}).get('netbox_cabinet_view', {})
    mm_to_px = plugin_cfg.get('MM_TO_PX', 2)

    width = int(panel_w * mm_to_px)
    height = int(panel_h * mm_to_px)

    # Port overlay colours.
    default_colors = {
        'connected_enabled': '2ecc71',
        'connected_disabled': 'f39c12',
        'unconnected_enabled': '95a5a6',
        'unconnected_disabled': '7f8c8d',
    }
    port_colors = {**default_colors, **plugin_cfg.get('PORT_STATUS_COLORS', {})}

    # Build the SVG.
    dwg = svgwrite.Drawing(size=(width + 40, height + 40), debug=False)
    dwg.viewbox(width=width + 40, height=height + 40)

    classes = []
    if theme == 'dark':
        classes.append('dark')
    elif theme == 'light':
        classes.append('light')
    if classes:
        dwg['class'] = ' '.join(classes)

    dwg.defs.add(dwg.style(_EMBEDDED_CSS))

    # Background.
    dwg.add(Rect(insert=(0, 0), size=(width + 40, height + 40), class_='svg-bg'))

    # Device label.
    dwg.add(Text(
        device.name or str(device.device_type),
        insert=(22, 15),
        class_='cabinet-label',
    ))

    ox, oy = 20, 20  # padding
    pw, ph = width, height

    # Front-panel image.
    if image_url:
        if image_url.startswith('/'):
            image_url = f'{base_url}{image_url}'
        img = Image(href=image_url, insert=(ox, oy), size=(pw, ph))
        img.fit(scale='slice')
        dwg.add(img)

    # Collect components.
    components = {}
    for iface in device.interfaces.all():
        components[iface.name] = iface
    for fp in device.frontports.all():
        components[fp.name] = fp
    for rp in device.rearports.all():
        components[rp.name] = rp

    if not components:
        return dwg.tostring()

    def _mm(mm):
        return round(float(mm or 0) * mm_to_px, 1)

    def _port_color(component):
        connected = (
            getattr(component, 'cable_id', None) is not None
            or getattr(component, 'mark_connected', False)
        )
        enabled = getattr(component, 'enabled', True)
        key = f"{'connected' if connected else 'unconnected'}_{'enabled' if enabled else 'disabled'}"
        return port_colors.get(key, '95a5a6')

    # Draw port overlay.
    for entry in port_map:
        entry_type = entry.get('type')

        if entry_type == 'zone':
            pattern = entry.get('name_pattern', '')
            matched = sorted(n for n in components if fnmatch.fnmatch(n, pattern))
            edge = entry.get('edge', 'top')
            start = entry.get('start_mm', 0)
            pitch = entry.get('pitch_mm', 10)
            count = entry.get('count', 0)
            pin_w = entry.get('pin_width_mm', 3)
            pin_h = entry.get('pin_height_mm', 3)
            protrudes = entry.get('protrudes_mm', 0)

            for i in range(count):
                offset = start + i * pitch
                if edge == 'left':
                    px, py = ox - _mm(protrudes), oy + _mm(offset)
                elif edge == 'right':
                    px, py = ox + pw - _mm(pin_w) + _mm(protrudes), oy + _mm(offset)
                elif edge == 'top':
                    px, py = ox + _mm(offset), oy - _mm(protrudes)
                elif edge == 'bottom':
                    px, py = ox + _mm(offset), oy + ph - _mm(pin_h) + _mm(protrudes)
                else:
                    continue

                comp = components.get(matched[i]) if i < len(matched) else None
                color = _port_color(comp) if comp else port_colors.get('unconnected_disabled', '7f8c8d')

                rect = Rect(
                    insert=(px, py), size=(_mm(pin_w), _mm(pin_h)),
                    style=f'fill: #{color}',
                    class_='port-pin protruding' if protrudes else 'port-pin',
                )
                if comp:
                    url = comp.get_absolute_url()
                    if url and url.startswith('/'):
                        url = f'{base_url}{url}'
                    link = Hyperlink(href=url, target='_parent')
                    link.add(rect)
                    dwg.add(link)
                else:
                    dwg.add(rect)

        elif entry_type == 'pin':
            name = entry.get('name', '')
            comp = components.get(name)
            color = _port_color(comp) if comp else port_colors.get('unconnected_disabled', '7f8c8d')
            protrudes = entry.get('protrudes_mm', 0)

            rect = Rect(
                insert=(ox + _mm(entry.get('x_mm', 0)), oy + _mm(entry.get('y_mm', 0))),
                size=(_mm(entry.get('width_mm', 3)), _mm(entry.get('height_mm', 3))),
                style=f'fill: #{color}',
                class_='port-pin protruding' if protrudes else 'port-pin',
            )
            if comp:
                url = comp.get_absolute_url()
                if url and url.startswith('/'):
                    url = f'{base_url}{url}'
                link = Hyperlink(href=url, target='_parent')
                link.add(rect)
                dwg.add(link)
            else:
                dwg.add(rect)

    return dwg.tostring()


def _empty_svg(message):
    dwg = svgwrite.Drawing(size=(400, 60), debug=False)
    dwg.add(Text(message, insert=(10, 30),
                 style='font: 14px sans-serif; fill: #888;'))
    return dwg.tostring()
