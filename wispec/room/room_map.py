"""Room map: device anchors registered during calibration, and "what is the user pointing at"."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from wispec.room.pointing import Ray, angular_error_deg, pointing_ray


@dataclass
class Anchor:
    name: str
    entity_id: str
    position: np.ndarray
    radius_m: float = 0.3
    aliases: list[str] = field(default_factory=list)

    @property
    def domain(self) -> str:
        return self.entity_id.split(".", 1)[0]


@dataclass
class Resolution:
    anchor: Anchor | None
    error_deg: float
    ambiguous: bool
    candidates: list[tuple[str, float]]   # (name, angular error deg), best first


@dataclass
class RoomMap:
    name: str
    size_m: tuple[float, float, float]
    anchors: list[Anchor]

    @classmethod
    def from_json(cls, path: str | Path) -> "RoomMap":
        d = json.loads(Path(path).read_text())
        anchors = [Anchor(a["name"], a["entity_id"], np.asarray(a["position"], float),
                          a.get("radius_m", 0.3), a.get("aliases", [])) for a in d["anchors"]]
        return cls(d.get("name", "room"), tuple(d.get("size_m", (0, 0, 0))), anchors)

    def find(self, word: str) -> Anchor | None:
        w = word.lower().strip()
        for a in self.anchors:
            if w == a.name.lower() or w in (x.lower() for x in a.aliases):
                return a
        return None

    def resolve_ray(self, ray: Ray, max_error_deg: float = 15.0,
                    ambiguity_margin_deg: float = 8.0) -> Resolution:
        scored = sorted(((angular_error_deg(ray, a.position, a.radius_m), a) for a in self.anchors),
                        key=lambda t: t[0])
        cands = [(a.name, round(e, 1)) for e, a in scored]
        if not scored or scored[0][0] > max_error_deg:
            return Resolution(None, scored[0][0] if scored else float("inf"), False, cands)
        best_err, best = scored[0]
        ambiguous = len(scored) > 1 and scored[1][0] - best_err < ambiguity_margin_deg
        return Resolution(best, best_err, ambiguous, cands)

    def resolve_joints(self, joints: np.ndarray, **kw) -> Resolution:
        ray = pointing_ray(joints)
        if ray is None:
            return Resolution(None, float("inf"), False, [])
        return self.resolve_ray(ray, **kw)
