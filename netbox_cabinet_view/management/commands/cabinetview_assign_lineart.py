"""
Assign bundled line-art images to ModuleMountProfile and DeviceMountProfile
records. Can be used standalone or called from cabinetview_seed.

Usage:
    # Assign line-art to all profiles that match the seed's module/device types
    python manage.py cabinetview_assign_lineart

    # List available line-art categories
    python manage.py cabinetview_assign_lineart --list

    # Assign a specific line-art file to a specific ModuleMountProfile
    python manage.py cabinetview_assign_lineart --module-profile-id 3 --art ied-type-a/psu.svg

    # Assign a specific line-art file to a specific DeviceMountProfile
    python manage.py cabinetview_assign_lineart --device-profile-id 155 --art host-chassis/ied-2row.svg

The command copies SVGs from the plugin's static/line-art/ directory into
Django's MEDIA_ROOT and sets the front_image field on the target profile.
Idempotent — re-running updates the image if it changed.
"""
import json
import os

from django.core.files import File
from django.core.management.base import BaseCommand

from netbox_cabinet_view.models import DeviceMountProfile, ModuleMountProfile


def _static_line_art_dir():
    """Return the absolute path to the bundled line-art directory."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'static', 'netbox_cabinet_view', 'line-art',
    )


def _load_manifest():
    """Load and return the manifest.json taxonomy."""
    manifest_path = os.path.join(_static_line_art_dir(), 'manifest.json')
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path) as f:
        return json.load(f)


def _assign_image(profile, art_relpath):
    """
    Copy a line-art SVG from static/ into the profile's front_image field.
    Returns True if the image was set, False if the file was not found.
    """
    art_dir = _static_line_art_dir()
    src = os.path.join(art_dir, art_relpath)
    if not os.path.exists(src):
        return False
    filename = art_relpath.replace('/', '-')
    with open(src, 'rb') as f:
        profile.front_image.save(filename, File(f), save=True)
    return True


# Mapping from seed ModuleType.model names to line-art relative paths.
_MODULE_ART_MAP = {
    'IED power supply module': 'ied-type-a/psu.svg',
    'IED CPU module': 'ied-type-a/cpu.svg',
    'IED binary I/O module': 'ied-type-a/binary-io.svg',
    'IED analog input module': 'ied-type-a/analog-io.svg',
    'IED Ethernet comms module': 'ied-type-a/comms-2slot.svg',
    'IED fibre comms module': 'ied-type-a/comms-2slot.svg',
    'IED high-speed I/O module': 'ied-type-a/binary-io.svg',
    'DI 16x24VDC': 'plc-fieldbus/di-8ch.svg',
    'Fibre splice cassette (12-splice)': 'transceivers/sfp-fibre.svg',
}

# Mapping from seed DeviceType.model names to line-art relative paths.
# Covers BOTH host chassis AND mountable devices (relays, MCBs, etc.).
_DEVICE_ART_MAP = {
    # Host chassis
    'Protection IED chassis 2-row (24-slot)': 'host-chassis/ied-2row.svg',
    'ODF chassis 1U (12-cassette grid)': 'host-chassis/odf-1u.svg',
    'Rack DIN shelf 2U (single rail)': 'host-chassis/din-shelf-2u.svg',
    'Rack DIN shelf 4U (dual rail)': 'host-chassis/din-shelf-4u.svg',
    'Rack DIN shelf 4U (single rail)': 'host-chassis/din-shelf-4u.svg',
    'Marshalling rack shelf 4U': 'host-chassis/din-shelf-4u.svg',
    'Fieldbus rack shelf 2U': 'host-chassis/din-shelf-2u.svg',
    'WDM shelf 1U 8-slot': 'host-chassis/wdm-1u.svg',
    'WDM shelf 1U 2-slot': 'host-chassis/wdm-1u.svg',
    'MCC cabinet 800x2200': 'host-chassis/mcc-panel.svg',
    'VFD cabinet 600x1800': 'host-chassis/vfd-cabinet.svg',
    'DIN rail TS35 480 mm': 'host-chassis/rtu-din.svg',
    # Mountable DIN-rail devices (relays, MCBs, terminals, PSUs, etc.)
    'DIN-mount relay': 'din-rail-devices/relay.svg',
    'Clip-on MCB 1P': 'din-rail-devices/mcb.svg',
    'DIN-mount MCB 1P': 'din-rail-devices/mcb.svg',
    'DIN-mount terminal block': 'din-rail-devices/terminal.svg',
    '24 V DIN-mount PSU': 'din-rail-devices/psu.svg',
    'Motor contactor': 'din-rail-devices/contactor.svg',
    'Fieldbus Ethernet coupler': 'plc-fieldbus/coupler.svg',
    'Fieldbus 8-channel DI module': 'plc-fieldbus/di-8ch.svg',
    'Fieldbus 8-channel DO module': 'plc-fieldbus/do-4ch.svg',
    'Industrial Ethernet switch (DIN)': 'network-switches/managed-switch-8port.svg',
    'Industrial Ethernet switch': 'network-switches/managed-switch-8port.svg',
    # Mountable plate devices
    'Variable frequency drive': 'din-rail-devices/psu.svg',
    'Auxiliary DIN rail strip 400 mm': 'host-chassis/rtu-din.svg',
    'Industrial panel-mount IPC': 'din-rail-devices/psu.svg',
    # Safety relays (plate-mounted)
    'Safety relay (generic)': 'din-rail-devices/relay.svg',
    # Protection IEDs (plate-mounted)
    'Overcurrent protection IED': 'ied-type-c/cpu.svg',
    'Line distance protection IED': 'ied-type-c/cpu.svg',
    # Test blocks
    'Test block (DIN-mount)': 'din-rail-devices/terminal.svg',
    # Eurocard cards
    'Eurocard 8HP plug-in card': 'ied-type-b/cpu.svg',
    # WDM filter children
    'WDM mux/demux filter 4-slot': 'transceivers/sfp-fibre.svg',
}


class Command(BaseCommand):
    help = (
        'Assign bundled line-art images to ModuleMountProfile and '
        'DeviceMountProfile records. Idempotent.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--list', action='store_true',
            help='List available line-art categories and files.',
        )
        parser.add_argument(
            '--module-profile-id', type=int,
            help='Assign art to a specific ModuleMountProfile by ID.',
        )
        parser.add_argument(
            '--device-profile-id', type=int,
            help='Assign art to a specific DeviceMountProfile by ID.',
        )
        parser.add_argument(
            '--art', type=str,
            help='Relative path to a line-art SVG (e.g. ied-type-a/psu.svg).',
        )

    def handle(self, *args, **options):
        if options['list']:
            return self._list_art()

        if options['module_profile_id'] and options['art']:
            return self._assign_single(
                ModuleMountProfile, options['module_profile_id'], options['art'],
            )

        if options['device_profile_id'] and options['art']:
            return self._assign_single(
                DeviceMountProfile, options['device_profile_id'], options['art'],
            )

        # Default: auto-assign to all seed profiles that match the mapping.
        return self._auto_assign()

    def _list_art(self):
        manifest = _load_manifest()
        if not manifest:
            self.stdout.write(self.style.ERROR('manifest.json not found'))
            return

        for cat in manifest.get('categories', []):
            self.stdout.write(self.style.SUCCESS(
                f"\n{cat['name']} ({cat['mount_type']}) — {cat['inspired_by']}"
            ))
            self.stdout.write(f"  Upload to: {cat['image_for']}")
            for item in cat.get('items', []):
                self.stdout.write(f"    {item['file']:40s}  {item['name']}")

    def _assign_single(self, model_cls, pk, art_path):
        try:
            profile = model_cls.objects.get(pk=pk)
        except model_cls.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'{model_cls.__name__} pk={pk} not found'))
            return

        if _assign_image(profile, art_path):
            self.stdout.write(self.style.SUCCESS(
                f'Assigned {art_path} to {profile}'
            ))
        else:
            self.stdout.write(self.style.ERROR(f'Art file not found: {art_path}'))

    def _auto_assign(self):
        count = _auto_assign_all(stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(f'\nAssigned {count} image(s).'))


def _auto_assign_all(stdout=None):
    """
    Auto-assign bundled line-art to all seed profiles that match
    the mapping. Callable from both the management command and the
    seed command. Returns the number of images assigned.
    """
    assigned = 0

    # Module profiles
    for profile in ModuleMountProfile.objects.select_related('module_type'):
        model_name = profile.module_type.model
        art = _MODULE_ART_MAP.get(model_name)
        if art and _assign_image(profile, art):
            if stdout:
                stdout.write(f'  module: {model_name} → {art}')
            assigned += 1

    # Device profiles (ALL — both hosts and mountable devices)
    for profile in DeviceMountProfile.objects.select_related('device_type'):
        model_name = profile.device_type.model
        # The seed prefixes with "Generic " — strip it for matching
        clean_name = model_name.replace('Generic ', '')
        art = _DEVICE_ART_MAP.get(clean_name) or _DEVICE_ART_MAP.get(model_name)
        if art and _assign_image(profile, art):
            if stdout:
                stdout.write(f'  device: {model_name} → {art}')
            assigned += 1

    return assigned
