"""Record one training session: tri-band CSI + teacher camera on the same host clock.

    python -m wispec.capture.session --config configs/rig_tri_band.json \
        --out data/sessions/2026-11-25_walk_01 --duration 600 --activity walking

Vary sessions deliberately (walking, sitting, pointing at each device,
empty room, different times of day). Afterwards convert the raw PicoScenes
files with ``--convert`` (or run the session again with ``--convert-only``).
"""

from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path

from wispec.capture.picoscenes import MultiBandCapture, convert_csi_file
from wispec.config import RigConfig


def convert_session(out: Path, cfg: RigConfig):
    for b in cfg.bands:
        src = out / f"raw_{b.name}.csi"
        if src.exists():
            n = convert_csi_file(src, out / f"csi_{b.name}.npz")
            print(f"{b.name}: {n} frames")
        else:
            print(f"{b.name}: missing {src}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="wispec.capture.session")
    p.add_argument("--config", default="configs/rig_tri_band.json")
    p.add_argument("--out", required=True)
    p.add_argument("--duration", type=float, default=300)
    p.add_argument("--activity", default="mixed", help="free-text label stored in meta.json")
    p.add_argument("--no-teacher", action="store_true", help="CSI only (e.g. inference-time recording)")
    p.add_argument("--skip-prepare", action="store_true", help="NICs already in monitor mode on the right channels")
    p.add_argument("--convert", action="store_true", help="convert raw .csi to .npz after recording")
    p.add_argument("--convert-only", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)

    cfg = RigConfig.from_json(a.config)
    out = Path(a.out)
    if a.convert_only:
        convert_session(out, cfg)
        return

    out.mkdir(parents=True, exist_ok=True)
    cap = MultiBandCapture(cfg, out, dry_run=a.dry_run)
    if not a.skip_prepare:
        cap.prepare()

    teacher = None
    if not a.no_teacher and not a.dry_run:
        from wispec.capture.teacher import make_teacher
        teacher = make_teacher(cfg.teacher_device, out)

    meta = {"config": cfg.to_dict(), "activity": a.activity, "host": socket.gethostname(),
            "clock": "time.time_ns (host)", "start_ns": time.time_ns(), "duration_s": a.duration}
    cap.start()
    if teacher:
        teacher.start()
    print(f"recording {a.duration:.0f}s -> {out}" + (" (dry run)" if a.dry_run else ""))
    try:
        if not a.dry_run:
            time.sleep(a.duration)
    except KeyboardInterrupt:
        print("stopped early")
    finally:
        cap.stop()
        if teacher:
            teacher.stop()
        meta["end_ns"] = time.time_ns()
        (out / "meta.json").write_text(json.dumps(meta, indent=2))

    if a.convert and not a.dry_run:
        convert_session(out, cfg)


if __name__ == "__main__":
    main()
