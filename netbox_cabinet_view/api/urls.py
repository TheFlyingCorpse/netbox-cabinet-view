"""
API urlconf.

Registers minimal DRF ViewSets so that NetBox's list/detail templates and
DynamicModelChoiceField autocomplete widgets can reverse the expected
`{model}-list` and `{model}-detail` names in the
`plugins-api:netbox_cabinet_view-api` namespace.
"""
from rest_framework import routers

from .views import CarrierViewSet, DeviceTypeProfileViewSet, MountViewSet

router = routers.DefaultRouter()
router.register('device-type-profiles', DeviceTypeProfileViewSet)
router.register('carriers', CarrierViewSet)
router.register('mounts', MountViewSet)

urlpatterns = router.urls
