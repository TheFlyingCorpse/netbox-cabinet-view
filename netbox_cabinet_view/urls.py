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

    # Carrier
    path('carriers/',
         views.CarrierListView.as_view(), name='carrier_list'),
    path('carriers/add/',
         views.CarrierEditView.as_view(), name='carrier_add'),
    path('carriers/<int:pk>/',
         views.CarrierView.as_view(), name='carrier'),
    path('carriers/<int:pk>/edit/',
         views.CarrierEditView.as_view(), name='carrier_edit'),
    path('carriers/<int:pk>/delete/',
         views.CarrierDeleteView.as_view(), name='carrier_delete'),
    path('carriers/<int:pk>/',
         include(get_model_urls('netbox_cabinet_view', 'carrier'))),

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
]
