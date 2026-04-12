"""
v0.6.0 Feature 1: front_image on ModuleMountProfile.

NetBox 4.5's core ModuleType has no front_image field (only DeviceType
does). This field fills the gap so the SVG renderer can composite
module front-panel images into the placement rectangle.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_cabinet_view', '0005_mount_face'),
    ]

    operations = [
        migrations.AddField(
            model_name='modulemountprofile',
            name='front_image',
            field=models.ImageField(blank=True, upload_to='moduletype-images'),
        ),
    ]
