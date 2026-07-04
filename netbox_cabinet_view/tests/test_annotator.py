"""Tests for the in-NetBox port-map annotator save view."""
import json

from dcim.models import DeviceType
from dcim.models import Manufacturer
from django.contrib.auth import get_user_model
from django.test import Client
from django.test import TestCase
from django.urls import reverse

from netbox_cabinet_view.models import DeviceMountProfile

ANNOTATOR = 'plugins:netbox_cabinet_view:portmap_annotator'


class AnnotatorViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        mfr = Manufacturer.objects.create(name='ACME', slug='acme')
        dt = DeviceType.objects.create(manufacturer=mfr, model='DT1', slug='dt1')
        cls.profile = DeviceMountProfile.objects.create(device_type=dt)
        user_model = get_user_model()
        cls.admin = user_model.objects.create_superuser('boss', password='pw')
        cls.plain = user_model.objects.create_user('nobody', password='pw')

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin)

    def test_get_loads(self):
        resp = self.client.get(f'{reverse(ANNOTATOR)}?device_profile={self.profile.pk}')
        self.assertEqual(resp.status_code, 200)

    def test_post_saves_front_and_isolates_rear(self):
        pm = json.dumps([
            {'name': 'a', 'type': 'pin', 'style': 'rj45', 'x_mm': 1, 'y_mm': 1, 'width_mm': 2, 'height_mm': 2},
        ])
        resp = self.client.post(reverse(ANNOTATOR), {
            'device_profile': self.profile.pk, 'face': 'front', 'port_map': pm,
        })
        self.assertEqual(resp.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(len(self.profile.port_map), 1)
        self.assertEqual(self.profile.rear_port_map, [])

    def test_post_saves_rear(self):
        pm = json.dumps([
            {'type': 'decor', 'style': 'led-red', 'x_mm': 1, 'y_mm': 1, 'width_mm': 2, 'height_mm': 2},
        ])
        resp = self.client.post(reverse(ANNOTATOR), {
            'device_profile': self.profile.pk, 'face': 'rear', 'port_map': pm,
        })
        self.assertEqual(resp.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(len(self.profile.rear_port_map), 1)
        self.assertEqual(self.profile.port_map, [])

    def test_frames_batch_save(self):
        frames = json.dumps([{
            'target': f'device:{self.profile.pk}',
            'port_map': [
                {'name': 'x', 'type': 'pin', 'x_mm': 0, 'y_mm': 0, 'width_mm': 1, 'height_mm': 1},
            ],
        }])
        resp = self.client.post(reverse(ANNOTATOR), {'face': 'front', 'frames': frames})
        self.assertEqual(resp.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(len(self.profile.port_map), 1)

    def test_invalid_port_map_rejected(self):
        pm = json.dumps([{'type': 'bogus'}])
        resp = self.client.post(reverse(ANNOTATOR), {
            'device_profile': self.profile.pk, 'face': 'front', 'port_map': pm,
        })
        self.assertEqual(resp.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.port_map, [])

    def test_save_requires_permission(self):
        self.client.force_login(self.plain)
        pm = json.dumps([
            {'name': 'a', 'type': 'pin', 'x_mm': 1, 'y_mm': 1, 'width_mm': 2, 'height_mm': 2},
        ])
        resp = self.client.post(reverse(ANNOTATOR), {
            'device_profile': self.profile.pk, 'face': 'front', 'port_map': pm,
        })
        self.assertEqual(resp.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.port_map, [])
