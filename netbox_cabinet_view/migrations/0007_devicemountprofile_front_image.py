"""
v0.6.0 Feature C: front_image on DeviceMountProfile.

Plugin-level fallback for host device front-panel images. The renderer
checks DeviceType.front_image (core) first, then this field.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_cabinet_view', '0006_modulemountprofile_front_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='devicemountprofile',
            name='front_image',
            field=models.ImageField(blank=True, upload_to='devicetype-images'),
        ),
    ]
