"""Pointing rays from 3D body joints, and target resolution against room anchors."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Minimal skeleton used across WiSpec (a subset that any body tracker can map onto).
JOINTS = ["head", "neck", "l_shoulder", "r_shoulder", "l_elbow", "r_elbow",
          "l_wrist", "r_wrist", "pelvis"]
J = {n: i for i, n in enumerate(JOINTS)}

# Mapping from Azure Kinect / Orbbec body-tracking joint names to WiSpec joints.
K4ABT_TO_WISPEC = {
    "HEAD": "head", "NECK": "neck",
    "SHOULDER_LEFT": "l_shoulder", "SHOULDER_RIGHT": "r_shoulder",
    "ELBOW_LEFT": "l_elbow", "ELBOW_RIGHT": "r_elbow",
    "WRIST_LEFT": "l_wrist", "WRIST_RIGHT": "r_wrist",
    "PELVIS": "pelvis",
}


@dataclass
class Ray:
    origin: np.ndarray      # [3]
    direction: np.ndarray   # [3], unit
    arm: str                # "l" | "r"
    extension: float        # 0..1, how straight/extended the arm is


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def arm_extension(joints: np.ndarray, side: str) -> float:
    """1.0 for a fully straight arm raised away from the body, ~0 for a hanging arm."""
    s, e, w = joints[J[f"{side}_shoulder"]], joints[J[f"{side}_elbow"]], joints[J[f"{side}_wrist"]]
    reach = np.linalg.norm(w - s) / max(np.linalg.norm(e - s) + np.linalg.norm(w - e), 1e-6)
    torso_down = _unit(joints[J["pelvis"]] - joints[J["neck"]])
    raised = 1.0 - max(0.0, float(np.dot(_unit(w - s), torso_down)))  # 0 if arm hangs straight down
    return float(np.clip(reach, 0, 1) * np.clip(raised, 0, 1))


def pointing_ray(joints: np.ndarray, min_extension: float = 0.6) -> Ray | None:
    """Head→wrist ray of the more extended arm ("head-hand line"), or None if not pointing.

    The head-hand line is a better estimate of where people think they're
    pointing than the forearm direction alone.
    """
    best = max(("l", "r"), key=lambda s: arm_extension(joints, s))
    ext = arm_extension(joints, best)
    if ext < min_extension:
        return None
    origin = joints[J["head"]]
    direction = _unit(joints[J[f"{best}_wrist"]] - origin)
    return Ray(origin=origin, direction=direction, arm=best, extension=ext)


def angular_error_deg(ray: Ray, target: np.ndarray, radius: float = 0.0) -> float:
    """Angle between the ray and the target centre, minus the target's angular radius (>= 0)."""
    to_t = target - ray.origin
    dist = np.linalg.norm(to_t)
    cosang = float(np.clip(np.dot(ray.direction, to_t / max(dist, 1e-9)), -1, 1))
    ang = np.degrees(np.arccos(cosang))
    ang_radius = np.degrees(np.arctan2(radius, max(dist, 1e-9)))
    return float(max(0.0, ang - ang_radius))
