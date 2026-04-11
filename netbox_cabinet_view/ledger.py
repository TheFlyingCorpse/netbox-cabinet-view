"""
Slot ledger — Finding D, v0.4.0.

Produces a tabular, spreadsheet-style view of every slot on every
mount of a host device, including empty ranges and (for modular
hosted devices) ModuleBay sub-rows. The SVG is still the primary
visual, but the ledger is what turns the Layout tab from a picture
into a tool: sortable, searchable, and with per-row "+ mount"
affordances that pre-fill the PlacementForm.

Lives in its own module so it doesn't pull in svgwrite. Gated on
``PLUGINS_CONFIG['netbox_cabinet_view']['SLOT_LEDGER_ENABLED']``
(default False in v0.4.0).

The enumeration logic intentionally mirrors the empty-slot
enumeration used by the SVG renderer's Finding C pass — if one
changes, the other should follow.
"""
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Row dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SubRow:
    """ModuleBay sub-row under a hosted device's primary row."""
    slot_label: str        # e.g. "Slot 3", "R1S2" — copied from ModuleBay.position or .name
    module_name: str       # str(module), which is str(module_type) in NetBox
    module_type: str       # str(module_type)
    role: str              # parent device role name
    empty: bool = False    # True when the bay is empty


@dataclass
class SlotRow:
    """
    One row in the ledger table. Represents either a populated slot
    (with a Placement + resolved device/module), an empty slot range
    (contiguous), an empty ModuleBay-backed Placement, or a dangling
    reference.
    """
    slot_label: str                       # e.g. "1", "3 – 6", "R1S3", "(100, 200) mm"
    size_label: str                       # e.g. "1 HP", "4 HP", "—"
    device_name: str                      # "" for empty rows
    device_url: str                       # "" for empty rows
    role: str                             # "" for empty rows
    type_name: str                        # DeviceType or ModuleType model string
    bay_label: str                        # e.g. "Slot 3 bay" or "—"
    state: str                            # "populated" | "empty" | "bay_empty" | "module_empty" | "dangling"
    action_label: str                     # "edit" | "+ mount" | "install" | "clean"
    action_url: str                       # href for the action cell
    sub_rows: list = field(default_factory=list)  # list of SubRow for hosted-device ModuleBays


@dataclass
class MountSection:
    """One section in the ledger — header (mount name + occupancy bar) plus rows."""
    mount: object                         # the Mount instance (template accesses .name, .subtype, etc.)
    rows: list                            # list[SlotRow]
    populated_count: int
    capacity: int                         # 0 for 2D mounts

    @property
    def occupancy_pct(self) -> int:
        """Occupancy as an integer percent; 0 when capacity is 0."""
        if self.capacity <= 0:
            return 0
        return int(round(100 * self.populated_count / self.capacity))


# ---------------------------------------------------------------------------
# Helpers reused from svg/cabinets.py
# ---------------------------------------------------------------------------

def _natural_sort_key(text):
    """
    Natural sort key for ModuleBay.position strings so "Slot 1" /
    "Slot 2" / "Slot 10" order correctly instead of "Slot 1" / "Slot
    10" / "Slot 2". Everything that isn't a run of digits is lowercased
    and compared lexically.
    """
    import re
    out = []
    for chunk in re.split(r'(\d+)', text or ''):
        if chunk.isdigit():
            out.append((0, int(chunk)))
        else:
            out.append((1, chunk.lower()))
    return out


def _empty_ranges(occupied, capacity):
    """List of (start, end) inclusive empty ranges in [1..capacity]."""
    ranges = []
    start = None
    for pos in range(1, capacity + 1):
        if pos not in occupied:
            if start is None:
                start = pos
        else:
            if start is not None:
                ranges.append((start, pos - 1))
                start = None
    if start is not None:
        ranges.append((start, capacity))
    return ranges


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _placement_add_url(**params):
    """Build a pre-filled placement_add URL. Falls back to '#' on NoReverseMatch."""
    from django.urls import NoReverseMatch, reverse
    try:
        base = reverse('plugins:netbox_cabinet_view:placement_add')
    except NoReverseMatch:
        return '#'
    qs = '&'.join(f'{k}={v}' for k, v in params.items() if v is not None)
    return f'{base}?{qs}' if qs else base


def _sub_rows_for_device(device) -> list:
    """
    β-ledger (Finding D): if the placed device itself has ModuleBays
    with installed modules, emit sub-rows so a single RTU / IED shows
    up as one primary row + one indented row per populated ModuleBay.

    Rules (per v0.4.0 decisions):
      - ONLY show populated ModuleBays. Empty bays that aren't
        explicitly referenced by a Placement stay hidden (don't
        over-claim geometry).
      - Natural-sort by ModuleBay.position so "Slot 1" / "Slot 2" /
        "Slot 10" order correctly.
      - Bay-empty is informational (state="module_empty"), NOT a warning.
    """
    if device is None:
        return []
    bays = list(device.modulebays.all().select_related(
        'installed_module__module_type',
    ))
    # Sort by natural position, then pk as a stable tiebreaker.
    bays.sort(key=lambda b: (_natural_sort_key(b.position or b.name), b.pk))
    out = []
    for bay in bays:
        mod = getattr(bay, 'installed_module', None)
        if mod is None:
            continue  # not populated — don't emit
        mt = mod.module_type
        role = device.role.name if device.role_id else ''
        out.append(SubRow(
            slot_label=bay.position or bay.name,
            module_name=str(mod),
            module_type=str(mt),
            role=role,
            empty=False,
        ))
    return out


def _slot_row_for_placement(placement, mount) -> SlotRow:
    """Build one SlotRow for an occupied Placement. May carry sub-rows."""
    device = None
    if placement.device_id:
        device = placement.device
    elif placement.device_bay_id:
        device = placement.device_bay.installed_device  # may be None (bay empty)

    # Slot label - 1D/grid uses position[..position+size-1], 2D uses (x,y)
    if mount.is_two_d:
        slot_label = f'({placement.position_x}, {placement.position_y}) mm'
        size_label = f'{placement.size_x or "—"} × {placement.size_y or "—"} mm'
    else:
        size = placement.size or 1
        if size == 1:
            slot_label = str(placement.position or 1)
        else:
            slot_label = f'{placement.position or 1} – {(placement.position or 1) + size - 1}'
        # Grid mounts prefix with the row
        if mount.is_grid and placement.row is not None:
            slot_label = f'R{placement.row}·{slot_label}'
        unit = mount.get_unit_display() if hasattr(mount, 'get_unit_display') else ''
        # Pretty-print the unit as HP for Eurocard, "mod" for DIN, or "mm"
        unit_short = {'Millimetres': 'mm',
                      'Eurocard HP (5.08 mm)': 'HP',
                      'DIN module (17.5 mm)': 'mod'}.get(unit, '')
        size_label = f'{size} {unit_short}'.strip()

    # Bay-empty detection (device_bay target without installed_device)
    if placement.device_bay_id and device is None:
        return SlotRow(
            slot_label=slot_label,
            size_label=size_label,
            device_name='(bay empty)',
            device_url='',
            role='',
            type_name='—',
            bay_label=str(placement.device_bay),
            state='bay_empty',
            action_label='install',
            action_url=placement.device_bay.get_absolute_url(),
        )

    # ModuleBay target
    if placement.module_bay_id:
        mod = getattr(placement.module_bay, 'installed_module', None)
        if mod is None:
            return SlotRow(
                slot_label=slot_label,
                size_label=size_label,
                device_name='(bay empty)',
                device_url='',
                role='',
                type_name='—',
                bay_label=str(placement.module_bay),
                state='module_empty',
                action_label='install',
                action_url=placement.module_bay.get_absolute_url(),
            )
        parent = placement.module_bay.device
        role = parent.role.name if parent and parent.role_id else ''
        return SlotRow(
            slot_label=slot_label,
            size_label=size_label,
            device_name=str(mod),
            device_url=mod.get_absolute_url(),
            role=role,
            type_name=str(mod.module_type),
            bay_label=str(placement.module_bay),
            state='populated',
            action_label='edit',
            action_url=placement.get_absolute_url(),
        )

    # Device-backed (direct or device_bay with resolved child)
    role = device.role.name if device and device.role_id else ''
    sub_rows = _sub_rows_for_device(device)
    return SlotRow(
        slot_label=slot_label,
        size_label=size_label,
        device_name=device.name or str(device.device_type) if device else '(none)',
        device_url=device.get_absolute_url() if device else '',
        role=role,
        type_name=str(device.device_type) if device else '—',
        bay_label=str(placement.device_bay) if placement.device_bay_id else '—',
        state='populated',
        action_label='edit',
        action_url=placement.get_absolute_url(),
        sub_rows=sub_rows,
    )


def _empty_slot_rows(mount) -> list:
    """Build SlotRows for empty slot ranges on a 1D or grid mount."""
    capacity = mount.capacity_units
    if capacity <= 0:
        return []

    rows = []
    if mount.is_grid:
        num_rows = max(1, mount.rows or 1)
        per_row = {r: set() for r in range(1, num_rows + 1)}
        for p in mount.placements.all():
            if p.row is None or p.position is None or p.size is None:
                continue
            span = max(1, p.row_span or 1)
            for r in range(p.row, min(p.row + span, num_rows + 1)):
                per_row[r].update(range(p.position, p.position + p.size))
        for r, occupied in per_row.items():
            for start, end in _empty_ranges(occupied, capacity):
                slot_label = f'R{r}·{start}' if start == end else f'R{r}·{start} – {end}'
                rows.append(SlotRow(
                    slot_label=slot_label,
                    size_label=f'{end - start + 1}',
                    device_name='(empty)',
                    device_url='',
                    role='',
                    type_name='—',
                    bay_label='—',
                    state='empty',
                    action_label='+ mount',
                    action_url=_placement_add_url(
                        mount=mount.pk, position=start, row=r,
                    ),
                ))
    else:  # 1D
        occupied = set()
        for p in mount.placements.all():
            if p.position is None or p.size is None:
                continue
            occupied.update(range(p.position, p.position + p.size))
        for start, end in _empty_ranges(occupied, capacity):
            slot_label = str(start) if start == end else f'{start} – {end}'
            rows.append(SlotRow(
                slot_label=slot_label,
                size_label=f'{end - start + 1}',
                device_name='(empty)',
                device_url='',
                role='',
                type_name='—',
                bay_label='—',
                state='empty',
                action_label='+ mount',
                action_url=_placement_add_url(mount=mount.pk, position=start),
            ))
    return rows


def enumerate_ledger(host_device, user=None) -> list:
    """
    Return a list of ``MountSection`` objects ready for the template.
    One section per Mount on the host device, in the same order the
    Mount CRUD lists them.

    Each section contains:
      * populated SlotRows (one per Placement, with optional ModuleBay
        sub-rows under hosted devices)
      * empty-slot SlotRows (one per contiguous empty range on 1D/grid
        mounts; 2D mounts don't emit empty rows because the "empty
        space" is a continuous 2D area, not enumerable)
    """
    sections = []
    mounts_qs = host_device.cabinet_mounts.all().prefetch_related(
        'placements__device__device_type',
        'placements__device__role',
        'placements__device__modulebays__installed_module__module_type',
        'placements__device_bay__installed_device__device_type',
        'placements__device_bay__installed_device__role',
        'placements__device_bay__installed_device__modulebays__installed_module__module_type',
        'placements__module_bay__installed_module__module_type',
        'placements__module_bay__device__role',
    )

    for mount in mounts_qs:
        placements = mount.placements.all()
        if user is not None:
            placements = placements.restrict(user, 'view')

        populated_rows = []
        populated_count = 0

        # Sort populated placements by their position for stable display
        sorted_placements = sorted(
            placements,
            key=lambda p: (
                p.row or 0,
                p.position or 0,
                p.position_x or 0,
                p.position_y or 0,
            ),
        )
        for placement in sorted_placements:
            populated_rows.append(_slot_row_for_placement(placement, mount))
            populated_count += (placement.size or 1) if not mount.is_two_d else 1

        empty_rows = _empty_slot_rows(mount) if not mount.is_two_d else []

        sections.append(MountSection(
            mount=mount,
            rows=populated_rows + empty_rows,
            populated_count=populated_count,
            capacity=mount.capacity_units,
        ))

    return sections
