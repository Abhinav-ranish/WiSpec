"""CSI cleaning and windowing aligned to teacher-camera frames.

On-disk session format (written by ``wispec.capture.session`` or
``wispec.data.synthetic``)::

    <session>/meta.json        rig config + labels
    <session>/csi_<band>.npz   t_ns int64 [N], csi complex64 [N, S, R]
    <session>/teacher.npz      t_ns int64 [M], frames (uint16 depth mm [M,H,W] or uint8 RGB [M,H,W,3])
    <session>/keypoints.npz    optional: t_ns [K], joints float32 [K,J,3] (metres, rig frame), names [J]

All timestamps are host ``time.time_ns()`` from the same machine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from wispec.config import RigConfig


# ---------------------------------------------------------------- cleaning

def group_subcarriers(x: np.ndarray, n_out: int) -> np.ndarray:
    """Average adjacent subcarriers (axis 1) down to ``n_out`` groups."""
    s = x.shape[1]
    if s == n_out:
        return x
    edges = np.linspace(0, s, n_out + 1).astype(int)
    return np.stack([x[:, a:max(b, a + 1)].mean(axis=1) for a, b in zip(edges[:-1], edges[1:])], axis=1)


def csi_features(csi: np.ndarray, n_subcarriers: int) -> np.ndarray:
    """Per-packet features from complex CSI [N, S, R] -> float32 [N, C, n_subcarriers].

    Channels: log-amplitude per RX antenna, plus (if R > 1) the phase of
    antenna 0 x conj(antenna 1). The conjugate product cancels the per-packet
    random phase (CFO/SFO/PLL offsets) that is common to both antennas on
    the same NIC, leaving phase differences caused by the environment.
    """
    n, s, r = csi.shape
    amp = np.log1p(np.abs(csi))                                     # [N, S, R]
    # Normalize out per-packet AGC gain: subtract mean log-amp per packet/antenna.
    amp = amp - amp.mean(axis=1, keepdims=True)
    chans = [amp[:, :, i] for i in range(r)]
    if r > 1:
        ratio = csi[:, :, 0] * np.conj(csi[:, :, 1])
        chans.append(np.angle(ratio) / np.pi)
    feats = np.stack([group_subcarriers(c, n_subcarriers) for c in chans], axis=1)
    return feats.astype(np.float32)


# ---------------------------------------------------------------- resampling

def resample_to_grid(t_ns: np.ndarray, feats: np.ndarray, grid_ns: np.ndarray,
                     max_gap_ns: int) -> tuple[np.ndarray, np.ndarray]:
    """Sample-and-hold packets onto a uniform time grid.

    Returns (feats_on_grid [G, ...], valid [G] bool). Grid points with no
    packet within ``max_gap_ns`` before them are zeroed and marked invalid.
    """
    idx = np.searchsorted(t_ns, grid_ns, side="right") - 1
    valid = idx >= 0
    idx_c = np.clip(idx, 0, len(t_ns) - 1)
    valid &= (grid_ns - t_ns[idx_c]) <= max_gap_ns
    out = feats[idx_c].copy()
    out[~valid] = 0.0
    return out, valid


# ---------------------------------------------------------------- sessions

@dataclass
class Session:
    name: str
    csi: dict[str, tuple[np.ndarray, np.ndarray]]   # band -> (t_ns, csi complex [N,S,R])
    teacher_t: np.ndarray
    frames: np.ndarray
    joints_t: np.ndarray | None = None
    joints: np.ndarray | None = None
    meta: dict | None = None


def load_session(path: str | Path, cfg: RigConfig) -> Session:
    path = Path(path)
    csi = {}
    for b in cfg.bands:
        f = path / f"csi_{b.name}.npz"
        if f.exists():
            z = np.load(f)
            csi[b.name] = (z["t_ns"].astype(np.int64), z["csi"])
    t = np.load(path / "teacher.npz")
    js_t = js = None
    if (path / "keypoints.npz").exists():
        k = np.load(path / "keypoints.npz")
        js_t, js = k["t_ns"].astype(np.int64), k["joints"].astype(np.float32)
    meta = json.loads((path / "meta.json").read_text()) if (path / "meta.json").exists() else {}
    return Session(path.name, csi, t["t_ns"].astype(np.int64), t["frames"], js_t, js, meta)


def prepare_frames(frames: np.ndarray, cfg: RigConfig) -> np.ndarray:
    """Teacher frames -> float32 [M, C, F, F] in [0, 1] at cfg.frame_size."""
    f = cfg.frame_size
    if frames.ndim == 3:                       # depth mm
        x = np.clip(frames.astype(np.float32) / cfg.max_depth_mm, 0, 1)[:, None]
    else:                                      # RGB uint8
        x = frames.astype(np.float32).transpose(0, 3, 1, 2) / 255.0
    m, c, h, w = x.shape
    if (h, w) != (f, f):                       # nearest-neighbour resize, no extra deps
        ys = (np.arange(f) * h / f).astype(int)
        xs = (np.arange(f) * w / f).astype(int)
        x = x[:, :, ys][:, :, :, xs]
    if cfg.teacher == "depth" and c != 1:
        x = x.mean(axis=1, keepdims=True)
    return x.astype(np.float32)


@dataclass
class Windows:
    x: list[np.ndarray]        # per band: float32 [N, C_b, T]
    band_valid: np.ndarray     # [N, n_bands] fraction of valid packets in window
    frames: np.ndarray         # [N, C, F, F]
    joints: np.ndarray | None  # [N, J, 3]
    session: np.ndarray        # [N] session index


def build_windows(sess: Session, cfg: RigConfig, stride: int = 1,
                  min_valid: float = 0.5) -> Windows:
    """One sample per teacher frame: the CSI window of cfg.window_s ending at the frame time."""
    period = int(1e9 / cfg.csi_rate_hz)
    T = cfg.window_len
    frame_t = sess.teacher_t[::stride]
    frames = prepare_frames(sess.frames[::stride], cfg)

    starts = [ts[0] for ts, _ in sess.csi.values()]
    t0 = max(starts) if starts else frame_t[0]
    grid = np.arange(t0, frame_t[-1] + period, period, dtype=np.int64)

    per_band, valid_masks = [], []
    for b in cfg.bands:
        if b.name in sess.csi:
            ts, c = sess.csi[b.name]
            g, v = resample_to_grid(ts, csi_features(c, b.model_subcarriers), grid, max_gap_ns=5 * period)
        else:   # band missing in this session -> zeros, all invalid
            ch = cfg.band_channels()[cfg.bands.index(b)] // b.model_subcarriers
            g = np.zeros((len(grid), ch, b.model_subcarriers), np.float32)
            v = np.zeros(len(grid), bool)
        per_band.append(g.reshape(len(grid), -1))
        valid_masks.append(v)

    end_idx = np.searchsorted(grid, frame_t, side="right") - 1
    keep = end_idx >= T - 1
    xs = [[] for _ in cfg.bands]
    bv, kept = [], []
    for i in np.nonzero(keep)[0]:
        e = end_idx[i]
        frac = np.array([m[e - T + 1:e + 1].mean() for m in valid_masks])
        if frac.max() < min_valid:
            continue
        for k, g in enumerate(per_band):
            xs[k].append(g[e - T + 1:e + 1].T)          # [C_b, T]
        bv.append(frac)
        kept.append(i)
    kept = np.array(kept, dtype=int)

    joints = None
    if sess.joints is not None and len(kept):
        j_idx = np.clip(np.searchsorted(sess.joints_t, frame_t[kept]), 0, len(sess.joints_t) - 1)
        joints = sess.joints[j_idx]

    n_b = len(cfg.bands)
    return Windows(
        x=[np.stack(v).astype(np.float32) if v else np.zeros((0, 1, T), np.float32) for v in xs],
        band_valid=np.array(bv, np.float32).reshape(-1, n_b),
        frames=frames[kept],
        joints=joints,
        session=np.zeros(len(kept), int),
    )


def concat_windows(ws: list[Windows]) -> Windows:
    for i, w in enumerate(ws):
        w.session[:] = i
    has_j = all(w.joints is not None for w in ws)
    return Windows(
        x=[np.concatenate([w.x[k] for w in ws]) for k in range(len(ws[0].x))],
        band_valid=np.concatenate([w.band_valid for w in ws]),
        frames=np.concatenate([w.frames for w in ws]),
        joints=np.concatenate([w.joints for w in ws]) if has_j else None,
        session=np.concatenate([w.session for w in ws]),
    )


def split_sessions(names: list[str], test_frac: float = 0.25, seed: int = 0) -> tuple[list[str], list[str]]:
    """Split by whole session — never by frame — so test minutes are truly unseen."""
    rng = np.random.default_rng(seed)
    names = sorted(names)
    order = rng.permutation(len(names))
    n_test = max(1, int(round(len(names) * test_frac))) if len(names) > 1 else 0
    test = sorted(names[i] for i in order[:n_test])
    train = sorted(n for n in names if n not in test)
    return train, test
