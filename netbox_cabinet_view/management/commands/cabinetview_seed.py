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

        # --- Scenarios A-G ---

        # A: Marshalling shelf + terminal block
        dt_marshalling_shelf = goc(DeviceType, manufacturer=mfr,
                                   model='Marshalling 4U 19" shelf',
                                   slug='marshalling-4u-19in-shelf',
                                   defaults={'u_height': 4})
        dt_terminal_block = goc(DeviceType, manufacturer=mfr,
                                model='Phoenix UT 2.5 terminal block',
                                slug='phoenix-ut-25-terminal-block',
                                defaults={'u_height': 0})

        # B: MCC cabinet, withdrawable bucket, motor contactor
        dt_mcc_cabinet = goc(DeviceType, manufacturer=mfr,
                             model='MCC cabinet 800x2200',
                             slug='mcc-cabinet-800x2200',
                             defaults={'u_height': 0})
        dt_mcc_bucket = goc(DeviceType, manufacturer=mfr,
                            model='MCC withdrawable bucket',
                            slug='mcc-withdrawable-bucket',
                            defaults={'u_height': 0})
        dt_contactor = goc(DeviceType, manufacturer=mfr,
                           model='Schneider LC1D motor contactor',
                           slug='schneider-lc1d-motor-contactor',
                           defaults={'u_height': 0})

        # C: VFD cabinet, VFD drive, aux DIN strip, 24V PSU
        dt_vfd_cabinet = goc(DeviceType, manufacturer=mfr,
                             model='VFD cabinet 600x1800',
                             slug='vfd-cabinet-600x1800',
                             defaults={'u_height': 0})
        dt_vfd_drive = goc(DeviceType, manufacturer=mfr,
                           model='Schneider ATV630 VFD',
                           slug='schneider-atv630-vfd',
                           defaults={'u_height': 0})
        dt_aux_din_strip = goc(DeviceType, manufacturer=mfr,
                               model='Auxiliary DIN rail strip 400mm',
                               slug='auxiliary-din-rail-strip-400mm',
                               defaults={'u_height': 0})
        dt_24v_psu = goc(DeviceType, manufacturer=mfr,
                         model='Mean Well 24V PSU',
                         slug='mean-well-24v-psu',
                         defaults={'u_height': 0})

        # D: Wago remote I/O shelf + coupler + I/O modules
        dt_fieldbus_shelf = goc(DeviceType, manufacturer=mfr,
                                model='Fieldbus 2U 19" shelf',
                                slug='fieldbus-2u-19in-shelf',
                                defaults={'u_height': 2})
        dt_wago_coupler = goc(DeviceType, manufacturer=mfr,
                              model='Wago 750-362 ETHERNET coupler',
                              slug='wago-750-362-ethernet-coupler',
                              defaults={'u_height': 0})
        dt_wago_di = goc(DeviceType, manufacturer=mfr,
                         model='Wago 750-430 8DI module',
                         slug='wago-750-430-8di-module',
                         defaults={'u_height': 0})
        dt_wago_do = goc(DeviceType, manufacturer=mfr,
                         model='Wago 750-530 8DO module',
                         slug='wago-750-530-8do-module',
                         defaults={'u_height': 0})

        # E: Industrial Ethernet switch
        dt_ethernet_switch = goc(DeviceType, manufacturer=mfr,
                                 model='Hirschmann MACH1000 switch',
                                 slug='hirschmann-mach1000-switch',
                                 defaults={'u_height': 0})

        # F: Safety relay panel + PNOZ safety relay
        dt_safety_panel = goc(DeviceType, manufacturer=mfr,
                              model='Safety panel enclosure 600x800',
                              slug='safety-panel-enclosure-600x800',
                              defaults={'u_height': 0})
        dt_pnoz = goc(DeviceType, manufacturer=mfr,
                      model='Pilz PNOZ X3 safety relay',
                      slug='pilz-pnoz-x3-safety-relay',
                      defaults={'u_height': 0})

        # G: Substation protection panel + IEDs + test block rail + test block
        dt_protection_cabinet = goc(DeviceType, manufacturer=mfr,
                                    model='Substation protection cabinet 800x2200',
                                    slug='substation-protection-cabinet-800x2200',
                                    defaults={'u_height': 0})
        dt_siprotec = goc(DeviceType, manufacturer=mfr,
                          model='Siemens SIPROTEC 7SJ82',
                          slug='siemens-siprotec-7sj82',
                          defaults={'u_height': 0})
        dt_rel670 = goc(DeviceType, manufacturer=mfr,
                        model='ABB REL670',
                        slug='abb-rel670',
                        defaults={'u_height': 0})
        dt_test_block_rail = goc(DeviceType, manufacturer=mfr,
                                 model='Test block DIN rail 600mm',
                                 slug='test-block-din-rail-600mm',
                                 defaults={'u_height': 0})
        dt_rtxf_test = goc(DeviceType, manufacturer=mfr,
                           model='ABB RTXF 8-pole test block',
                           slug='abb-rtxf-8-pole-test-block',
                           defaults={'u_height': 0})

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

        # Scenarios A-G profiles
        ensure_profile(dt_marshalling_shelf, hosts_carriers=True, internal_width_mm=440,
                       internal_height_mm=175, internal_depth_mm=200)
        ensure_profile(dt_terminal_block, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=6)  # 5.2 mm wide, rounded to 6 mm

        ensure_profile(dt_mcc_cabinet, hosts_carriers=True, internal_width_mm=760,
                       internal_height_mm=2160, internal_depth_mm=600)
        # Bucket is BOTH a host (holds its own DIN rail with contactors) AND
        # mountable on the cabinet's vertical busbar.
        ensure_profile(dt_mcc_bucket, hosts_carriers=True, internal_width_mm=300,
                       internal_height_mm=250,
                       mountable_on='busbar', mountable_subtype='bb_riline_60',
                       footprint_primary=300, footprint_secondary=250)
        ensure_profile(dt_contactor, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=45)

        ensure_profile(dt_vfd_cabinet, hosts_carriers=True, internal_width_mm=560,
                       internal_height_mm=1760, internal_depth_mm=400)
        ensure_profile(dt_vfd_drive, mountable_on='mounting_plate',
                       mountable_subtype='plate_generic',
                       footprint_primary=250, footprint_secondary=400)
        # Aux DIN strip is BOTH a host (has its own DIN rail inside) AND mountable
        # on the VFD cabinet's back plate. Classic "rail on plate" nesting.
        ensure_profile(dt_aux_din_strip, hosts_carriers=True, internal_width_mm=400,
                       internal_height_mm=80,
                       mountable_on='mounting_plate', mountable_subtype='plate_generic',
                       footprint_primary=400, footprint_secondary=80)
        ensure_profile(dt_24v_psu, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=80)

        ensure_profile(dt_fieldbus_shelf, hosts_carriers=True, internal_width_mm=440,
                       internal_height_mm=88, internal_depth_mm=250)
        ensure_profile(dt_wago_coupler, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=100)
        ensure_profile(dt_wago_di, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=12)
        ensure_profile(dt_wago_do, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=12)

        ensure_profile(dt_ethernet_switch, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=90)

        ensure_profile(dt_safety_panel, hosts_carriers=True, internal_width_mm=600,
                       internal_height_mm=800, internal_depth_mm=250)
        ensure_profile(dt_pnoz, mountable_on='mounting_plate', mountable_subtype='plate_generic',
                       footprint_primary=45, footprint_secondary=100)

        ensure_profile(dt_protection_cabinet, hosts_carriers=True, internal_width_mm=760,
                       internal_height_mm=2160, internal_depth_mm=600)
        ensure_profile(dt_siprotec, mountable_on='mounting_plate', mountable_subtype='plate_generic',
                       footprint_primary=215, footprint_secondary=270)
        ensure_profile(dt_rel670, mountable_on='mounting_plate', mountable_subtype='plate_generic',
                       footprint_primary=483, footprint_secondary=270)
        ensure_profile(dt_test_block_rail, hosts_carriers=True, internal_width_mm=600,
                       internal_height_mm=60,
                       mountable_on='mounting_plate', mountable_subtype='plate_generic',
                       footprint_primary=600, footprint_secondary=60)
        ensure_profile(dt_rtxf_test, mountable_on='din_rail', mountable_subtype='ts35',
                       footprint_primary=80)

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
        mcb_4u_a = ensure_device('MCB 4U-A', dt_mcb, 'mcb')
        mcb_4u_b = ensure_device('MCB 4U-B', dt_mcb, 'mcb')
        mcb_4u_c = ensure_device('MCB 4U-C', dt_mcb, 'mcb')

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
        vfd_drive = ensure_device('ATV630-M1', dt_vfd_drive, 'ipc')
        aux_rail_device = ensure_device('VFD aux DIN strip', dt_aux_din_strip, 'rail')
        psu_device = ensure_device('24V PSU #1', dt_24v_psu, 'relay')
        vfd_contactor_a = ensure_device('VFD contactor KM1', dt_contactor, 'relay')
        vfd_contactor_b = ensure_device('VFD contactor KM2', dt_contactor, 'relay')

        # --- Scenario D: Wago remote I/O station (2U rack) ---
        wago_shelf = ensure_device('Wago Remote I/O #1', dt_fieldbus_shelf, 'plc')
        wago_coupler = ensure_device('Wago 750-362 #1', dt_wago_coupler, 'plc')
        wago_di_modules = [
            ensure_device(f'Wago DI #{i}', dt_wago_di, 'plc') for i in range(1, 5)
        ]
        wago_do_modules = [
            ensure_device(f'Wago DO #{i}', dt_wago_do, 'plc') for i in range(1, 4)
        ]

        # --- Scenario E: Industrial Ethernet switch (2U rack) ---
        switch_shelf = ensure_device('Industrial Switch Shelf #1', dt_fieldbus_shelf, 'plc')
        industrial_switch = ensure_device('Hirschmann MACH1000 #1', dt_ethernet_switch, 'plc')

        # --- Scenario F: Safety relay panel (standalone) ---
        safety_cabinet = ensure_device('Safety Panel #1', dt_safety_panel, 'enclosure')
        pnoz_relays = [
            ensure_device(f'PNOZ {name}', dt_pnoz, 'relay')
            for name in ('E-Stop 1', 'E-Stop 2', 'Guard', 'Light Curtain')
        ]

        # --- Scenario G: Substation protection panel (standalone) ---
        protection_cabinet = ensure_device('Protection Panel #1', dt_protection_cabinet, 'plc')
        siprotec_1 = ensure_device('7SJ82-F1', dt_siprotec, 'plc')
        siprotec_2 = ensure_device('7SJ82-F2', dt_siprotec, 'plc')
        rel670 = ensure_device('REL670-L1', dt_rel670, 'plc')
        test_rail_device = ensure_device('Test block rail #1', dt_test_block_rail, 'rail')
        test_blocks = [
            ensure_device(f'Test block F{i:02d}', dt_rtxf_test, 'relay')
            for i in range(1, 5)
        ]

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
            (wago_shelf,         17,  'front'),
            (switch_shelf,       19,  'front'),
        ]

        managed_devices = [d for d, _, _ in rack_layout]
        for dev in managed_devices:
            if dev.rack_id is not None or dev.position is not None:
                dev.rack = None
                dev.position = None
                dev.face = ''
                dev.save()

        for dev, u, face in rack_layout:
            dev.rack = rack
            dev.position = u
            dev.face = face
            dev.save()

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

        # --- Scenarios A-G carriers ---

        # A: Marshalling shelf — one DIN rail in mm units (terminal blocks are 5-6 mm)
        c_marshalling = ensure_carrier(
            marshalling_shelf, 'Terminal rail',
            carrier_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='mm', length_mm=420, offset_x_mm=10, offset_y_mm=88,
        )

        # B: MCC cabinet — vertical busbar, plus one DIN rail inside each bucket
        c_mcc_busbar = ensure_carrier(
            mcc_cabinet, 'Vertical busbar',
            carrier_type='busbar', subtype='bb_riline_60', orientation='vertical',
            unit='mm', length_mm=1800, offset_x_mm=250, offset_y_mm=200,
        )
        c_bucket_rails = []
        for i, bucket in enumerate(buckets):
            c_bucket_rails.append(ensure_carrier(
                bucket, 'Bucket rail',
                carrier_type='din_rail', subtype='ts35', orientation='horizontal',
                unit='mm', length_mm=280, offset_x_mm=10, offset_y_mm=80,
            ))

        # C: VFD cabinet — back plate, plus a nested DIN strip device with its own rail
        c_vfd_plate = ensure_carrier(
            vfd_cabinet, 'Back plate',
            carrier_type='mounting_plate', subtype='plate_generic',
            unit='mm', width_mm=560, height_mm=1760, offset_x_mm=0, offset_y_mm=0,
        )
        c_aux_rail = ensure_carrier(
            aux_rail_device, 'Aux rail',
            carrier_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='mm', length_mm=380, offset_x_mm=10, offset_y_mm=30,
        )

        # D: Wago remote I/O — DIN rail with coupler + I/O modules
        c_wago = ensure_carrier(
            wago_shelf, 'Main rail',
            carrier_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='mm', length_mm=420, offset_x_mm=10, offset_y_mm=44,
        )

        # E: Industrial switch — DIN rail with a single 90 mm switch
        c_switch = ensure_carrier(
            switch_shelf, 'Main rail',
            carrier_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='mm', length_mm=420, offset_x_mm=10, offset_y_mm=44,
        )

        # F: Safety relay panel — back plate with PNOZ relays
        c_safety_plate = ensure_carrier(
            safety_cabinet, 'Back plate',
            carrier_type='mounting_plate', subtype='plate_generic',
            unit='mm', width_mm=600, height_mm=800, offset_x_mm=0, offset_y_mm=0,
        )

        # G: Protection panel — back plate with IEDs + nested test block rail
        c_protection_plate = ensure_carrier(
            protection_cabinet, 'Back plate',
            carrier_type='mounting_plate', subtype='plate_generic',
            unit='mm', width_mm=760, height_mm=2160, offset_x_mm=0, offset_y_mm=0,
        )
        c_test_rail = ensure_carrier(
            test_rail_device, 'Test rail',
            carrier_type='din_rail', subtype='ts35', orientation='horizontal',
            unit='mm', length_mm=580, offset_x_mm=10, offset_y_mm=20,
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

        # ISP 4U DIN shelf: 5 relays along the single rail
        for i, r in enumerate((relay_isp_a, relay_isp_b, relay_isp_c, relay_isp_d, relay_isp_e)):
            ensure_mount(c_din_4u_isp, device=r, position=1 + i * 4, size=1)

        # --- Scenarios A-G mounts (sizes mostly default from device profile footprint) ---

        # A: Marshalling — 20 terminal blocks at 6 mm spacing, starting 10 mm in
        for i, tb in enumerate(terminal_blocks):
            ensure_mount(c_marshalling, device=tb, position=10 + i * 6)

        # B: MCC — 3 withdrawable buckets on the vertical busbar
        ensure_mount(c_mcc_busbar, device=buckets[0], position=100)
        ensure_mount(c_mcc_busbar, device=buckets[1], position=500)
        ensure_mount(c_mcc_busbar, device=buckets[2], position=900)
        # Each bucket has its own DIN rail with one contactor and one relay
        for rail, contactor, aux in zip(c_bucket_rails, bucket_contactors, bucket_relays):
            ensure_mount(rail, device=contactor, position=30)
            ensure_mount(rail, device=aux, position=100)

        # C: VFD cabinet plate — VFD drive at top, aux DIN strip below
        ensure_mount(c_vfd_plate, device=vfd_drive, position_x=150, position_y=100)
        ensure_mount(c_vfd_plate, device=aux_rail_device, position_x=80, position_y=600)
        # Aux DIN strip carries a PSU and two VFD contactors
        ensure_mount(c_aux_rail, device=psu_device, position=20)
        ensure_mount(c_aux_rail, device=vfd_contactor_a, position=120)
        ensure_mount(c_aux_rail, device=vfd_contactor_b, position=180)

        # D: Wago remote I/O — coupler at left, then alternating DI/DO modules
        ensure_mount(c_wago, device=wago_coupler, position=10)
        x = 115  # left edge of the first I/O module, just right of the coupler
        for di in wago_di_modules:
            ensure_mount(c_wago, device=di, position=x)
            x += 14
        for do in wago_do_modules:
            ensure_mount(c_wago, device=do, position=x)
            x += 14

        # E: Industrial switch — single switch centered on the rail
        ensure_mount(c_switch, device=industrial_switch, position=160)

        # F: Safety relay panel — 4 PNOZ relays spaced along the plate top
        for i, pnoz in enumerate(pnoz_relays):
            ensure_mount(c_safety_plate, device=pnoz, position_x=60 + i * 130, position_y=150)

        # G: Protection panel — 2 SIPROTEC IEDs, 1 REL670, test block rail below
        ensure_mount(c_protection_plate, device=siprotec_1, position_x=270, position_y=200)
        ensure_mount(c_protection_plate, device=siprotec_2, position_x=270, position_y=550)
        ensure_mount(c_protection_plate, device=rel670,    position_x=140, position_y=900)
        ensure_mount(c_protection_plate, device=test_rail_device,
                     position_x=80, position_y=1300)
        # The test block rail carries 4 test blocks
        for i, tb in enumerate(test_blocks):
            ensure_mount(c_test_rail, device=tb, position=20 + i * 130)

        self.stdout.write('  site:       OT Test Site')
        self.stdout.write('  rack:       Test Rack A (24U)')
        self.stdout.write('  scenarios:  9 standalone + 7 classic OT/ICS (A marshalling, B MCC,')
        self.stdout.write('              C VFD, D Wago I/O, E industrial switch, F safety panel,')
        self.stdout.write('              G substation protection panel)')
