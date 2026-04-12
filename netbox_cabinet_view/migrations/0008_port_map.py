"""
v0.7.0 Feature 1: port_map JSONField + enable_port_overlay toggle on both
profile models.

port_map stores a list of port/connector overlay entries (zones, individual
pins, module bay positions, LCD areas) that the SVG renderer uses to draw
clickable status-coloured hotspots on device and module front-panel images.

enable_port_overlay is a per-profile boolean (default True) that controls
whether the overlay renders for this specific device/module type.  A global
ENABLE_PORT_OVERLAY setting in PLUGINS_CONFIG acts as a master switch.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_cabinet_view', '0007_devicemountprofile_front_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='devicemountprofile',
            name='port_map',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Port/connector overlay definitions (zones, pins, module bays, LCD areas).',
            ),
        ),
        migrations.AddField(
            model_name='devicemountprofile',
            name='enable_port_overlay',
            field=models.BooleanField(
                default=True,
                help_text='Render the port/connector overlay on this device type.',
            ),
        ),
        migrations.AddField(
            model_name='modulemountprofile',
            name='port_map',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Port/connector overlay definitions (zones, pins, LCD areas).',
            ),
        ),
        migrations.AddField(
            model_name='modulemountprofile',
            name='enable_port_overlay',
            field=models.BooleanField(
                default=True,
                help_text='Render the port/connector overlay on this module type.',
            ),
        ),
    ]
