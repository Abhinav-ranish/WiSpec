import numpy as np

from wispec.config import BandConfig, RigConfig
from wispec.data.synthetic import generate_session
from wispec.data.windows import (build_windows, csi_features, load_session, resample_to_grid,
                                 split_sessions)


def small_cfg():
    return RigConfig(bands=[BandConfig("5g", "4", 5180, 160, 5250, 16),
                            BandConfig("6g", "5", 5955, 160, 6025, 16)],
                     frame_size=32, window_s=0.5)


def test_csi_features_cancel_common_phase():
    rng = np.random.default_rng(0)
    csi = rng.standard_normal((4, 32, 2)) + 1j * rng.standard_normal((4, 32, 2))
    rotated = csi * np.exp(1j * rng.uniform(0, 6.28, (4, 1, 1)))   # per-packet CFO-like phase
    a, b = csi_features(csi, 8), csi_features(rotated, 8)
    assert a.shape == (4, 3, 8)
    np.testing.assert_allclose(a, b, atol=1e-5)


def test_resample_marks_gaps_invalid():
    t = np.array([0, 10, 20, 100], dtype=np.int64)
    f = np.arange(4, dtype=np.float32)[:, None]
    g, v = resample_to_grid(t, f, np.array([5, 15, 60, 105]), max_gap_ns=20)
    assert v.tolist() == [True, True, False, True]
    assert g[:, 0].tolist() == [0, 1, 0, 3]


def test_split_is_by_session_and_disjoint():
    train, test = split_sessions([f"s{i}" for i in range(8)], 0.25)
    assert len(test) == 2 and not set(train) & set(test)


def test_build_windows_on_synthetic(tmp_path):
    cfg = small_cfg()
    generate_session(tmp_path / "s", cfg, seconds=6, teacher_fps=5, seed=1, drop_bands=("6g",))
    w = build_windows(load_session(tmp_path / "s", cfg), cfg)
    n = len(w.frames)
    assert n > 0
    assert w.x[0].shape == (n, 3 * 16, cfg.window_len)
    assert w.x[1].shape == (n, 3 * 16, cfg.window_len)       # missing band -> zeros
    assert np.all(w.band_valid[:, 1] == 0) and np.all(w.band_valid[:, 0] > 0.5)
    assert w.frames.shape == (n, 1, 32, 32) and w.frames.max() <= 1
    assert w.joints.shape == (n, 9, 3)
