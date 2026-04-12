"""
v0.5.0 Feature 1: per-face mounting.

Adds ``Mount.face`` — a CharField with choices ('', 'front', 'rear')
and default '' (both faces). Existing mounts automatically get
face='' so they continue to render on both faces, preserving
backward-compatible behavior.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_cabinet_view', '0004_mount_profiles'),
    ]

    operations = [
        migrations.AddField(
            model_name='mount',
            name='face',
            field=models.CharField(blank=True, default='', max_length=10),
        ),
    ]
