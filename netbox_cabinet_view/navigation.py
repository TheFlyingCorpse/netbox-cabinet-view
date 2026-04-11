from netbox.plugins.navigation import PluginMenu, PluginMenuButton, PluginMenuItem


menu = PluginMenu(
    label='Cabinet View',
    groups=(
        (
            'Mounts & Placements',
            (
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
                PluginMenuItem(
                    link='plugins:netbox_cabinet_view:placement_list',
                    link_text='Placements',
                    permissions=['netbox_cabinet_view.view_placement'],
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_cabinet_view:placement_add',
                            title='Add',
                            icon_class='mdi mdi-plus-thick',
                            permissions=['netbox_cabinet_view.add_placement'],
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
