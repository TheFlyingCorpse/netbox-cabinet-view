from rest_framework.viewsets import ModelViewSet

from ..models import DeviceMountProfile, ModuleMountProfile, Mount, Placement
from .serializers import (
    DeviceMountProfileSerializer,
    ModuleMountProfileSerializer,
    MountSerializer,
    PlacementSerializer,
)


class DeviceMountProfileViewSet(ModelViewSet):
    queryset = DeviceMountProfile.objects.all()
    serializer_class = DeviceMountProfileSerializer


class ModuleMountProfileViewSet(ModelViewSet):
    queryset = ModuleMountProfile.objects.all()
    serializer_class = ModuleMountProfileSerializer


class MountViewSet(ModelViewSet):
    queryset = Mount.objects.all()
    serializer_class = MountSerializer


class PlacementViewSet(ModelViewSet):
    queryset = Placement.objects.all()
    serializer_class = PlacementSerializer
