"""SageMaker training-job entry point: runs the WiSpec pipeline inside the job container.

Modes:
  synthetic  generate synthetic sessions inside the job (no data upload; good for agent smoke runs)
  data       train on recorded sessions from the "training" input channel (S3)

Spot-safe: the run directory lives in /opt/ml/checkpoints, which SageMaker
syncs to S3, so an interrupted spot job resumes and skips finished stages.
Results (eval.json, examples.npz, checkpoints) end up in model.tar.gz.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Inside the job, code is staged next to this file; locally, use the repo root.
HERE = HERE if (HERE / "wispec").exists() else HERE.parents[1]
sys.path.insert(0, str(HERE))

from wispec import train  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["synthetic", "data"], default="synthetic")
    p.add_argument("--config", default="configs/rig_tri_band.json")
    p.add_argument("--room", default="configs/room_example.json")
    p.add_argument("--sessions", type=int, default=8)
    p.add_argument("--seconds", type=float, default=150)
    p.add_argument("--stage1-epochs", type=int, default=30)
    p.add_argument("--stage2-epochs", type=int, default=40)
    p.add_argument("--stride", type=int, default=1)
    p.add_argument("--band-dropout", type=float, default=0.15)
    a, _ = p.parse_known_args()

    cfg = str(HERE / a.config)
    room = str(HERE / a.room)
    ckpt = Path(os.environ.get("SM_CHECKPOINT_DIR", "/opt/ml/checkpoints"))
    run = ckpt / "run"
    model_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    run.mkdir(parents=True, exist_ok=True)

    if a.mode == "synthetic":
        data = ckpt / "synth"
        if not data.exists() or len(list(data.iterdir())) < a.sessions:
            train.main(["synth", "--config", cfg, "--room", room, "--out", str(data),
                        "--sessions", str(a.sessions), "--seconds", str(a.seconds)])
    else:
        data = Path(os.environ["SM_CHANNEL_TRAINING"])

    common = ["--config", cfg, "--data", str(data), "--run", str(run), "--stride", str(a.stride)]
    if not (run / "stage1.pt").exists():
        train.main(["stage1", *common, "--epochs", str(a.stage1_epochs)])
    if not (run / "stage2.pt").exists():
        train.main(["stage2", *common, "--epochs", str(a.stage2_epochs), "--band-dropout", str(a.band_dropout)])
    train.main(["eval", *common, "--room", room, "--save-examples"])

    for f in ("eval.json", "examples.npz", "split.json", "stage1.pt", "stage2.pt"):
        if (run / f).exists():
            shutil.copy(run / f, model_dir / f)
    print("WISPEC_EVAL_JSON " + json.dumps(json.loads((run / "eval.json").read_text())))


if __name__ == "__main__":
    main()
