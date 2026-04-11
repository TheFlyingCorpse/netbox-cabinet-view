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
# DeviceMountProfile
# ---------------------------------------------------------------------------

class DeviceMountProfileListView(generic.ObjectListView):
    queryset = models.DeviceMountProfile.objects.select_related('device_type__manufacturer')
    table = tables.DeviceMountProfileTable
    filterset = filtersets.DeviceMountProfileFilterSet
    filterset_form = forms.DeviceMountProfileFilterForm


class DeviceMountProfileView(generic.ObjectView):
    queryset = models.DeviceMountProfile.objects.select_related('device_type__manufacturer')


class DeviceMountProfileEditView(generic.ObjectEditView):
    queryset = models.DeviceMountProfile.objects.all()
    form = forms.DeviceMountProfileForm


class DeviceMountProfileDeleteView(generic.ObjectDeleteView):
    queryset = models.DeviceMountProfile.objects.all()


# ---------------------------------------------------------------------------
# ModuleMountProfile (new in v0.4.0)
# ---------------------------------------------------------------------------

class ModuleMountProfileListView(generic.ObjectListView):
    queryset = models.ModuleMountProfile.objects.select_related('module_type__manufacturer')
    table = tables.ModuleMountProfileTable
    filterset = filtersets.ModuleMountProfileFilterSet
    filterset_form = forms.ModuleMountProfileFilterForm


class ModuleMountProfileView(generic.ObjectView):
    queryset = models.ModuleMountProfile.objects.select_related('module_type__manufacturer')


class ModuleMountProfileEditView(generic.ObjectEditView):
    queryset = models.ModuleMountProfile.objects.all()
    form = forms.ModuleMountProfileForm


class ModuleMountProfileDeleteView(generic.ObjectDeleteView):
    queryset = models.ModuleMountProfile.objects.all()


# ---------------------------------------------------------------------------
# Mount
# ---------------------------------------------------------------------------

class MountListView(generic.ObjectListView):
    queryset = models.Mount.objects.annotate(
        placement_count=Count('placements'),
    ).select_related('host_device')
    table = tables.MountTable
    filterset = filtersets.MountFilterSet
    filterset_form = forms.MountFilterForm


class MountView(generic.ObjectView):
    queryset = models.Mount.objects.select_related('host_device').prefetch_related(
        'placements__device__device_type',
        'placements__device_bay__installed_device__device_type',
        'placements__module_bay__installed_module__module_type',
    )

    def get_extra_context(self, request, instance):
        placement_table = tables.PlacementTable(
            data=instance.placements.restrict(request.user, 'view').select_related(
                'device__device_type',
                'device_bay__installed_device__device_type',
                'module_bay__installed_module__module_type',
            )
        )
        placement_table.configure(request)
        return {'placement_table': placement_table}


class MountEditView(generic.ObjectEditView):
    queryset = models.Mount.objects.all()
    form = forms.MountForm


class MountDeleteView(generic.ObjectDeleteView):
    queryset = models.Mount.objects.all()


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------

class PlacementListView(generic.ObjectListView):
    queryset = models.Placement.objects.select_related(
        'mount__host_device',
        'device__device_type',
        'device_bay__installed_device__device_type',
        'module_bay__installed_module__module_type',
    )
    table = tables.PlacementTable
    filterset = filtersets.PlacementFilterSet
    filterset_form = forms.PlacementFilterForm


class PlacementView(generic.ObjectView):
    queryset = models.Placement.objects.select_related(
        'mount__host_device',
        'device__device_type',
        'device_bay__installed_device__device_type',
        'module_bay__installed_module__module_type',
    )


class PlacementEditView(generic.ObjectEditView):
    queryset = models.Placement.objects.all()
    form = forms.PlacementForm


class PlacementDeleteView(generic.ObjectDeleteView):
    queryset = models.Placement.objects.all()


# ---------------------------------------------------------------------------
# Device detail integration — Layout tab + SVG endpoint
# ---------------------------------------------------------------------------

@register_model_view(Device, 'cabinet_layout', path='cabinet-layout')
class DeviceCabinetLayoutView(generic.ObjectView):
    """Adds a 'Layout' tab to the Device detail page, showing the host's mounts."""

    queryset = Device.objects.all()
    template_name = 'netbox_cabinet_view/device_layout_tab.html'
    tab = ViewTab(
        label=_('Layout'),
        badge=lambda obj: obj.cabinet_mounts.count(),
        permission='netbox_cabinet_view.view_mount',
        weight=2000,
        hide_if_empty=True,
    )

    def get_extra_context(self, request, instance):
        mounts = instance.cabinet_mounts.prefetch_related(
            'placements__device__device_type',
            'placements__device__role',
            'placements__device_bay__installed_device__device_type',
            'placements__device_bay__installed_device__role',
            'placements__module_bay__installed_module__module_type',
        )
        return {
            'mounts': mounts,
        }


@register_model_view(Device, 'cabinet_layout_svg', path='cabinet-layout/svg')
class DeviceCabinetLayoutSVGView(View):
    """
    Raw SVG payload for the Layout tab's <object> embed.

    Accepts three optional query parameters:

    * ``?w=<int>`` and ``?h=<int>`` — render the drawing letterboxed into
      this pixel box (used by the rack elevation patch to fit a cabinet
      layout into a U slot without distortion).
    * ``?v=<str>`` — cache-buster token. Ignored by the view but varies
      the URL so the browser invalidates its cached copy whenever the
      host device's mounts or placements change.
    """

    def get(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        try:
            fit_w = int(request.GET['w']) if 'w' in request.GET else None
            fit_h = int(request.GET['h']) if 'h' in request.GET else None
        except (ValueError, TypeError):
            fit_w = fit_h = None
        svg = CabinetLayoutSVG(
            host_device=device,
            user=request.user,
            base_url=request.build_absolute_uri('/').rstrip('/'),
            include_images=True,
            fit_width=fit_w,
            fit_height=fit_h,
        ).render()
        return HttpResponse(svg, content_type='image/svg+xml')
