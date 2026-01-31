from dataclasses import dataclass, field
from uuid import uuid4
import inspect
import sys
from typing import Union


@dataclass
class RemoteAPIMessage:
    pass


@dataclass
class LoadImageCollectionMessage(RemoteAPIMessage):
    url: str
    event: str = "load_image_collection"
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class CenterOnCoordinatesMessage(RemoteAPIMessage):
    ra: float
    dec: float
    fov: float
    instant: bool
    event: str = "center_on_coordinates"
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class TableLayerCreateMessage(RemoteAPIMessage):
    table: str
    frame: str
    event: str = "table_layer_create"
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class TableLayerSetMessage(RemoteAPIMessage):
    setting: str
    value: Union[float, str]
    event: str = "table_layer_set"
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class TableLayerRemoveMessage(RemoteAPIMessage):
    event: str = "table_layer_remove"
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class SetForegroundByNameMessage(RemoteAPIMessage):
    name: str
    event: str = "set_foreground_by_name"
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class SetBackgroundByNameMessage(RemoteAPIMessage):
    name: str
    event: str = "set_background_by_name"
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class SetForegroundByOpacityMessage(RemoteAPIMessage):
    value: float
    event: str = "set_foreground_opacity"
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class ClearTileCacheMessage(RemoteAPIMessage):
    event: str = "clear_tile_cache"
    id: str = field(default_factory=lambda: str(uuid4()))


msg_ref = dict(
    inspect.getmembers(
        sys.modules[__name__],
        lambda member: inspect.isclass(member) and member.__module__ == __name__,
    )
)
msg_ref = {v.event: v for k, v in msg_ref.items() if hasattr(v, "event")}


if __name__ == "__main__":
    print(msg_ref)
