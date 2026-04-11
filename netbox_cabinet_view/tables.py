import django_tables2 as tables

from netbox.tables import NetBoxTable
from netbox.tables.columns import ChoiceFieldColumn

from .models import Carrier, DeviceTypeProfile, Mount


class DeviceTypeProfileTable(NetBoxTable):
    device_type = tables.Column(linkify=True)
    hosts_carriers = tables.BooleanColumn()
    mountable_on = ChoiceFieldColumn()
    mountable_subtype = ChoiceFieldColumn()

    class Meta(NetBoxTable.Meta):
        model = DeviceTypeProfile
        fields = (
            'pk', 'id', 'device_type',
            'hosts_carriers', 'internal_width_mm', 'internal_height_mm', 'internal_depth_mm',
            'mountable_on', 'mountable_subtype', 'footprint_primary', 'footprint_secondary',
            'actions',
        )
        default_columns = (
            'device_type', 'hosts_carriers', 'mountable_on', 'mountable_subtype',
            'footprint_primary', 'actions',
        )


class CarrierTable(NetBoxTable):
    name = tables.Column(linkify=True)
    host_device = tables.Column(linkify=True)
    carrier_type = ChoiceFieldColumn()
    subtype = ChoiceFieldColumn()
    orientation = ChoiceFieldColumn()
    unit = ChoiceFieldColumn()
    mount_count = tables.Column(verbose_name='Mounts', orderable=False)

    class Meta(NetBoxTable.Meta):
        model = Carrier
        fields = (
            'pk', 'id', 'name', 'host_device', 'carrier_type', 'subtype',
            'orientation', 'unit',
            'offset_x_mm', 'offset_y_mm', 'length_mm', 'width_mm', 'height_mm',
            'rows', 'row_height_mm',
            'mount_count', 'description', 'actions',
        )
        default_columns = (
            'name', 'host_device', 'carrier_type', 'subtype', 'orientation',
            'length_mm', 'mount_count', 'actions',
        )


class MountTable(NetBoxTable):
    carrier = tables.Column(linkify=True)
    device = tables.Column(linkify=True)
    device_bay = tables.Column(linkify=True)
    module_bay = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = Mount
        fields = (
            'pk', 'id', 'carrier', 'device', 'device_bay', 'module_bay',
            'position', 'size', 'row', 'row_span',
            'position_x', 'position_y', 'size_x', 'size_y',
            'actions',
        )
        default_columns = (
            'carrier', 'device', 'device_bay', 'module_bay',
            'row', 'position', 'size', 'actions',
        )
