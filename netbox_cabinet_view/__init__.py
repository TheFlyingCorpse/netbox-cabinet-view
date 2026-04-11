from netbox.plugins import PluginConfig


class CabinetViewConfig(PluginConfig):
    name = 'netbox_cabinet_view'
    verbose_name = 'Cabinet View'
    description = (
        'DIN rails, subracks, mounting plates, and busbars for NetBox — with SVG '
        'visualization of cabinet interiors, including chassis/parent-child devices '
        'and modular PLCs.'
    )
    version = '0.1.1'
    author = 'Rune Darrud'
    author_email = 'theflyingcorpse@gmail.com'
    base_url = 'cabinet-view'
    # All APIs used (NetBoxModel, ViewTab, register_model_view, get_model_urls,
    # PluginTemplateExtension `models` list) are present in 4.4.0. Active
    # development and testing happens against 4.5.x.
    min_version = '4.4.0'
    max_version = '4.9.99'
    default_settings = {
        # SVG scale factor — 1 mm of carrier geometry = this many SVG pixels.
        'MM_TO_PX': 2,
        # Whether the Layout tab's SVG embeds DeviceType/ModuleType front images by default.
        'INCLUDE_IMAGES_DEFAULT': True,
    }


config = CabinetViewConfig
