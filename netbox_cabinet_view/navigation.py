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
            'Mount Profiles',
            (
                PluginMenuItem(
                    link='plugins:netbox_cabinet_view:devicemountprofile_list',
                    link_text='Device Mount Profiles',
                    permissions=['netbox_cabinet_view.view_devicemountprofile'],
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_cabinet_view:devicemountprofile_add',
                            title='Add',
                            icon_class='mdi mdi-plus-thick',
                            permissions=['netbox_cabinet_view.add_devicemountprofile'],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link='plugins:netbox_cabinet_view:modulemountprofile_list',
                    link_text='Module Mount Profiles',
                    permissions=['netbox_cabinet_view.view_modulemountprofile'],
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_cabinet_view:modulemountprofile_add',
                            title='Add',
                            icon_class='mdi mdi-plus-thick',
                            permissions=['netbox_cabinet_view.add_modulemountprofile'],
                        ),
                    ),
                ),
            ),
        ),
        (
            'Resources',
            (
                PluginMenuItem(
                    link='plugins:netbox_cabinet_view:line_art_gallery',
                    link_text='Line-Art Gallery',
                    permissions=[],
                ),
            ),
        ),
    ),
    icon_class='mdi mdi-cabinet',
)
