from django import forms
from django.utils.translation import gettext_lazy as _

from dcim.models import Device, DeviceBay, DeviceType, ModuleBay
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField
from utilities.forms.rendering import FieldSet

from .choices import (
    CarrierSubtypeChoices,
    CarrierTypeChoices,
    OrientationChoices,
    UnitChoices,
)
from .models import Carrier, DeviceTypeProfile, Mount


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
            'hosts_carriers', 'internal_width_mm', 'internal_height_mm', 'internal_depth_mm',
            name=_('Host / enclosure'),
        ),
        FieldSet(
            'mountable_on', 'mountable_subtype', 'footprint_primary', 'footprint_secondary',
            name=_('Mountable on carriers'),
        ),
        FieldSet('tags', name=_('Details')),
    )

    class Meta:
        model = DeviceTypeProfile
        fields = (
            'device_type',
            'hosts_carriers', 'internal_width_mm', 'internal_height_mm', 'internal_depth_mm',
            'mountable_on', 'mountable_subtype', 'footprint_primary', 'footprint_secondary',
            'tags',
        )


class DeviceTypeProfileFilterForm(NetBoxModelFilterSetForm):
    model = DeviceTypeProfile

    hosts_carriers = forms.NullBooleanField(required=False, label='Hosts carriers')
    mountable_on = forms.MultipleChoiceField(
        choices=CarrierTypeChoices, required=False, label='Mountable on',
    )

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag', name=_('Search')),
        FieldSet('hosts_carriers', 'mountable_on', name=_('Attributes')),
    )


# ---------------------------------------------------------------------------
# Carrier
# ---------------------------------------------------------------------------

class CarrierForm(NetBoxModelForm):
    host_device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        label='Host Device',
        help_text='The enclosure / rail / plate / subrack device.',
    )

    fieldsets = (
        FieldSet('host_device', 'name', 'description', name=_('Carrier')),
        FieldSet(
            'carrier_type', 'subtype', 'orientation', 'unit',
            name=_('Type'),
        ),
        FieldSet(
            'offset_x_mm', 'offset_y_mm', 'length_mm', 'width_mm', 'height_mm',
            name=_('Geometry (mm)'),
        ),
        FieldSet('tags', name=_('Details')),
    )

    class Meta:
        model = Carrier
        fields = (
            'host_device', 'name', 'description',
            'carrier_type', 'subtype', 'orientation', 'unit',
            'offset_x_mm', 'offset_y_mm',
            'length_mm', 'width_mm', 'height_mm',
            'tags',
        )


class CarrierFilterForm(NetBoxModelFilterSetForm):
    model = Carrier

    host_device_id = DynamicModelChoiceField(
        queryset=Device.objects.all(), required=False, label='Host Device',
    )
    carrier_type = forms.MultipleChoiceField(
        choices=CarrierTypeChoices, required=False, label='Carrier type',
    )
    subtype = forms.MultipleChoiceField(
        choices=CarrierSubtypeChoices, required=False, label='Subtype',
    )
    orientation = forms.MultipleChoiceField(
        choices=OrientationChoices, required=False, label='Orientation',
    )
    unit = forms.MultipleChoiceField(
        choices=UnitChoices, required=False, label='Unit',
    )

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag', name=_('Search')),
        FieldSet('host_device_id', 'carrier_type', 'subtype', 'orientation', 'unit', name=_('Attributes')),
    )


# ---------------------------------------------------------------------------
# Mount
# ---------------------------------------------------------------------------

class MountForm(NetBoxModelForm):
    carrier = DynamicModelChoiceField(
        queryset=Carrier.objects.all(),
        label='Carrier',
    )
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label='Device (standalone)',
        help_text='Use for bare rail mounts. Leave blank when using a DeviceBay or ModuleBay.',
    )
    device_bay = DynamicModelChoiceField(
        queryset=DeviceBay.objects.all(),
        required=False,
        label='Device Bay',
        help_text='Use for chassis/parent-child mounts.',
    )
    module_bay = DynamicModelChoiceField(
        queryset=ModuleBay.objects.all(),
        required=False,
        label='Module Bay',
        help_text='Use for modular chassis (PLC I/O, line cards, …).',
    )

    fieldsets = (
        FieldSet('carrier', name=_('Carrier')),
        FieldSet('device', 'device_bay', 'module_bay', name=_('Target (pick exactly one)')),
        FieldSet('position', 'size', name=_('1D placement (DIN / subrack / busbar)')),
        FieldSet('position_x', 'position_y', 'size_x', 'size_y', name=_('2D placement (mounting plate)')),
        FieldSet('tags', name=_('Details')),
    )

    class Meta:
        model = Mount
        fields = (
            'carrier', 'device', 'device_bay', 'module_bay',
            'position', 'size',
            'position_x', 'position_y', 'size_x', 'size_y',
            'tags',
        )


class MountFilterForm(NetBoxModelFilterSetForm):
    model = Mount

    carrier_id = DynamicModelChoiceField(
        queryset=Carrier.objects.all(), required=False, label='Carrier',
    )
    device_id = DynamicModelChoiceField(
        queryset=Device.objects.all(), required=False, label='Device',
    )

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag', name=_('Search')),
        FieldSet('carrier_id', 'device_id', name=_('Attributes')),
    )
