import json

import pytest

torch = pytest.importorskip("torch")

from wispec import train  # noqa: E402


def test_pipeline_end_to_end(tmp_path):
    cfg = tmp_path / "rig.json"
    cfg.write_text(json.dumps({
        "bands": [{"name": "5g", "phy": "4", "primary_mhz": 5180, "bandwidth_mhz": 160, "center_mhz": 5250, "model_subcarriers": 16},
                  {"name": "6g", "phy": "5", "primary_mhz": 5955, "bandwidth_mhz": 160, "center_mhz": 6025, "model_subcarriers": 16}],
        "frame_size": 32, "window_s": 0.5}))
    data, run = tmp_path / "data", tmp_path / "run"
    c = ["--config", str(cfg)]
    train.main(["synth", *c, "--out", str(data), "--sessions", "3", "--seconds", "8"])
    train.main(["stage1", *c, "--data", str(data), "--run", str(run), "--epochs", "1"])
    train.main(["stage2", *c, "--data", str(data), "--run", str(run), "--epochs", "1"])
    train.main(["eval", *c, "--data", str(data), "--run", str(run), "--room", "configs/room_example.json"])
    rep = json.loads((run / "eval.json").read_text())
    assert set(rep["ablation"]) == {"5g", "6g", "5g+6g"}
    assert "psnr_mean_frame_baseline" in rep and "pointing" in rep
