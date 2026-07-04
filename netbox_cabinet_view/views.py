from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import View

from dcim.models import Device
from netbox.views import generic
from utilities.views import ViewTab, register_model_view

import json
import os

from . import filtersets, forms, models, tables
from .ledger import enumerate_ledger
from .provision import auto_provision_mount_and_placements, auto_provision_placements
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
    template_name = 'netbox_cabinet_view/placement_edit.html'

    def get_extra_context(self, request, instance):
        # Feature 6 (v0.5.0): compute the preview base URL from the
        # selected mount so the template's JS can build SVG URLs.
        mount_pk = None
        if instance and instance.mount_id:
            mount_pk = instance.mount_id
        elif 'mount' in request.GET:
            mount_pk = request.GET.get('mount')
        elif request.method == 'POST' and 'mount' in request.POST:
            mount_pk = request.POST.get('mount')

        preview_base_url = ''
        if mount_pk:
            try:
                mount = models.Mount.objects.select_related('host_device').get(pk=mount_pk)
                svg_url = reverse(
                    'dcim:device_cabinet_layout_svg',
                    kwargs={'pk': mount.host_device.pk},
                )
                preview_base_url = f'{svg_url}?mount_only={mount.pk}'
            except (models.Mount.DoesNotExist, ValueError):
                pass

        return {'preview_base_url': preview_base_url}


class PlacementDeleteView(generic.ObjectDeleteView):
    queryset = models.Placement.objects.all()


# ---------------------------------------------------------------------------
# Device detail integration — Layout tab + SVG endpoint
# ---------------------------------------------------------------------------

def _device_hosts_mounts(device):
    """
    Tab visibility predicate for DeviceCabinetLayoutView — Finding B
    (v0.4.0), extended in v0.7.2 for non-host devices with port_map.

    The Layout tab is visible when:
    * The device's DeviceType has a profile with ``hosts_mounts=True``
      (even with zero mounts — unlocks the empty-state CTA), OR
    * The profile has a non-empty ``port_map`` (v0.7.2) or
      ``rear_port_map`` (v0.8.0). Enables a full-size front/rear-panel
      view with interactive port overlay for standalone rack-mount
      devices like switches that don't host internal mounts.
    """
    profile = getattr(device.device_type, 'cabinet_profile', None)
    if not profile:
        return False
    return bool(profile.hosts_mounts or profile.port_map or profile.rear_port_map)


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

        # v0.7.2: front-panel-only mode for non-host devices with port_map.
        # v0.8.0: also triggers on a rear_port_map (front and/or rear).
        has_front_panel = bool(profile and profile.port_map)
        has_rear_panel = bool(profile and profile.rear_port_map)
        front_panel_only = bool(
            profile and not profile.hosts_mounts
            and (has_front_panel or has_rear_panel) and not has_mounts
        )

        return {
            'mounts': mounts,
            'has_mounts': has_mounts,
            'front_panel_only': front_panel_only,
            'has_front_panel': has_front_panel,
            'has_rear_panel': has_rear_panel,
            # Internal dimensions for the empty-state scale-reference
            # canvas. May be None — the template degrades gracefully to
            # a plain Bootstrap card + button when unset.
            'internal_width_mm': profile.internal_width_mm if profile else None,
            'internal_height_mm': profile.internal_height_mm if profile else None,
            'ledger_enabled': ledger_enabled,
            'ledger_sections': ledger_sections,
            # Feature 3 (v0.5.0): auto-provision button visibility.
            'has_bays': instance.devicebays.exists() or instance.modulebays.exists(),
            # Feature 1 (v0.5.0): if any mount has an explicit face, the
            # template renders two SVGs (front + rear) side by side.
            'has_face_specific': any(m.face in ('front', 'rear') for m in mounts),
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


# ---------------------------------------------------------------------------
# Auto-provisioning — Feature 3 (v0.5.0)
# ---------------------------------------------------------------------------

class AutoProvisionView(LoginRequiredMixin, View):
    """
    One-click auto-provisioning of Placements from a device's bays.

    **Mode A** (POST with ``mount_pk`` + ``device_pk``): create
    sequential Placements on an existing Mount for every unplaced bay.

    **Mode B** (POST with ``device_pk`` only): derive a new Mount
    from the bays' profiles, then fill it with Placements.

    POST-based because it creates shared data. CSRF token required.
    """

    def post(self, request):
        device_pk = request.POST.get('device_pk')
        mount_pk = request.POST.get('mount_pk')
        device = get_object_or_404(Device, pk=device_pk)

        if mount_pk:
            # Mode A — placements only on an existing mount.
            if not request.user.has_perm('netbox_cabinet_view.add_placement'):
                messages.error(request, 'You do not have permission to add placements.')
                return redirect(device.get_absolute_url())

            mount = get_object_or_404(models.Mount, pk=mount_pk, host_device=device)
            created, skipped = auto_provision_placements(mount)
            if created:
                messages.success(
                    request,
                    f'Auto-provisioned {created} placement(s) on {mount.name}.'
                    + (f' {skipped} bay(s) skipped (capacity/validation).' if skipped else ''),
                )
            else:
                messages.info(request, 'No new placements to create (all bays already placed or mount at capacity).')
            return redirect(mount.get_absolute_url())
        else:
            # Mode B — create mount + placements.
            if not request.user.has_perm('netbox_cabinet_view.add_mount'):
                messages.error(request, 'You do not have permission to add mounts.')
                return redirect(device.get_absolute_url())
            if not request.user.has_perm('netbox_cabinet_view.add_placement'):
                messages.error(request, 'You do not have permission to add placements.')
                return redirect(device.get_absolute_url())

            mount, created, skipped = auto_provision_mount_and_placements(device)
            if mount is None:
                messages.warning(request, 'No bays found on this device — nothing to provision.')
                return redirect(device.get_absolute_url())
            messages.success(
                request,
                f'Created mount "{mount.name}" with {created} placement(s).'
                + (f' {skipped} bay(s) skipped.' if skipped else ''),
            )
            # Redirect to the Layout tab.
            return redirect(reverse('dcim:device_cabinet_layout', kwargs={'pk': device.pk}))


# ---------------------------------------------------------------------------
# Line-art gallery — v0.6.1
# ---------------------------------------------------------------------------

class LineArtGalleryView(LoginRequiredMixin, View):
    """
    In-NetBox gallery of bundled line-art images, browsable offline.
    Reads the manifest.json taxonomy and renders it as an HTML page
    with thumbnail images served from the plugin's static files.
    """

    def get(self, request):
        from django.shortcuts import render as django_render
        manifest_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'static', 'netbox_cabinet_view', 'line-art', 'manifest.json',
        )
        categories = []
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                data = json.load(f)
            categories = data.get('categories', [])
        return django_render(request, 'netbox_cabinet_view/line_art_gallery.html', {
            'categories': categories,
        })


class PortMapAnnotatorView(LoginRequiredMixin, View):
    """
    In-NetBox port-map annotator. Load a Device/Module mount profile's
    front image, drag boxes over its ports/slots, and save the result
    straight to the profile's ``port_map`` - no external tool, no
    copy/paste of JSON.

    Positions are normalised against a "module frame" box drawn on the
    image, whose real width/height in mm the user sets. That decouples the
    annotation from the image's own pixel scale, so a single photo (not
    perfectly to scale, possibly holding several modules) can be used to
    draw up multiple faceplates - each frame exports its own port_map.
    """
    template_name = 'netbox_cabinet_view/portmap_annotator.html'

    def _resolve(self, data):
        mp = data.get('module_profile')
        dp = data.get('device_profile')
        if mp:
            return get_object_or_404(models.ModuleMountProfile, pk=mp), 'module'
        if dp:
            return get_object_or_404(models.DeviceMountProfile, pk=dp), 'device'
        return None, None

    @staticmethod
    def _face(data):
        return 'rear' if data.get('face') == 'rear' else 'front'

    def _url_for(self, profile, kind, face='front'):
        base = reverse('plugins:netbox_cabinet_view:portmap_annotator')
        if not profile:
            return base
        param = 'module_profile' if kind == 'module' else 'device_profile'
        url = f'{base}?{param}={profile.pk}'
        if face == 'rear':
            url += '&face=rear'
        return url

    def get(self, request):
        from django.shortcuts import render as django_render
        profile, kind = self._resolve(request.GET)
        face = self._face(request.GET)
        image_url = ''
        frame_w, frame_h = 73, 255.8
        port_map = []
        if profile:
            image_field = profile.rear_image if face == 'rear' else profile.front_image
            try:
                if image_field:
                    image_url = image_field.url
            except ValueError:
                pass
            port_map = (profile.rear_port_map if face == 'rear' else profile.port_map) or []
            if kind == 'device':
                frame_w = profile.internal_width_mm or 483
                frame_h = profile.internal_height_mm or 88
        return django_render(request, self.template_name, {
            'profile': profile,
            'kind': kind,
            'face': face,
            'image_url': image_url,
            'frame_w': frame_w,
            'frame_h': frame_h,
            'port_map_json': json.dumps(port_map),
            'module_profiles': models.ModuleMountProfile.objects.all().select_related('module_type'),
            'device_profiles': models.DeviceMountProfile.objects.all().select_related('device_type'),
        })

    def post(self, request):
        profile, kind = self._resolve(request.POST)
        face = self._face(request.POST)

        # v0.8.0: batch save - one canvas, several frames each to its own profile.
        frames = request.POST.get('frames')
        if frames is not None:
            return self._save_frames(request, frames, face, profile, kind)

        if not profile:
            messages.error(request, 'Select a profile before saving.')
            return redirect(reverse('plugins:netbox_cabinet_view:portmap_annotator'))
        perm = f'netbox_cabinet_view.change_{kind}mountprofile'
        if not request.user.has_perm(perm):
            messages.error(request, 'You do not have permission to edit this profile.')
            return redirect(self._url_for(profile, kind, face))

        # v0.8.0: save generated line art as the profile's front/rear image.
        image_svg = request.POST.get('image_svg')
        if image_svg:
            from django.core.files.base import ContentFile
            field = profile.rear_image if face == 'rear' else profile.front_image
            field.save(
                f'{kind}-{profile.pk}-{face}-lineart.svg',
                ContentFile(image_svg.encode('utf-8')),
                save=True,
            )
            messages.success(request, f'Saved generated line art as the {face} image of {profile}.')
            return redirect(self._url_for(profile, kind, face))

        try:
            port_map = json.loads(request.POST.get('port_map') or '[]')
            if face == 'rear':
                profile.rear_port_map = port_map
            else:
                profile.port_map = port_map
            profile.full_clean()
            profile.save()
            n = len(port_map)
            messages.success(
                request,
                f'Saved {n} {face} port-map entr{"y" if n == 1 else "ies"} to {profile}.',
            )
        except json.JSONDecodeError as exc:
            messages.error(request, f'Invalid JSON: {exc}')
        except ValidationError as exc:
            messages.error(request, f'Invalid port map: {exc.messages[0] if exc.messages else exc}')
        return redirect(self._url_for(profile, kind, face))

    def _save_frames(self, request, frames_json, face, profile, kind):
        """
        Batch save: each item is {target: 'module:pk'|'device:pk', port_map: [...]}.
        Saves each port_map to the target profile's front or rear map. Per-record
        errors are collected and surfaced, never silently dropped.
        """
        try:
            batch = json.loads(frames_json or '[]')
        except json.JSONDecodeError as exc:
            messages.error(request, f'Invalid frames JSON: {exc}')
            return redirect(self._url_for(profile, kind, face))
        if not isinstance(batch, list):
            messages.error(request, 'frames must be a JSON list.')
            return redirect(self._url_for(profile, kind, face))

        saved = 0
        errors = []
        for item in batch:
            if not isinstance(item, dict):
                errors.append('malformed frame entry')
                continue
            target = str(item.get('target') or '')
            port_map = item.get('port_map') or []
            tkind, _, tpk = target.partition(':')
            if tkind not in ('module', 'device') or not tpk.isdigit():
                errors.append(f'bad target "{target}"')
                continue
            model = models.ModuleMountProfile if tkind == 'module' else models.DeviceMountProfile
            prof = model.objects.filter(pk=int(tpk)).first()
            if not prof:
                errors.append(f'{target}: profile not found')
                continue
            if not request.user.has_perm(f'netbox_cabinet_view.change_{tkind}mountprofile'):
                errors.append(f'{prof}: no permission')
                continue
            if face == 'rear':
                prof.rear_port_map = port_map
            else:
                prof.port_map = port_map
            try:
                prof.full_clean()
                prof.save()
                saved += 1
            except ValidationError as exc:
                errors.append(f'{prof}: {exc.messages[0] if exc.messages else exc}')

        if saved:
            messages.success(request, f'Saved {face} port maps to {saved} profile(s).')
        for err in errors[:10]:
            messages.error(request, err)
        if not saved and not errors:
            messages.warning(request, 'No frames had a target profile assigned.')
        return redirect(self._url_for(profile, kind, face))


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
    * ``?face=front|rear`` — render only mounts assigned to this face
      (plus mounts with face='' which appear on both). Feature 1,
      v0.5.0.
    """

    def get(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        try:
            fit_w = int(request.GET['w']) if 'w' in request.GET else None
            fit_h = int(request.GET['h']) if 'h' in request.GET else None
        except (ValueError, TypeError):
            fit_w = fit_h = None
        thumbnail = request.GET.get('thumb') in ('1', 'true', 'yes')
        theme = request.GET.get('theme') or None
        if theme not in ('dark', 'light', None):
            theme = None
        face = request.GET.get('face') or None
        if face not in ('front', 'rear', None):
            face = None

        # Feature 6 (v0.5.0): optional mount_only + highlight params
        # for the live preview chip on the PlacementForm.
        mount_only_pk = request.GET.get('mount_only') or None
        highlight = {}
        for key in ('position', 'size', 'row', 'position_x', 'position_y', 'size_x', 'size_y'):
            val = request.GET.get(f'highlight_{key}')
            if val:
                try:
                    highlight[key] = int(val)
                except (ValueError, TypeError):
                    pass

        svg = CabinetLayoutSVG(
            host_device=device,
            user=request.user,
            base_url=request.build_absolute_uri('/').rstrip('/'),
            include_images=True,
            fit_width=fit_w,
            fit_height=fit_h,
            thumbnail=thumbnail,
            face=face,
            mount_only_pk=mount_only_pk,
            highlight=highlight or None,
            theme=theme,
        ).render()
        return HttpResponse(svg, content_type='image/svg+xml')


@register_model_view(Device, 'cabinet_front_panel_svg', path='cabinet-layout/front-panel.svg')
class DeviceFrontPanelSVGView(View):
    """
    v0.7.2: standalone front-panel SVG for non-host devices with port_map.

    Renders the device's front_image at full size with port overlay pins
    on top. Used by the Layout tab when the device has a port_map but
    no internal mounts (e.g. a 1U rack-mount switch).
    """

    def get(self, request, pk):
        from .svg.front_panel import render_front_panel
        device = get_object_or_404(Device, pk=pk)
        theme = request.GET.get('theme') or None
        if theme not in ('dark', 'light', None):
            theme = None
        face = request.GET.get('face')
        if face not in ('front', 'rear'):
            face = 'front'
        base_url = request.build_absolute_uri('/').rstrip('/')
        svg = render_front_panel(device, base_url=base_url, theme=theme, face=face)
        return HttpResponse(svg, content_type='image/svg+xml')
