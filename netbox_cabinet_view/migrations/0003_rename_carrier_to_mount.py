"""
v0.4.0 rename: Carrier → Mount, Mount → Placement.

HAND-WRITTEN. Do NOT replace via `makemigrations` — Django's
autodetector produces incorrect output for a mutual rename where both
sides exist and one references the other. Operation order below is
carefully sequenced:

1. Rename field ``DeviceTypeProfile.hosts_carriers`` → ``hosts_mounts``.
2. Rename field ``Carrier.carrier_type`` → ``mount_type`` (still on
   the old 'Carrier' model name).
3. Rename model ``Mount`` → ``Placement`` FIRST to free the 'Mount'
   name, THEN rename ``Carrier`` → ``Mount``.
4. Rename the FK field that used to be ``Mount.carrier`` (now sitting
   on ``Placement``, still named ``carrier``) to ``mount``.
5. ``AlterField`` every FK to update its ``related_name`` — Django's
   ``RenameField`` does not touch ``related_name``.
6. Remove and re-add the three unique constraints (names embedded
   ``mount_``, now stale).
7. ``AlterModelOptions`` to install the new ``verbose_name`` /
   ``verbose_name_plural`` / ``ordering``.

Phases 1–7 are pure metadata. No DB rows are rewritten. Every existing
row in ``netbox_cabinet_view_carrier`` survives in
``netbox_cabinet_view_mount`` with the same PK; every row in
``netbox_cabinet_view_mount`` survives in
``netbox_cabinet_view_placement``; every FK stays pointing at the same
row. ``migrate netbox_cabinet_view 0002`` reverses every operation
cleanly.
"""

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('dcim', '0226_modulebay_rebuild_tree'),
        ('netbox_cabinet_view', '0002_grid_carrier'),
    ]

    operations = [
        # ---- Phase 1: rename DeviceTypeProfile field ----
        migrations.RenameField(
            model_name='devicetypeprofile',
            old_name='hosts_carriers',
            new_name='hosts_mounts',
        ),

        # ---- Phase 2: rename Carrier.carrier_type → mount_type ----
        migrations.RenameField(
            model_name='carrier',
            old_name='carrier_type',
            new_name='mount_type',
        ),

        # ---- Phase 3: rename models. Order matters — rename Mount first
        # to free the name, THEN rename Carrier to Mount.
        migrations.RenameModel(
            old_name='Mount',
            new_name='Placement',
        ),
        migrations.RenameModel(
            old_name='Carrier',
            new_name='Mount',
        ),

        # ---- Phase 4: rename the FK field on Placement from 'carrier' to 'mount'.
        migrations.RenameField(
            model_name='placement',
            old_name='carrier',
            new_name='mount',
        ),

        # ---- Phase 5: update related_name on every FK via AlterField.
        migrations.AlterField(
            model_name='mount',
            name='host_device',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cabinet_mounts',
                to='dcim.device',
            ),
        ),
        migrations.AlterField(
            model_name='placement',
            name='mount',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='placements',
                to='netbox_cabinet_view.mount',
            ),
        ),
        migrations.AlterField(
            model_name='placement',
            name='device',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cabinet_placements',
                to='dcim.device',
            ),
        ),
        migrations.AlterField(
            model_name='placement',
            name='device_bay',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cabinet_placements',
                to='dcim.devicebay',
            ),
        ),
        migrations.AlterField(
            model_name='placement',
            name='module_bay',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cabinet_placements',
                to='dcim.modulebay',
            ),
        ),

        # ---- Phase 6: re-name the three unique constraints.
        migrations.RemoveConstraint(
            model_name='placement',
            name='unique_mount_device',
        ),
        migrations.RemoveConstraint(
            model_name='placement',
            name='unique_mount_device_bay',
        ),
        migrations.RemoveConstraint(
            model_name='placement',
            name='unique_mount_module_bay',
        ),
        migrations.AddConstraint(
            model_name='placement',
            constraint=models.UniqueConstraint(
                condition=Q(('device__isnull', False)),
                fields=('device',),
                name='unique_placement_device',
            ),
        ),
        migrations.AddConstraint(
            model_name='placement',
            constraint=models.UniqueConstraint(
                condition=Q(('device_bay__isnull', False)),
                fields=('device_bay',),
                name='unique_placement_device_bay',
            ),
        ),
        migrations.AddConstraint(
            model_name='placement',
            constraint=models.UniqueConstraint(
                condition=Q(('module_bay__isnull', False)),
                fields=('module_bay',),
                name='unique_placement_module_bay',
            ),
        ),

        # ---- Phase 7: install new Meta options.
        migrations.AlterModelOptions(
            name='mount',
            options={
                'ordering': ('host_device', 'name'),
                'verbose_name': 'Mount',
                'verbose_name_plural': 'Mounts',
            },
        ),
        migrations.AlterModelOptions(
            name='placement',
            options={
                'ordering': ('mount', 'position', 'position_x', 'position_y'),
                'verbose_name': 'Placement',
                'verbose_name_plural': 'Placements',
            },
        ),
    ]
