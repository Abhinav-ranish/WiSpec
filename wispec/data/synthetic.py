"""Synthetic sessions with a simple multipath model.

This is NOT a physically accurate simulator. It exists so the full pipeline
(windowing → training → evaluation → pointing → automation) can be run and
tested before the rig is built. It writes the same on-disk format as a real
capture (see ``wispec.data.windows``).

Model: an AP and a 2-antenna receiver in a box-shaped room. CSI per band is
a sum of a direct path, a few static wall reflections, and paths scattered
off the person's body joints, with a random per-packet common phase (like
real CFO), packet jitter, drops and noise. The teacher is a depth camera
next to the receiver rendering the room walls and the person as spheres.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from wispec.config import RigConfig
from wispec.room.pointing import J, JOINTS

C = 3e8
ROOM = np.array([5.0, 4.0, 2.6])
AP = np.array([4.9, 3.6, 1.8])
RX = np.array([0.05, 2.0, 1.0])
RX_SPACING = 0.025          # ~lambda/2 at 6 GHz
CAM = np.array([0.05, 2.0, 1.2])
CAM_FOV_DEG = 90.0
RAW_SUBCARRIERS = {20: 56, 40: 114, 80: 242, 160: 484}  # kept small for speed


def skeleton(pos_xy: np.ndarray, heading: float, point_target: np.ndarray | None,
             phase: float) -> np.ndarray:
    """Very simple 3D skeleton [J, 3] standing at pos_xy, optionally pointing the right arm."""
    fwd = np.array([np.cos(heading), np.sin(heading), 0.0])
    left = np.array([-fwd[1], fwd[0], 0.0])
    base = np.array([pos_xy[0], pos_xy[1], 0.0])
    j = np.zeros((len(JOINTS), 3))
    j[J["pelvis"]] = base + [0, 0, 1.0]
    j[J["neck"]] = base + [0, 0, 1.5]
    j[J["head"]] = base + [0, 0, 1.68]
    for side, sgn in (("l", 1), ("r", -1)):
        sh = j[J["neck"]] + sgn * 0.19 * left - [0, 0, 0.03]
        j[J[f"{side}_shoulder"]] = sh
        swing = 0.12 * np.sin(phase + (0 if side == "l" else np.pi))
        j[J[f"{side}_elbow"]] = sh + [0, 0, -0.29] + swing * fwd
        j[J[f"{side}_wrist"]] = sh + [0, 0, -0.55] + 1.6 * swing * fwd
    if point_target is not None:
        # People put the hand on the eye-target line; place the wrist on the
        # head->target ray at full arm reach (0.57 m) from the shoulder.
        sh, head = j[J["r_shoulder"]], j[J["head"]]
        d = point_target - head
        d /= np.linalg.norm(d)
        o = head - sh
        b = float(o @ d)
        t = -b + np.sqrt(max(b * b - (o @ o - 0.57 ** 2), 0.0))
        wrist = head + t * d
        j[J["r_wrist"]] = wrist
        j[J["r_elbow"]] = (sh + wrist) / 2
    return j


def _wall_images(p: np.ndarray) -> list[np.ndarray]:
    """First-order image sources of point p across the 4 walls + floor."""
    imgs = []
    for ax in (0, 1):
        for wall in (0.0, ROOM[ax]):
            q = p.copy()
            q[ax] = 2 * wall - q[ax]
            imgs.append(q)
    q = p.copy()
    q[2] = -q[2]
    imgs.append(q)
    return imgs


def band_csi(freqs: np.ndarray, joints: np.ndarray | None, rng: np.random.Generator,
             noise: float = 0.02) -> np.ndarray:
    """Complex CSI [S, 2] for one packet."""
    rx_ants = [RX + [0, -RX_SPACING / 2, 0], RX + [0, RX_SPACING / 2, 0]]
    out = np.zeros((len(freqs), 2), np.complex128)
    for r, ant in enumerate(rx_ants):
        paths = [(np.linalg.norm(AP - ant), 1.0)]
        paths += [(np.linalg.norm(img - ant), 0.45) for img in _wall_images(AP)]
        if joints is not None:
            for name, w in (("pelvis", 0.6), ("neck", 0.4), ("head", 0.25),
                            ("l_wrist", 0.15), ("r_wrist", 0.15), ("l_elbow", 0.1), ("r_elbow", 0.1)):
                p = joints[J[name]]
                paths.append((np.linalg.norm(AP - p) + np.linalg.norm(p - ant), w))
        for d, a in paths:
            out[:, r] += (a / d) * np.exp(-2j * np.pi * freqs * d / C)
    out *= np.exp(1j * rng.uniform(0, 2 * np.pi))            # common random phase (CFO)
    out *= rng.uniform(0.8, 1.25)                              # AGC
    scale = np.abs(out).mean()
    out += noise * scale * (rng.standard_normal(out.shape) + 1j * rng.standard_normal(out.shape))
    return out.astype(np.complex64)


def render_depth(joints: np.ndarray | None, size: int) -> np.ndarray:
    """Depth image [size, size] in mm from a pinhole camera at CAM looking +x."""
    f = (size / 2) / np.tan(np.radians(CAM_FOV_DEG / 2))
    u, v = np.meshgrid(np.arange(size) - size / 2 + 0.5, np.arange(size) - size / 2 + 0.5)
    dirs = np.stack([np.full_like(u, f), -u, -v], axis=-1)
    dirs /= np.linalg.norm(dirs, axis=-1, keepdims=True)
    # Distance along each ray to the room box.
    with np.errstate(divide="ignore", invalid="ignore"):
        t_hi = np.where(dirs > 0, (ROOM - CAM) / dirs, np.where(dirs < 0, (0 - CAM) / dirs, np.inf))
    t = t_hi.min(axis=-1)
    if joints is not None:
        centers, radii = [], []
        for a, b, r in (("pelvis", "neck", 0.17), ("neck", "head", 0.11),
                        ("l_shoulder", "l_elbow", 0.06), ("l_elbow", "l_wrist", 0.05),
                        ("r_shoulder", "r_elbow", 0.06), ("r_elbow", "r_wrist", 0.05)):
            for s in np.linspace(0, 1, 5):
                centers.append(joints[J[a]] * (1 - s) + joints[J[b]] * s)
                radii.append(r)
        pel = joints[J["pelvis"]]
        for s in np.linspace(0, 1, 5):    # legs
            centers.append(pel * (1 - s) + (pel - [0, 0, 1.0]) * s)
            radii.append(0.13)
        for c, r in zip(centers, radii):
            oc = CAM - c
            b = (dirs * oc).sum(-1)
            disc = b * b - (oc @ oc - r * r)
            hit = disc > 0
            th = np.where(hit, -b - np.sqrt(np.maximum(disc, 0)), np.inf)
            th = np.where(th > 0, th, np.inf)
            t = np.minimum(t, th)
    depth = t * dirs[..., 0]      # z-depth along optical axis
    return np.clip(depth * 1000, 0, 65535).astype(np.uint16)


def generate_session(out_dir: str | Path, cfg: RigConfig, seconds: float = 120.0,
                     teacher_fps: float = 10.0, anchors: list[np.ndarray] | None = None,
                     seed: int = 0, drop_bands: tuple[str, ...] = ()) -> Path:
    rng = np.random.default_rng(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = 1_700_000_000_000_000_000 + seed * 10**12
    anchors = anchors or []

    # Person trajectory at 100 Hz: wander to random waypoints, sometimes stop and point.
    dt = 0.01
    n = int(seconds / dt)
    pos = rng.uniform([1.0, 0.8], [4.2, 3.2])
    goal = rng.uniform([1.0, 0.8], [4.2, 3.2])
    heading, phase, pause, point = 0.0, 0.0, 0, None
    present = True
    traj = []
    for _ in range(n):
        if pause > 0:
            pause -= 1
            if pause == 0:
                point = None
                present = True
        else:
            d = goal - pos
            if np.linalg.norm(d) < 0.1:
                goal = rng.uniform([1.0, 0.8], [4.2, 3.2])
                r = rng.random()
                if r < 0.4 and anchors:
                    point = anchors[rng.integers(len(anchors))]
                    pause = int(rng.uniform(2, 4) / dt)
                elif r < 0.5:
                    present = False                          # leaves the room for a bit
                    pause = int(rng.uniform(3, 6) / dt)
                else:
                    pause = int(rng.uniform(0.5, 3) / dt)    # stands still / sits
            else:
                heading = np.arctan2(d[1], d[0])
                pos = pos + 1.0 * dt * d / np.linalg.norm(d)
                phase += 2 * np.pi * 1.8 * dt
        traj.append(skeleton(pos, heading, point, phase) if present else None)

    grid_t = t0 + (np.arange(n) * dt * 1e9).astype(np.int64)

    for b in cfg.bands:
        if b.name in drop_bands:
            continue
        s = RAW_SUBCARRIERS.get(b.bandwidth_mhz, 114)
        freqs = b.center_mhz * 1e6 + np.linspace(-b.bandwidth_mhz / 2, b.bandwidth_mhz / 2, s) * 1e6
        keep = rng.random(n) > 0.02                                # 2% packet loss
        jitter = rng.normal(0, 1.5e6, n).astype(np.int64)          # ~1.5 ms jitter
        ts = (grid_t + jitter)[keep]
        csi = np.stack([band_csi(freqs, traj[i], rng) for i in np.nonzero(keep)[0]])
        order = np.argsort(ts)
        np.savez_compressed(out / f"csi_{b.name}.npz", t_ns=ts[order], csi=csi[order])

    step = int(round(1 / (teacher_fps * dt)))
    idx = np.arange(0, n, step)
    frames = np.stack([render_depth(traj[i], cfg.frame_size) for i in idx])
    np.savez_compressed(out / "teacher.npz", t_ns=grid_t[idx], frames=frames)

    absent = np.full((len(JOINTS), 3), np.nan, np.float32)
    joints = np.stack([traj[i] if traj[i] is not None else absent for i in idx]).astype(np.float32)
    np.savez_compressed(out / "keypoints.npz", t_ns=grid_t[idx], joints=joints, names=np.array(JOINTS))

    (out / "meta.json").write_text(json.dumps({
        "synthetic": True, "seed": seed, "seconds": seconds, "config": cfg.to_dict(),
    }, indent=2))
    return out
