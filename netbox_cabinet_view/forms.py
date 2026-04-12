from django import forms
from django.utils.translation import gettext_lazy as _

from dcim.models import Device, DeviceBay, DeviceType, ModuleBay, ModuleType
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField
from utilities.forms.rendering import FieldSet
from utilities.forms.utils import get_field_value

from .choices import (
    MountFaceChoices,
    MountSubtypeChoices,
    MountTypeChoices,
    OrientationChoices,
    UnitChoices,
)
from .models import DeviceMountProfile, ModuleMountProfile, Mount, Placement


# ---------------------------------------------------------------------------
# DeviceMountProfile (formerly DeviceTypeProfile)
# ---------------------------------------------------------------------------

class DeviceMountProfileForm(NetBoxModelForm):
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
        FieldSet('front_image', name=_('Front-panel image')),
        FieldSet('tags', name=_('Details')),
    )

    class Meta:
        model = DeviceMountProfile
        fields = (
            'device_type',
            'hosts_mounts', 'internal_width_mm', 'internal_height_mm', 'internal_depth_mm',
            'mountable_on', 'mountable_subtype', 'footprint_primary', 'footprint_secondary',
            'front_image',
            'tags',
        )


class DeviceMountProfileFilterForm(NetBoxModelFilterSetForm):
    model = DeviceMountProfile

    hosts_mounts = forms.NullBooleanField(required=False, label='Hosts mounts')
    mountable_on = forms.MultipleChoiceField(
        choices=MountTypeChoices, required=False, label='Mountable on',
    )

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag', name=_('Search')),
        FieldSet('hosts_mounts', 'mountable_on', name=_('Attributes')),
    )


# ---------------------------------------------------------------------------
# ModuleMountProfile (new in v0.4.0)
# ---------------------------------------------------------------------------

class ModuleMountProfileForm(NetBoxModelForm):
    module_type = DynamicModelChoiceField(
        queryset=ModuleType.objects.all(),
        label='Module Type',
    )

    fieldsets = (
        FieldSet('module_type', name=_('Module Type')),
        FieldSet(
            'mountable_on', 'mountable_subtype', 'footprint_primary', 'footprint_secondary',
            name=_('Mountable on mounts'),
        ),
        FieldSet('front_image', name=_('Front-panel image')),
        FieldSet('tags', name=_('Details')),
    )

    class Meta:
        model = ModuleMountProfile
        fields = (
            'module_type',
            'mountable_on', 'mountable_subtype', 'footprint_primary', 'footprint_secondary',
            'front_image',
            'tags',
        )


class ModuleMountProfileFilterForm(NetBoxModelFilterSetForm):
    model = ModuleMountProfile

    mountable_on = forms.MultipleChoiceField(
        choices=MountTypeChoices, required=False, label='Mountable on',
    )

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag', name=_('Search')),
        FieldSet('mountable_on', name=_('Attributes')),
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
            'mount_type', 'subtype', 'orientation', 'unit', 'face',
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
            'mount_type', 'subtype', 'orientation', 'unit', 'face',
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
    face = forms.MultipleChoiceField(
        choices=MountFaceChoices, required=False, label='Face',
    )

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag', name=_('Search')),
        FieldSet('host_device_id', 'mount_type', 'subtype', 'orientation', 'unit', 'face', name=_('Attributes')),
    )


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------

class PlacementForm(NetBoxModelForm):
    """
    Carrier-driven dynamic Placement form — Finding G, v0.4.0.

    Reshapes itself when the user picks a Mount:

    - **1D mounts** (DIN rail / subrack / busbar): only ``position`` +
      ``size`` are shown. Grid (``row``/``row_span``) and 2D
      (``position_x/y``, ``size_x/y``) fields are removed from the
      form entirely so they can't be accidentally filled.
    - **Grid mounts**: adds ``row`` + ``row_span`` alongside position
      + size. Drops 2D fields.
    - **2D mounting plates**: shows ``position_x/y`` + ``size_x/y``,
      drops 1D and grid fields.

    Target dropdowns (``device`` / ``device_bay`` / ``module_bay``)
    are compatibility-filtered based on the chosen mount's type and
    subtype, so users can only pick valid, unoccupied targets:

    - ``device``: DeviceTypes with ``mountable_on == mount.mount_type``
      (and matching subtype when declared), excluding devices
      already placed on any mount.
    - ``device_bay``: bays on the mount's ``host_device`` whose
      parent device matches the compatibility filter, excluding
      bays already used by another Placement.
    - ``module_bay``: bays on the mount's ``host_device``, excluding
      bays already used by another Placement.

    Numeric placement fields get computed ``help_text`` hints
    ("Range: 1 – 79") so users don't have to read the Mount record
    to figure out how many slots are available.

    Driven by NetBox 4.5's HTMX `hx-get='.' / hx-include='#form_fields'
    / hx-target='#form_fields'` convention: when the user changes the
    mount selection, the browser re-POSTs the form to the same URL,
    the generic edit view re-renders the form, and the server
    returns just the reshaped field section.
    """

    mount = DynamicModelChoiceField(
        queryset=Mount.objects.all(),
        label='Mount',
        help_text='Pick a mount first — the form below adapts to its type.',
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

    class Meta:
        model = Placement
        fields = (
            'mount', 'device', 'device_bay', 'module_bay',
            'position', 'size',
            'row', 'row_span',
            'position_x', 'position_y', 'size_x', 'size_y',
            'tags',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Wire the HTMX re-render trigger to the mount selector.
        # Matches NetBox's own pattern from dcim/forms/model_forms.py.
        # The attrs go on the widget, not the field.
        self.fields['mount'].widget.attrs.update({
            'hx-get': '.',
            'hx-include': '#form_fields',
            'hx-target': '#form_fields',
        })

        # Try to resolve the currently selected mount. get_field_value
        # works on both bound (POST) and unbound (GET with ?mount=N
        # querystring from the inline add-placement affordance) forms.
        mount_pk = get_field_value(self, 'mount')
        mount = None
        if mount_pk:
            try:
                mount = Mount.objects.select_related('host_device').get(pk=mount_pk)
            except (Mount.DoesNotExist, ValueError, TypeError):
                mount = None

        # If no mount yet, leave the form in its "pick a mount first"
        # shape - strip placement fields to reduce noise.
        if mount is None:
            for fname in (
                'position', 'size', 'row', 'row_span',
                'position_x', 'position_y', 'size_x', 'size_y',
            ):
                if fname in self.fields:
                    del self.fields[fname]
            self.fieldsets = (
                FieldSet('mount', name=_('Mount')),
                FieldSet('device', 'device_bay', 'module_bay',
                         name=_('Target (pick exactly one)')),
                FieldSet('tags', name=_('Details')),
            )
            return

        # Mount is known — reshape the form to its type.
        self._reshape_for_mount(mount)
        self._filter_target_querysets(mount)
        self._set_range_hints(mount)

    # ------------------------------------------------------------------
    # Reshape helpers
    # ------------------------------------------------------------------

    def _reshape_for_mount(self, mount):
        """Drop irrelevant placement fields and rebuild fieldsets."""
        def _drop(*names):
            for n in names:
                if n in self.fields:
                    del self.fields[n]

        if mount.is_one_d:
            _drop('row', 'row_span', 'position_x', 'position_y', 'size_x', 'size_y')
            placement_fieldset = FieldSet(
                'position', 'size',
                name=_('1D placement ({type})').format(
                    type=mount.get_mount_type_display(),
                ),
            )
        elif mount.is_grid:
            _drop('position_x', 'position_y', 'size_x', 'size_y')
            placement_fieldset = FieldSet(
                'row', 'row_span', 'position', 'size',
                name=_('Grid placement ({rows} rows × {cap} slots)').format(
                    rows=mount.rows or 1,
                    cap=mount.capacity_units,
                ),
            )
        elif mount.is_two_d:
            _drop('position', 'size', 'row', 'row_span')
            placement_fieldset = FieldSet(
                'position_x', 'position_y', 'size_x', 'size_y',
                name=_('2D placement ({w} × {h} mm)').format(
                    w=mount.width_mm or 0,
                    h=mount.height_mm or 0,
                ),
            )
        else:
            placement_fieldset = FieldSet('position', 'size', name=_('Placement'))

        self.fieldsets = (
            FieldSet('mount', name=_('Mount')),
            FieldSet('device', 'device_bay', 'module_bay',
                     name=_('Target (pick exactly one)')),
            placement_fieldset,
            FieldSet('tags', name=_('Details')),
        )

    def _filter_target_querysets(self, mount):
        """
        Filter the three target querysets to compatible + unoccupied
        options for the given mount. Compatibility is determined by
        each candidate's DeviceMountProfile / ModuleMountProfile:
        ``mountable_on`` must match ``mount.mount_type``, and if the
        profile declares ``mountable_subtype``, it must match
        ``mount.subtype`` too.

        Unoccupied means: not currently the target of another
        Placement (per the three ``unique_placement_*`` constraints).
        """
        from django.db.models import Q

        # Build the compatibility Q-object for DeviceType.cabinet_profile.
        compat_q = Q(device_type__cabinet_profile__mountable_on=mount.mount_type)
        if mount.subtype:
            compat_q &= (
                Q(device_type__cabinet_profile__mountable_subtype=mount.subtype)
                | Q(device_type__cabinet_profile__mountable_subtype='')
            )

        # device: compatible + not already placed anywhere.
        self.fields['device'].queryset = (
            Device.objects
            .filter(compat_q)
            .exclude(cabinet_placements__isnull=False)
        )

        # device_bay: bays on the mount's host device, not already used.
        self.fields['device_bay'].queryset = (
            DeviceBay.objects
            .filter(device=mount.host_device)
            .exclude(cabinet_placements__isnull=False)
        )

        # module_bay: bays on the mount's host device, not already used.
        self.fields['module_bay'].queryset = (
            ModuleBay.objects
            .filter(device=mount.host_device)
            .exclude(cabinet_placements__isnull=False)
        )

    def _set_range_hints(self, mount):
        """
        Annotate numeric placement fields with a computed help_text
        "Range: 1 – N" derived from mount capacity. Users learn the
        valid range without reading the Mount record separately.
        """
        unit_short = {
            'mm': 'mm',
            'module_17_5': 'DIN modules',
            'hp_5_08': 'HP',
        }.get(mount.unit, 'units')

        if mount.is_one_d or mount.is_grid:
            if 'position' in self.fields:
                self.fields['position'].help_text = _(
                    'Range: 1 – {cap} ({unit}).'
                ).format(cap=mount.capacity_units, unit=unit_short)
            if 'size' in self.fields:
                self.fields['size'].help_text = _(
                    'Width in {unit}. Leave blank to auto-fill from the '
                    'device profile footprint.'
                ).format(unit=unit_short)
        if mount.is_grid:
            if 'row' in self.fields:
                self.fields['row'].help_text = _(
                    'Row number, 1 – {rows}.'
                ).format(rows=mount.rows or 1)
            if 'row_span' in self.fields:
                self.fields['row_span'].help_text = _(
                    'How many rows this placement spans. Default 1.'
                )
        if mount.is_two_d:
            if 'position_x' in self.fields:
                self.fields['position_x'].help_text = _(
                    'X position in mm (0 – {w}).'
                ).format(w=mount.width_mm or 0)
            if 'position_y' in self.fields:
                self.fields['position_y'].help_text = _(
                    'Y position in mm (0 – {h}).'
                ).format(h=mount.height_mm or 0)
            if 'size_x' in self.fields:
                self.fields['size_x'].help_text = _(
                    'Width in mm. Leave blank to auto-fill from the '
                    'device profile footprint.'
                )
            if 'size_y' in self.fields:
                self.fields['size_y'].help_text = _(
                    'Height in mm. Leave blank to auto-fill from the '
                    'device profile footprint.'
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
