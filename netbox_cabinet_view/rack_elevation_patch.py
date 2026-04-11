"""
Monkey-patch ``dcim.svg.racks.RackElevationSVG`` so that cabinet-host
devices render their cabinet layout SVG *inside* the rack elevation at
their U slot, instead of the stock DeviceType.front_image /
DeviceType.rear_image.

The core rack elevation does not expose a plugin hook for this — it
iterates a rack's devices and emits one ``<image>`` per device from
Python. The only practical seam is patching the ``draw_device_front``
and ``draw_device_rear`` methods at plugin ``ready()`` time.

Both front and rear faces are patched in v0.3.0+. The rear patch is
particularly important for ISPs running fibre patch panels and ODF
chassis where the *rear* face is where the interesting stuff is.

Design notes
============
* **Opt-out flag** — controlled by ``PLUGINS_CONFIG['netbox_cabinet_view']
  ['PATCH_RACK_ELEVATION']``. Defaults to ``True``. Flip to ``False`` if
  a NetBox upgrade breaks the patch.
* **1U fallback** — devices with ``u_height < 2`` fall through to the
  stock behaviour. A 230×22 px slot is too narrow to usefully show a
  cabinet layout, and real-world DIN shelves in a rack are always 2U+
  anyway (a DIN module with wire management needs ~90 mm = 2U).
* **Letterboxing** — for 2U+ devices we request the cabinet-layout SVG
  at the slot's exact pixel dimensions via ``?w=&h=``. The renderer
  emits an outer ``<svg>`` with ``preserveAspectRatio="xMidYMid meet"``
  so the layout keeps its natural aspect ratio and any spare strip
  above/below is filled with the theme background.
* **Cache-busting** — the URL gains a ``?v=<hash>`` query token derived
  from the device's carriers and mounts. When a Mount is added or
  moved, the hash changes, the URL changes, the browser refetches.
* **Idempotent** — ``install_patch`` tags each wrapper so re-entry (from
  Django autoreload) doesn't double-wrap.
* **Graceful degradation** — any exception during patch installation
  is logged at WARNING level and swallowed, so a broken patch never
  prevents the plugin from loading.
"""
import hashlib
import logging

from django.urls import NoReverseMatch, reverse

log = logging.getLogger(__name__)

_PATCH_FLAG = '_cabinet_view_patched'
_MIN_U_FOR_LAYOUT = 2  # devices shorter than this fall through to front/rear_image


class _URLOnlyImage:
    """
    Duck-typed stand-in for Django's ``FieldFile`` — just a ``.url``
    attribute, which is the only thing ``RackElevationSVG._draw_device``
    reads off the image argument.
    """

    __slots__ = ('url',)

    def __init__(self, url: str) -> None:
        self.url = url


def _content_hash(device) -> str:
    """
    Return a short stable hash of a device's mounts and placements, used
    as a cache-busting token in the embedded SVG URL. Cheap — a single
    query returning the (mount_id, last_updated) for each mount and the
    (placement_id, last_updated) for each placement.

    Uses SHA-256 truncated to 10 hex chars, which is more than enough for
    cache-busting collisions on any realistic device.
    """
    hasher = hashlib.sha256()
    for mount in device.cabinet_mounts.all().order_by('pk'):
        hasher.update(f'{mount.pk}:{mount.last_updated}'.encode())
        for placement in mount.placements.all().order_by('pk'):
            hasher.update(f'{placement.pk}:{placement.last_updated}'.encode())
    return hasher.hexdigest()[:10]


def _make_face_patch(original, face_name: str):
    """
    Build an upgraded draw_device_{front,rear} method that replaces the
    stock DeviceType image with our cabinet-layout SVG URL when the
    device is a carrier host. The replacement logic is identical for
    both faces — only the original callable and the log label differ.
    """

    def patched(self, device, coords, size):
        try:
            profile = getattr(device.device_type, 'cabinet_profile', None)
            u_height = getattr(device.device_type, 'u_height', 0) or 0
            if (
                self.include_images
                and profile is not None
                and profile.hosts_mounts
                and u_height >= _MIN_U_FOR_LAYOUT
                and device.cabinet_mounts.exists()
            ):
                slot_w = max(1, int(size[0]))
                slot_h = max(1, int(size[1]))
                url = reverse(
                    'dcim:device_cabinet_layout_svg',
                    kwargs={'pk': device.pk},
                )
                version = _content_hash(device)
                # Finding E (v0.4.0): request the SVG in thumbnail mode
                # so the embedded rendering reads as "preview, zoom in
                # to interact" instead of pretending the placements are
                # clickable from inside the rack elevation <image>
                # wrapper (they aren't — clicking lands on the HOST
                # device via the core rack-elevation hyperlink, which
                # is a click-target lie without the diminishment).
                href = f'{url}?w={slot_w}&h={slot_h}&v={version}&thumb=1'
                color = device.role.color if device.role_id else None
                self._draw_device(
                    device, coords, size,
                    color=color,
                    image=_URLOnlyImage(href),
                )
                return
        except NoReverseMatch as exc:
            log.debug(
                'netbox_cabinet_view: cabinet_layout_svg URL not registered '
                'yet for %s, falling back to stock %s: %s',
                device, face_name, exc,
            )
        except Exception as exc:
            log.warning(
                'netbox_cabinet_view: rack-elevation %s patch fell back for '
                '%s: %s', face_name, device, exc,
            )

        return original(self, device, coords, size)

    setattr(patched, _PATCH_FLAG, True)
    return patched


def install_patch() -> None:
    """
    Wrap ``RackElevationSVG.draw_device_front`` AND
    ``RackElevationSVG.draw_device_rear`` with our cabinet-layout
    substitution. Safe to call multiple times (idempotent).
    """
    try:
        from dcim.svg.racks import RackElevationSVG
    except ImportError as exc:
        log.warning(
            'netbox_cabinet_view: cannot import RackElevationSVG, '
            'skipping rack-elevation patch: %s', exc,
        )
        return

    # Front face
    original_front = RackElevationSVG.draw_device_front
    if not getattr(original_front, _PATCH_FLAG, False):
        RackElevationSVG.draw_device_front = _make_face_patch(
            original_front, 'front',
        )
        log.info('netbox_cabinet_view: patched RackElevationSVG.draw_device_front')

    # Rear face
    original_rear = RackElevationSVG.draw_device_rear
    if not getattr(original_rear, _PATCH_FLAG, False):
        RackElevationSVG.draw_device_rear = _make_face_patch(
            original_rear, 'rear',
        )
        log.info('netbox_cabinet_view: patched RackElevationSVG.draw_device_rear')
