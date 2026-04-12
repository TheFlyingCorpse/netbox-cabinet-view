from django.urls import include, path

from utilities.urls import get_model_urls

from . import views

urlpatterns = [
    # DeviceMountProfile
    path('device-mount-profiles/',
         views.DeviceMountProfileListView.as_view(), name='devicemountprofile_list'),
    path('device-mount-profiles/add/',
         views.DeviceMountProfileEditView.as_view(), name='devicemountprofile_add'),
    path('device-mount-profiles/<int:pk>/',
         views.DeviceMountProfileView.as_view(), name='devicemountprofile'),
    path('device-mount-profiles/<int:pk>/edit/',
         views.DeviceMountProfileEditView.as_view(), name='devicemountprofile_edit'),
    path('device-mount-profiles/<int:pk>/delete/',
         views.DeviceMountProfileDeleteView.as_view(), name='devicemountprofile_delete'),
    # Auto-registered feature views (changelog, journal, …)
    path('device-mount-profiles/<int:pk>/',
         include(get_model_urls('netbox_cabinet_view', 'devicemountprofile'))),

    # ModuleMountProfile
    path('module-mount-profiles/',
         views.ModuleMountProfileListView.as_view(), name='modulemountprofile_list'),
    path('module-mount-profiles/add/',
         views.ModuleMountProfileEditView.as_view(), name='modulemountprofile_add'),
    path('module-mount-profiles/<int:pk>/',
         views.ModuleMountProfileView.as_view(), name='modulemountprofile'),
    path('module-mount-profiles/<int:pk>/edit/',
         views.ModuleMountProfileEditView.as_view(), name='modulemountprofile_edit'),
    path('module-mount-profiles/<int:pk>/delete/',
         views.ModuleMountProfileDeleteView.as_view(), name='modulemountprofile_delete'),
    path('module-mount-profiles/<int:pk>/',
         include(get_model_urls('netbox_cabinet_view', 'modulemountprofile'))),

    # Mount
    path('mounts/',
         views.MountListView.as_view(), name='mount_list'),
    path('mounts/add/',
         views.MountEditView.as_view(), name='mount_add'),
    path('mounts/<int:pk>/',
         views.MountView.as_view(), name='mount'),
    path('mounts/<int:pk>/edit/',
         views.MountEditView.as_view(), name='mount_edit'),
    path('mounts/<int:pk>/delete/',
         views.MountDeleteView.as_view(), name='mount_delete'),
    path('mounts/<int:pk>/',
         include(get_model_urls('netbox_cabinet_view', 'mount'))),

    # Discovery hint dismissal — Finding H (v0.4.0).
    path('hints/dismiss/<int:device_pk>/',
         views.DiscoveryHintDismissView.as_view(), name='hint_dismiss'),

    # Auto-provisioning — Feature 3 (v0.5.0).
    path('auto-provision/',
         views.AutoProvisionView.as_view(), name='auto_provision'),

    # Placement
    path('placements/',
         views.PlacementListView.as_view(), name='placement_list'),
    path('placements/add/',
         views.PlacementEditView.as_view(), name='placement_add'),
    path('placements/<int:pk>/',
         views.PlacementView.as_view(), name='placement'),
    path('placements/<int:pk>/edit/',
         views.PlacementEditView.as_view(), name='placement_edit'),
    path('placements/<int:pk>/delete/',
         views.PlacementDeleteView.as_view(), name='placement_delete'),
    path('placements/<int:pk>/',
         include(get_model_urls('netbox_cabinet_view', 'placement'))),
]
