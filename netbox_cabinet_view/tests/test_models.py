"""Model-level tests: profile clean() validates front and rear port maps."""
from dcim.models import DeviceType
from dcim.models import Manufacturer
from django.core.exceptions import ValidationError
from django.test import TestCase

from netbox_cabinet_view.models import DeviceMountProfile


class DeviceMountProfileCleanTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        mfr = Manufacturer.objects.create(name='ACME', slug='acme')
        cls.device_type = DeviceType.objects.create(manufacturer=mfr, model='DT1', slug='dt1')

    def test_rear_port_map_is_validated(self):
        profile = DeviceMountProfile(device_type=self.device_type, rear_port_map=[{'type': 'bogus'}])
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_valid_front_and_rear_maps(self):
        profile = DeviceMountProfile(
            device_type=self.device_type,
            port_map=[
                {'name': 'eth0', 'type': 'pin', 'style': 'rj45', 'x_mm': 1, 'y_mm': 1, 'width_mm': 2, 'height_mm': 2},
            ],
            rear_port_map=[
                {'name': 'PSU', 'type': 'pin', 'style': 'iec-inlet', 'x_mm': 0, 'y_mm': 0, 'width_mm': 5, 'height_mm': 5},
            ],
        )
        profile.full_clean()
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(len(profile.port_map), 1)
        self.assertEqual(len(profile.rear_port_map), 1)
