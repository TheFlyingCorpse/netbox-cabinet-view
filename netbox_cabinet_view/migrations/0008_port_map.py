"""
v0.7.0 Feature 1a: port_map JSONField on both profile models.

Stores a list of port/connector overlay entries (zones, individual pins,
module bay positions, LCD areas) that the SVG renderer uses to draw
clickable status-coloured hotspots on device and module front-panel images.
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
            model_name='modulemountprofile',
            name='port_map',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Port/connector overlay definitions (zones, pins, LCD areas).',
            ),
        ),
    ]
