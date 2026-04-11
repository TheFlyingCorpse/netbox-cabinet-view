from netbox.plugins.navigation import PluginMenu, PluginMenuButton, PluginMenuItem


menu = PluginMenu(
    label='Cabinet View',
    groups=(
        (
            'Carriers & Mounts',
            (
                PluginMenuItem(
                    link='plugins:netbox_cabinet_view:carrier_list',
                    link_text='Carriers',
                    permissions=['netbox_cabinet_view.view_carrier'],
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_cabinet_view:carrier_add',
                            title='Add',
                            icon_class='mdi mdi-plus-thick',
                            permissions=['netbox_cabinet_view.add_carrier'],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link='plugins:netbox_cabinet_view:mount_list',
                    link_text='Mounts',
                    permissions=['netbox_cabinet_view.view_mount'],
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_cabinet_view:mount_add',
                            title='Add',
                            icon_class='mdi mdi-plus-thick',
                            permissions=['netbox_cabinet_view.add_mount'],
                        ),
                    ),
                ),
            ),
        ),
        (
            'Device Type Profiles',
            (
                PluginMenuItem(
                    link='plugins:netbox_cabinet_view:devicetypeprofile_list',
                    link_text='Device Type Profiles',
                    permissions=['netbox_cabinet_view.view_devicetypeprofile'],
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_cabinet_view:devicetypeprofile_add',
                            title='Add',
                            icon_class='mdi mdi-plus-thick',
                            permissions=['netbox_cabinet_view.add_devicetypeprofile'],
                        ),
                    ),
                ),
            ),
        ),
    ),
    icon_class='mdi mdi-cabinet',
)
