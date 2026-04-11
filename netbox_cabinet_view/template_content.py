from netbox.plugins import PluginTemplateExtension

from .models import Carrier


class RackCarrierHostsPanel(PluginTemplateExtension):
    """
    Injects a panel at the bottom of the Rack detail page listing devices in the
    rack that host cabinet carriers. Each entry links to that device's Layout tab.
    """

    models = ['dcim.rack']

    def full_width_page(self):
        rack = self.context['object']
        carriers = (
            Carrier.objects
            .filter(host_device__rack=rack)
            .select_related('host_device')
            .order_by('host_device__position', 'host_device__name', 'name')
        )
        # Group by host device for the template.
        by_device: dict = {}
        for carrier in carriers:
            by_device.setdefault(carrier.host_device, []).append(carrier)
        return self.render(
            'netbox_cabinet_view/inc/rack_carrier_hosts.html',
            extra_context={
                'rack': rack,
                'hosts': list(by_device.items()),
            },
        )


template_extensions = [RackCarrierHostsPanel]
