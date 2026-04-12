import strawberry
import strawberry_django

from .types import *


@strawberry.type(name="Query")
class CabinetViewQuery:
    device_mount_profile: DeviceMountProfileType = strawberry_django.field()
    device_mount_profile_list: list[DeviceMountProfileType] = strawberry_django.field()

    module_mount_profile: ModuleMountProfileType = strawberry_django.field()
    module_mount_profile_list: list[ModuleMountProfileType] = strawberry_django.field()

    mount: MountType = strawberry_django.field()
    mount_list: list[MountType] = strawberry_django.field()

    placement: PlacementType = strawberry_django.field()
    placement_list: list[PlacementType] = strawberry_django.field()


schema = [CabinetViewQuery]
