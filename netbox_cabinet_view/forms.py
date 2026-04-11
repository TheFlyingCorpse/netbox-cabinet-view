from django import forms
from django.utils.translation import gettext_lazy as _

from dcim.models import Device, DeviceBay, DeviceType, ModuleBay
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField
from utilities.forms.rendering import FieldSet

from .choices import (
    MountSubtypeChoices,
    MountTypeChoices,
    OrientationChoices,
    UnitChoices,
)
from .models import DeviceTypeProfile, Mount, Placement


# ---------------------------------------------------------------------------
# DeviceTypeProfile
# ---------------------------------------------------------------------------

class DeviceTypeProfileForm(NetBoxModelForm):
    device_type = DynamicModelChoiceField(
        queryset=DeviceType.objects.all(),
        label='Device Type',
    )

    fieldsets = (
        FieldSet('device_type', name=_('Device Type')),
        FieldSet(
            'hosts_mounts', 'internal_width_mm', 'internal_height_mm', 'internal_depth_mm',
            name=_('Host / enclosure'),
        ),
        FieldSet(
            'mountable_on', 'mountable_subtype', 'footprint_primary', 'footprint_secondary',
            name=_('Mountable on mounts'),
        ),
        FieldSet('tags', name=_('Details')),
    )

    class Meta:
        model = DeviceTypeProfile
        fields = (
            'device_type',
            'hosts_mounts', 'internal_width_mm', 'internal_height_mm', 'internal_depth_mm',
            'mountable_on', 'mountable_subtype', 'footprint_primary', 'footprint_secondary',
            'tags',
        )


class DeviceTypeProfileFilterForm(NetBoxModelFilterSetForm):
    model = DeviceTypeProfile

    hosts_mounts = forms.NullBooleanField(required=False, label='Hosts mounts')
    mountable_on = forms.MultipleChoiceField(
        choices=MountTypeChoices, required=False, label='Mountable on',
    )

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag', name=_('Search')),
        FieldSet('hosts_mounts', 'mountable_on', name=_('Attributes')),
    )


# ---------------------------------------------------------------------------
# Mount
# ---------------------------------------------------------------------------

class MountForm(NetBoxModelForm):
    host_device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        label='Host Device',
        help_text='The enclosure / rail / plate / subrack device.',
    )

    fieldsets = (
        FieldSet('host_device', 'name', 'description', name=_('Mount')),
        FieldSet(
            'mount_type', 'subtype', 'orientation', 'unit',
            name=_('Type'),
        ),
        FieldSet(
            'offset_x_mm', 'offset_y_mm', 'length_mm', 'width_mm', 'height_mm',
            name=_('Geometry (mm)'),
        ),
        FieldSet(
            'rows', 'row_height_mm',
            name=_('Grid layout (grid mounts only)'),
        ),
        FieldSet('tags', name=_('Details')),
    )

    class Meta:
        model = Mount
        fields = (
            'host_device', 'name', 'description',
            'mount_type', 'subtype', 'orientation', 'unit',
            'offset_x_mm', 'offset_y_mm',
            'length_mm', 'width_mm', 'height_mm',
            'rows', 'row_height_mm',
            'tags',
        )


class MountFilterForm(NetBoxModelFilterSetForm):
    model = Mount

    host_device_id = DynamicModelChoiceField(
        queryset=Device.objects.all(), required=False, label='Host Device',
    )
    mount_type = forms.MultipleChoiceField(
        choices=MountTypeChoices, required=False, label='Mount type',
    )
    subtype = forms.MultipleChoiceField(
        choices=MountSubtypeChoices, required=False, label='Subtype',
    )
    orientation = forms.MultipleChoiceField(
        choices=OrientationChoices, required=False, label='Orientation',
    )
    unit = forms.MultipleChoiceField(
        choices=UnitChoices, required=False, label='Unit',
    )

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag', name=_('Search')),
        FieldSet('host_device_id', 'mount_type', 'subtype', 'orientation', 'unit', name=_('Attributes')),
    )


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------

class PlacementForm(NetBoxModelForm):
    mount = DynamicModelChoiceField(
        queryset=Mount.objects.all(),
        label='Mount',
    )
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label='Device (standalone)',
        help_text='Use for bare rail placements. Leave blank when using a DeviceBay or ModuleBay.',
    )
    device_bay = DynamicModelChoiceField(
        queryset=DeviceBay.objects.all(),
        required=False,
        label='Device Bay',
        help_text='Use for chassis/parent-child placements.',
    )
    module_bay = DynamicModelChoiceField(
        queryset=ModuleBay.objects.all(),
        required=False,
        label='Module Bay',
        help_text='Use for modular chassis (PLC I/O, line cards, …).',
    )

    fieldsets = (
        FieldSet('mount', name=_('Mount')),
        FieldSet('device', 'device_bay', 'module_bay', name=_('Target (pick exactly one)')),
        FieldSet('position', 'size', name=_('1D placement (DIN / subrack / busbar)')),
        FieldSet('row', 'row_span', name=_('Grid placement (grid mounts only)')),
        FieldSet('position_x', 'position_y', 'size_x', 'size_y', name=_('2D placement (mounting plate)')),
        FieldSet('tags', name=_('Details')),
    )

    class Meta:
        model = Placement
        fields = (
            'mount', 'device', 'device_bay', 'module_bay',
            'position', 'size',
            'row', 'row_span',
            'position_x', 'position_y', 'size_x', 'size_y',
            'tags',
        )


class PlacementFilterForm(NetBoxModelFilterSetForm):
    model = Placement

    mount_id = DynamicModelChoiceField(
        queryset=Mount.objects.all(), required=False, label='Mount',
    )
    device_id = DynamicModelChoiceField(
        queryset=Device.objects.all(), required=False, label='Device',
    )

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag', name=_('Search')),
        FieldSet('mount_id', 'device_id', name=_('Attributes')),
    )
