"""Train and evaluate WiSpec Tier C models.

    # end-to-end on synthetic data (no hardware needed)
    python -m wispec.train synth  --config configs/rig_tri_band.json --out data/synth --sessions 6 --seconds 120
    python -m wispec.train stage1 --config configs/rig_tri_band.json --data data/synth --run runs/synth
    python -m wispec.train stage2 --config configs/rig_tri_band.json --data data/synth --run runs/synth
    python -m wispec.train eval   --config configs/rig_tri_band.json --data data/synth --run runs/synth \
                                  --room configs/room_example.json

Sessions are split into train/test by whole session (see ``split_sessions``),
and the split is saved in the run directory so every stage uses the same one.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

from wispec.config import RigConfig
from wispec.data.windows import (Windows, build_windows, concat_windows, load_session,
                                 split_sessions)
from wispec.models.networks import CSINet, FrameAutoencoder


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _sessions(data: Path) -> list[str]:
    return sorted(p.name for p in data.iterdir() if (p / "teacher.npz").exists())


def _split(run: Path, data: Path, test_frac: float) -> dict:
    f = run / "split.json"
    if f.exists():
        return json.loads(f.read_text())
    train, test = split_sessions(_sessions(data), test_frac)
    split = {"train": train, "test": test}
    run.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(split, indent=2))
    return split


def _windows(data: Path, names: list[str], cfg: RigConfig, stride: int) -> Windows:
    return concat_windows([build_windows(load_session(data / n, cfg), cfg, stride=stride) for n in names])


def psnr(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    mse = ((a - b) ** 2).reshape(len(a), -1).mean(1)
    return 10 * np.log10(1.0 / np.maximum(mse, 1e-10))


# ------------------------------------------------------------------ synth

def cmd_synth(a, cfg: RigConfig):
    from wispec.data.synthetic import generate_session
    from wispec.room.room_map import RoomMap
    anchors = [an.position for an in RoomMap.from_json(a.room).anchors] if a.room else None
    for i in range(a.sessions):
        p = generate_session(Path(a.out) / f"synth_{i:02d}", cfg, seconds=a.seconds, seed=i, anchors=anchors)
        print("wrote", p)


# ------------------------------------------------------------------ stage 1

def cmd_stage1(a, cfg: RigConfig):
    data, run = Path(a.data), Path(a.run)
    split = _split(run, data, a.test_frac)
    frames = np.concatenate([
        build_windows(load_session(data / n, cfg), cfg, stride=1).frames for n in split["train"]])
    dev = _device()
    ae = FrameAutoencoder(cfg.frame_channels, cfg.latent_dim, cfg.frame_size).to(dev)
    opt = torch.optim.AdamW(ae.parameters(), lr=a.lr, weight_decay=1e-4)
    x_all = torch.from_numpy(frames)
    for ep in range(a.epochs):
        ae.train()
        perm = torch.randperm(len(x_all))
        tot = 0.0
        for i in range(0, len(perm), a.batch):
            x = x_all[perm[i:i + a.batch]].to(dev)
            rec, _ = ae(x)
            loss = nn.functional.mse_loss(rec, x)
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(x)
        print(f"[stage1] epoch {ep + 1}/{a.epochs} mse={tot / len(x_all):.5f}")
    torch.save({"model": ae.state_dict(), "mean_frame": frames.mean(0)}, run / "stage1.pt")
    print("saved", run / "stage1.pt")


def _load_ae(run: Path, cfg: RigConfig, dev) -> tuple[FrameAutoencoder, np.ndarray]:
    ck = torch.load(run / "stage1.pt", map_location=dev, weights_only=False)
    ae = FrameAutoencoder(cfg.frame_channels, cfg.latent_dim, cfg.frame_size).to(dev)
    ae.load_state_dict(ck["model"])
    ae.eval()
    return ae, ck["mean_frame"]


# ------------------------------------------------------------------ stage 2

def _targets(w: Windows, ae: FrameAutoencoder, dev) -> dict:
    with torch.no_grad():
        z = torch.cat([ae.encode(torch.from_numpy(w.frames[i:i + 512]).to(dev)).cpu()
                       for i in range(0, len(w.frames), 512)])
    t = {"latent": z}
    if w.joints is not None:
        present = ~np.isnan(w.joints).any(axis=(1, 2))
        t["joints"] = torch.from_numpy(np.nan_to_num(w.joints))
        t["present"] = torch.from_numpy(present.astype(np.float32))
    return t


def _norm_stats(w: Windows) -> list[tuple[np.ndarray, np.ndarray]]:
    return [(x.mean(axis=(0, 2), keepdims=True)[0], x.std(axis=(0, 2), keepdims=True)[0] + 1e-5) for x in w.x]


def _apply_norm(w: Windows, stats) -> list[torch.Tensor]:
    return [torch.from_numpy((x - m) / s) for x, (m, s) in zip(w.x, stats)]


def cmd_stage2(a, cfg: RigConfig):
    data, run = Path(a.data), Path(a.run)
    split = _split(run, data, a.test_frac)
    dev = _device()
    ae, _ = _load_ae(run, cfg, dev)
    w = _windows(data, split["train"], cfg, a.stride)
    stats = _norm_stats(w)
    xs = _apply_norm(w, stats)
    bmask = torch.from_numpy((w.band_valid > 0.5).astype(np.float32))
    tg = _targets(w, ae, dev)
    z_mean, z_std = tg["latent"].mean(0), tg["latent"].std(0) + 1e-5
    has_j = "joints" in tg

    net = CSINet(cfg.band_channels(), cfg.latent_dim, band_dropout=a.band_dropout).to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=1e-3)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, a.epochs)
    n = len(tg["latent"])
    print(f"[stage2] {n} training windows from {len(split['train'])} sessions; bands={[b.name for b in cfg.bands]}")
    for ep in range(a.epochs):
        net.train()
        perm = torch.randperm(n)
        tot = 0.0
        for i in range(0, n, a.batch):
            idx = perm[i:i + a.batch]
            out = net([x[idx].to(dev) for x in xs], bmask[idx].to(dev))
            zt = ((tg["latent"][idx] - z_mean) / z_std).to(dev)
            loss = nn.functional.mse_loss(out["latent"], zt)
            if has_j:
                pr = tg["present"][idx].to(dev)
                loss = loss + 0.5 * nn.functional.binary_cross_entropy_with_logits(out["presence"], pr)
                if pr.sum() > 0:
                    jerr = (out["joints"] - tg["joints"][idx].to(dev)).abs().mean(dim=(1, 2))
                    loss = loss + a.joint_weight * (jerr * pr).sum() / pr.sum()
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
        sched.step()
        print(f"[stage2] epoch {ep + 1}/{a.epochs} loss={tot / n:.4f}")
    torch.save({"model": net.state_dict(), "stats": stats, "z_mean": z_mean, "z_std": z_std,
                "band_dropout": a.band_dropout}, run / "stage2.pt")
    print("saved", run / "stage2.pt")


# ------------------------------------------------------------------ eval

@torch.no_grad()
def _predict(net, ae, xs, bmask, z_mean, z_std, dev, batch=256) -> dict:
    outs = {"frames": [], "joints": [], "presence": []}
    for i in range(0, len(xs[0]), batch):
        o = net([x[i:i + batch].to(dev) for x in xs], bmask[i:i + batch].to(dev))
        z = o["latent"] * z_std.to(dev) + z_mean.to(dev)
        outs["frames"].append(ae.decode(z).cpu().numpy())
        outs["joints"].append(o["joints"].cpu().numpy())
        outs["presence"].append(torch.sigmoid(o["presence"]).cpu().numpy())
    return {k: np.concatenate(v) for k, v in outs.items()}


def cmd_eval(a, cfg: RigConfig):
    data, run = Path(a.data), Path(a.run)
    split = json.loads((run / "split.json").read_text())
    dev = _device()
    ae, mean_frame = _load_ae(run, cfg, dev)
    ck = torch.load(run / "stage2.pt", map_location=dev, weights_only=False)
    net = CSINet(cfg.band_channels(), cfg.latent_dim).to(dev)
    net.load_state_dict(ck["model"])
    net.eval()

    w = _windows(data, split["test"], cfg, a.stride)
    xs = _apply_norm(w, ck["stats"])
    valid = torch.from_numpy((w.band_valid > 0.5).astype(np.float32))
    gt = w.frames
    with torch.no_grad():
        ae_rec = np.concatenate([ae(torch.from_numpy(gt[i:i + 256]).to(dev))[0].cpu().numpy()
                                 for i in range(0, len(gt), 256)])
    report = {
        "test_sessions": split["test"], "n_windows": int(len(gt)),
        "psnr_mean_frame_baseline": float(psnr(np.broadcast_to(mean_frame, gt.shape), gt).mean()),
        "psnr_autoencoder_upper_bound": float(psnr(ae_rec, gt).mean()),
        "ablation": {},
    }

    names = [b.name for b in cfg.bands]
    combos = [c for r in range(1, len(names) + 1) for c in itertools.combinations(range(len(names)), r)]
    full_pred = None
    for combo in combos:
        m = torch.zeros_like(valid)
        m[:, list(combo)] = 1
        pred = _predict(net, ae, xs, valid * m, ck["z_mean"], ck["z_std"], dev)
        entry = {"psnr": float(psnr(pred["frames"], gt).mean())}
        if w.joints is not None:
            present = ~np.isnan(w.joints).any(axis=(1, 2))
            if present.any():
                err = np.linalg.norm(pred["joints"][present] - w.joints[present], axis=-1)
                entry["mpjpe_m"] = float(err.mean())
                entry["position_err_m"] = float(np.linalg.norm(
                    pred["joints"][present, -1, :2] - w.joints[present, -1, :2], axis=-1).mean())
            entry["presence_acc"] = float(((pred["presence"] > 0.5) == present).mean())
        report["ablation"]["+".join(names[i] for i in combo)] = entry
        if len(combo) == len(names):
            full_pred = pred

    if a.room and w.joints is not None and full_pred is not None:
        from wispec.room.room_map import RoomMap
        room = RoomMap.from_json(a.room)
        hits = total = 0
        for gj, pj in zip(w.joints, full_pred["joints"]):
            if np.isnan(gj).any():
                continue
            g = room.resolve_joints(gj)
            if g.anchor is None:
                continue
            total += 1
            p = room.resolve_joints(pj)
            hits += int(p.anchor is not None and p.anchor.name == g.anchor.name)
        report["pointing"] = {"n_pointing_windows": total,
                              "target_accuracy": hits / total if total else None}

    (run / "eval.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

    if a.save_examples:
        idx = np.linspace(0, len(gt) - 1, 8).astype(int)
        np.savez_compressed(run / "examples.npz", gt=gt[idx], wifi=full_pred["frames"][idx], ae=ae_rec[idx])


# ------------------------------------------------------------------ cli

def main(argv=None):
    p = argparse.ArgumentParser(prog="wispec.train")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--config", default="configs/rig_tri_band.json")
        sp.add_argument("--test-frac", type=float, default=0.25)
        sp.add_argument("--stride", type=int, default=1, help="use every Nth teacher frame")

    s = sub.add_parser("synth"); common(s)
    s.add_argument("--out", required=True); s.add_argument("--sessions", type=int, default=6)
    s.add_argument("--seconds", type=float, default=120); s.add_argument("--room", default="configs/room_example.json")

    for name, ep, lr in (("stage1", 30, 2e-3), ("stage2", 40, 1e-3)):
        s = sub.add_parser(name); common(s)
        s.add_argument("--data", required=True); s.add_argument("--run", required=True)
        s.add_argument("--epochs", type=int, default=ep); s.add_argument("--batch", type=int, default=64)
        s.add_argument("--lr", type=float, default=lr)
        s.add_argument("--band-dropout", type=float, default=0.15)
        s.add_argument("--joint-weight", type=float, default=1.0)

    s = sub.add_parser("eval"); common(s)
    s.add_argument("--data", required=True); s.add_argument("--run", required=True)
    s.add_argument("--room", default=None); s.add_argument("--save-examples", action="store_true")

    a = p.parse_args(argv)
    cfg = RigConfig.from_json(a.config)
    {"synth": cmd_synth, "stage1": cmd_stage1, "stage2": cmd_stage2, "eval": cmd_eval}[a.cmd](a, cfg)


if __name__ == "__main__":
    main()
