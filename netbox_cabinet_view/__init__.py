import logging

from netbox.plugins import PluginConfig


class CabinetViewConfig(PluginConfig):
    name = 'netbox_cabinet_view'
    verbose_name = 'Cabinet View'
    description = (
        'DIN rails, subracks, mounting plates, busbars, and multi-row grids '
        'for NetBox — with SVG visualization of cabinet interiors, chassis/'
        'parent-child devices, and modular PLCs. OT/ICS focus.'
    )
    version = '0.7.0'
    author = 'Rune Darrud'
    author_email = 'theflyingcorpse@gmail.com'
    base_url = 'cabinet-view'
    graphql_schema = 'graphql.schema.schema'
    # All APIs used (NetBoxModel, ViewTab, register_model_view, get_model_urls,
    # PluginTemplateExtension `models` list) are present in 4.4.0. Active
    # development and testing happens against 4.5.x.
    min_version = '4.4.0'
    max_version = '4.9.99'
    default_settings = {
        # SVG scale factor — 1 mm of mount geometry = this many SVG pixels.
        'MM_TO_PX': 2,
        # Whether the Layout tab's SVG embeds DeviceType/ModuleType front images by default.
        'INCLUDE_IMAGES_DEFAULT': True,
        # Monkey-patch the core `RackElevationSVG.draw_device_front` so that
        # devices whose DeviceType has `hosts_mounts=True` render their
        # cabinet layout SVG inside the rack elevation at their U slot.
        # Falls back to the stock `DeviceType.front_image` for 1U devices
        # (too narrow for a layout) and whenever the patch can't resolve its
        # target URL. Flip to False if a NetBox upgrade breaks the patch.
        'PATCH_RACK_ELEVATION': True,
        # Finding D (v0.4.0): opt-in spreadsheet-style slot ledger above
        # the SVG on the Layout tab. Default False because the table is
        # noisy for dense cabinets and some users just want the picture.
        # Flip to True in PLUGINS_CONFIG to try it:
        #   PLUGINS_CONFIG = {
        #       'netbox_cabinet_view': {'SLOT_LEDGER_ENABLED': True},
        #   }
        'SLOT_LEDGER_ENABLED': False,
        # v0.7.0: port/connector overlay status colours (hex, no '#' prefix).
        # Keys: connected_enabled, connected_disabled, unconnected_enabled,
        # unconnected_disabled. Override in PLUGINS_CONFIG to customise.
        'PORT_STATUS_COLORS': {
            'connected_enabled': '2ecc71',    # green
            'connected_disabled': 'f39c12',   # amber
            'unconnected_enabled': '95a5a6',  # grey
            'unconnected_disabled': '7f8c8d', # dark grey
        },
        # v0.7.0: show device.primary_ip4 on CPU-type placements as an LCD
        # overlay. Off by default — opt in per deployment.
        'SHOW_MANAGEMENT_IP': False,
    }

    def ready(self):
        super().ready()
        from django.conf import settings
        cfg = settings.PLUGINS_CONFIG.get(self.name, {}) if hasattr(settings, 'PLUGINS_CONFIG') else {}
        if cfg.get('PATCH_RACK_ELEVATION', self.default_settings['PATCH_RACK_ELEVATION']):
            try:
                from .rack_elevation_patch import install_patch
                install_patch()
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    'netbox_cabinet_view: rack-elevation patch install failed '
                    '(plugin will load without it): %s', exc,
                )


config = CabinetViewConfig
