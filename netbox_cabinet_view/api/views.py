from rest_framework.viewsets import ModelViewSet

from ..models import DeviceMountProfile
from ..models import ModuleMountProfile
from ..models import Mount
from ..models import Placement
from .serializers import DeviceMountProfileSerializer
from .serializers import ModuleMountProfileSerializer
from .serializers import MountSerializer
from .serializers import PlacementSerializer


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
