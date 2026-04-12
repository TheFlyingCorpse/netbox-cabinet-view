"""
Seed a realistic OT/ICS demo dataset for visually testing the plugin.

This command is not run on install. Users who want demo data invoke it
explicitly:

    python manage.py cabinetview_seed

It is idempotent — every object is created via get_or_create /
update_or_create, so re-running it is safe and updates any drifted fields
back to the canonical seed values.

Creates:
  * a Site + Location + Manufacturer + several DeviceRoles
  * 11 DeviceType + DeviceMountProfile rows covering all five mount types
    and both host + mountable roles
  * Devices wired up into six scenarios (DIN rail, mounting plate, WDM 8-slot
    shelf, WDM 2-slot shelf, LV panel busbar, modular PLC backplane)
  * Two rack-mounted DIN rail shelves (2U and 4U) inside Test Rack A, the
    realistic rack-elevation test cases for the cabinet-view rack integration
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from dcim.models import (
    Device,
    DeviceBay,
    DeviceBayTemplate,
    DeviceRole,
    DeviceType,
    Location,
    Manufacturer,
    Module,
    ModuleBay,
    ModuleBayTemplate,
    ModuleType,
    Rack,
    Site,
)
from netbox_cabinet_view.models import (
    DeviceMountProfile,
    ModuleMountProfile,
    Mount,
    Placement,
)


def goc(_model_cls, defaults=None, **lookup):
    obj, _ = _model_cls.objects.get_or_create(defaults=defaults or {}, **lookup)
    return obj


def ensure_device_type(mfr, slug, model, **extras):
    """
    Look up a DeviceType by (manufacturer, slug) — the only real identity
    key NetBox enforces — and update the ``model`` display name plus any
    other extras on every run. This makes the seed command safely
    idempotent across renames: if an earlier run created the DT with a
    different ``model`` string, we update it in place instead of failing
    the unique-constraint check that fires when Django tries to INSERT a
    second row with the same (manufacturer, slug) pair.
    """
    obj, _ = DeviceType.objects.update_or_create(
        manufacturer=mfr,
        slug=slug,
        defaults={'model': model, **extras},
    )
    return obj


def ensure_profile(dt, **fields):
    obj, _ = DeviceMountProfile.objects.update_or_create(
        device_type=dt, defaults=fields,
    )
    return obj


def ensure_module_profile(mt, **fields):
    obj, _ = ModuleMountProfile.objects.update_or_create(
        module_type=mt, defaults=fields,
    )
    return obj


def ensure_mount_obj(host, name, **fields):
    obj, created = Mount.objects.get_or_create(
        host_device=host, name=name, defaults=fields,
    )
    if not created:
        for k, v in fields.items():
            setattr(obj, k, v)
        obj.save()
    return obj


def ensure_placement(mount, **fields):
    """
    Upsert a Placement keyed on the target (device / device_bay /
    module_bay) alone — NOT on the mount — because the Placement model
    has a per-target uniqueness constraint. Keying on (mount, target)
    would cause ``get_or_create`` to miss a stale placement that points
    to the same target but a different (old) mount, and the subsequent
    INSERT would trip ``unique_placement_device`` /
    ``unique_placement_device_bay`` / ``unique_placement_module_bay``.

    Why this is hand-rolled instead of ``update_or_create``: Django's
    ``update_or_create`` restricts ``save()`` to ``update_fields=set(defaults)``,
    which silently drops any fields that ``Placement.clean()`` auto-fills
    from the device's DeviceMountProfile footprint (``size``, ``size_x``,
    ``size_y``). That masked Finding A in v0.3.0. Explicit get-and-save
    below calls ``obj.save()`` without ``update_fields``, so the full
    ``full_clean()`` pass runs and every field it touched gets written.
    """
    key = {}
    for k in ('device', 'device_bay', 'module_bay'):
        if fields.get(k) is not None:
            key[k] = fields[k]
            break
    try:
        obj = Placement.objects.get(**key)
    except Placement.DoesNotExist:
        obj = Placement(**key)
    obj.mount = mount
    for k, v in fields.items():
        setattr(obj, k, v)
    obj.save()  # full_clean() runs via Placement.save() override (Finding A)
    return obj


class Command(BaseCommand):
    help = (
        'Create a realistic OT/ICS demo dataset for visually testing '
        'netbox-cabinet-view. Idempotent; safe to re-run.'
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            self._seed()
        self.stdout.write(self.style.SUCCESS('cabinet-view demo data seeded'))

    def _seed(self):
        # ------------------------------------------------------------------
        # Organisation
        # ------------------------------------------------------------------
        site = goc(Site, name='OT Test Site', slug='ot-test-site',
                   defaults={'status': 'active'})
        location = goc(Location, name='Control Room', slug='control-room',
                       site=site, defaults={'status': 'active'})

        mfr = goc(Manufacturer, name='Generic', slug='generic')

        roles = {
            'rail':      goc(DeviceRole, name='Rail',      slug='rail',      defaults={'color': '607d8b'}),
            'relay':     goc(DeviceRole, name='Relay',     slug='relay',     defaults={'color': '2196f3'}),
            'enclosure': goc(DeviceRole, name='Enclosure', slug='enclosure', defaults={'color': '795548'}),
            'ipc':       goc(DeviceRole, name='IPC',       slug='ipc',       defaults={'color': '9c27b0'}),
            'plc':       goc(DeviceRole, name='PLC',       slug='plc',       defaults={'color': '4caf50'}),
            'shelf':     goc(DeviceRole, name='Shelf',     slug='shelf',     defaults={'color': '3f51b5'}),
            'wdm':       goc(DeviceRole, name='WDM',       slug='wdm',       defaults={'color': 'e91e63'}),
            'busbar':    goc(DeviceRole, name='Busbar',    slug='busbar',    defaults={'color': 'ff9800'}),
            'mcb':       goc(DeviceRole, name='MCB',       slug='mcb',       defaults={'color': 'f44336'}),
        }

        # ------------------------------------------------------------------
        # DeviceTypes
        #
        # All names here are deliberately generic by category. Specific
        # vendor part numbers are withheld as an operational-security hygiene
        # measure — do not add "brand X model Y" identifiers to this file.
        # ------------------------------------------------------------------
        dt_din_rail = ensure_device_type(mfr, 'din-rail-ts35-480mm',
                                         'DIN rail TS35 480 mm',
                                         u_height=0)
        dt_relay = ensure_device_type(mfr, 'din-mount-relay-17-5mm',
                                      'DIN-mount relay 17.5 mm',
                                      u_height=0)
        dt_plate = ensure_device_type(mfr, 'floor-enclosure-800x2000',
                                      'Floor enclosure 800x2000 (back plate)',
                                      u_height=0)
        dt_ipc = ensure_device_type(mfr, 'industrial-pc',
                                    'Industrial PC',
                                    u_height=0)
        dt_plc_backplane = ensure_device_type(mfr, 'modular-plc-backplane-8-slot',
                                              'Modular PLC backplane (8-slot)',
                                              u_height=0)
        dt_wdm_shelf = ensure_device_type(mfr, 'wdm-shelf-1u-8-slot',
                                          'WDM shelf 1U 8-slot',
                                          u_height=1, subdevice_role='parent',
                                          is_full_depth=False)
        dt_wdm_shelf2 = ensure_device_type(mfr, 'wdm-shelf-1u-2-slot',
                                           'WDM shelf 1U 2-slot',
                                           u_height=1, subdevice_role='parent',
                                           is_full_depth=False)
        dt_wdm_filter = ensure_device_type(mfr, 'wdm-mux-demux-filter-4-slot',
                                           'WDM mux/demux filter 4-slot',
                                           u_height=0, subdevice_role='child')
        dt_busbar = ensure_device_type(mfr, 'lv-distribution-busbar-1m',
                                       'LV distribution busbar 1 m',
                                       u_height=0)
        dt_mcb = ensure_device_type(mfr, 'clip-on-mcb-1p',
                                    'Clip-on MCB 1P',
                                    u_height=0)
        # Separate DIN-mount MCB type — same conceptual device (1P
        # circuit breaker) but a different clip system. Real installs
        # carry both variants because different cabinets standardise on
        # different mounting platforms.
        dt_mcb_din = ensure_device_type(mfr, 'din-mount-mcb-1p',
                                        'DIN-mount MCB 1P',
                                        u_height=0)
        # Rack-mounted DIN shelves — marked is_full_depth=False because
        # real DIN shelves terminate well short of the rack's rear rails
        # (the rails + cable management stay near the front face), so
        # they should only render on whichever face they're installed on.
        dt_din_shelf_2u = ensure_device_type(mfr, 'rack-din-shelf-2u-single-rail',
                                             'Rack DIN shelf 2U (single rail)',
                                             u_height=2, is_full_depth=False)
        dt_din_shelf_4u = ensure_device_type(mfr, 'rack-din-shelf-4u-dual-rail',
                                             'Rack DIN shelf 4U (dual rail)',
                                             u_height=4, is_full_depth=False)
        dt_din_shelf_4u_isp = ensure_device_type(mfr, 'rack-din-shelf-4u-single-rail',
                                                 'Rack DIN shelf 4U (single rail)',
                                                 u_height=4, is_full_depth=False)

        # --- Scenarios A-G ---

        # A: Marshalling shelf + terminal block
        dt_marshalling_shelf = ensure_device_type(mfr, 'marshalling-rack-shelf-4u',
                                                  'Marshalling rack shelf 4U',
                                                  u_height=4, is_full_depth=False)
        dt_terminal_block = ensure_device_type(mfr, 'din-mount-terminal-block',
                                               'DIN-mount terminal block',
                                               u_height=0)

        # B: MCC cabinet, withdrawable bucket, motor contactor
        dt_mcc_cabinet = ensure_device_type(mfr, 'mcc-cabinet-800x2200',
                                            'MCC cabinet 800x2200',
                                            u_height=0)
        dt_mcc_bucket = ensure_device_type(mfr, 'mcc-withdrawable-bucket',
                                           'MCC withdrawable bucket',
                                           u_height=0)
        dt_contactor = ensure_device_type(mfr, 'motor-contactor',
                                          'Motor contactor',
                                          u_height=0)

        # C: VFD cabinet, VFD drive, aux DIN strip, 24V PSU
        dt_vfd_cabinet = ensure_device_type(mfr, 'vfd-cabinet-600x1800',
                                            'VFD cabinet 600x1800',
                                            u_height=0)
        dt_vfd_drive = ensure_device_type(mfr, 'variable-frequency-drive',
                                          'Variable frequency drive',
                                          u_height=0)
        dt_aux_din_strip = ensure_device_type(mfr, 'auxiliary-din-rail-strip-400mm',
                                              'Auxiliary DIN rail strip 400 mm',
                                              u_height=0)
        dt_24v_psu = ensure_device_type(mfr, '24v-din-mount-psu',
                                        '24 V DIN-mount PSU',
                                        u_height=0)

        # D: Fieldbus remote I/O shelf + coupler + I/O modules
        dt_fieldbus_shelf = ensure_device_type(mfr, 'fieldbus-rack-shelf-2u',
                                               'Fieldbus rack shelf 2U',
                                               u_height=2, is_full_depth=False)
        dt_fb_coupler = ensure_device_type(mfr, 'fieldbus-ethernet-coupler',
                                           'Fieldbus Ethernet coupler',
                                           u_height=0)
        dt_fb_di = ensure_device_type(mfr, 'fieldbus-8-channel-di-module',
                                      'Fieldbus 8-channel DI module',
                                      u_height=0)
        dt_fb_do = ensure_device_type(mfr, 'fieldbus-8-channel-do-module',
                                      'Fieldbus 8-channel DO module',
                                      u_height=0)

        # E: Industrial Ethernet switch
        dt_ethernet_switch = ensure_device_type(mfr, 'industrial-ethernet-switch',
                                                'Industrial Ethernet switch',
                                                u_height=0)

        # F: Safety relay panel + safety relay
        dt_safety_panel = ensure_device_type(mfr, 'safety-panel-enclosure-600x800',
                                             'Safety panel enclosure 600x800',
                                             u_height=0)
        dt_safety_relay = ensure_device_type(mfr, 'safety-relay-estop',
                                             'Safety relay (E-Stop)',
                                             u_height=0)

        # G: Substation protection panel + IEDs + test block rail + test block
        dt_protection_cabinet = ensure_device_type(mfr, 'substation-protection-cabinet-800x2200',
                                                   'Substation protection cabinet 800x2200',
                                                   u_height=0)
        dt_overcurrent_ied = ensure_device_type(mfr, 'overcurrent-protection-ied-single-slot',
                                                'Overcurrent protection IED (single-slot)',
                                                u_height=0)
        dt_line_distance_ied = ensure_device_type(mfr, 'line-distance-protection-ied',
                                                  'Line distance protection IED',
                                                  u_height=0)
        dt_test_block_rail = ensure_device_type(mfr, 'test-block-din-rail-600mm',
                                                'Test block DIN rail 600 mm',
                                                u_height=0)
        dt_test_block = ensure_device_type(mfr, 'test-block-8-pole',
                                           'Test block (8-pole)',
                                           u_height=0)

        # --- Scenarios H / I / J (v0.3.0: vertical orientation + grid carrier) ---

        # H: Vertical DIN rail wall cabinet with stacked relays
        dt_wall_box_vert = ensure_device_type(mfr, 'vertical-din-wall-box-200x600',
                                              'Vertical DIN wall box 200x600',
                                              u_height=0)

        # I: Vertical Eurocard subrack (rotated 90 degrees for space reasons)
        dt_subrack_vert = ensure_device_type(mfr, 'vertical-6u-eurocard-subrack',
                                             'Vertical 6U Eurocard subrack',
                                             u_height=0)
        dt_eurocard_card = ensure_device_type(mfr, 'eurocard-6u-8hp-card',
                                              'Eurocard 6U 8HP card',
                                              u_height=0)

        # K: ISP Optical Distribution Frame chassis with a grid of fibre
        # splice cassettes. A single 1U chassis holds a 2-row × 6-column grid
        # (12 cassettes) with ModuleBay-backed mounts, demonstrating the
        # ODF / fibre patch panel pattern for ISP deployments.
        dt_odf_chassis = ensure_device_type(
            mfr, 'odf-chassis-1u-12-cassette',
            'ODF chassis 1U (12-cassette grid)',
            u_height=1,
        )
        for row in (1, 2):
            for slot in range(1, 7):
                goc(ModuleBayTemplate, device_type=dt_odf_chassis,
                    name=f'C{row}-{slot}',
                    defaults={'position': f'C{row}-{slot}'})

        mt_splice_cassette = goc(ModuleType, manufacturer=mfr,
                                 model='Fibre splice cassette (12-splice)')

        # J: Generic protection-IED chassis with 2 rows of module slots.
        # Models the family of line/diff/overcurrent IEDs from multiple vendors
        # that use a modular backplane (first slots for PSU, then CPU, then a
        # mix of I/O / analog / comms cards). Device types and module types are
        # deliberately named generically here to keep the seed trademark-free.
        dt_ied_chassis = ensure_device_type(mfr, 'protection-ied-chassis-2-row-24-slot',
                                            'Protection IED chassis 2-row (24-slot)',
                                            u_height=0)
        # Per-slot module bay templates (R1S1..R1S12, R2S1..R2S12).
        for row in (1, 2):
            for slot in range(1, 13):
                goc(ModuleBayTemplate, device_type=dt_ied_chassis,
                    name=f'R{row}S{slot}',
                    defaults={'position': f'R{row}S{slot}'})

        # Generic module types — every vendor ships rough equivalents.
        mt_psu_module = goc(ModuleType, manufacturer=mfr, model='IED power supply module')
        mt_cpu_module = goc(ModuleType, manufacturer=mfr, model='IED CPU module')
        mt_bin_io_module = goc(ModuleType, manufacturer=mfr, model='IED binary I/O module')
        mt_ana_io_module = goc(ModuleType, manufacturer=mfr, model='IED analog input module')
        mt_hs_io_module = goc(ModuleType, manufacturer=mfr, model='IED high-speed I/O module')
        mt_eth_module = goc(ModuleType, manufacturer=mfr, model='IED Ethernet comms module')
        mt_fibre_module = goc(ModuleType, manufacturer=mfr, model='IED fibre comms module')

        # DeviceBay templates for the WDM shelves
        for i in range(1, 9):
            goc(DeviceBayTemplate, device_type=dt_wdm_shelf, name=f'Slot {i}')
        for i in range(1, 3):
            goc(DeviceBayTemplate, device_type=dt_wdm_shelf2, name=f'Slot {i}')

        # ModuleBay templates for the modular PLC
        for i in range(1, 9):
            goc(ModuleBayTemplate, device_type=dt_plc_backplane, name=f'Slot {i}',
                defaults={'position': str(i)})

        # Module type for the PLC I/O card
        mt_io = goc(ModuleType, manufacturer=mfr, model='DI 16x24VDC')

        # ------------------------------------------------------------------
        # ModuleMountProfiles (new in v0.4.0)
        #
        # Modules need per-type footprints just like devices do, otherwise
        # every module renders at size=1 on its host mount. These are the
        # profiles for the module types used in scenarios K (ODF cassettes)
        # and J (IED chassis modules); the sizes here are in mm since all
        # scenarios that use ModuleBay-backed placements drive the mount's
        # unit=mm.
        # ------------------------------------------------------------------
        ensure_module_profile(mt_io, mountable_on='subrack', footprint_primary=10)
        ensure_module_profile(mt_splice_cassette, mountable_on='grid', footprint_primary=70)
        ensure_module_profile(mt_psu_module,    mountable_on='grid', footprint_primary=30)
        ensure_module_profile(mt_cpu_module,    mountable_on='grid', footprint_primary=30)
        ensure_module_profile(mt_bin_io_module, mountable_on='grid', footprint_primary=30)
        ensure_module_profile(mt_ana_io_module, mountable_on='grid', footprint_primary=30)
        ensure_module_profile(mt_hs_io_module,  mountable_on='grid', footprint_primary=60)
        ensure_module_profile(mt_eth_module,    mountable_on='grid', footprint_primary=60)
        ensure_module_profile(mt_fibre_module,  mountable_on='grid', footprint_primary=60)

        # ------------------------------------------------------------------
        # DeviceMountProfiles
        # ------------------------------------------------------------------
        ensure_profile(dt_din_rail,      hosts_mounts=True, internal_width_mm=480, internal_height_mm=80)
        ensure_profile(dt_relay,         mountable_on='din_rail', mountable_subtype='ts35', footprint_primary=1)
        ensure_profile(dt_plate,         hosts_mounts=True, internal_width_mm=760, internal_height_mm=1960)
        ensure_profile(dt_ipc,           mountable_on='mounting_plate', footprint_primary=220, footprint_secondary=90)
        ensure_profile(dt_plc_backplane, hosts_mounts=True, internal_width_mm=400, internal_height_mm=160)
        ensure_profile(dt_wdm_shelf,     hosts_mounts=True, internal_width_mm=440, internal_height_mm=44)
        ensure_profile(dt_wdm_shelf2,    hosts_mounts=True, internal_width_mm=440, internal_height_mm=44)
        ensure_profile(dt_wdm_filter,    mountable_on='subrack', mountable_subtype='hp_3u', footprint_primary=20)
        ensure_profile(dt_busbar,        hosts_mounts=True, internal_width_mm=1000, internal_height_mm=60)
        ensure_profile(dt_mcb,           mountable_on='busbar', mountable_subtype='bb_60mm_pitch', footprint_primary=18)
        ensure_profile(dt_mcb_din,       mountable_on='din_rail', mountable_subtype='ts35', footprint_primary=18)
        # 2U shelf: 2U inner ≈ 88 mm, real depth 200 mm for cable clearance
        ensure_profile(dt_din_shelf_2u,  hosts_mounts=True, internal_width_mm=440,
                       internal_height_mm=88, internal_depth_mm=200)
        # 4U shelf: 4U inner ≈ 175 mm, room for two stacked DIN rails + wire management
        ensure_profile(dt_din_shelf_4u,  hosts_mounts=True, internal_width_mm=440,
                       internal_height_mm=175, internal_depth_mm=200)
        # 4U shelf, single rail (ISP marshalling style) — one rail centered with
        # generous wire-management space above and below.
        ensure_profile(dt_din_shelf_4u_isp, hosts_mounts=True, internal_width_mm=440,
                       internal_height_mm=175, internal_depth_mm=200)

        # Scenarios A-G profiles
        ensure_profile(dt_marshalling_shelf, hosts_mounts=True, internal_width_mm=440,
                       internal_height_mm=175, internal_depth_mm=200)
        ensure_profile(dt_terminal_block, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=6)  # 5.2 mm wide, rounded to 6 mm

        ensure_profile(dt_mcc_cabinet, hosts_mounts=True, internal_width_mm=760,
                       internal_height_mm=2160, internal_depth_mm=600)
        # Bucket is BOTH a host (holds its own DIN rail with contactors) AND
        # mountable on the cabinet's vertical busbar.
        ensure_profile(dt_mcc_bucket, hosts_mounts=True, internal_width_mm=300,
                       internal_height_mm=250,
                       mountable_on='busbar', mountable_subtype='bb_60mm_pitch',
                       footprint_primary=300, footprint_secondary=250)
        ensure_profile(dt_contactor, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=45)

        ensure_profile(dt_vfd_cabinet, hosts_mounts=True, internal_width_mm=560,
                       internal_height_mm=1760, internal_depth_mm=400)
        ensure_profile(dt_vfd_drive, mountable_on='mounting_plate',
                       mountable_subtype='plate_generic',
                       footprint_primary=250, footprint_secondary=400)
        # Aux DIN strip is BOTH a host (has its own DIN rail inside) AND mountable
        # on the VFD cabinet's back plate. Classic "rail on plate" nesting.
        ensure_profile(dt_aux_din_strip, hosts_mounts=True, internal_width_mm=400,
                       internal_height_mm=80,
                       mountable_on='mounting_plate', mountable_subtype='plate_generic',
                       footprint_primary=400, footprint_secondary=80)
        ensure_profile(dt_24v_psu, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=80)

        ensure_profile(dt_fieldbus_shelf, hosts_mounts=True, internal_width_mm=440,
                       internal_height_mm=88, internal_depth_mm=250)
        ensure_profile(dt_fb_coupler, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=100)
        ensure_profile(dt_fb_di, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=12)
        ensure_profile(dt_fb_do, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=12)

        ensure_profile(dt_ethernet_switch, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=90)

        ensure_profile(dt_safety_panel, hosts_mounts=True, internal_width_mm=600,
                       internal_height_mm=800, internal_depth_mm=250)
        ensure_profile(dt_safety_relay, mountable_on='mounting_plate', mountable_subtype='plate_generic',
                       footprint_primary=45, footprint_secondary=100)

        ensure_profile(dt_protection_cabinet, hosts_mounts=True, internal_width_mm=760,
                       internal_height_mm=2160, internal_depth_mm=600)
        ensure_profile(dt_overcurrent_ied, mountable_on='mounting_plate', mountable_subtype='plate_generic',
                       footprint_primary=215, footprint_secondary=270)
        ensure_profile(dt_line_distance_ied, mountable_on='mounting_plate', mountable_subtype='plate_generic',
                       footprint_primary=483, footprint_secondary=270)
        ensure_profile(dt_test_block_rail, hosts_mounts=True, internal_width_mm=600,
                       internal_height_mm=60,
                       mountable_on='mounting_plate', mountable_subtype='plate_generic',
                       footprint_primary=600, footprint_secondary=60)
        ensure_profile(dt_test_block, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=80)

        # H/I/J profiles
        ensure_profile(dt_wall_box_vert, hosts_mounts=True,
                       internal_width_mm=200, internal_height_mm=600, internal_depth_mm=150)
        ensure_profile(dt_subrack_vert, hosts_mounts=True,
                       internal_width_mm=260, internal_height_mm=500, internal_depth_mm=220)
        ensure_profile(dt_eurocard_card, mountable_on='subrack', mountable_subtype='hp_6u',
                       footprint_primary=8)  # 8 HP wide
        # Generic IED chassis: host; 2 bars of 12 slots at 30 mm slot width.
        # Slot addressing is in mm along each row so a physical "slot N" lives
        # at position = 1 + (N-1) * 30 with size = 30 per slot.
        ensure_profile(dt_ied_chassis, hosts_mounts=True,
                       internal_width_mm=440, internal_height_mm=260, internal_depth_mm=250)

        # K: ODF chassis — 1U fibre patch frame with a 2x6 cassette grid.
        ensure_profile(dt_odf_chassis, hosts_mounts=True,
                       internal_width_mm=440, internal_height_mm=44, internal_depth_mm=250)

        # ------------------------------------------------------------------
        # Devices (standalone scenarios)
        # ------------------------------------------------------------------
        def ensure_device(name, device_type, role_slug, **kw):
            obj, _ = Device.objects.get_or_create(
                name=name, site=site,
                defaults={'device_type': device_type, 'role': roles[role_slug],
                          'location': location, **kw},
            )
            return obj

        # Scenario 1: Standalone DIN rail with two relays
        din_device = ensure_device('DIN Rail #1', dt_din_rail, 'rail')
        relay1 = ensure_device('Relay A', dt_relay, 'relay')
        relay2 = ensure_device('Relay B', dt_relay, 'relay')

        # Scenario 2: Mounting plate with an IPC
        plate_device = ensure_device('Floor Enclosure #1', dt_plate, 'enclosure')
        ipc = ensure_device('IPC A', dt_ipc, 'ipc')

        # Scenario 3: WDM 8-slot shelf + 2 filter children
        wdm_shelf = ensure_device('WDM Shelf #1', dt_wdm_shelf, 'shelf')
        wdm_filter_a = ensure_device('WDM Filter A', dt_wdm_filter, 'wdm')
        wdm_filter_b = ensure_device('WDM Filter B', dt_wdm_filter, 'wdm')
        bay1 = DeviceBay.objects.get(device=wdm_shelf, name='Slot 1')
        bay5 = DeviceBay.objects.get(device=wdm_shelf, name='Slot 5')
        if not bay1.installed_device_id:
            bay1.installed_device = wdm_filter_a
            bay1.save()
        if not bay5.installed_device_id:
            bay5.installed_device = wdm_filter_b
            bay5.save()

        # Scenario 4: WDM 2-slot shelf + 2 filter children
        wdm_shelf2 = ensure_device('WDM Shelf 2-slot #1', dt_wdm_shelf2, 'shelf')
        wdm_filter_c = ensure_device('WDM Filter C', dt_wdm_filter, 'wdm')
        wdm_filter_d = ensure_device('WDM Filter D', dt_wdm_filter, 'wdm')
        bay2_1 = DeviceBay.objects.get(device=wdm_shelf2, name='Slot 1')
        bay2_2 = DeviceBay.objects.get(device=wdm_shelf2, name='Slot 2')
        if not bay2_1.installed_device_id:
            bay2_1.installed_device = wdm_filter_c
            bay2_1.save()
        if not bay2_2.installed_device_id:
            bay2_2.installed_device = wdm_filter_d
            bay2_2.save()

        # Scenario 5: Busbar with MCBs
        busbar_device = ensure_device('LV Distribution Busbar', dt_busbar, 'busbar')
        mcb1 = ensure_device('MCB F01', dt_mcb, 'mcb')
        mcb2 = ensure_device('MCB F02', dt_mcb, 'mcb')
        mcb3 = ensure_device('MCB F03', dt_mcb, 'mcb')

        # Scenario 6: Modular PLC with I/O modules
        plc_backplane = ensure_device('PLC Backplane #1', dt_plc_backplane, 'plc')
        mb2 = ModuleBay.objects.get(device=plc_backplane, name='Slot 2')
        mb4 = ModuleBay.objects.get(device=plc_backplane, name='Slot 4')
        Module.objects.get_or_create(device=plc_backplane, module_bay=mb2,
                                     defaults={'module_type': mt_io})
        Module.objects.get_or_create(device=plc_backplane, module_bay=mb4,
                                     defaults={'module_type': mt_io})

        # ------------------------------------------------------------------
        # Rack + rack-mounted DIN shelves
        # ------------------------------------------------------------------
        rack = goc(Rack, name='Test Rack A', site=site,
                   defaults={'u_height': 24, 'status': 'active'})
        if rack.u_height < 24:
            rack.u_height = 24
            rack.save()

        # Scenario 7: 2U DIN rail shelf with a single rail and 3 relays
        din_shelf_2u = ensure_device('DIN Shelf 2U #1', dt_din_shelf_2u, 'shelf')
        relay_2u_a = ensure_device('Relay 2U-A', dt_relay, 'relay')
        relay_2u_b = ensure_device('Relay 2U-B', dt_relay, 'relay')
        relay_2u_c = ensure_device('Relay 2U-C', dt_relay, 'relay')

        # Scenario 8: 4U DIN rail shelf with two stacked rails and a mix of modules
        din_shelf_4u = ensure_device('DIN Shelf 4U #1', dt_din_shelf_4u, 'shelf')
        relay_4u_a = ensure_device('Relay 4U-A', dt_relay, 'relay')
        relay_4u_b = ensure_device('Relay 4U-B', dt_relay, 'relay')
        mcb_4u_a = ensure_device('MCB 4U-A', dt_mcb_din, 'mcb')
        mcb_4u_b = ensure_device('MCB 4U-B', dt_mcb_din, 'mcb')
        mcb_4u_c = ensure_device('MCB 4U-C', dt_mcb_din, 'mcb')

        # Scenario 9: ISP-style 4U DIN rail shelf with a single centered rail
        din_shelf_4u_isp = ensure_device('DIN Shelf 4U ISP #1', dt_din_shelf_4u_isp, 'shelf')
        relay_isp_a = ensure_device('Relay ISP-A', dt_relay, 'relay')
        relay_isp_b = ensure_device('Relay ISP-B', dt_relay, 'relay')
        relay_isp_c = ensure_device('Relay ISP-C', dt_relay, 'relay')
        relay_isp_d = ensure_device('Relay ISP-D', dt_relay, 'relay')
        relay_isp_e = ensure_device('Relay ISP-E', dt_relay, 'relay')

        # --- Scenario A: Marshalling cabinet (4U rack) ---
        marshalling_shelf = ensure_device('Marshalling Cabinet #1', dt_marshalling_shelf, 'rail')
        terminal_blocks = [
            ensure_device(f'TB{i:02d}', dt_terminal_block, 'rail')
            for i in range(1, 21)
        ]

        # --- Scenario B: MCC with withdrawable buckets (standalone) ---
        mcc_cabinet = ensure_device('MCC Cabinet #1', dt_mcc_cabinet, 'busbar')
        buckets = [
            ensure_device(f'MCC Bucket #{i}', dt_mcc_bucket, 'shelf')
            for i in (1, 2, 3)
        ]
        bucket_contactors = [
            ensure_device(f'Contactor K{i:02d}', dt_contactor, 'relay')
            for i in range(1, 4)
        ]
        bucket_relays = [
            ensure_device(f'Aux relay BR{i:02d}', dt_relay, 'relay')
            for i in range(1, 4)
        ]

        # --- Scenario C: VFD control cabinet (standalone) ---
        vfd_cabinet = ensure_device('VFD Cabinet #1', dt_vfd_cabinet, 'enclosure')
        vfd_drive = ensure_device('VFD-M1', dt_vfd_drive, 'ipc')
        aux_rail_device = ensure_device('VFD aux DIN strip', dt_aux_din_strip, 'rail')
        psu_device = ensure_device('24 V PSU #1', dt_24v_psu, 'relay')
        vfd_contactor_a = ensure_device('VFD contactor KM1', dt_contactor, 'relay')
        vfd_contactor_b = ensure_device('VFD contactor KM2', dt_contactor, 'relay')

        # --- Scenario D: Fieldbus remote I/O station (2U rack) ---
        fieldbus_shelf = ensure_device('Fieldbus Remote I/O #1', dt_fieldbus_shelf, 'plc')
        fb_coupler = ensure_device('Fieldbus coupler #1', dt_fb_coupler, 'plc')
        fb_di_modules = [
            ensure_device(f'DI module #{i}', dt_fb_di, 'plc') for i in range(1, 5)
        ]
        fb_do_modules = [
            ensure_device(f'DO module #{i}', dt_fb_do, 'plc') for i in range(1, 4)
        ]

        # --- Scenario E: Industrial Ethernet switch (2U rack) ---
        switch_shelf = ensure_device('Industrial Switch Shelf #1', dt_fieldbus_shelf, 'plc')
        industrial_switch = ensure_device('Industrial Ethernet switch #1', dt_ethernet_switch, 'plc')

        # --- Scenario F: Safety relay panel (standalone) ---
        safety_cabinet = ensure_device('Safety Panel #1', dt_safety_panel, 'enclosure')
        safety_relays = [
            ensure_device(f'Safety relay {name}', dt_safety_relay, 'relay')
            for name in ('E-Stop 1', 'E-Stop 2', 'Guard', 'Light Curtain')
        ]

        # --- Scenario G: Substation protection panel (standalone) ---
        protection_cabinet = ensure_device('Protection Panel #1', dt_protection_cabinet, 'plc')
        oc_ied_1 = ensure_device('Overcurrent IED F1', dt_overcurrent_ied, 'plc')
        oc_ied_2 = ensure_device('Overcurrent IED F2', dt_overcurrent_ied, 'plc')
        ld_ied = ensure_device('Line distance IED L1', dt_line_distance_ied, 'plc')
        test_rail_device = ensure_device('Test block rail #1', dt_test_block_rail, 'rail')
        test_blocks = [
            ensure_device(f'Test block F{i:02d}', dt_test_block, 'relay')
            for i in range(1, 5)
        ]

        # --- Scenario H: Vertical DIN rail wall box (standalone) ---
        wall_box_v = ensure_device('Vertical DIN Wall Box #1', dt_wall_box_vert, 'enclosure')
        wall_box_relays = [
            ensure_device(f'Wall relay WR{i:02d}', dt_relay, 'relay')
            for i in range(1, 7)
        ]

        # --- Scenario I: Vertical Eurocard subrack (standalone) ---
        vsubrack = ensure_device('Vertical Subrack #1', dt_subrack_vert, 'shelf')
        eurocards = [
            ensure_device(f'Eurocard EC{i:02d}', dt_eurocard_card, 'plc')
            for i in range(1, 5)
        ]

        # --- Scenario K: ISP ODF — 1U chassis with 12 fibre splice cassettes ---
        # The interesting face of an ODF is usually the REAR (where the splices
        # and trunk fibres terminate), so this scenario is also the proving
        # ground for the rear-face rack elevation patch in v0.3.0+.
        odf = ensure_device('ODF Frame #1', dt_odf_chassis, 'shelf')
        for row in (1, 2):
            for slot in range(1, 7):
                bay = ModuleBay.objects.get(device=odf, name=f'C{row}-{slot}')
                Module.objects.get_or_create(
                    device=odf, module_bay=bay,
                    defaults={'module_type': mt_splice_cassette},
                )

        # --- Scenario J: Grid-mounted IED with ModuleBay-backed mounts ---
        # This is the one that answers "can a single device be many entries
        # in a rail/bus, depending on its module bays and mounted modules?"
        # — YES. The IED is one dcim.Device with 24 ModuleBays. Some bays
        # are populated with a mix of Modules (PSU / CPU / I/O / comms),
        # some stay empty. Each populated bay becomes ONE Mount on the grid
        # carrier, showing the Module's ModuleType as the slot's visual.
        ied = ensure_device('Protection IED L01', dt_ied_chassis, 'plc')

        # Populate a realistic subset of the 24 module bays. Vendors differ
        # in which slots they reserve for which card types; this layout is
        # a common pattern across several protection-IED families.
        ied_population = [
            # (row, slot,   module_type)
            (1,  1,  mt_psu_module),      # primary power supply
            (1,  2,  mt_psu_module),      # redundant power supply
            (1,  3,  mt_cpu_module),      # IED CPU
            (1,  4,  mt_bin_io_module),
            (1,  5,  mt_ana_io_module),
            (1,  7,  mt_bin_io_module),
            (1,  8,  mt_eth_module),      # takes slots 8-9 (size=2)
            (1, 11,  mt_fibre_module),    # spans rows 1-2, slots 11-12
            (2,  1,  mt_bin_io_module),
            (2,  3,  mt_bin_io_module),
            (2,  5,  mt_hs_io_module),    # takes slots 5-6 (size=2)
            (2,  8,  mt_bin_io_module),
        ]
        for row, slot, mtype in ied_population:
            bay = ModuleBay.objects.get(device=ied, name=f'R{row}S{slot}')
            Module.objects.get_or_create(
                device=ied, module_bay=bay, defaults={'module_type': mtype},
            )

        # ------------------------------------------------------------------
        # Rack placement — done in two passes so re-runs never collide.
        #
        # Pass 1: clear any existing rack position for every device we manage.
        # Pass 2: assign each device to its canonical (rack, U, face).
        # ------------------------------------------------------------------
        rack_layout = [
            # (device, U position, face)
            (wdm_shelf2,          1,  'front'),
            (wdm_shelf,           2,  'front'),
            (din_shelf_2u,        3,  'front'),
            (din_shelf_4u,        5,  'front'),
            (din_shelf_4u_isp,    9,  'front'),
            (marshalling_shelf,  13,  'front'),
            (fieldbus_shelf,         17,  'front'),
            (switch_shelf,       19,  'front'),
            (odf,                21,  'front'),
        ]

        managed_devices = [d for d, _, _ in rack_layout]

        # Clear rack placement on every device currently in this rack so
        # stale occupants from earlier seed versions don't block our
        # canonical layout. Then also clear managed devices in case any
        # of them is currently in a different rack or unracked.
        Device.objects.filter(rack=rack).update(
            rack=None, position=None, face='',
        )
        for dev in managed_devices:
            dev.refresh_from_db()
            if dev.rack_id is not None or dev.position is not None:
                dev.rack = None
                dev.position = None
                dev.face = ''
                dev.save()

        for dev, u, face in rack_layout:
            dev.refresh_from_db()
            dev.rack = rack
            dev.position = u
            dev.face = face
            dev.save()

        # ------------------------------------------------------------------
        # Mounts
        # ------------------------------------------------------------------
        c_din = ensure_mount_obj(
            din_device, 'Main rail',
            mount_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='module_17_5', length_mm=480, offset_x_mm=0, offset_y_mm=20,
        )
        c_plate = ensure_mount_obj(
            plate_device, 'Back plate',
            mount_type='mounting_plate', subtype='plate_generic',
            unit='mm', width_mm=760, height_mm=1960, offset_x_mm=0, offset_y_mm=0,
        )
        c_wdm = ensure_mount_obj(
            wdm_shelf, 'Slot carrier',
            mount_type='subrack', subtype='hp_3u', orientation='horizontal',
            unit='hp_5_08', length_mm=406, offset_x_mm=15, offset_y_mm=5,
        )
        c_wdm2 = ensure_mount_obj(
            wdm_shelf2, 'Slot carrier',
            mount_type='subrack', subtype='hp_3u', orientation='horizontal',
            unit='hp_5_08', length_mm=440, offset_x_mm=0, offset_y_mm=4,
        )
        c_busbar = ensure_mount_obj(
            busbar_device, 'L1/L2/L3 bar',
            mount_type='busbar', subtype='bb_60mm_pitch', orientation='horizontal',
            unit='mm', length_mm=1000, offset_x_mm=0, offset_y_mm=20,
        )
        c_plc = ensure_mount_obj(
            plc_backplane, 'Backplane',
            mount_type='subrack', subtype='hp_3u', orientation='horizontal',
            unit='hp_5_08', length_mm=400, offset_x_mm=0, offset_y_mm=10,
        )

        # 2U DIN shelf — single rail centered vertically
        c_din_2u = ensure_mount_obj(
            din_shelf_2u, 'Main rail',
            mount_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='module_17_5', length_mm=420, offset_x_mm=10, offset_y_mm=40,
        )

        # 4U DIN shelf — two stacked rails
        c_din_4u_upper = ensure_mount_obj(
            din_shelf_4u, 'Upper rail',
            mount_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='module_17_5', length_mm=420, offset_x_mm=10, offset_y_mm=45,
        )
        c_din_4u_lower = ensure_mount_obj(
            din_shelf_4u, 'Lower rail',
            mount_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='module_17_5', length_mm=420, offset_x_mm=10, offset_y_mm=130,
        )

        # ISP 4U DIN shelf — one rail centered vertically, wire room above/below
        c_din_4u_isp = ensure_mount_obj(
            din_shelf_4u_isp, 'Main rail',
            mount_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='module_17_5', length_mm=420, offset_x_mm=10, offset_y_mm=88,
        )

        # --- Scenarios A-G carriers ---

        # A: Marshalling shelf — one DIN rail in mm units (terminal blocks are 5-6 mm)
        c_marshalling = ensure_mount_obj(
            marshalling_shelf, 'Terminal rail',
            mount_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='mm', length_mm=420, offset_x_mm=10, offset_y_mm=88,
        )

        # B: MCC cabinet — vertical busbar, plus one DIN rail inside each bucket
        c_mcc_busbar = ensure_mount_obj(
            mcc_cabinet, 'Vertical busbar',
            mount_type='busbar', subtype='bb_60mm_pitch', orientation='vertical',
            unit='mm', length_mm=1800, offset_x_mm=250, offset_y_mm=200,
        )
        c_bucket_rails = []
        for i, bucket in enumerate(buckets):
            c_bucket_rails.append(ensure_mount_obj(
                bucket, 'Bucket rail',
                mount_type='din_rail', subtype='ts35', orientation='horizontal',
                unit='mm', length_mm=280, offset_x_mm=10, offset_y_mm=80,
            ))

        # C: VFD cabinet — back plate, plus a nested DIN strip device with its own rail
        c_vfd_plate = ensure_mount_obj(
            vfd_cabinet, 'Back plate',
            mount_type='mounting_plate', subtype='plate_generic',
            unit='mm', width_mm=560, height_mm=1760, offset_x_mm=0, offset_y_mm=0,
        )
        c_aux_rail = ensure_mount_obj(
            aux_rail_device, 'Aux rail',
            mount_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='mm', length_mm=380, offset_x_mm=10, offset_y_mm=30,
        )

        # D: Fieldbus remote I/O — DIN rail with coupler + I/O modules
        c_fieldbus = ensure_mount_obj(
            fieldbus_shelf, 'Main rail',
            mount_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='mm', length_mm=420, offset_x_mm=10, offset_y_mm=44,
        )

        # E: Industrial switch — DIN rail with a single 90 mm switch
        c_switch = ensure_mount_obj(
            switch_shelf, 'Main rail',
            mount_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='mm', length_mm=420, offset_x_mm=10, offset_y_mm=44,
        )

        # F: Safety relay panel — back plate with 4 safety relays
        c_safety_plate = ensure_mount_obj(
            safety_cabinet, 'Back plate',
            mount_type='mounting_plate', subtype='plate_generic',
            unit='mm', width_mm=600, height_mm=800, offset_x_mm=0, offset_y_mm=0,
        )

        # G: Protection panel — back plate with IEDs + nested test block rail
        c_protection_plate = ensure_mount_obj(
            protection_cabinet, 'Back plate',
            mount_type='mounting_plate', subtype='plate_generic',
            unit='mm', width_mm=760, height_mm=2160, offset_x_mm=0, offset_y_mm=0,
        )
        c_test_rail = ensure_mount_obj(
            test_rail_device, 'Test rail',
            mount_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='mm', length_mm=580, offset_x_mm=10, offset_y_mm=20,
        )

        # --- Scenarios H / I / J carriers ---

        # H: Vertical DIN rail wall box — one vertical TS35 rail
        c_wall_v = ensure_mount_obj(
            wall_box_v, 'Vertical rail',
            mount_type='din_rail', subtype='ts35', orientation='vertical',
            unit='mm', length_mm=560, offset_x_mm=80, offset_y_mm=20,
        )

        # I: Vertical 6U subrack — one vertical subrack carrier holding cards
        c_vsubrack = ensure_mount_obj(
            vsubrack, 'Card cage',
            mount_type='subrack', subtype='hp_6u', orientation='vertical',
            unit='hp_5_08', length_mm=460, offset_x_mm=20, offset_y_mm=20,
        )

        # K: ODF — 1U chassis with a 2x6 grid of 70 mm fibre splice cassettes.
        # Row height is half the 44 mm 1U internal space = 22 mm per row.
        c_odf_grid = ensure_mount_obj(
            odf, 'Cassette grid',
            mount_type='grid', orientation='horizontal',
            unit='mm', length_mm=420, rows=2, row_height_mm=22,
            offset_x_mm=10, offset_y_mm=0,
        )

        # J: IED grid — 2 rows ("bars") of 12 slots at 30 mm slot width.
        # Row length = 12 * 30 mm. Row spacing = 100 mm so labels breathe.
        c_ied_grid = ensure_mount_obj(
            ied, 'Module bars',
            mount_type='grid', orientation='horizontal',
            unit='mm', length_mm=360, rows=2, row_height_mm=100,
            offset_x_mm=40, offset_y_mm=40,
        )

        # ------------------------------------------------------------------
        # Mounts (sizes left implicit where the profile provides a footprint)
        # ------------------------------------------------------------------
        ensure_placement(c_din, device=relay1, position=1, size=1)
        ensure_placement(c_din, device=relay2, position=5, size=1)

        ensure_placement(c_plate, device=ipc, position_x=100, position_y=200, size_x=220, size_y=90)

        ensure_placement(c_wdm, device_bay=bay1, position=1, size=4)
        ensure_placement(c_wdm, device_bay=bay5, position=41, size=4)

        # WDM 2-slot: fixed 20-HP slots centered in each half of the 86-HP carrier
        ensure_placement(c_wdm2, device_bay=bay2_1, position=12, size=20)
        ensure_placement(c_wdm2, device_bay=bay2_2, position=55, size=20)

        ensure_placement(c_busbar, device=mcb1, position=20, size=18)
        ensure_placement(c_busbar, device=mcb2, position=60, size=18)
        ensure_placement(c_busbar, device=mcb3, position=100, size=18)

        ensure_placement(c_plc, module_bay=mb2, position=11, size=10)
        ensure_placement(c_plc, module_bay=mb4, position=31, size=10)

        # 2U DIN shelf: three relays spread across the rail
        ensure_placement(c_din_2u, device=relay_2u_a, position=1,  size=1)
        ensure_placement(c_din_2u, device=relay_2u_b, position=5,  size=1)
        ensure_placement(c_din_2u, device=relay_2u_c, position=9,  size=1)

        # 4U DIN shelf: 2 relays on upper rail, 3 MCBs on lower rail
        ensure_placement(c_din_4u_upper, device=relay_4u_a, position=1, size=1)
        ensure_placement(c_din_4u_upper, device=relay_4u_b, position=5, size=1)
        ensure_placement(c_din_4u_lower, device=mcb_4u_a, position=1,  size=1)
        ensure_placement(c_din_4u_lower, device=mcb_4u_b, position=3,  size=1)
        ensure_placement(c_din_4u_lower, device=mcb_4u_c, position=5,  size=1)

        # ISP 4U DIN shelf: 5 relays along the single rail
        for i, r in enumerate((relay_isp_a, relay_isp_b, relay_isp_c, relay_isp_d, relay_isp_e)):
            ensure_placement(c_din_4u_isp, device=r, position=1 + i * 4, size=1)

        # --- Scenarios A-G mounts (sizes mostly default from device profile footprint) ---

        # A: Marshalling — 20 terminal blocks at 6 mm spacing, starting 10 mm in
        for i, tb in enumerate(terminal_blocks):
            ensure_placement(c_marshalling, device=tb, position=10 + i * 6)

        # B: MCC — 3 withdrawable buckets on the vertical busbar
        ensure_placement(c_mcc_busbar, device=buckets[0], position=100)
        ensure_placement(c_mcc_busbar, device=buckets[1], position=500)
        ensure_placement(c_mcc_busbar, device=buckets[2], position=900)
        # Each bucket has its own DIN rail with one contactor and one relay
        for rail, contactor, aux in zip(c_bucket_rails, bucket_contactors, bucket_relays):
            ensure_placement(rail, device=contactor, position=30)
            ensure_placement(rail, device=aux, position=100)

        # C: VFD cabinet plate — VFD drive at top, aux DIN strip below
        ensure_placement(c_vfd_plate, device=vfd_drive, position_x=150, position_y=100)
        ensure_placement(c_vfd_plate, device=aux_rail_device, position_x=80, position_y=600)
        # Aux DIN strip carries a PSU and two VFD contactors
        ensure_placement(c_aux_rail, device=psu_device, position=20)
        ensure_placement(c_aux_rail, device=vfd_contactor_a, position=120)
        ensure_placement(c_aux_rail, device=vfd_contactor_b, position=180)

        # D: Fieldbus remote I/O — coupler at left, then alternating DI/DO modules
        ensure_placement(c_fieldbus, device=fb_coupler, position=10)
        x = 115  # left edge of the first I/O module, just right of the coupler
        for di in fb_di_modules:
            ensure_placement(c_fieldbus, device=di, position=x)
            x += 14
        for do in fb_do_modules:
            ensure_placement(c_fieldbus, device=do, position=x)
            x += 14

        # E: Industrial switch — single switch centered on the rail
        ensure_placement(c_switch, device=industrial_switch, position=160)

        # F: Safety relay panel — 4 safety relays spaced along the plate top
        for i, sr in enumerate(safety_relays):
            ensure_placement(c_safety_plate, device=sr, position_x=60 + i * 130, position_y=150)

        # G: Protection panel — 2 overcurrent IEDs, 1 line-distance IED, test block rail below
        ensure_placement(c_protection_plate, device=oc_ied_1, position_x=270, position_y=200)
        ensure_placement(c_protection_plate, device=oc_ied_2, position_x=270, position_y=550)
        ensure_placement(c_protection_plate, device=ld_ied,    position_x=140, position_y=900)
        ensure_placement(c_protection_plate, device=test_rail_device,
                     position_x=80, position_y=1300)
        # The test block rail carries 4 test blocks
        for i, tb in enumerate(test_blocks):
            ensure_placement(c_test_rail, device=tb, position=20 + i * 130)

        # --- Scenarios H / I / J mounts ---

        # H: 6 relays stacked along the vertical rail
        for i, r in enumerate(wall_box_relays):
            # Each relay is 1 module (17.5 mm) but we're in mm units here for
            # the vertical rail, so space them ~30 mm apart.
            ensure_placement(c_wall_v, device=r, position=10 + i * 30, size=25)

        # I: 4 Eurocard 8HP cards stacked along the vertical subrack
        for i, card in enumerate(eurocards):
            ensure_placement(c_vsubrack, device=card, position=1 + i * 10)  # 10 HP per card

        # K: ODF cassette mounts — each ModuleBay holds a fibre splice
        # cassette, placed at its position on the 2x6 grid carrier.
        CASSETTE_MM = 70  # slot width along each row in mm
        for row in (1, 2):
            for slot in range(1, 7):
                bay = ModuleBay.objects.get(device=odf, name=f'C{row}-{slot}')
                ensure_placement(
                    c_odf_grid, module_bay=bay,
                    row=row, row_span=1,
                    position=1 + (slot - 1) * CASSETTE_MM,
                    size=CASSETTE_MM,
                )

        # J: IED grid mounts — each physical module bay in the IED becomes
        # ONE Mount row on the grid carrier. This demonstrates the key
        # "one Device appears as many entries on its own carrier" story:
        # the IED (`ied`) is a single dcim.Device, but its 24 ModuleBays
        # give it up to 24 distinct positions on the grid carrier. Empty
        # bays just don't get a Mount (and can be rendered as placeholders
        # or simply absent).
        SLOT_MM = 30

        def slot_pos(n):
            """Convert slot number (1-indexed) to a Mount.position in mm units."""
            return 1 + (n - 1) * SLOT_MM

        # Helper to look up a ModuleBay by "R{row}S{slot}" name and mount it.
        def mount_slot(row, slot, size_slots=1, row_span=1):
            bay = ModuleBay.objects.get(device=ied, name=f'R{row}S{slot}')
            ensure_placement(
                c_ied_grid, module_bay=bay,
                row=row, row_span=row_span,
                position=slot_pos(slot),
                size=size_slots * SLOT_MM,
            )

        # Single-slot mounts matching the ied_population list above.
        mount_slot(1, 1)                 # primary PSU
        mount_slot(1, 2)                 # redundant PSU
        mount_slot(1, 3)                 # CPU
        mount_slot(1, 4)                 # binary I/O
        mount_slot(1, 5)                 # analog I/O
        mount_slot(1, 7)                 # binary I/O
        mount_slot(1, 8, size_slots=2)   # ethernet comms — occupies slots 8-9
        mount_slot(1, 11, size_slots=2,  # fibre comms — spans rows 1-2, slots 11-12
                   row_span=2)
        mount_slot(2, 1)                 # binary I/O
        mount_slot(2, 3)                 # binary I/O
        mount_slot(2, 5, size_slots=2)   # high-speed I/O — occupies slots 5-6
        mount_slot(2, 8)                 # binary I/O

        # v0.6.1: assign bundled line-art to the seed's profiles.
        from .cabinetview_assign_lineart import _auto_assign_all
        art_count = _auto_assign_all(stdout=self.stdout)

        self.stdout.write('  site:       OT Test Site')
        self.stdout.write('  rack:       Test Rack A (24U)')
        self.stdout.write('  scenarios:  20 total — 9 baseline + 7 classic OT/ICS (A-G) +')
        self.stdout.write('              4 v0.3.0 scenarios (H vertical DIN wall box,')
        self.stdout.write('              I vertical Eurocard subrack, J grid IED with 2 bars,')
        self.stdout.write('              K ISP ODF with 12-cassette grid)')
        self.stdout.write(f'  line-art:   {art_count} image(s) assigned to profiles')
