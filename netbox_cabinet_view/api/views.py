from rest_framework.viewsets import ModelViewSet

from ..models import Carrier, DeviceTypeProfile, Mount
from .serializers import CarrierSerializer, DeviceTypeProfileSerializer, MountSerializer


class DeviceTypeProfileViewSet(ModelViewSet):
    queryset = DeviceTypeProfile.objects.all()
    serializer_class = DeviceTypeProfileSerializer


class CarrierViewSet(ModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer


class MountViewSet(ModelViewSet):
    queryset = Mount.objects.all()
    serializer_class = MountSerializer
