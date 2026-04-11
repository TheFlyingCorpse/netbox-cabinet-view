from netbox.plugins import PluginTemplateExtension

from .models import Mount


class RackMountHostsPanel(PluginTemplateExtension):
    """
    Injects a panel at the bottom of the Rack detail page listing devices in the
    rack that host cabinet mounts. Each entry links to that device's Layout tab.
    """

    models = ['dcim.rack']

    def full_width_page(self):
        rack = self.context['object']
        mounts = (
            Mount.objects
            .filter(host_device__rack=rack)
            .select_related('host_device')
            .order_by('host_device__position', 'host_device__name', 'name')
        )
        # Group by host device for the template.
        by_device: dict = {}
        for mount in mounts:
            by_device.setdefault(mount.host_device, []).append(mount)
        return self.render(
            'netbox_cabinet_view/inc/rack_mount_hosts.html',
            extra_context={
                'rack': rack,
                'hosts': list(by_device.items()),
            },
        )


class CabinetViewHintExtension(PluginTemplateExtension):
    """
    Discovery hint card — Finding H, v0.4.0.

    Injects a soft CTA on Device detail pages whose DeviceType looks
    "cabinet-shaped" but has no DeviceMountProfile yet. Answers the
    "a new user installs the plugin and doesn't notice it" problem:
    instead of forcing users to dig through the sidebar, the hint
    appears on the exact Device pages where it's relevant.

    Heuristic (ALL must be true):
      1. DeviceType has NO ``cabinet_profile`` yet
      2. DeviceType.u_height == 0 (not a rack-mount device; most
         OT/ICS enclosures, MCCs, marshalling cabinets, panels live
         in a Location without a rack U position)
      3. The viewing user has ``netbox_cabinet_view.add_devicemountprofile``
         permission (don't show the CTA to users who can't act on it)
      4. The hint has not been dismissed for this device by the
         current user (dismissal persists per-user via
         ``user.config['cabinet_view']['dismissed_hints']``)

    Renders in the Device detail page's right column via
    ``right_page()``. Returns empty string (→ no extension content)
    when any condition fails, so the hint vanishes the moment the
    user creates a profile, dismisses it, or lacks permission.
    """

    models = ['dcim.device']

    def right_page(self):
        device = self.context['object']
        request = self.context['request']

        # (1) No profile yet.
        if getattr(device.device_type, 'cabinet_profile', None) is not None:
            return ''

        # (2) u_height == 0 — looks cabinet-shaped.
        if (device.device_type.u_height or 0) != 0:
            return ''

        # (3) User can create profiles.
        if not request.user.has_perm('netbox_cabinet_view.add_devicemountprofile'):
            return ''

        # (4) Not already dismissed by this user. UserConfig stores an
        # arbitrary JSON blob keyed by dotted path; we nest under
        # "cabinet_view.dismissed_hints" so we can add other keys
        # later without colliding.
        dismissed = self._dismissed_device_pks(request.user)
        if device.pk in dismissed:
            return ''

        return self.render(
            'netbox_cabinet_view/inc/discovery_hint_card.html',
            extra_context={'device': device},
        )

    @staticmethod
    def _dismissed_device_pks(user) -> set:
        """
        Return the set of Device PKs for which this user has dismissed
        the discovery hint. Robust against legacy data shapes —
        ``user.config.get('cabinet_view.dismissed_hints')`` returns
        None, a list, or something else depending on what was stored.
        """
        try:
            raw = user.config.get('cabinet_view.dismissed_hints')
        except Exception:
            return set()
        if isinstance(raw, (list, tuple, set)):
            return {int(pk) for pk in raw if str(pk).isdigit()}
        return set()


template_extensions = [RackMountHostsPanel, CabinetViewHintExtension]
