"""
API urlconf.

Registers minimal DRF ViewSets so that NetBox's list/detail templates and
DynamicModelChoiceField autocomplete widgets can reverse the expected
`{model}-list` and `{model}-detail` names in the
`plugins-api:netbox_cabinet_view-api` namespace.
"""
from rest_framework import routers

from .views import (
    DeviceMountProfileViewSet,
    ModuleMountProfileViewSet,
    MountViewSet,
    PlacementViewSet,
)

router = routers.DefaultRouter()
router.register('device-mount-profiles', DeviceMountProfileViewSet)
router.register('module-mount-profiles', ModuleMountProfileViewSet)
router.register('mounts', MountViewSet)
router.register('placements', PlacementViewSet)

urlpatterns = router.urls
