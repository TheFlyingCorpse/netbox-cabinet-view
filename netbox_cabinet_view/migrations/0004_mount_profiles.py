"""
v0.4.0 Stage 2: DeviceTypeProfile → DeviceMountProfile rename + new
ModuleMountProfile model.

**Why the rename:** NetBox 4.5 ships a core ``dcim.ModuleTypeProfile``
which is an unrelated concept (reusable attribute schema for module
types, inheritable by ModuleType instances). To avoid collisions and
keep terminology consistent with the v0.4.0 "Mount / Placement"
vocabulary, the plugin renames:

- ``DeviceTypeProfile`` → ``DeviceMountProfile``
- new: ``ModuleMountProfile`` (the module-side counterpart)

Both Python class names AND DB table names are renamed. Existing
rows in ``netbox_cabinet_view_devicetypeprofile`` move into
``netbox_cabinet_view_devicemountprofile`` verbatim — no data is
rewritten or lost.

HAND-WRITTEN in the same style as 0003 because Django's autodetector
correctly handles simple single-model renames, but bundling the
rename with a new ``CreateModel`` and doing it by hand keeps both
operations in one reviewable file and preserves the ordering
documentation for future maintainers.
"""

import django.db.models.deletion
import netbox.models.deletion
import taggit.managers
import utilities.json
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dcim', '0226_modulebay_rebuild_tree'),
        ('extras', '0134_owner'),
        ('netbox_cabinet_view', '0003_rename_carrier_to_mount'),
    ]

    operations = [
        # ---- Phase 1: rename the existing DeviceTypeProfile model
        #               (also renames the underlying DB table).
        migrations.RenameModel(
            old_name='DeviceTypeProfile',
            new_name='DeviceMountProfile',
        ),

        # ---- Phase 2: update the Meta options so the new model carries
        # the new verbose_name (ordering doesn't change, but we rewrite
        # it to match the class definition in models.py).
        migrations.AlterModelOptions(
            name='devicemountprofile',
            options={
                'ordering': ('device_type',),
                'verbose_name': 'Device Mount Profile',
                'verbose_name_plural': 'Device Mount Profiles',
            },
        ),

        # ---- Phase 3: create the new ModuleMountProfile model.
        migrations.CreateModel(
            name='ModuleMountProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(
                    blank=True, default=dict,
                    encoder=utilities.json.CustomFieldJSONEncoder,
                )),
                ('mountable_on', models.CharField(blank=True, max_length=30)),
                ('mountable_subtype', models.CharField(blank=True, max_length=30)),
                ('footprint_primary', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('footprint_secondary', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('module_type', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cabinet_profile',
                    to='dcim.moduletype',
                )),
                ('tags', taggit.managers.TaggableManager(
                    through='extras.TaggedItem',
                    to='extras.Tag',
                )),
            ],
            options={
                'verbose_name': 'Module Mount Profile',
                'verbose_name_plural': 'Module Mount Profiles',
                'ordering': ('module_type',),
            },
            bases=(netbox.models.deletion.DeleteMixin, models.Model),
        ),
    ]
