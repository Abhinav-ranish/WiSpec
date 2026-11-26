"""Multi-NIC PicoScenes capture (one AX210 per band) and conversion to WiSpec's .npz format.

PicoScenes' CLI changes between releases, so the commands are templates in
one place. Check them against the manual for your installed version
(https://ps.zpj.io/) and adjust ``PREPARE_TEMPLATE`` / ``LOGGER_TEMPLATE``
if needed. ``--dry-run`` prints the commands without running anything.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

import numpy as np

from wispec.config import BandConfig, RigConfig

# Put a NIC in monitor mode on a channel: '<phy>' '<primary> <cbw> <center>'.
PREPARE_TEMPLATE = 'array_prepare_for_picoscenes {phy} "{primary} {cbw} {center}"'
# Passive logger on one NIC writing <output>.csi.
LOGGER_TEMPLATE = 'PicoScenes "-d debug; -i {phy} --mode logger --output {output}"'


def prepare_cmd(b: BandConfig) -> str:
    return PREPARE_TEMPLATE.format(phy=b.phy, primary=b.primary_mhz, cbw=b.bandwidth_mhz, center=b.center_mhz)


def logger_cmd(b: BandConfig, out_dir: Path) -> str:
    return LOGGER_TEMPLATE.format(phy=b.phy, output=shlex.quote(str(out_dir / f"raw_{b.name}")))


class MultiBandCapture:
    """Starts one PicoScenes logger per band so all bands record concurrently."""

    def __init__(self, cfg: RigConfig, out_dir: Path, dry_run: bool = False):
        self.cfg, self.out_dir, self.dry_run = cfg, Path(out_dir), dry_run
        self.procs: list[subprocess.Popen] = []

    def prepare(self) -> list[str]:
        cmds = [prepare_cmd(b) for b in self.cfg.bands]
        for c in cmds:
            print("$", c)
            if not self.dry_run:
                subprocess.run(c, shell=True, check=True)
        return cmds

    def start(self) -> list[str]:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        cmds = [logger_cmd(b, self.out_dir) for b in self.cfg.bands]
        for b, c in zip(self.cfg.bands, cmds):
            print("$", c)
            if not self.dry_run:
                log = open(self.out_dir / f"picoscenes_{b.name}.log", "w")
                self.procs.append(subprocess.Popen(c, shell=True, stdout=log, stderr=subprocess.STDOUT))
        return cmds

    def stop(self):
        for p in self.procs:
            p.terminate()
        for p in self.procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
        self.procs.clear()


def convert_csi_file(src: Path, dst: Path) -> int:
    """Convert a PicoScenes .csi file to WiSpec npz (t_ns, csi[N, S, R]).

    Uses the PicoScenes Python Toolbox (``pip install picoscenes`` / build from
    the PicoScenes-Python-Toolbox repo). Field names follow the toolbox's
    parsed-frame dicts; if your toolbox version differs, adjust ``_frame_fields``.
    Returns the number of frames written.
    """
    try:
        from picoscenes import Picoscenes  # type: ignore
    except ImportError as e:  # pragma: no cover - depends on local install
        raise RuntimeError("PicoScenes Python Toolbox not installed; see the PicoScenes manual") from e

    frames = Picoscenes(str(src))
    ts, csis = [], []
    for i in range(frames.count):
        t, c = _frame_fields(frames.raw[i])
        if c is None:
            continue
        ts.append(t)
        csis.append(c)
    if not csis:
        raise RuntimeError(f"no CSI frames parsed from {src}")
    s = min(c.shape[0] for c in csis)
    csi = np.stack([c[:s] for c in csis]).astype(np.complex64)
    t_ns = np.asarray(ts, np.int64)
    order = np.argsort(t_ns)
    np.savez_compressed(dst, t_ns=t_ns[order], csi=csi[order])
    return len(t_ns)


def _frame_fields(frame: dict) -> tuple[int, np.ndarray | None]:
    """(host timestamp ns, CSI [S, R]) from one parsed PicoScenes frame. Verify keys per toolbox version."""
    rxs = frame.get("RxSBasic", {})
    t = int(rxs.get("systemns") or rxs.get("timestamp", 0))
    csi_seg = frame.get("CSI", {})
    raw = csi_seg.get("CSI")
    if raw is None:
        return t, None
    n_tones = int(csi_seg.get("numTones", len(raw)))
    arr = np.asarray(raw).reshape(n_tones, -1)   # tones x (tx*rx); keep first TX stream's RX antennas
    n_rx = int(csi_seg.get("numRx", arr.shape[1]))
    return t, arr[:, :n_rx]
