import django_filters
from django.db.models import Q

from dcim.models import Device, DeviceType
from netbox.filtersets import NetBoxModelFilterSet

from .choices import (
    CarrierSubtypeChoices,
    CarrierTypeChoices,
    OrientationChoices,
    UnitChoices,
)
from .models import Carrier, DeviceTypeProfile, Mount


class DeviceTypeProfileFilterSet(NetBoxModelFilterSet):
    device_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        label='Device Type (ID)',
    )
    mountable_on = django_filters.MultipleChoiceFilter(choices=CarrierTypeChoices)

    class Meta:
        model = DeviceTypeProfile
        fields = (
            'id', 'device_type_id', 'hosts_carriers', 'mountable_on', 'mountable_subtype',
        )

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(device_type__model__icontains=value)
            | Q(device_type__manufacturer__name__icontains=value)
        )


class CarrierFilterSet(NetBoxModelFilterSet):
    host_device_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label='Host Device (ID)',
    )
    carrier_type = django_filters.MultipleChoiceFilter(choices=CarrierTypeChoices)
    subtype = django_filters.MultipleChoiceFilter(choices=CarrierSubtypeChoices)
    orientation = django_filters.MultipleChoiceFilter(choices=OrientationChoices)
    unit = django_filters.MultipleChoiceFilter(choices=UnitChoices)

    class Meta:
        model = Carrier
        fields = (
            'id', 'name', 'host_device_id',
            'carrier_type', 'subtype', 'orientation', 'unit',
        )

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) | Q(description__icontains=value)
        )


class MountFilterSet(NetBoxModelFilterSet):
    carrier_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Carrier.objects.all(),
        label='Carrier (ID)',
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label='Device (ID)',
    )

    class Meta:
        model = Mount
        fields = (
            'id', 'carrier_id', 'device_id', 'device_bay', 'module_bay',
            'position', 'size',
        )

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(device__name__icontains=value)
            | Q(carrier__name__icontains=value)
        )
