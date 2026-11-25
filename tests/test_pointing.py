from pathlib import Path

import numpy as np

from wispec.data.synthetic import skeleton
from wispec.room.pointing import pointing_ray
from wispec.room.room_map import RoomMap

ROOM = RoomMap.from_json(Path(__file__).parent.parent / "configs" / "room_example.json")


def test_hanging_arms_are_not_pointing():
    assert pointing_ray(skeleton(np.array([2.0, 2.0]), 0.0, None, 0.0)) is None


def test_points_at_each_anchor():
    for a in ROOM.anchors:
        j = skeleton(np.array([2.5, 2.0]), 0.0, a.position, 0.0)
        res = ROOM.resolve_joints(j)
        assert res.anchor is not None and res.anchor.name == a.name, (a.name, res.candidates)


def test_pointing_at_nothing_resolves_to_none():
    j = skeleton(np.array([2.5, 2.0]), 0.0, np.array([2.5, -5.0, 1.5]), 0.0)
    assert ROOM.resolve_joints(j).anchor is None
