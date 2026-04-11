"""
Monkey-patch ``dcim.svg.racks.RackElevationSVG`` so that cabinet-host
devices render their cabinet layout SVG *inside* the rack elevation at
their U slot, instead of the stock DeviceType.front_image.

The core rack elevation does not expose a plugin hook for this — it
iterates a model's devices and emits one ``<image>`` per device from
Python. The only practical seam is patching the ``draw_device_front``
method at plugin ``ready()`` time.

Design notes
============
* **Opt-out flag** — controlled by ``PLUGINS_CONFIG['netbox_cabinet_view']
  ['PATCH_RACK_ELEVATION']``. Defaults to ``True``. Flip to ``False`` if
  a NetBox upgrade breaks the patch.
* **1U fallback** — devices with ``u_height <= 1`` fall through to the
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
* **Idempotent** — ``install_patch`` tags the wrapper so re-entry (from
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
_MIN_U_FOR_LAYOUT = 2  # devices shorter than this fall through to front_image


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
    Return a short stable hash of a device's carriers and mounts, used as
    a cache-busting token in the embedded SVG URL. Cheap — a single query
    returning the (carrier_id, last_updated) for each carrier and the
    (mount_id, last_updated) for each mount.

    Uses SHA-256 truncated to 10 hex chars, which is more than enough for
    cache-busting collisions on any realistic device.
    """
    hasher = hashlib.sha256()
    for carrier in device.cabinet_carriers.all().order_by('pk'):
        hasher.update(f'{carrier.pk}:{carrier.last_updated}'.encode())
        for mount in carrier.mounts.all().order_by('pk'):
            hasher.update(f'{mount.pk}:{mount.last_updated}'.encode())
    return hasher.hexdigest()[:10]


def install_patch() -> None:
    """
    Wrap ``RackElevationSVG.draw_device_front`` with our cabinet-layout
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

    original = RackElevationSVG.draw_device_front
    if getattr(original, _PATCH_FLAG, False):
        return

    def patched_draw_device_front(self, device, coords, size):
        # Only intercept when: the caller wants images; the device's
        # DeviceType has a cabinet_profile declaring hosts_carriers=True;
        # the device is tall enough (>= 2U) to usefully show a layout;
        # and at least one carrier actually exists on the device.
        try:
            profile = getattr(device.device_type, 'cabinet_profile', None)
            u_height = getattr(device.device_type, 'u_height', 0) or 0
            if (
                self.include_images
                and profile is not None
                and profile.hosts_carriers
                and u_height >= _MIN_U_FOR_LAYOUT
                and device.cabinet_carriers.exists()
            ):
                slot_w = max(1, int(size[0]))
                slot_h = max(1, int(size[1]))
                url = reverse(
                    'dcim:device_cabinet_layout_svg',
                    kwargs={'pk': device.pk},
                )
                version = _content_hash(device)
                href = f'{url}?w={slot_w}&h={slot_h}&v={version}'
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
                'yet for %s, falling back: %s', device, exc,
            )
        except Exception as exc:
            log.warning(
                'netbox_cabinet_view: rack-elevation patch fell back for '
                '%s: %s', device, exc,
            )

        return original(self, device, coords, size)

    setattr(patched_draw_device_front, _PATCH_FLAG, True)
    RackElevationSVG.draw_device_front = patched_draw_device_front
    log.info('netbox_cabinet_view: patched RackElevationSVG.draw_device_front')
