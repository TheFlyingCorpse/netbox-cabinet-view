from utilities.choices import ChoiceSet


class MountTypeChoices(ChoiceSet):
    key = 'Mount.mount_type'

    TYPE_DIN_RAIL       = 'din_rail'
    TYPE_SUBRACK        = 'subrack'
    TYPE_MOUNTING_PLATE = 'mounting_plate'
    TYPE_BUSBAR         = 'busbar'
    TYPE_GRID           = 'grid'

    CHOICES = [
        (TYPE_DIN_RAIL,       'DIN rail',       'blue'),
        (TYPE_SUBRACK,        'Subrack (HP)',   'teal'),
        (TYPE_MOUNTING_PLATE, 'Mounting plate', 'purple'),
        (TYPE_BUSBAR,         'Busbar',         'orange'),
        (TYPE_GRID,           'Grid (multi-row)', 'gray'),
    ]


# Mount types that are one-dimensional (position along a single axis).
ONE_D_MOUNT_TYPES = frozenset((
    MountTypeChoices.TYPE_DIN_RAIL,
    MountTypeChoices.TYPE_SUBRACK,
    MountTypeChoices.TYPE_BUSBAR,
))

# Mount types that are two-dimensional (x, y placement on an area).
TWO_D_MOUNT_TYPES = frozenset((
    MountTypeChoices.TYPE_MOUNTING_PLATE,
))

# Mount types that are multi-row grids (row + position within row).
GRID_MOUNT_TYPES = frozenset((
    MountTypeChoices.TYPE_GRID,
))


class MountSubtypeChoices(ChoiceSet):
    key = 'Mount.subtype'

    # DIN rail variants
    TS35   = 'ts35'
    TS32   = 'ts32'
    TS15   = 'ts15'
    G_RAIL = 'g_rail'

    # Eurocard subrack variants
    HP_3U = 'hp_3u'
    HP_6U = 'hp_6u'
    HP_9U = 'hp_9u'

    # Mounting plate variants
    PLATE_GENERIC = 'plate_generic'

    # Busbar variants (named by mechanical pitch / slot system rather than
    # vendor product line so the taxonomy stays generic).
    BB_60MM_PITCH    = 'bb_60mm_pitch'
    BB_40MM_PITCH    = 'bb_40mm_pitch'
    BB_CLIP_ON       = 'bb_clip_on'
    BB_GENERIC_CU    = 'bb_generic_cu'

    CHOICES = [
        (TS35,             'DIN TS35 (EN 50022)',       'blue'),
        (TS32,             'DIN TS32',                  'cyan'),
        (TS15,             'DIN TS15 (EN 50035)',       'indigo'),
        (G_RAIL,           'G-rail',                    'green'),
        (HP_3U,             'Eurocard 3U (5.08 mm HP)',  'teal'),
        (HP_6U,             'Eurocard 6U',               'teal'),
        (HP_9U,             'Eurocard 9U',               'teal'),
        (PLATE_GENERIC,    'Generic back plate',        'purple'),
        (BB_60MM_PITCH,    '60 mm pitch busbar system', 'orange'),
        (BB_40MM_PITCH,    '40 mm pitch busbar system', 'orange'),
        (BB_CLIP_ON,       'Clip-on modular busbar',    'orange'),
        (BB_GENERIC_CU,    'Generic Cu busbar',         'yellow'),
    ]


# Which subtypes are valid for a given mount_type. Used by validation.
MOUNT_TYPE_SUBTYPES = {
    MountTypeChoices.TYPE_DIN_RAIL: frozenset((
        MountSubtypeChoices.TS35,
        MountSubtypeChoices.TS32,
        MountSubtypeChoices.TS15,
        MountSubtypeChoices.G_RAIL,
    )),
    MountTypeChoices.TYPE_SUBRACK: frozenset((
        MountSubtypeChoices.HP_3U,
        MountSubtypeChoices.HP_6U,
        MountSubtypeChoices.HP_9U,
    )),
    MountTypeChoices.TYPE_MOUNTING_PLATE: frozenset((
        MountSubtypeChoices.PLATE_GENERIC,
    )),
    MountTypeChoices.TYPE_BUSBAR: frozenset((
        MountSubtypeChoices.BB_60MM_PITCH,
        MountSubtypeChoices.BB_40MM_PITCH,
        MountSubtypeChoices.BB_CLIP_ON,
        MountSubtypeChoices.BB_GENERIC_CU,
    )),
    # Grid mounts don't have subtypes — they're driven entirely by the
    # `rows` / `row_height_mm` / `unit` / `length_mm` fields. An empty
    # frozenset means no subtype is accepted.
    MountTypeChoices.TYPE_GRID: frozenset(),
}


class MountFaceChoices(ChoiceSet):
    """
    Which device face a Mount renders on — Feature 1, v0.5.0.

    ``''`` (blank) = both faces (default, backward-compatible).
    ``'front'`` / ``'rear'`` = only on that face. Aligns with
    NetBox core's ``dcim.choices.DeviceFaceChoices`` values but adds
    the blank "Both" option that core doesn't have.
    """
    key = 'Mount.face'

    BOTH  = ''
    FRONT = 'front'
    REAR  = 'rear'

    CHOICES = [
        (BOTH,  'Both',  'gray'),
        (FRONT, 'Front', 'blue'),
        (REAR,  'Rear',  'green'),
    ]


class OrientationChoices(ChoiceSet):
    key = 'Mount.orientation'

    HORIZONTAL = 'horizontal'
    VERTICAL   = 'vertical'

    CHOICES = [
        (HORIZONTAL, 'Horizontal', 'blue'),
        (VERTICAL,   'Vertical',   'green'),
    ]


class UnitChoices(ChoiceSet):
    key = 'Mount.unit'

    MM         = 'mm'
    MODULE_175 = 'module_17_5'   # DIN module — 17.5 mm
    HP_508     = 'hp_5_08'       # Eurocard HP — 5.08 mm

    CHOICES = [
        (MM,         'Millimetres',           'gray'),
        (MODULE_175, 'DIN module (17.5 mm)',  'blue'),
        (HP_508,     'Eurocard HP (5.08 mm)', 'teal'),
    ]


# Millimetre equivalent of one unit, for each unit choice.
UNIT_TO_MM = {
    UnitChoices.MM:         1.0,
    UnitChoices.MODULE_175: 17.5,
    UnitChoices.HP_508:     5.08,
}
