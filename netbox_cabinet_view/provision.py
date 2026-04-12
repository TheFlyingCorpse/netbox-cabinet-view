"""
Auto-provisioning — Feature 3, v0.5.0.

Two modes:

**Mode A** — ``auto_provision_placements(mount)``: given an existing
Mount, create one Placement per DeviceBay / ModuleBay on the mount's
host device that doesn't already have a Placement on this mount.
Positions are sequential at footprint-width intervals.

**Mode B** — ``auto_provision_mount_and_placements(device)``: create
a Mount (type + unit + length derived from the bays' profiles) and
then call Mode A to fill it. One-click from zero to a fully
populated mount.
"""
import logging
import re
from collections import Counter

from django.core.exceptions import ValidationError

from .choices import UNIT_TO_MM, MountTypeChoices, UnitChoices
from .models import Mount, Placement

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _natural_sort_key(text):
    """Natural sort so "Slot 2" < "Slot 10"."""
    out = []
    for chunk in re.split(r'(\d+)', text or ''):
        if chunk.isdigit():
            out.append((0, int(chunk)))
        else:
            out.append((1, chunk.lower()))
    return out


def _bay_footprint(bay):
    """
    Return the footprint_primary for a bay's installed entity, or 1
    as a fallback. Works for both DeviceBay and ModuleBay.
    """
    # DeviceBay → installed_device → DeviceType → cabinet_profile
    child = getattr(bay, 'installed_device', None)
    if child is not None:
        profile = getattr(child.device_type, 'cabinet_profile', None)
        if profile and profile.footprint_primary:
            return profile.footprint_primary

    # ModuleBay → installed_module → ModuleType → cabinet_profile
    module = getattr(bay, 'installed_module', None)
    if module is not None:
        profile = getattr(module.module_type, 'cabinet_profile', None)
        if profile and profile.footprint_primary:
            return profile.footprint_primary

    return 1


def _bay_mountable_on(bay):
    """
    Return the ``mountable_on`` value from the bay's installed
    entity's profile, or '' if unavailable.
    """
    child = getattr(bay, 'installed_device', None)
    if child is not None:
        profile = getattr(child.device_type, 'cabinet_profile', None)
        if profile and profile.mountable_on:
            return profile.mountable_on

    module = getattr(bay, 'installed_module', None)
    if module is not None:
        profile = getattr(module.module_type, 'cabinet_profile', None)
        if profile and profile.mountable_on:
            return profile.mountable_on

    return ''


# ---------------------------------------------------------------------------
# Mode A: Placements only, on an existing Mount
# ---------------------------------------------------------------------------

def auto_provision_placements(mount):
    """
    Create one Placement per unplaced DeviceBay / ModuleBay on the
    mount's host device. Returns ``(created_count, skipped_count)``.

    Bays already referenced by a Placement on **this** mount are
    skipped (idempotent). Bays placed on a **different** mount are
    also skipped (the unique constraint prevents double-placement).

    Positions are sequential starting at 1, incrementing by each
    bay's footprint_primary (from profile, fallback 1). If the
    mount runs out of capacity, remaining bays are skipped.
    """
    host = mount.host_device

    # Collect all bays on the host device, excluding those already
    # placed on ANY mount (the unique constraint is per-bay, not
    # per-mount — a bay can only have one Placement total).
    device_bays = list(
        host.devicebays.all()
        .select_related('installed_device__device_type__cabinet_profile')
        .exclude(cabinet_placements__isnull=False)
    )
    module_bays = list(
        host.modulebays.all()
        .select_related('installed_module__module_type__cabinet_profile')
        .exclude(cabinet_placements__isnull=False)
    )

    # Combine and natural-sort by name.
    all_bays = [(b, 'device_bay') for b in device_bays] + \
               [(b, 'module_bay') for b in module_bays]
    all_bays.sort(key=lambda pair: _natural_sort_key(pair[0].name))

    created = 0
    skipped = 0
    cursor = 1

    for bay, bay_type in all_bays:
        footprint = _bay_footprint(bay)
        kwargs = {
            'mount': mount,
            bay_type: bay,
            'position': cursor,
            # Always set size explicitly so placements succeed even
            # for empty bays (no installed device/module → no profile
            # → clean() can't auto-fill → ValidationError). The
            # footprint is either from the profile or the fallback 1.
            'size': footprint,
        }
        try:
            p = Placement(**kwargs)
            p.save()  # full_clean() runs, auto-fills size, validates bounds
            created += 1
            # Advance cursor by the ACTUAL saved size (which may have
            # been auto-filled by full_clean to the profile footprint).
            cursor += (p.size or footprint)
        except (ValidationError, Exception) as exc:
            log.info(
                'auto_provision: skipped bay %s on mount %s: %s',
                bay.name, mount.name, exc,
            )
            skipped += 1
            # Still advance cursor so the next bay doesn't overlap
            # the position that was attempted.
            cursor += footprint

    return created, skipped


# ---------------------------------------------------------------------------
# Mode B: Mount + Placements, one-click from scratch
# ---------------------------------------------------------------------------

# Default unit per mount type.
_DEFAULT_UNIT = {
    MountTypeChoices.TYPE_SUBRACK: UnitChoices.HP_508,
    MountTypeChoices.TYPE_DIN_RAIL: UnitChoices.MODULE_175,
}


def auto_provision_mount_and_placements(device):
    """
    Create a Mount (type + unit + length derived from the device's
    bays' profiles) and fill it with sequential Placements. Returns
    ``(mount, created_count, skipped_count)``.

    The mount type is determined by majority vote of the bays'
    ``mountable_on`` values. Falls back to ``din_rail`` if no
    profiles declare a preference.

    The mount length is computed as the sum of all bays' footprint
    (in the mount's unit, converted to mm) plus 10% padding.
    """
    # Gather all bays on the device.
    device_bays = list(
        device.devicebays.all()
        .select_related('installed_device__device_type__cabinet_profile')
    )
    module_bays = list(
        device.modulebays.all()
        .select_related('installed_module__module_type__cabinet_profile')
    )
    all_bays = device_bays + module_bays

    if not all_bays:
        return None, 0, 0

    # Majority-vote mount type.
    type_votes = Counter(
        _bay_mountable_on(b) for b in all_bays
    )
    # Remove blank votes.
    type_votes.pop('', None)
    if type_votes:
        mount_type = type_votes.most_common(1)[0][0]
    else:
        mount_type = MountTypeChoices.TYPE_DIN_RAIL

    # Derive unit from mount type.
    unit = _DEFAULT_UNIT.get(mount_type, UnitChoices.MM)
    mm_per_unit = UNIT_TO_MM.get(unit, 1.0)

    # Compute total footprint in mount units, then convert to mm for
    # the mount's length_mm field.
    total_units = sum(_bay_footprint(b) for b in all_bays)
    length_mm = int(total_units * mm_per_unit * 1.1)  # +10% padding

    # Friendly display name for the mount type.
    type_display = {v: label for v, label, _ in MountTypeChoices.CHOICES}.get(mount_type, mount_type)

    mount = Mount(
        host_device=device,
        name=f'Auto-provisioned {type_display}',
        mount_type=mount_type,
        unit=unit,
        length_mm=max(length_mm, 1),
        offset_x_mm=0,
        offset_y_mm=0,
    )
    mount.save()

    created, skipped = auto_provision_placements(mount)
    return mount, created, skipped
