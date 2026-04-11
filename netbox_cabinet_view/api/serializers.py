"""
Minimal DRF serializers — just enough to satisfy NetBox's list-view filter
forms and DynamicModelChoiceField autocomplete. Not intended as a public
REST API in v1.
"""
from rest_framework import serializers

from ..models import Carrier, DeviceTypeProfile, Mount


class DeviceTypeProfileSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_cabinet_view-api:devicetypeprofile-detail'
    )
    display = serializers.CharField(read_only=True, source='__str__')

    class Meta:
        model = DeviceTypeProfile
        fields = (
            'id', 'url', 'display', 'device_type',
            'hosts_carriers', 'internal_width_mm', 'internal_height_mm', 'internal_depth_mm',
            'mountable_on', 'mountable_subtype', 'footprint_primary', 'footprint_secondary',
        )


class CarrierSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_cabinet_view-api:carrier-detail'
    )
    display = serializers.CharField(read_only=True, source='__str__')

    class Meta:
        model = Carrier
        fields = (
            'id', 'url', 'display', 'host_device', 'name',
            'carrier_type', 'subtype', 'orientation', 'unit',
            'offset_x_mm', 'offset_y_mm', 'length_mm', 'width_mm', 'height_mm',
            'rows', 'row_height_mm',
            'description',
        )


class MountSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_cabinet_view-api:mount-detail'
    )
    display = serializers.CharField(read_only=True, source='__str__')

    class Meta:
        model = Mount
        fields = (
            'id', 'url', 'display', 'carrier',
            'device', 'device_bay', 'module_bay',
            'position', 'size', 'row', 'row_span',
            'position_x', 'position_y', 'size_x', 'size_y',
        )
