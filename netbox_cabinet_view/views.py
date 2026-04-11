from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic import View

from dcim.models import Device
from netbox.views import generic
from utilities.views import ViewTab, register_model_view

from . import filtersets, forms, models, tables
from .svg import CabinetLayoutSVG


# ---------------------------------------------------------------------------
# DeviceTypeProfile
# ---------------------------------------------------------------------------

class DeviceTypeProfileListView(generic.ObjectListView):
    queryset = models.DeviceTypeProfile.objects.select_related('device_type__manufacturer')
    table = tables.DeviceTypeProfileTable
    filterset = filtersets.DeviceTypeProfileFilterSet
    filterset_form = forms.DeviceTypeProfileFilterForm


class DeviceTypeProfileView(generic.ObjectView):
    queryset = models.DeviceTypeProfile.objects.select_related('device_type__manufacturer')


class DeviceTypeProfileEditView(generic.ObjectEditView):
    queryset = models.DeviceTypeProfile.objects.all()
    form = forms.DeviceTypeProfileForm


class DeviceTypeProfileDeleteView(generic.ObjectDeleteView):
    queryset = models.DeviceTypeProfile.objects.all()


# ---------------------------------------------------------------------------
# Carrier
# ---------------------------------------------------------------------------

class CarrierListView(generic.ObjectListView):
    queryset = models.Carrier.objects.annotate(
        mount_count=Count('mounts'),
    ).select_related('host_device')
    table = tables.CarrierTable
    filterset = filtersets.CarrierFilterSet
    filterset_form = forms.CarrierFilterForm


class CarrierView(generic.ObjectView):
    queryset = models.Carrier.objects.select_related('host_device').prefetch_related(
        'mounts__device__device_type',
        'mounts__device_bay__installed_device__device_type',
        'mounts__module_bay__installed_module__module_type',
    )

    def get_extra_context(self, request, instance):
        mount_table = tables.MountTable(
            data=instance.mounts.restrict(request.user, 'view').select_related(
                'device__device_type',
                'device_bay__installed_device__device_type',
                'module_bay__installed_module__module_type',
            )
        )
        mount_table.configure(request)
        return {'mount_table': mount_table}


class CarrierEditView(generic.ObjectEditView):
    queryset = models.Carrier.objects.all()
    form = forms.CarrierForm


class CarrierDeleteView(generic.ObjectDeleteView):
    queryset = models.Carrier.objects.all()


# ---------------------------------------------------------------------------
# Mount
# ---------------------------------------------------------------------------

class MountListView(generic.ObjectListView):
    queryset = models.Mount.objects.select_related(
        'carrier__host_device',
        'device__device_type',
        'device_bay__installed_device__device_type',
        'module_bay__installed_module__module_type',
    )
    table = tables.MountTable
    filterset = filtersets.MountFilterSet
    filterset_form = forms.MountFilterForm


class MountView(generic.ObjectView):
    queryset = models.Mount.objects.select_related(
        'carrier__host_device',
        'device__device_type',
        'device_bay__installed_device__device_type',
        'module_bay__installed_module__module_type',
    )


class MountEditView(generic.ObjectEditView):
    queryset = models.Mount.objects.all()
    form = forms.MountForm


class MountDeleteView(generic.ObjectDeleteView):
    queryset = models.Mount.objects.all()


# ---------------------------------------------------------------------------
# Device detail integration — Layout tab + SVG endpoint
# ---------------------------------------------------------------------------

@register_model_view(Device, 'cabinet_layout', path='cabinet-layout')
class DeviceCabinetLayoutView(generic.ObjectView):
    """Adds a 'Layout' tab to the Device detail page, showing the host's carriers."""

    queryset = Device.objects.all()
    template_name = 'netbox_cabinet_view/device_layout_tab.html'
    tab = ViewTab(
        label=_('Layout'),
        badge=lambda obj: obj.cabinet_carriers.count(),
        permission='netbox_cabinet_view.view_carrier',
        weight=2000,
        hide_if_empty=True,
    )

    def get_extra_context(self, request, instance):
        carriers = instance.cabinet_carriers.prefetch_related(
            'mounts__device__device_type',
            'mounts__device__role',
            'mounts__device_bay__installed_device__device_type',
            'mounts__device_bay__installed_device__role',
            'mounts__module_bay__installed_module__module_type',
        )
        return {
            'carriers': carriers,
        }


@register_model_view(Device, 'cabinet_layout_svg', path='cabinet-layout/svg')
class DeviceCabinetLayoutSVGView(View):
    """Raw SVG payload for the Layout tab's <object> embed."""

    def get(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        svg = CabinetLayoutSVG(
            host_device=device,
            user=request.user,
            base_url=request.build_absolute_uri('/').rstrip('/'),
            include_images=True,
        ).render()
        return HttpResponse(svg, content_type='image/svg+xml')
