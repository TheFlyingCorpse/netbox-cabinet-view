from typing import Annotated

import strawberry
import strawberry_django

from netbox.graphql.types import NetBoxObjectType
from netbox_cabinet_view import models

__all__ = (
    'DeviceMountProfileType',
    'ModuleMountProfileType',
    'MountType',
    'PlacementType',
)


@strawberry_django.type(
    models.DeviceMountProfile,
    fields='__all__',
)
class DeviceMountProfileType(NetBoxObjectType):
    device_type: Annotated[
        'DeviceTypeType', strawberry.lazy('dcim.graphql.types')
    ]


@strawberry_django.type(
    models.ModuleMountProfile,
    fields='__all__',
)
class ModuleMountProfileType(NetBoxObjectType):
    module_type: Annotated[
        'ModuleTypeType', strawberry.lazy('dcim.graphql.types')
    ]


@strawberry_django.type(
    models.Mount,
    fields='__all__',
)
class MountType(NetBoxObjectType):
    host_device: Annotated[
        'DeviceType', strawberry.lazy('dcim.graphql.types')
    ]
    placements: list[Annotated[
        'PlacementType', strawberry.lazy('netbox_cabinet_view.graphql.types')
    ]]


@strawberry_django.type(
    models.Placement,
    fields='__all__',
)
class PlacementType(NetBoxObjectType):
    mount: Annotated[
        'MountType', strawberry.lazy('netbox_cabinet_view.graphql.types')
    ]
    device: Annotated[
        'DeviceType', strawberry.lazy('dcim.graphql.types')
    ] | None
    device_bay: Annotated[
        'DeviceBayType', strawberry.lazy('dcim.graphql.types')
    ] | None
    module_bay: Annotated[
        'ModuleBayType', strawberry.lazy('dcim.graphql.types')
    ] | None
