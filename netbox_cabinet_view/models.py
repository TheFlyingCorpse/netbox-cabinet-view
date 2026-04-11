from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse

from netbox.models import NetBoxModel

from .choices import (
    CARRIER_TYPE_SUBTYPES,
    CarrierSubtypeChoices,
    CarrierTypeChoices,
    ONE_D_CARRIER_TYPES,
    OrientationChoices,
    TWO_D_CARRIER_TYPES,
    UNIT_TO_MM,
    UnitChoices,
)


# ---------------------------------------------------------------------------
# DeviceTypeProfile
# ---------------------------------------------------------------------------

class DeviceTypeProfile(NetBoxModel):
    """
    Per-DeviceType declaration of cabinet-view behaviour.

    A single profile on a DeviceType can cover two roles:

    * **Host**: `hosts_carriers=True` means devices of this type are enclosures
      / rails / plates / subracks that can themselves carry other devices. The
      `internal_*` dimensions describe the usable area inside the host.
    * **Mountable**: `mountable_on` declares that devices of this type clip onto
      carriers of the given type and subtype. `footprint_primary` gives the
      width in carrier units; `footprint_secondary` gives the height for 2D
      carriers (mounting plates).

    A DeviceType can be both (a subrack that is itself mounted on a plate), or
    either, or neither. One profile per DeviceType.
    """

    device_type = models.OneToOneField(
        to='dcim.DeviceType',
        on_delete=models.CASCADE,
        related_name='cabinet_profile',
    )

    # Host role ---------------------------------------------------------------
    hosts_carriers = models.BooleanField(
        default=False,
        help_text='Devices of this type can have Carriers (DIN rails, plates, …) attached.',
    )
    internal_width_mm = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Usable interior width in mm. Omit to render without an outer outline.',
    )
    internal_height_mm = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Usable interior height in mm.',
    )
    internal_depth_mm = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Usable interior depth in mm. Informational only.',
    )

    # Mountable role ----------------------------------------------------------
    mountable_on = models.CharField(
        max_length=30,
        blank=True,
        choices=CarrierTypeChoices,
        help_text='Carrier type this device mounts on (DIN rail, subrack, …). Leave blank if not mountable.',
    )
    mountable_subtype = models.CharField(
        max_length=30,
        blank=True,
        choices=CarrierSubtypeChoices,
        help_text='Specific carrier subtype (e.g. TS35, HP-3U, RiLine 60). Leave blank to accept any subtype.',
    )
    footprint_primary = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Width in carrier units (DIN modules, HP, or mm — matches the carrier\'s unit).',
    )
    footprint_secondary = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Height in carrier units. Used only for 2D carriers (mounting plate).',
    )

    class Meta:
        ordering = ('device_type',)
        verbose_name = 'Device Type Profile'
        verbose_name_plural = 'Device Type Profiles'

    def __str__(self):
        return f'{self.device_type} — cabinet profile'

    def get_absolute_url(self):
        return reverse('plugins:netbox_cabinet_view:devicetypeprofile', args=[self.pk])

    def clean(self):
        super().clean()
        if self.mountable_on and not self.footprint_primary:
            raise ValidationError({
                'footprint_primary': 'Required when a mountable carrier type is set.',
            })
        if self.mountable_subtype and not self.mountable_on:
            raise ValidationError({
                'mountable_on': 'Must be set when a mountable subtype is chosen.',
            })
        if (
            self.mountable_on
            and self.mountable_subtype
            and self.mountable_subtype not in CARRIER_TYPE_SUBTYPES.get(self.mountable_on, set())
        ):
            raise ValidationError({
                'mountable_subtype': (
                    f'Subtype "{self.mountable_subtype}" is not valid for carrier type '
                    f'"{self.mountable_on}".'
                ),
            })


# ---------------------------------------------------------------------------
# Carrier
# ---------------------------------------------------------------------------

class Carrier(NetBoxModel):
    """
    A geometric mounting structure inside a host Device.

    Four carrier types are supported:

    * **din_rail** — 1D rail, positions in `position` / `size` (units: mm, DIN
      module 17.5 mm, …). Orientation horizontal or vertical.
    * **subrack** — 1D Eurocard rail, positions in HP (5.08 mm) or mm.
    * **mounting_plate** — 2D back plate, positions in `position_x/y`, sizes in
      `size_x/y` (mm).
    * **busbar** — 1D copper bar, positions in mm (typically).

    The carrier's `offset_x_mm` / `offset_y_mm` place it inside the host
    device's internal area (from the top-left of the host's interior).
    """

    host_device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.CASCADE,
        related_name='cabinet_carriers',
        help_text='The enclosure/rail/plate device that carries this structure.',
    )
    name = models.CharField(max_length=100)
    carrier_type = models.CharField(
        max_length=30,
        choices=CarrierTypeChoices,
    )
    subtype = models.CharField(
        max_length=30,
        blank=True,
        choices=CarrierSubtypeChoices,
        help_text='Specific carrier subtype (optional but recommended — controls compatibility checks).',
    )
    orientation = models.CharField(
        max_length=20,
        default=OrientationChoices.HORIZONTAL,
        choices=OrientationChoices,
        help_text='1D carriers only. Ignored for mounting plates.',
    )
    unit = models.CharField(
        max_length=20,
        default=UnitChoices.MM,
        choices=UnitChoices,
        help_text='Unit used by positions and sizes on this carrier.',
    )

    offset_x_mm = models.PositiveIntegerField(
        default=0,
        help_text='X offset inside the host device (mm from the left of the interior).',
    )
    offset_y_mm = models.PositiveIntegerField(
        default=0,
        help_text='Y offset inside the host device (mm from the top of the interior).',
    )

    # 1D carriers (din_rail, subrack, busbar)
    length_mm = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Physical length of the rail/bar in mm. Required for 1D carriers.',
    )
    # 2D carriers (mounting_plate)
    width_mm = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Plate width in mm. Required for 2D carriers.',
    )
    height_mm = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Plate height in mm. Required for 2D carriers.',
    )

    description = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ('host_device', 'name')
        verbose_name = 'Carrier'
        verbose_name_plural = 'Carriers'

    def __str__(self):
        return f'{self.host_device} — {self.name}'

    def get_absolute_url(self):
        return reverse('plugins:netbox_cabinet_view:carrier', args=[self.pk])

    def get_carrier_type_color(self):
        return CarrierTypeChoices.colors.get(self.carrier_type)

    @property
    def is_one_d(self):
        return self.carrier_type in ONE_D_CARRIER_TYPES

    @property
    def is_two_d(self):
        return self.carrier_type in TWO_D_CARRIER_TYPES

    @property
    def mm_per_unit(self) -> float:
        return UNIT_TO_MM.get(self.unit, 1.0)

    def units_to_mm(self, n) -> float:
        if n is None:
            return 0.0
        return float(n) * self.mm_per_unit

    @property
    def capacity_units(self) -> int:
        """
        How many carrier-units fit on this carrier (1D only).

        Returns 0 for 2D carriers.
        """
        if not self.is_one_d or not self.length_mm:
            return 0
        return int(self.length_mm / self.mm_per_unit)

    def clean(self):
        super().clean()

        # 1D vs 2D field coherence
        if self.is_one_d:
            if not self.length_mm:
                raise ValidationError({
                    'length_mm': f'Required for {self.carrier_type} carriers.',
                })
            if self.width_mm or self.height_mm:
                raise ValidationError({
                    'width_mm': '2D dimensions are only valid for mounting plates.',
                })
        elif self.is_two_d:
            if not self.width_mm or not self.height_mm:
                raise ValidationError({
                    'width_mm': 'width_mm and height_mm are required for mounting plates.',
                })
            if self.length_mm:
                raise ValidationError({
                    'length_mm': 'length_mm is only valid for 1D carriers (DIN rail, subrack, busbar).',
                })

        # Subtype must belong to carrier_type
        if (
            self.subtype
            and self.subtype not in CARRIER_TYPE_SUBTYPES.get(self.carrier_type, set())
        ):
            raise ValidationError({
                'subtype': (
                    f'Subtype "{self.subtype}" is not valid for carrier type '
                    f'"{self.carrier_type}".'
                ),
            })


# ---------------------------------------------------------------------------
# Mount
# ---------------------------------------------------------------------------

class Mount(NetBoxModel):
    """
    A device placement on a Carrier.

    Exactly one of `device`, `device_bay`, or `module_bay` must be set:

    * `device` — a standalone `dcim.Device` is mounted directly on the carrier.
      Typical for bare DIN-rail installations.
    * `device_bay` — the mount represents a chassis child slot. Resolves to
      `device_bay.installed_device` at render time. Typical for WDM shelves,
      blade chassis, parent/child device relationships.
    * `module_bay` — the mount represents a modular chassis slot. Resolves to
      `module_bay.installed_module` at render time. Typical for PLC backplanes
      and line-card chassis.

    For 1D carriers (DIN rail, subrack, busbar), `position` and `size` are
    populated in the carrier's own units. For 2D carriers (mounting plate),
    `position_x`, `position_y`, `size_x`, `size_y` are populated in mm.
    """

    carrier = models.ForeignKey(
        to=Carrier,
        on_delete=models.CASCADE,
        related_name='mounts',
    )

    # Exactly one of these three is populated (XOR enforced in clean()).
    device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='cabinet_mounts',
    )
    device_bay = models.ForeignKey(
        to='dcim.DeviceBay',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='cabinet_mounts',
    )
    module_bay = models.ForeignKey(
        to='dcim.ModuleBay',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='cabinet_mounts',
    )

    # 1D placement (din_rail, subrack, busbar)
    position = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Starting position in carrier units (1-indexed for discrete units, mm for mm units).',
    )
    size = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text=(
            'Width in carrier units. Leave blank to default to the mounted '
            "device's DeviceTypeProfile.footprint_primary (slots are fixed-width)."
        ),
    )

    # 2D placement (mounting_plate)
    position_x = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='X position in mm (mounting plates only).',
    )
    position_y = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Y position in mm (mounting plates only).',
    )
    size_x = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=(
            'Width in mm (mounting plates only). Leave blank to default to '
            "the mounted device's DeviceTypeProfile.footprint_primary."
        ),
    )
    size_y = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=(
            'Height in mm (mounting plates only). Leave blank to default to '
            "the mounted device's DeviceTypeProfile.footprint_secondary."
        ),
    )

    class Meta:
        ordering = ('carrier', 'position', 'position_x', 'position_y')
        verbose_name = 'Mount'
        verbose_name_plural = 'Mounts'
        constraints = [
            models.UniqueConstraint(
                fields=('device',),
                condition=Q(device__isnull=False),
                name='unique_mount_device',
            ),
            models.UniqueConstraint(
                fields=('device_bay',),
                condition=Q(device_bay__isnull=False),
                name='unique_mount_device_bay',
            ),
            models.UniqueConstraint(
                fields=('module_bay',),
                condition=Q(module_bay__isnull=False),
                name='unique_mount_module_bay',
            ),
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _target_summary(self) -> str:
        if self.device_id:
            return str(self.device)
        if self.device_bay_id:
            return f'bay:{self.device_bay}'
        if self.module_bay_id:
            return f'modbay:{self.module_bay}'
        return '(unassigned)'

    def __str__(self):
        if self.carrier_id and self.carrier.is_two_d:
            loc = f'({self.position_x or 0},{self.position_y or 0})'
        else:
            loc = f'@{self.position or 0}'
        return f'{self._target_summary()} {loc}'

    def get_absolute_url(self):
        return reverse('plugins:netbox_cabinet_view:mount', args=[self.pk])

    @property
    def effective_device(self):
        """
        The Device this mount visually represents, if any.

        * Direct device mount → the device itself.
        * DeviceBay mount → the bay's installed_device (may be None).
        * ModuleBay mount → the parent device of the bay (for role colour / URL fallback).
        """
        if self.device_id:
            return self.device
        if self.device_bay_id and self.device_bay.installed_device_id:
            return self.device_bay.installed_device
        if self.module_bay_id:
            return self.module_bay.device
        return None

    @property
    def effective_module(self):
        if self.module_bay_id:
            return getattr(self.module_bay, 'installed_module', None)
        return None

    @property
    def effective_profile(self):
        """
        DeviceTypeProfile of the mounted device, if any.

        Slot sizes (``size``, ``size_x``, ``size_y``) default to this profile's
        ``footprint_primary`` / ``footprint_secondary`` when the user leaves
        them blank on the form. ModuleBay-backed mounts don't get a profile
        default in v1 (ModuleType has no profile table yet).
        """
        dev = None
        if self.device_id:
            dev = self.device
        elif self.device_bay_id and self.device_bay.installed_device_id:
            dev = self.device_bay.installed_device
        if dev is None:
            return None
        return getattr(dev.device_type, 'cabinet_profile', None)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        super().clean()

        # 1. Three-way XOR: exactly one target populated.
        targets = [self.device_id, self.device_bay_id, self.module_bay_id]
        populated = sum(1 for t in targets if t)
        if populated != 1:
            raise ValidationError(
                'A Mount must reference exactly one of: device, device_bay, or module_bay.'
            )

        if not self.carrier_id:
            return

        carrier = self.carrier

        # 2. Auto-fill slot size from the mounted device's profile footprint
        #    when the user left it blank. Slots are conceptually fixed-width;
        #    the user only needs to pick a position.
        profile = self.effective_profile
        if profile:
            if carrier.is_one_d and self.size is None and profile.footprint_primary:
                self.size = profile.footprint_primary
            elif carrier.is_two_d:
                if self.size_x is None and profile.footprint_primary:
                    self.size_x = profile.footprint_primary
                if self.size_y is None and profile.footprint_secondary:
                    self.size_y = profile.footprint_secondary

        # 3. Field coherence: 1D vs 2D
        if carrier.is_one_d:
            if self.position is None:
                raise ValidationError({
                    'position': f'Required for {carrier.carrier_type} carriers.',
                })
            if self.size is None:
                raise ValidationError({
                    'size': (
                        'Required for 1D carriers. Either set a value or '
                        "configure the mounted device's DeviceTypeProfile.footprint_primary."
                    ),
                })
            if any(v is not None for v in (self.position_x, self.position_y, self.size_x, self.size_y)):
                raise ValidationError({
                    'position_x': '2D position fields are only valid for mounting plates.',
                })

            # Bounds
            end = self.position + self.size - 1
            if self.position < 1 or end > carrier.capacity_units:
                raise ValidationError({
                    'position': (
                        f'Mount occupies units {self.position}–{end}, but the carrier '
                        f'has only {carrier.capacity_units} units.'
                    ),
                })

            # Overlap with sibling mounts (1D)
            siblings = carrier.mounts.exclude(pk=self.pk).filter(position__isnull=False)
            my_range = set(range(self.position, self.position + self.size))
            for other in siblings:
                other_range = set(range(other.position, other.position + (other.size or 1)))
                overlap = my_range & other_range
                if overlap:
                    raise ValidationError({
                        'position': f'Overlaps with {other._target_summary()} at units {sorted(overlap)}.',
                    })

        elif carrier.is_two_d:
            if None in (self.position_x, self.position_y, self.size_x, self.size_y):
                raise ValidationError({
                    'position_x': 'position_x, position_y, size_x, and size_y are required for mounting plates.',
                })
            if self.position is not None or self.size not in (None, 1):
                raise ValidationError({
                    'position': '1D position/size are not valid for mounting plates.',
                })

            if self.position_x + self.size_x > (carrier.width_mm or 0):
                raise ValidationError({
                    'size_x': f'Mount extends beyond carrier width ({carrier.width_mm} mm).',
                })
            if self.position_y + self.size_y > (carrier.height_mm or 0):
                raise ValidationError({
                    'size_y': f'Mount extends beyond carrier height ({carrier.height_mm} mm).',
                })

            # Overlap detection (2D bounding boxes)
            siblings = carrier.mounts.exclude(pk=self.pk).filter(position_x__isnull=False)
            for other in siblings:
                if (
                    self.position_x < (other.position_x + other.size_x)
                    and (self.position_x + self.size_x) > other.position_x
                    and self.position_y < (other.position_y + other.size_y)
                    and (self.position_y + self.size_y) > other.position_y
                ):
                    raise ValidationError({
                        'position_x': f'Overlaps with {other._target_summary()}.',
                    })

        # 3. Ownership: device_bay/module_bay must belong to the carrier host device.
        if self.device_bay_id and self.device_bay.device_id != carrier.host_device_id:
            raise ValidationError({
                'device_bay': 'DeviceBay must belong to the carrier\'s host device.',
            })
        if self.module_bay_id and self.module_bay.device_id != carrier.host_device_id:
            raise ValidationError({
                'module_bay': 'ModuleBay must belong to the carrier\'s host device.',
            })

        # 4. Compatibility: mounted device's profile must agree with the carrier.
        eff = None
        if self.device_id:
            eff = self.device
        elif self.device_bay_id:
            eff = self.device_bay.installed_device  # may be None if bay is empty
        if eff is not None:
            profile = getattr(eff.device_type, 'cabinet_profile', None)
            if profile and profile.mountable_on:
                if profile.mountable_on != carrier.carrier_type:
                    raise ValidationError({
                        'device': (
                            f'Device type declares mountable_on="{profile.mountable_on}" '
                            f'but carrier type is "{carrier.carrier_type}".'
                        ),
                    })
                if (
                    profile.mountable_subtype
                    and carrier.subtype
                    and profile.mountable_subtype != carrier.subtype
                ):
                    raise ValidationError({
                        'device': (
                            f'Device type declares mountable_subtype="{profile.mountable_subtype}" '
                            f'but carrier subtype is "{carrier.subtype}".'
                        ),
                    })
