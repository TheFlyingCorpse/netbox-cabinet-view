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
  * 11 DeviceType + DeviceTypeProfile rows covering all four carrier types
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
from netbox_cabinet_view.models import Carrier, DeviceTypeProfile, Mount


def goc(_model_cls, defaults=None, **lookup):
    obj, _ = _model_cls.objects.get_or_create(defaults=defaults or {}, **lookup)
    return obj


def ensure_profile(dt, **fields):
    obj, _ = DeviceTypeProfile.objects.update_or_create(
        device_type=dt, defaults=fields,
    )
    return obj


def ensure_carrier(host, name, **fields):
    obj, created = Carrier.objects.get_or_create(
        host_device=host, name=name, defaults=fields,
    )
    if not created:
        for k, v in fields.items():
            setattr(obj, k, v)
        obj.save()
    return obj


def ensure_mount(carrier, **fields):
    key = {'carrier': carrier}
    for k in ('device', 'device_bay', 'module_bay'):
        if fields.get(k) is not None:
            key[k] = fields[k]
            break
    obj, created = Mount.objects.get_or_create(**key, defaults=fields)
    if not created:
        for k, v in fields.items():
            setattr(obj, k, v)
        obj.save()
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
        # ------------------------------------------------------------------
        dt_din_rail = goc(DeviceType, manufacturer=mfr, model='DIN TS35 480mm', slug='din-ts35-480mm',
                          defaults={'u_height': 0})
        dt_relay = goc(DeviceType, manufacturer=mfr, model='Phoenix REL-MR', slug='phoenix-rel-mr',
                       defaults={'u_height': 0})
        dt_plate = goc(DeviceType, manufacturer=mfr, model='Rittal TS8 800x2000', slug='rittal-ts8-800x2000',
                       defaults={'u_height': 0})
        dt_ipc = goc(DeviceType, manufacturer=mfr, model='Industrial PC', slug='industrial-pc',
                     defaults={'u_height': 0})
        dt_plc_backplane = goc(DeviceType, manufacturer=mfr, model='Test PLC Backplane 8-slot',
                               slug='test-plc-backplane-8-slot', defaults={'u_height': 0})
        dt_wdm_shelf = goc(DeviceType, manufacturer=mfr, model='WDM Shelf 1U 8-slot',
                           slug='wdm-shelf-1u-8-slot',
                           defaults={'u_height': 1, 'subdevice_role': 'parent'})
        dt_wdm_shelf2 = goc(DeviceType, manufacturer=mfr, model='WDM Shelf 1U 2-slot',
                            slug='wdm-shelf-1u-2-slot',
                            defaults={'u_height': 1, 'subdevice_role': 'parent'})
        dt_wdm_filter = goc(DeviceType, manufacturer=mfr, model='WDM Mux/Demux 4-slot',
                            slug='wdm-mux-demux-4-slot',
                            defaults={'u_height': 0, 'subdevice_role': 'child'})
        dt_busbar = goc(DeviceType, manufacturer=mfr, model='Rittal RiLine 60 1m',
                        slug='rittal-riline-60-1m', defaults={'u_height': 0})
        dt_mcb = goc(DeviceType, manufacturer=mfr, model='MCB 1P 45mm', slug='mcb-1p-45mm',
                     defaults={'u_height': 0})
        # Rack-mounted DIN shelves for rack-elevation testing
        dt_din_shelf_2u = goc(DeviceType, manufacturer=mfr, model='Rittal 2U 19" DIN rail shelf',
                              slug='rittal-2u-19in-din-rail-shelf',
                              defaults={'u_height': 2})
        dt_din_shelf_4u = goc(DeviceType, manufacturer=mfr, model='Rittal 4U 19" DIN rail shelf',
                              slug='rittal-4u-19in-din-rail-shelf',
                              defaults={'u_height': 4})
        dt_din_shelf_4u_isp = goc(DeviceType, manufacturer=mfr,
                                  model='ISP 4U 19" DIN rail shelf (1 rail)',
                                  slug='isp-4u-19in-din-rail-shelf-1-rail',
                                  defaults={'u_height': 4})

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
        # DeviceTypeProfiles
        # ------------------------------------------------------------------
        ensure_profile(dt_din_rail,      hosts_carriers=True, internal_width_mm=480, internal_height_mm=80)
        ensure_profile(dt_relay,         mountable_on='din_rail', mountable_subtype='ts35', footprint_primary=1)
        ensure_profile(dt_plate,         hosts_carriers=True, internal_width_mm=760, internal_height_mm=1960)
        ensure_profile(dt_ipc,           mountable_on='mounting_plate', footprint_primary=220, footprint_secondary=90)
        ensure_profile(dt_plc_backplane, hosts_carriers=True, internal_width_mm=400, internal_height_mm=160)
        ensure_profile(dt_wdm_shelf,     hosts_carriers=True, internal_width_mm=440, internal_height_mm=44)
        ensure_profile(dt_wdm_shelf2,    hosts_carriers=True, internal_width_mm=440, internal_height_mm=44)
        ensure_profile(dt_wdm_filter,    mountable_on='subrack', mountable_subtype='hp_3u', footprint_primary=20)
        ensure_profile(dt_busbar,        hosts_carriers=True, internal_width_mm=1000, internal_height_mm=60)
        ensure_profile(dt_mcb,           mountable_on='busbar', mountable_subtype='bb_riline_60', footprint_primary=18)
        # 2U shelf: 2U inner ≈ 88 mm, real depth 200 mm for cable clearance
        ensure_profile(dt_din_shelf_2u,  hosts_carriers=True, internal_width_mm=440,
                       internal_height_mm=88, internal_depth_mm=200)
        # 4U shelf: 4U inner ≈ 175 mm, room for two stacked DIN rails + wire management
        ensure_profile(dt_din_shelf_4u,  hosts_carriers=True, internal_width_mm=440,
                       internal_height_mm=175, internal_depth_mm=200)
        # 4U shelf, single rail (ISP marshalling style) — one rail centered with
        # generous wire-management space above and below.
        ensure_profile(dt_din_shelf_4u_isp, hosts_carriers=True, internal_width_mm=440,
                       internal_height_mm=175, internal_depth_mm=200)

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
        plate_device = ensure_device('Enclosure #1', dt_plate, 'enclosure')
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
        busbar_device = ensure_device('LV Panel Busbar', dt_busbar, 'busbar')
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
                   defaults={'u_height': 16, 'status': 'active'})
        if rack.u_height < 16:
            rack.u_height = 16
            rack.save()

        # Scenario 7: 2U DIN rail shelf at U6-7 with a single rail and 3 relays
        din_shelf_2u = ensure_device('DIN Shelf 2U #1', dt_din_shelf_2u, 'shelf',
                                     rack=rack, position=6, face='front')
        relay_2u_a = ensure_device('Relay 2U-A', dt_relay, 'relay')
        relay_2u_b = ensure_device('Relay 2U-B', dt_relay, 'relay')
        relay_2u_c = ensure_device('Relay 2U-C', dt_relay, 'relay')

        # Scenario 8: 4U DIN rail shelf at U8-11 with two stacked rails and a mix of modules
        din_shelf_4u = ensure_device('DIN Shelf 4U #1', dt_din_shelf_4u, 'shelf',
                                     rack=rack, position=8, face='front')
        relay_4u_a = ensure_device('Relay 4U-A', dt_relay, 'relay')
        relay_4u_b = ensure_device('Relay 4U-B', dt_relay, 'relay')
        mcb_4u_a = ensure_device('MCB 4U-A', dt_mcb, 'mcb')
        mcb_4u_b = ensure_device('MCB 4U-B', dt_mcb, 'mcb')
        mcb_4u_c = ensure_device('MCB 4U-C', dt_mcb, 'mcb')

        # Scenario 9: ISP-style 4U DIN rail shelf at U12-15 with a single centered rail
        din_shelf_4u_isp = ensure_device('DIN Shelf 4U ISP #1', dt_din_shelf_4u_isp, 'shelf',
                                         rack=rack, position=12, face='front')
        relay_isp_a = ensure_device('Relay ISP-A', dt_relay, 'relay')
        relay_isp_b = ensure_device('Relay ISP-B', dt_relay, 'relay')
        relay_isp_c = ensure_device('Relay ISP-C', dt_relay, 'relay')
        relay_isp_d = ensure_device('Relay ISP-D', dt_relay, 'relay')
        relay_isp_e = ensure_device('Relay ISP-E', dt_relay, 'relay')

        # Move existing WDM shelves into the rack at U4 and U5 (so we have the
        # full variety 1U / 2U / 4U on one rack).
        if wdm_shelf2.rack_id != rack.pk:
            wdm_shelf2.rack = rack
            wdm_shelf2.position = 4
            wdm_shelf2.face = 'front'
            wdm_shelf2.save()
        if wdm_shelf.rack_id != rack.pk:
            wdm_shelf.rack = rack
            wdm_shelf.position = 5
            wdm_shelf.face = 'front'
            wdm_shelf.save()

        # ------------------------------------------------------------------
        # Carriers
        # ------------------------------------------------------------------
        c_din = ensure_carrier(
            din_device, 'Main rail',
            carrier_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='module_17_5', length_mm=480, offset_x_mm=0, offset_y_mm=20,
        )
        c_plate = ensure_carrier(
            plate_device, 'Back plate',
            carrier_type='mounting_plate', subtype='plate_generic',
            unit='mm', width_mm=760, height_mm=1960, offset_x_mm=0, offset_y_mm=0,
        )
        c_wdm = ensure_carrier(
            wdm_shelf, 'Slot carrier',
            carrier_type='subrack', subtype='hp_3u', orientation='horizontal',
            unit='hp_5_08', length_mm=406, offset_x_mm=15, offset_y_mm=5,
        )
        c_wdm2 = ensure_carrier(
            wdm_shelf2, 'Slot carrier',
            carrier_type='subrack', subtype='hp_3u', orientation='horizontal',
            unit='hp_5_08', length_mm=440, offset_x_mm=0, offset_y_mm=4,
        )
        c_busbar = ensure_carrier(
            busbar_device, 'L1/L2/L3 bar',
            carrier_type='busbar', subtype='bb_riline_60', orientation='horizontal',
            unit='mm', length_mm=1000, offset_x_mm=0, offset_y_mm=20,
        )
        c_plc = ensure_carrier(
            plc_backplane, 'Backplane',
            carrier_type='subrack', subtype='hp_3u', orientation='horizontal',
            unit='hp_5_08', length_mm=400, offset_x_mm=0, offset_y_mm=10,
        )

        # 2U DIN shelf — single rail centered vertically
        c_din_2u = ensure_carrier(
            din_shelf_2u, 'Main rail',
            carrier_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='module_17_5', length_mm=420, offset_x_mm=10, offset_y_mm=40,
        )

        # 4U DIN shelf — two stacked rails
        c_din_4u_upper = ensure_carrier(
            din_shelf_4u, 'Upper rail',
            carrier_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='module_17_5', length_mm=420, offset_x_mm=10, offset_y_mm=45,
        )
        c_din_4u_lower = ensure_carrier(
            din_shelf_4u, 'Lower rail',
            carrier_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='module_17_5', length_mm=420, offset_x_mm=10, offset_y_mm=130,
        )

        # ISP 4U DIN shelf — one rail centered vertically, wire room above/below
        c_din_4u_isp = ensure_carrier(
            din_shelf_4u_isp, 'Main rail',
            carrier_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='module_17_5', length_mm=420, offset_x_mm=10, offset_y_mm=88,
        )

        # ------------------------------------------------------------------
        # Mounts (sizes left implicit where the profile provides a footprint)
        # ------------------------------------------------------------------
        ensure_mount(c_din, device=relay1, position=1, size=1)
        ensure_mount(c_din, device=relay2, position=5, size=1)

        ensure_mount(c_plate, device=ipc, position_x=100, position_y=200, size_x=220, size_y=90)

        ensure_mount(c_wdm, device_bay=bay1, position=1, size=4)
        ensure_mount(c_wdm, device_bay=bay5, position=41, size=4)

        # WDM 2-slot: fixed 20-HP slots centered in each half of the 86-HP carrier
        ensure_mount(c_wdm2, device_bay=bay2_1, position=12, size=20)
        ensure_mount(c_wdm2, device_bay=bay2_2, position=55, size=20)

        ensure_mount(c_busbar, device=mcb1, position=20, size=18)
        ensure_mount(c_busbar, device=mcb2, position=60, size=18)
        ensure_mount(c_busbar, device=mcb3, position=100, size=18)

        ensure_mount(c_plc, module_bay=mb2, position=11, size=10)
        ensure_mount(c_plc, module_bay=mb4, position=31, size=10)

        # 2U DIN shelf: three relays spread across the rail
        ensure_mount(c_din_2u, device=relay_2u_a, position=1,  size=1)
        ensure_mount(c_din_2u, device=relay_2u_b, position=5,  size=1)
        ensure_mount(c_din_2u, device=relay_2u_c, position=9,  size=1)

        # 4U DIN shelf: 2 relays on upper rail, 3 MCBs on lower rail
        ensure_mount(c_din_4u_upper, device=relay_4u_a, position=1, size=1)
        ensure_mount(c_din_4u_upper, device=relay_4u_b, position=5, size=1)
        ensure_mount(c_din_4u_lower, device=mcb_4u_a, position=1,  size=1)
        ensure_mount(c_din_4u_lower, device=mcb_4u_b, position=3,  size=1)
        ensure_mount(c_din_4u_lower, device=mcb_4u_c, position=5,  size=1)

        self.stdout.write('  site:       OT Test Site')
        self.stdout.write('  rack:       Test Rack A (12U)')
        self.stdout.write('  scenarios:  DIN rail, mounting plate, WDM 8-slot, WDM 2-slot,')
        self.stdout.write('              LV busbar, modular PLC, 2U rack DIN shelf, 4U rack DIN shelf')
