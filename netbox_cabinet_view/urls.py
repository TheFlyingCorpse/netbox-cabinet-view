from django.urls import include, path

from utilities.urls import get_model_urls

from . import views

urlpatterns = [
    # DeviceTypeProfile
    path('device-type-profiles/',
         views.DeviceTypeProfileListView.as_view(), name='devicetypeprofile_list'),
    path('device-type-profiles/add/',
         views.DeviceTypeProfileEditView.as_view(), name='devicetypeprofile_add'),
    path('device-type-profiles/<int:pk>/',
         views.DeviceTypeProfileView.as_view(), name='devicetypeprofile'),
    path('device-type-profiles/<int:pk>/edit/',
         views.DeviceTypeProfileEditView.as_view(), name='devicetypeprofile_edit'),
    path('device-type-profiles/<int:pk>/delete/',
         views.DeviceTypeProfileDeleteView.as_view(), name='devicetypeprofile_delete'),
    # Auto-registered feature views (changelog, journal, …)
    path('device-type-profiles/<int:pk>/',
         include(get_model_urls('netbox_cabinet_view', 'devicetypeprofile'))),

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
