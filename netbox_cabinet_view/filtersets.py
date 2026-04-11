import django_filters
from django.db.models import Q

from dcim.models import Device, DeviceType
from netbox.filtersets import NetBoxModelFilterSet

from .choices import (
    MountSubtypeChoices,
    MountTypeChoices,
    OrientationChoices,
    UnitChoices,
)
from .models import DeviceTypeProfile, Mount, Placement


class DeviceTypeProfileFilterSet(NetBoxModelFilterSet):
    device_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        label='Device Type (ID)',
    )
    mountable_on = django_filters.MultipleChoiceFilter(choices=MountTypeChoices)

    class Meta:
        model = DeviceTypeProfile
        fields = (
            'id', 'device_type_id', 'hosts_mounts', 'mountable_on', 'mountable_subtype',
        )

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(device_type__model__icontains=value)
            | Q(device_type__manufacturer__name__icontains=value)
        )


class MountFilterSet(NetBoxModelFilterSet):
    host_device_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label='Host Device (ID)',
    )
    mount_type = django_filters.MultipleChoiceFilter(choices=MountTypeChoices)
    subtype = django_filters.MultipleChoiceFilter(choices=MountSubtypeChoices)
    orientation = django_filters.MultipleChoiceFilter(choices=OrientationChoices)
    unit = django_filters.MultipleChoiceFilter(choices=UnitChoices)

    class Meta:
        model = Mount
        fields = (
            'id', 'name', 'host_device_id',
            'mount_type', 'subtype', 'orientation', 'unit',
        )

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) | Q(description__icontains=value)
        )


class PlacementFilterSet(NetBoxModelFilterSet):
    mount_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Mount.objects.all(),
        label='Mount (ID)',
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label='Device (ID)',
    )

    class Meta:
        model = Placement
        fields = (
            'id', 'mount_id', 'device_id', 'device_bay', 'module_bay',
            'position', 'size', 'row', 'row_span',
        )

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(device__name__icontains=value)
            | Q(mount__name__icontains=value)
        )
