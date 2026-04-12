from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse

from netbox.models import NetBoxModel

from .choices import (
    MOUNT_TYPE_SUBTYPES,
    MountFaceChoices,
    MountSubtypeChoices,
    MountTypeChoices,
    GRID_MOUNT_TYPES,
    ONE_D_MOUNT_TYPES,
    OrientationChoices,
    TWO_D_MOUNT_TYPES,
    UNIT_TO_MM,
    UnitChoices,
)


# ---------------------------------------------------------------------------
# DeviceMountProfile (formerly DeviceTypeProfile)
# ---------------------------------------------------------------------------

class DeviceMountProfile(NetBoxModel):
    """
    Per-DeviceType declaration of cabinet-view mounting behaviour.

    A single profile on a DeviceType can cover two roles:

    * **Host**: `hosts_mounts=True` means devices of this type are enclosures
      / rails / plates / subracks that can themselves carry other devices. The
      `internal_*` dimensions describe the usable area inside the host.
    * **Mountable**: `mountable_on` declares that devices of this type clip onto
      mounts of the given type and subtype. `footprint_primary` gives the
      width in mount units; `footprint_secondary` gives the height for 2D
      mounts (mounting plates).

    A DeviceType can be both (a subrack that is itself mounted on a plate), or
    either, or neither. One profile per DeviceType.

    Named ``DeviceMountProfile`` (renamed from ``DeviceTypeProfile`` in v0.4.0)
    for symmetry with ``ModuleMountProfile`` and to avoid implying kinship with
    NetBox 4.5's core ``dcim.ModuleTypeProfile`` which is an unrelated concept
    (reusable attribute schema, not mount geometry).
    """

    device_type = models.OneToOneField(
        to='dcim.DeviceType',
        on_delete=models.CASCADE,
        related_name='cabinet_profile',
    )

    # Host role ---------------------------------------------------------------
    hosts_mounts = models.BooleanField(
        default=False,
        help_text='Devices of this type can have Mounts (DIN rails, plates, …) attached.',
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
        choices=MountTypeChoices,
        help_text='Mount type this device mounts on (DIN rail, subrack, …). Leave blank if not mountable.',
    )
    mountable_subtype = models.CharField(
        max_length=30,
        blank=True,
        choices=MountSubtypeChoices,
        help_text='Specific mount subtype (e.g. TS35, HP-3U, 60 mm pitch busbar). Leave blank to accept any subtype.',
    )
    footprint_primary = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Width in mount units (DIN modules, HP, or mm — matches the mount\'s unit).',
    )
    footprint_secondary = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Height in mount units. Used only for 2D mounts (mounting plate).',
    )

    class Meta:
        ordering = ('device_type',)
        verbose_name = 'Device Mount Profile'
        verbose_name_plural = 'Device Mount Profiles'

    def __str__(self):
        return f'{self.device_type} — mount profile'

    def get_absolute_url(self):
        return reverse('plugins:netbox_cabinet_view:devicemountprofile', args=[self.pk])

    def clean(self):
        super().clean()
        if self.mountable_on and not self.footprint_primary:
            raise ValidationError({
                'footprint_primary': 'Required when a mountable mount type is set.',
            })
        if self.mountable_subtype and not self.mountable_on:
            raise ValidationError({
                'mountable_on': 'Must be set when a mountable subtype is chosen.',
            })
        if (
            self.mountable_on
            and self.mountable_subtype
            and self.mountable_subtype not in MOUNT_TYPE_SUBTYPES.get(self.mountable_on, set())
        ):
            raise ValidationError({
                'mountable_subtype': (
                    f'Subtype "{self.mountable_subtype}" is not valid for mount type '
                    f'"{self.mountable_on}".'
                ),
            })


# ---------------------------------------------------------------------------
# ModuleMountProfile (new in v0.4.0)
# ---------------------------------------------------------------------------

class ModuleMountProfile(NetBoxModel):
    """
    Per-ModuleType declaration of cabinet-view mounting behaviour for
    plug-in modules.

    Mirror of ``DeviceMountProfile``'s "mountable" role, scoped to
    ``dcim.ModuleType``. When a Placement is created with
    ``module_bay=X`` and the bay's ``installed_module.module_type``
    has a profile, the Placement's ``size`` (1D/grid) or
    ``size_x``/``size_y`` (2D) auto-fill from this profile's
    ``footprint_primary`` / ``footprint_secondary``.

    ModuleTypes don't host mounts (no ``hosts_mounts`` field here)
    and don't have interior dimensions — modules are always themselves
    mounted on some containing device's mount. This model captures
    only the "where does this module fit" side of the story.

    Not to be confused with NetBox 4.5's core ``dcim.ModuleTypeProfile``
    which is an unrelated concept — a reusable attribute schema
    (key/value definitions) inheritable by ModuleTypes.
    """

    module_type = models.OneToOneField(
        to='dcim.ModuleType',
        on_delete=models.CASCADE,
        related_name='cabinet_profile',
    )

    mountable_on = models.CharField(
        max_length=30,
        blank=True,
        choices=MountTypeChoices,
        help_text='Mount type this module fits on. Leave blank to accept any mount type.',
    )
    mountable_subtype = models.CharField(
        max_length=30,
        blank=True,
        choices=MountSubtypeChoices,
        help_text='Specific mount subtype (HP-3U, TS35, …). Leave blank to accept any subtype.',
    )
    footprint_primary = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Width in mount units (HP, DIN modules, or mm — matches the mount\'s unit).',
    )
    footprint_secondary = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Height in mount units. 2D mounts (mounting plate) only.',
    )

    class Meta:
        ordering = ('module_type',)
        verbose_name = 'Module Mount Profile'
        verbose_name_plural = 'Module Mount Profiles'

    def __str__(self):
        return f'{self.module_type} — mount profile'

    def get_absolute_url(self):
        return reverse('plugins:netbox_cabinet_view:modulemountprofile', args=[self.pk])

    def clean(self):
        super().clean()
        if self.mountable_on and not self.footprint_primary:
            raise ValidationError({
                'footprint_primary': 'Required when a mountable mount type is set.',
            })
        if self.mountable_subtype and not self.mountable_on:
            raise ValidationError({
                'mountable_on': 'Must be set when a mountable subtype is chosen.',
            })
        if (
            self.mountable_on
            and self.mountable_subtype
            and self.mountable_subtype not in MOUNT_TYPE_SUBTYPES.get(self.mountable_on, set())
        ):
            raise ValidationError({
                'mountable_subtype': (
                    f'Subtype "{self.mountable_subtype}" is not valid for mount type '
                    f'"{self.mountable_on}".'
                ),
            })


# ---------------------------------------------------------------------------
# Mount (formerly Carrier)
# ---------------------------------------------------------------------------

class Mount(NetBoxModel):
    """
    A geometric mounting structure inside a host Device.

    Five mount types are supported:

    * **din_rail** — 1D rail, positions in `position` / `size` (units: mm, DIN
      module 17.5 mm, …). Orientation horizontal or vertical.
    * **subrack** — 1D Eurocard rail, positions in HP (5.08 mm) or mm.
    * **mounting_plate** — 2D back plate, positions in `position_x/y`, sizes in
      `size_x/y` (mm).
    * **busbar** — 1D copper bar, positions in mm (typically).
    * **grid** — multi-row grid (rows of 1D strips), positions in `(row, position)`.

    The mount's `offset_x_mm` / `offset_y_mm` place it inside the host
    device's internal area (from the top-left of the host's interior).
    """

    host_device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.CASCADE,
        related_name='cabinet_mounts',
        help_text='The enclosure/rail/plate device that carries this structure.',
    )
    name = models.CharField(max_length=100)
    mount_type = models.CharField(
        max_length=30,
        choices=MountTypeChoices,
    )
    subtype = models.CharField(
        max_length=30,
        blank=True,
        choices=MountSubtypeChoices,
        help_text='Specific mount subtype (optional but recommended — controls compatibility checks).',
    )
    orientation = models.CharField(
        max_length=20,
        default=OrientationChoices.HORIZONTAL,
        choices=OrientationChoices,
        help_text='1D mounts only. Ignored for mounting plates.',
    )
    unit = models.CharField(
        max_length=20,
        default=UnitChoices.MM,
        choices=UnitChoices,
        help_text='Unit used by positions and sizes on this mount.',
    )

    offset_x_mm = models.PositiveIntegerField(
        default=0,
        help_text='X offset inside the host device (mm from the left of the interior).',
    )
    offset_y_mm = models.PositiveIntegerField(
        default=0,
        help_text='Y offset inside the host device (mm from the top of the interior).',
    )

    # 1D mounts (din_rail, subrack, busbar) and grid (length of each row)
    length_mm = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Physical length of the rail/bar in mm. Required for 1D and grid mounts.',
    )
    # 2D mounts (mounting_plate)
    width_mm = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Plate width in mm. Required for 2D mounts.',
    )
    height_mm = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Plate height in mm. Required for 2D mounts.',
    )
    # Grid mounts only
    rows = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Number of rows (bars) in a grid mount. Required for grid mounts.',
    )
    row_height_mm = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Vertical spacing between grid rows in mm. Required for grid mounts.',
    )

    description = models.CharField(max_length=500, blank=True)

    # Feature 1 (v0.5.0): per-face mounting. Blank = both faces
    # (default, backward-compatible). 'front' / 'rear' restricts the
    # mount to one face of the parent device, so the SVG renderer can
    # draw different layouts depending on which face of the rack
    # elevation is being rendered.
    face = models.CharField(
        max_length=10,
        blank=True,
        default='',
        choices=MountFaceChoices,
        help_text='Which device face this mount renders on. Blank = both faces.',
    )

    class Meta:
        ordering = ('host_device', 'name')
        verbose_name = 'Mount'
        verbose_name_plural = 'Mounts'

    def __str__(self):
        return f'{self.host_device} — {self.name}'

    def get_absolute_url(self):
        return reverse('plugins:netbox_cabinet_view:mount', args=[self.pk])

    def get_mount_type_color(self):
        return MountTypeChoices.colors.get(self.mount_type)

    @property
    def is_one_d(self):
        return self.mount_type in ONE_D_MOUNT_TYPES

    @property
    def is_two_d(self):
        return self.mount_type in TWO_D_MOUNT_TYPES

    @property
    def is_grid(self):
        return self.mount_type in GRID_MOUNT_TYPES

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
        How many mount-units fit along a single row of this mount.

        Returns 0 for 2D mounts.
        """
        if not (self.is_one_d or self.is_grid) or not self.length_mm:
            return 0
        return int(self.length_mm / self.mm_per_unit)

    def clean(self):
        super().clean()

        # 1D / 2D / grid field coherence
        if self.is_one_d:
            if not self.length_mm:
                raise ValidationError({
                    'length_mm': f'Required for {self.mount_type} mounts.',
                })
            if self.width_mm or self.height_mm:
                raise ValidationError({
                    'width_mm': '2D dimensions are only valid for mounting plates.',
                })
            if self.rows or self.row_height_mm:
                raise ValidationError({
                    'rows': 'Grid fields (rows, row_height_mm) are only valid for grid mounts.',
                })
        elif self.is_two_d:
            if not self.width_mm or not self.height_mm:
                raise ValidationError({
                    'width_mm': 'width_mm and height_mm are required for mounting plates.',
                })
            if self.length_mm:
                raise ValidationError({
                    'length_mm': 'length_mm is only valid for 1D mounts (DIN rail, subrack, busbar) or grid mounts.',
                })
            if self.rows or self.row_height_mm:
                raise ValidationError({
                    'rows': 'Grid fields (rows, row_height_mm) are only valid for grid mounts.',
                })
        elif self.is_grid:
            if not self.length_mm:
                raise ValidationError({
                    'length_mm': 'Required for grid mounts (row length).',
                })
            if not self.rows or self.rows < 1:
                raise ValidationError({
                    'rows': 'Required for grid mounts (number of rows/bars, minimum 1).',
                })
            if not self.row_height_mm:
                raise ValidationError({
                    'row_height_mm': 'Required for grid mounts (vertical spacing between rows).',
                })
            if self.width_mm or self.height_mm:
                raise ValidationError({
                    'width_mm': '2D dimensions are only valid for mounting plates.',
                })

        # Subtype must belong to mount_type
        if (
            self.subtype
            and self.subtype not in MOUNT_TYPE_SUBTYPES.get(self.mount_type, set())
        ):
            raise ValidationError({
                'subtype': (
                    f'Subtype "{self.subtype}" is not valid for mount type '
                    f'"{self.mount_type}".'
                ),
            })


# ---------------------------------------------------------------------------
# Placement (formerly Mount)
# ---------------------------------------------------------------------------

class Placement(NetBoxModel):
    """
    A device placement on a Mount.

    Exactly one of `device`, `device_bay`, or `module_bay` must be set:

    * `device` — a standalone `dcim.Device` is placed directly on the mount.
      Typical for bare DIN-rail installations.
    * `device_bay` — the placement represents a chassis child slot. Resolves
      to `device_bay.installed_device` at render time. Typical for WDM
      shelves, blade chassis, parent/child device relationships.
    * `module_bay` — the placement represents a modular chassis slot. Resolves
      to `module_bay.installed_module` at render time. Typical for PLC
      backplanes and line-card chassis.

    For 1D mounts (DIN rail, subrack, busbar), `position` and `size` are
    populated in the mount's own units. For 2D mounts (mounting plate),
    `position_x`, `position_y`, `size_x`, `size_y` are populated in mm.
    """

    mount = models.ForeignKey(
        to=Mount,
        on_delete=models.CASCADE,
        related_name='placements',
    )

    # Exactly one of these three is populated (XOR enforced in clean()).
    device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='cabinet_placements',
    )
    device_bay = models.ForeignKey(
        to='dcim.DeviceBay',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='cabinet_placements',
    )
    module_bay = models.ForeignKey(
        to='dcim.ModuleBay',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='cabinet_placements',
    )

    # 1D placement (din_rail, subrack, busbar) and grid row placement
    position = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Starting position along the mount (or within a grid row), in mount units.',
    )
    size = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text=(
            'Width in mount units. Leave blank to default to the mounted '
            "device's DeviceMountProfile.footprint_primary (slots are fixed-width)."
        ),
    )

    # Grid placement (grid mounts only)
    row = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='1-indexed row (bar) number on a grid mount.',
    )
    row_span = models.PositiveSmallIntegerField(
        null=True, blank=True, default=1,
        help_text='How many rows this placement spans starting at `row`. Defaults to 1.',
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
            "the mounted device's DeviceMountProfile.footprint_primary."
        ),
    )
    size_y = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=(
            'Height in mm (mounting plates only). Leave blank to default to '
            "the mounted device's DeviceMountProfile.footprint_secondary."
        ),
    )

    class Meta:
        ordering = ('mount', 'position', 'position_x', 'position_y')
        verbose_name = 'Placement'
        verbose_name_plural = 'Placements'
        constraints = [
            models.UniqueConstraint(
                fields=('device',),
                condition=Q(device__isnull=False),
                name='unique_placement_device',
            ),
            models.UniqueConstraint(
                fields=('device_bay',),
                condition=Q(device_bay__isnull=False),
                name='unique_placement_device_bay',
            ),
            models.UniqueConstraint(
                fields=('module_bay',),
                condition=Q(module_bay__isnull=False),
                name='unique_placement_module_bay',
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
        if self.mount_id and self.mount.is_two_d:
            loc = f'({self.position_x or 0},{self.position_y or 0})'
        else:
            loc = f'@{self.position or 0}'
        return f'{self._target_summary()} {loc}'

    def get_absolute_url(self):
        return reverse('plugins:netbox_cabinet_view:placement', args=[self.pk])

    # ------------------------------------------------------------------
    # Persistence — Finding A (v0.4.0): make full_clean() run on every
    # save() code path, not just form submissions.
    #
    # The v0.3.0 seed command used update_or_create(), which bypasses
    # full_clean(). That meant the profile-driven size auto-fill in
    # clean() never ran, every Mount.size defaulted to None -> the
    # renderer fell back to size=1, and the marshalling cabinet's 48
    # terminal blocks all rendered as 2-pixel hairlines.
    #
    # Overriding save() to call full_clean() makes the auto-fill fire
    # for forms, shell, admin, seeds, and API clients alike. Tiny
    # perf cost on a plugin that creates ~50 placements per session
    # is irrelevant; the consistency gain is the point.
    # ------------------------------------------------------------------

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def effective_device(self):
        """
        The Device this placement visually represents, if any.

        * Direct device placement → the device itself.
        * DeviceBay placement → the bay's installed_device (may be None).
        * ModuleBay placement → the parent device of the bay (for role
          colour / URL fallback).
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
        DeviceMountProfile or ModuleMountProfile for the placed entity, if any.

        Slot sizes (``size``, ``size_x``, ``size_y``) default to this
        profile's ``footprint_primary`` / ``footprint_secondary`` when
        the user leaves them blank on the form. Resolution order:

        * ``device`` → the device's DeviceType.cabinet_profile
        * ``device_bay`` → the installed child device's DeviceType.cabinet_profile
        * ``module_bay`` with installed_module → that ModuleType.cabinet_profile
          (introduced in v0.4.0; modules finally get per-type footprints)
        * anything else → None (empty bay, unresolved placement)
        """
        if self.device_id:
            return getattr(self.device.device_type, 'cabinet_profile', None)
        if self.device_bay_id and self.device_bay.installed_device_id:
            return getattr(self.device_bay.installed_device.device_type, 'cabinet_profile', None)
        if self.module_bay_id:
            mod = getattr(self.module_bay, 'installed_module', None)
            if mod is not None:
                return getattr(mod.module_type, 'cabinet_profile', None)
        return None

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
                'A Placement must reference exactly one of: device, device_bay, or module_bay.'
            )

        if not self.mount_id:
            return

        mount = self.mount

        # 2. Auto-fill slot size from the placed device's profile footprint
        #    when the user left it blank. Slots are conceptually fixed-width;
        #    the user only needs to pick a position.
        profile = self.effective_profile
        if profile:
            if (mount.is_one_d or mount.is_grid) and self.size is None and profile.footprint_primary:
                self.size = profile.footprint_primary
            elif mount.is_two_d:
                if self.size_x is None and profile.footprint_primary:
                    self.size_x = profile.footprint_primary
                if self.size_y is None and profile.footprint_secondary:
                    self.size_y = profile.footprint_secondary

        # 3. Field coherence: 1D / 2D / grid
        if mount.is_one_d:
            if self.position is None:
                raise ValidationError({
                    'position': f'Required for {mount.mount_type} mounts.',
                })
            if self.size is None:
                raise ValidationError({
                    'size': (
                        'Required for 1D mounts. Either set a value or '
                        "configure the placed device's DeviceMountProfile.footprint_primary."
                    ),
                })
            if any(v is not None for v in (self.position_x, self.position_y, self.size_x, self.size_y)):
                raise ValidationError({
                    'position_x': '2D position fields are only valid for mounting plates.',
                })
            if self.row is not None or (self.row_span or 1) != 1:
                raise ValidationError({
                    'row': 'Grid row fields are only valid on grid mounts.',
                })

            # Bounds
            end = self.position + self.size - 1
            if self.position < 1 or end > mount.capacity_units:
                raise ValidationError({
                    'position': (
                        f'Placement occupies units {self.position}–{end}, but the mount '
                        f'has only {mount.capacity_units} units.'
                    ),
                })

            # Overlap with sibling placements (1D). Filter siblings with
            # complete geometry — see 2D overlap check below for the
            # Finding A / pre-v0.4.0 NULL-size caveat.
            siblings = mount.placements.exclude(pk=self.pk).filter(
                position__isnull=False, size__isnull=False,
            )
            my_range = set(range(self.position, self.position + self.size))
            for other in siblings:
                other_range = set(range(other.position, other.position + (other.size or 1)))
                overlap = my_range & other_range
                if overlap:
                    raise ValidationError({
                        'position': f'Overlaps with {other._target_summary()} at units {sorted(overlap)}.',
                    })

        elif mount.is_two_d:
            if None in (self.position_x, self.position_y, self.size_x, self.size_y):
                raise ValidationError({
                    'position_x': 'position_x, position_y, size_x, and size_y are required for mounting plates.',
                })
            if self.position is not None or self.size not in (None, 1):
                raise ValidationError({
                    'position': '1D position/size are not valid for mounting plates.',
                })
            if self.row is not None or (self.row_span or 1) != 1:
                raise ValidationError({
                    'row': 'Grid row fields are only valid on grid mounts.',
                })

            if self.position_x + self.size_x > (mount.width_mm or 0):
                raise ValidationError({
                    'size_x': f'Placement extends beyond mount width ({mount.width_mm} mm).',
                })
            if self.position_y + self.size_y > (mount.height_mm or 0):
                raise ValidationError({
                    'size_y': f'Placement extends beyond mount height ({mount.height_mm} mm).',
                })

            # Overlap detection (2D bounding boxes).
            # Filter siblings with complete geometry — Finding A (v0.4.0)
            # forces full_clean() on every save, but pre-v0.4.0 DB rows
            # may have NULL size_x/size_y because the auto-fill never
            # ran. Such siblings just get skipped here (they will fail
            # their own validation next time they are saved).
            siblings = mount.placements.exclude(pk=self.pk).filter(
                position_x__isnull=False,
                size_x__isnull=False,
                position_y__isnull=False,
                size_y__isnull=False,
            )
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

        elif mount.is_grid:
            if self.row is None:
                raise ValidationError({
                    'row': 'Required for grid mounts (1-indexed row number).',
                })
            if self.position is None:
                raise ValidationError({
                    'position': 'Required for grid mounts (position within the row).',
                })
            if self.size is None:
                raise ValidationError({
                    'size': (
                        'Required for grid mounts. Either set a value or '
                        "configure the placed device's DeviceMountProfile.footprint_primary."
                    ),
                })
            if any(v is not None for v in (self.position_x, self.position_y, self.size_x, self.size_y)):
                raise ValidationError({
                    'position_x': '2D position fields are only valid for mounting plates.',
                })

            span = max(1, self.row_span or 1)
            if self.row < 1 or self.row + span - 1 > (mount.rows or 0):
                raise ValidationError({
                    'row': (
                        f'Placement spans rows {self.row}–{self.row + span - 1}, but the mount '
                        f'has only {mount.rows} rows.'
                    ),
                })

            end = self.position + self.size - 1
            if self.position < 1 or end > mount.capacity_units:
                raise ValidationError({
                    'position': (
                        f'Placement occupies units {self.position}–{end} within a row, but each '
                        f'row has only {mount.capacity_units} units.'
                    ),
                })

            # Overlap detection: any sibling whose (row, row+span, position, size)
            # rectangle intersects ours is a conflict. Filter siblings
            # with complete geometry per the Finding A caveat.
            siblings = mount.placements.exclude(pk=self.pk).filter(
                row__isnull=False, position__isnull=False, size__isnull=False,
            )
            my_row_lo, my_row_hi = self.row, self.row + span - 1
            my_col_lo, my_col_hi = self.position, end
            for other in siblings:
                o_span = max(1, other.row_span or 1)
                o_row_lo, o_row_hi = other.row, other.row + o_span - 1
                o_col_lo = other.position
                o_col_hi = other.position + (other.size or 1) - 1
                if (
                    my_row_lo <= o_row_hi and my_row_hi >= o_row_lo
                    and my_col_lo <= o_col_hi and my_col_hi >= o_col_lo
                ):
                    raise ValidationError({
                        'row': (
                            f'Overlaps with {other._target_summary()} at rows '
                            f'{o_row_lo}–{o_row_hi}, cols {o_col_lo}–{o_col_hi}.'
                        ),
                    })

        # 3. Ownership: device_bay/module_bay must belong to the mount host device.
        if self.device_bay_id and self.device_bay.device_id != mount.host_device_id:
            raise ValidationError({
                'device_bay': 'DeviceBay must belong to the mount\'s host device.',
            })
        if self.module_bay_id and self.module_bay.device_id != mount.host_device_id:
            raise ValidationError({
                'module_bay': 'ModuleBay must belong to the mount\'s host device.',
            })

        # 4. Compatibility: the placed entity's profile must agree with
        #    the mount. Applies to device-backed placements (via
        #    DeviceMountProfile) AND module-backed placements (via
        #    ModuleTypeProfile, new in v0.4.0).
        profile = self.effective_profile
        field_for_error = (
            'device' if (self.device_id or self.device_bay_id) else 'module_bay'
        )
        if profile and profile.mountable_on:
            if profile.mountable_on != mount.mount_type:
                raise ValidationError({
                    field_for_error: (
                        f'Profile declares mountable_on="{profile.mountable_on}" '
                        f'but mount type is "{mount.mount_type}".'
                    ),
                })
            if (
                profile.mountable_subtype
                and mount.subtype
                and profile.mountable_subtype != mount.subtype
            ):
                raise ValidationError({
                    field_for_error: (
                        f'Profile declares mountable_subtype="{profile.mountable_subtype}" '
                        f'but mount subtype is "{mount.subtype}".'
                    ),
                })
