from utilities.choices import ChoiceSet


class CarrierTypeChoices(ChoiceSet):
    key = 'Carrier.carrier_type'

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


# Carrier types that are one-dimensional (position along a single axis).
ONE_D_CARRIER_TYPES = frozenset((
    CarrierTypeChoices.TYPE_DIN_RAIL,
    CarrierTypeChoices.TYPE_SUBRACK,
    CarrierTypeChoices.TYPE_BUSBAR,
))

# Carrier types that are two-dimensional (x, y placement on an area).
TWO_D_CARRIER_TYPES = frozenset((
    CarrierTypeChoices.TYPE_MOUNTING_PLATE,
))

# Carrier types that are multi-row grids (row + position within row).
GRID_CARRIER_TYPES = frozenset((
    CarrierTypeChoices.TYPE_GRID,
))


class CarrierSubtypeChoices(ChoiceSet):
    key = 'Carrier.subtype'

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
        (HP_3U,            'Eurocard 3U (5.08 mm HP)',  'teal'),
        (HP_6U,            'Eurocard 6U',               'teal'),
        (HP_9U,            'Eurocard 9U',               'teal'),
        (PLATE_GENERIC,    'Generic back plate',        'purple'),
        (BB_60MM_PITCH,    '60 mm pitch busbar system', 'orange'),
        (BB_40MM_PITCH,    '40 mm pitch busbar system', 'orange'),
        (BB_CLIP_ON,       'Clip-on modular busbar',    'orange'),
        (BB_GENERIC_CU,    'Generic Cu busbar',         'yellow'),
    ]


# Which subtypes are valid for a given carrier_type. Used by validation.
CARRIER_TYPE_SUBTYPES = {
    CarrierTypeChoices.TYPE_DIN_RAIL: frozenset((
        CarrierSubtypeChoices.TS35,
        CarrierSubtypeChoices.TS32,
        CarrierSubtypeChoices.TS15,
        CarrierSubtypeChoices.G_RAIL,
    )),
    CarrierTypeChoices.TYPE_SUBRACK: frozenset((
        CarrierSubtypeChoices.HP_3U,
        CarrierSubtypeChoices.HP_6U,
        CarrierSubtypeChoices.HP_9U,
    )),
    CarrierTypeChoices.TYPE_MOUNTING_PLATE: frozenset((
        CarrierSubtypeChoices.PLATE_GENERIC,
    )),
    CarrierTypeChoices.TYPE_BUSBAR: frozenset((
        CarrierSubtypeChoices.BB_60MM_PITCH,
        CarrierSubtypeChoices.BB_40MM_PITCH,
        CarrierSubtypeChoices.BB_CLIP_ON,
        CarrierSubtypeChoices.BB_GENERIC_CU,
    )),
    # Grid carriers don't have subtypes in v0.3.0 — they're driven entirely
    # by the `rows` / `row_height_mm` / `unit` / `length_mm` fields. Leaving
    # this empty means no subtype is accepted.
    CarrierTypeChoices.TYPE_GRID: frozenset(),
}


class OrientationChoices(ChoiceSet):
    key = 'Carrier.orientation'

    HORIZONTAL = 'horizontal'
    VERTICAL   = 'vertical'

    CHOICES = [
        (HORIZONTAL, 'Horizontal', 'blue'),
        (VERTICAL,   'Vertical',   'green'),
    ]


class UnitChoices(ChoiceSet):
    key = 'Carrier.unit'

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
