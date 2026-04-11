import django_tables2 as tables

from netbox.tables import NetBoxTable
from netbox.tables.columns import ChoiceFieldColumn

from .models import DeviceMountProfile, ModuleMountProfile, Mount, Placement


class DeviceMountProfileTable(NetBoxTable):
    device_type = tables.Column(linkify=True)
    hosts_mounts = tables.BooleanColumn()
    mountable_on = ChoiceFieldColumn()
    mountable_subtype = ChoiceFieldColumn()

    class Meta(NetBoxTable.Meta):
        model = DeviceMountProfile
        fields = (
            'pk', 'id', 'device_type',
            'hosts_mounts', 'internal_width_mm', 'internal_height_mm', 'internal_depth_mm',
            'mountable_on', 'mountable_subtype', 'footprint_primary', 'footprint_secondary',
            'actions',
        )
        default_columns = (
            'device_type', 'hosts_mounts', 'mountable_on', 'mountable_subtype',
            'footprint_primary', 'actions',
        )


class ModuleMountProfileTable(NetBoxTable):
    module_type = tables.Column(linkify=True)
    mountable_on = ChoiceFieldColumn()
    mountable_subtype = ChoiceFieldColumn()

    class Meta(NetBoxTable.Meta):
        model = ModuleMountProfile
        fields = (
            'pk', 'id', 'module_type',
            'mountable_on', 'mountable_subtype', 'footprint_primary', 'footprint_secondary',
            'actions',
        )
        default_columns = (
            'module_type', 'mountable_on', 'mountable_subtype',
            'footprint_primary', 'footprint_secondary', 'actions',
        )


class MountTable(NetBoxTable):
    name = tables.Column(linkify=True)
    host_device = tables.Column(linkify=True)
    mount_type = ChoiceFieldColumn()
    subtype = ChoiceFieldColumn()
    orientation = ChoiceFieldColumn()
    unit = ChoiceFieldColumn()
    placement_count = tables.Column(verbose_name='Placements', orderable=False)

    class Meta(NetBoxTable.Meta):
        model = Mount
        fields = (
            'pk', 'id', 'name', 'host_device', 'mount_type', 'subtype',
            'orientation', 'unit',
            'offset_x_mm', 'offset_y_mm', 'length_mm', 'width_mm', 'height_mm',
            'rows', 'row_height_mm',
            'placement_count', 'description', 'actions',
        )
        default_columns = (
            'name', 'host_device', 'mount_type', 'subtype', 'orientation',
            'length_mm', 'placement_count', 'actions',
        )


class PlacementTable(NetBoxTable):
    mount = tables.Column(linkify=True)
    device = tables.Column(linkify=True)
    device_bay = tables.Column(linkify=True)
    module_bay = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = Placement
        fields = (
            'pk', 'id', 'mount', 'device', 'device_bay', 'module_bay',
            'position', 'size', 'row', 'row_span',
            'position_x', 'position_y', 'size_x', 'size_y',
            'actions',
        )
        default_columns = (
            'mount', 'device', 'device_bay', 'module_bay',
            'row', 'position', 'size', 'actions',
        )
