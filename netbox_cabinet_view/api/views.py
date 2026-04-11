from rest_framework.viewsets import ModelViewSet

from ..models import DeviceTypeProfile, Mount, Placement
from .serializers import DeviceTypeProfileSerializer, MountSerializer, PlacementSerializer


class DeviceTypeProfileViewSet(ModelViewSet):
    queryset = DeviceTypeProfile.objects.all()
    serializer_class = DeviceTypeProfileSerializer


class MountViewSet(ModelViewSet):
    queryset = Mount.objects.all()
    serializer_class = MountSerializer


class PlacementViewSet(ModelViewSet):
    queryset = Placement.objects.all()
    serializer_class = PlacementSerializer
