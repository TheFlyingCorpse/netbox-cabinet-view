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


template_extensions = [RackMountHostsPanel]
