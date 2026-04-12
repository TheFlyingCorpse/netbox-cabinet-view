"""
Minimal DRF serializers — just enough to satisfy NetBox's list-view filter
forms and DynamicModelChoiceField autocomplete. Not intended as a public
REST API in v1.
"""
from rest_framework import serializers

from ..models import DeviceMountProfile, ModuleMountProfile, Mount, Placement


class DeviceMountProfileSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_cabinet_view-api:devicemountprofile-detail'
    )
    display = serializers.CharField(read_only=True, source='__str__')

    class Meta:
        model = DeviceMountProfile
        fields = (
            'id', 'url', 'display', 'device_type',
            'hosts_mounts', 'internal_width_mm', 'internal_height_mm', 'internal_depth_mm',
            'mountable_on', 'mountable_subtype', 'footprint_primary', 'footprint_secondary',
            'enable_port_overlay', 'port_map',
        )


class ModuleMountProfileSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_cabinet_view-api:modulemountprofile-detail'
    )
    display = serializers.CharField(read_only=True, source='__str__')

    class Meta:
        model = ModuleMountProfile
        fields = (
            'id', 'url', 'display', 'module_type',
            'mountable_on', 'mountable_subtype', 'footprint_primary', 'footprint_secondary',
            'enable_port_overlay', 'port_map',
        )


class MountSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_cabinet_view-api:mount-detail'
    )
    display = serializers.CharField(read_only=True, source='__str__')

    class Meta:
        model = Mount
        fields = (
            'id', 'url', 'display', 'host_device', 'name',
            'mount_type', 'subtype', 'orientation', 'unit',
            'offset_x_mm', 'offset_y_mm', 'length_mm', 'width_mm', 'height_mm',
            'rows', 'row_height_mm',
            'description',
        )


class PlacementSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_cabinet_view-api:placement-detail'
    )
    display = serializers.CharField(read_only=True, source='__str__')

    class Meta:
        model = Placement
        fields = (
            'id', 'url', 'display', 'mount',
            'device', 'device_bay', 'module_bay',
            'position', 'size', 'row', 'row_span',
            'position_x', 'position_y', 'size_x', 'size_y',
        )
