"""Unit tests for the port_map validator (pure, no DB)."""
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from netbox_cabinet_view.models import _validate_port_map


class ValidatePortMapTests(SimpleTestCase):
    def test_valid_pin(self):
        _validate_port_map([
            {'name': 'eth0', 'type': 'pin', 'x_mm': 1, 'y_mm': 2, 'width_mm': 3, 'height_mm': 4},
        ])

    def test_valid_module_bay(self):
        _validate_port_map([
            {'name': 'E', 'type': 'module_bay', 'x_mm': 0, 'y_mm': 0, 'width_mm': 10, 'height_mm': 10},
        ])

    def test_valid_decor_with_style(self):
        _validate_port_map([
            {'type': 'decor', 'style': 'led-green', 'x_mm': 0, 'y_mm': 0, 'width_mm': 3, 'height_mm': 3},
        ])

    def test_pin_carries_connector_style(self):
        _validate_port_map([
            {'name': 'p', 'type': 'pin', 'style': 'qsfp', 'x_mm': 0, 'y_mm': 0, 'width_mm': 3, 'height_mm': 3},
        ])

    def test_not_a_list(self):
        with self.assertRaises(ValidationError):
            _validate_port_map({'type': 'pin'})

    def test_unknown_type(self):
        with self.assertRaises(ValidationError):
            _validate_port_map([{'type': 'bogus', 'x_mm': 0, 'y_mm': 0, 'width_mm': 1, 'height_mm': 1}])

    def test_pin_missing_keys(self):
        with self.assertRaises(ValidationError):
            _validate_port_map([{'type': 'pin', 'name': 'x'}])

    def test_decor_requires_style(self):
        with self.assertRaises(ValidationError):
            _validate_port_map([{'type': 'decor', 'x_mm': 0, 'y_mm': 0, 'width_mm': 1, 'height_mm': 1}])

    def test_style_must_be_string(self):
        with self.assertRaises(ValidationError):
            _validate_port_map([
                {'type': 'pin', 'name': 'x', 'x_mm': 0, 'y_mm': 0, 'width_mm': 1, 'height_mm': 1, 'style': 5},
            ])

    def test_error_keyed_to_field_name(self):
        with self.assertRaises(ValidationError) as ctx:
            _validate_port_map([{'type': 'bogus'}], field='rear_port_map')
        self.assertIn('rear_port_map', ctx.exception.message_dict)
