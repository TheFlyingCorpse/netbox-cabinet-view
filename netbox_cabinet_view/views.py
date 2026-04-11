from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import View

from dcim.models import Device
from netbox.views import generic
from utilities.views import ViewTab, register_model_view

from . import filtersets, forms, models, tables
from .ledger import enumerate_ledger
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

def _device_hosts_mounts(device):
    """
    Tab visibility predicate for DeviceCabinetLayoutView — Finding B
    (v0.4.0).

    The Layout tab should be visible whenever the device's DeviceType
    has a DeviceMountProfile with ``hosts_mounts=True``, EVEN IF there
    are zero mounts yet. That unlocks the empty-state "Add the first
    mount" CTA for devices that the admin has declared as
    cabinet-shaped but not yet populated.

    Devices with no profile, or with ``hosts_mounts=False``, still
    suppress the tab. That preserves the "don't pollute every Device
    page with a useless tab" guarantee from v0.3.0.
    """
    profile = getattr(device.device_type, 'cabinet_profile', None)
    return bool(profile and profile.hosts_mounts)


@register_model_view(Device, 'cabinet_layout', path='cabinet-layout')
class DeviceCabinetLayoutView(generic.ObjectView):
    """Adds a 'Layout' tab to the Device detail page, showing the host's mounts."""

    queryset = Device.objects.all()
    template_name = 'netbox_cabinet_view/device_layout_tab.html'
    tab = ViewTab(
        label=_('Layout'),
        visible=_device_hosts_mounts,
        badge=lambda obj: obj.cabinet_mounts.count(),
        permission='netbox_cabinet_view.view_mount',
        weight=2000,
        # hide_if_empty removed in v0.4.0: the visible= callable above
        # already gates on profile presence, and the empty-state CTA
        # inside the tab body handles the zero-mounts case explicitly.
    )

    def get_extra_context(self, request, instance):
        mounts = instance.cabinet_mounts.prefetch_related(
            'placements__device__device_type',
            'placements__device__role',
            'placements__device_bay__installed_device__device_type',
            'placements__device_bay__installed_device__role',
            'placements__module_bay__installed_module__module_type',
        )
        has_mounts = mounts.exists()
        profile = getattr(instance.device_type, 'cabinet_profile', None)

        # Finding D (v0.4.0): opt-in slot ledger. Default False so the
        # normal "just show me the picture" workflow is unchanged.
        plugin_cfg = getattr(settings, 'PLUGINS_CONFIG', {}).get('netbox_cabinet_view', {})
        ledger_enabled = plugin_cfg.get('SLOT_LEDGER_ENABLED', False)
        ledger_sections = (
            enumerate_ledger(instance, user=request.user)
            if (ledger_enabled and has_mounts)
            else []
        )

        return {
            'mounts': mounts,
            'has_mounts': has_mounts,
            # Internal dimensions for the empty-state scale-reference
            # canvas. May be None — the template degrades gracefully to
            # a plain Bootstrap card + button when unset.
            'internal_width_mm': profile.internal_width_mm if profile else None,
            'internal_height_mm': profile.internal_height_mm if profile else None,
            'ledger_enabled': ledger_enabled,
            'ledger_sections': ledger_sections,
        }


# ---------------------------------------------------------------------------
# Discovery hint — Finding H (v0.4.0)
# ---------------------------------------------------------------------------

class DiscoveryHintDismissView(LoginRequiredMixin, View):
    """
    Dismiss the discovery hint card for a specific device, for the
    current user only. Writes the device PK into
    ``user.config['cabinet_view.dismissed_hints']`` and redirects back
    to the device detail page.

    GET is used rather than POST so the plain `<a href>` in the hint
    card works without a CSRF token and without JavaScript. The
    action is idempotent and user-scoped - no shared state is
    modified - so GET-based mutation is acceptable here.
    """

    def get(self, request, device_pk):
        device = get_object_or_404(Device, pk=device_pk)
        # UserConfig uses dotted keys. Read current list, append, write back.
        key = 'cabinet_view.dismissed_hints'
        current = request.user.config.get(key) or []
        if not isinstance(current, list):
            current = []
        if device.pk not in current:
            current.append(device.pk)
            request.user.config.set(key, current, commit=True)
        return redirect(device.get_absolute_url())


@register_model_view(Device, 'cabinet_layout_svg', path='cabinet-layout/svg')
class DeviceCabinetLayoutSVGView(View):
    """
    Raw SVG payload for the Layout tab's <object> embed.

    Accepts four optional query parameters:

    * ``?w=<int>`` and ``?h=<int>`` — render the drawing letterboxed into
      this pixel box (used by the rack elevation patch to fit a cabinet
      layout into a U slot without distortion).
    * ``?v=<str>`` — cache-buster token. Ignored by the view but varies
      the URL so the browser invalidates its cached copy whenever the
      host device's mounts or placements change.
    * ``?thumb=1`` — render in thumbnail mode (lowered contrast, no
      labels, desaturated role colours). Used by the rack elevation
      patch so the embedded cabinet reads as a preview, not a live
      click target. Finding E, v0.4.0.
    """

    def get(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        try:
            fit_w = int(request.GET['w']) if 'w' in request.GET else None
            fit_h = int(request.GET['h']) if 'h' in request.GET else None
        except (ValueError, TypeError):
            fit_w = fit_h = None
        thumbnail = request.GET.get('thumb') in ('1', 'true', 'yes')
        svg = CabinetLayoutSVG(
            host_device=device,
            user=request.user,
            base_url=request.build_absolute_uri('/').rstrip('/'),
            include_images=True,
            fit_width=fit_w,
            fit_height=fit_h,
            thumbnail=thumbnail,
        ).render()
        return HttpResponse(svg, content_type='image/svg+xml')
