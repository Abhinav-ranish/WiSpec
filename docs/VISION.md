# WiSpec Vision — Room Mapping and "Point-and-Say" Home Automation

## Goal

Turn the Wi-Fi a home already has into a room sensor: know **where people
are, what pose they're in, and what they're pointing at**, so that
"play that", "turn that off" or "start that" just works. No cameras or
motion/occupancy sensors at runtime.

## Honest constraints

- **Training needs a teacher.** Like the WiFiCam-style demo, the Wi-Fi
  models learn from a camera during training. The product version needs a
  short one-time **calibration** per home (walk around with the camera on,
  or a phone scan) to fit the room and register device locations. After
  that, the camera can be removed.
- **Cross-room generalization is the hard open problem.** Models trained in
  one room degrade in another. The plan assumes per-room calibration plus a
  pretrained backbone, not zero-shot generalization.
- **Pointing from Wi-Fi alone is research-grade.** Coarse arm direction is
  realistic; picking between two devices 10° apart probably isn't. The
  target is distinguishing devices at least ~30° apart from the user's
  viewpoint, and asking "the TV or the speaker?" when it's ambiguous.
- **More data ≠ better data.** Sessions must vary activities, positions and
  times of day (the reference demo got *worse* after adding 7 hours of
  mostly-sitting data). Train/test splits are by session, never by frame.
- **Privacy.** Wi-Fi sensing can work through walls. Only record people who
  have consented, and keep the runtime local.

## System architecture

```
           ┌─────────────── calibration only ────────────────┐
           │ Femto Bolt: depth frames, room point cloud,      │
           │ 3D body joints (labels)                          │
           └──────────────────────┬──────────────────────────┘
                                  │ training targets
 Tri-band AP ─► 3× AX210 (2.4/5/6 GHz, one host clock)
                 │
                 ▼
  CSI windows (1.5 s × 3 bands) ─► CSINet (per-band stems + fusion)
                                     ├─► depth latent ─► frame decoder ─► silhouette/depth image
                                     ├─► 3D joints ─► pointing ray
                                     └─► position / presence
                                                        │
  Room map (walls, device anchors) ◄────────────────────┤
                                                        ▼
  Voice: "play that" ─► intent parser ─► resolve "that" = anchor hit by ray
                                         ─► Home Assistant service call
```

Code map:

| Module | What it does |
|--------|--------------|
| `wispec/capture/` | Multi-NIC PicoScenes capture + teacher camera recording on one clock |
| `wispec/data/` | CSI cleaning, windowing aligned to camera frames, synthetic sessions for testing |
| `wispec/models/` | Frame autoencoder (stage 1) and tri-band CSINet (stage 2) |
| `wispec/train.py` | Training/evaluation CLI incl. mean-frame baseline and per-band ablation |
| `wispec/room/` | Room map with device anchors; pointing ray from joints; target resolution |
| `wispec/automation/` | Utterance → intent → Home Assistant service call |

## Milestones

| # | Milestone | Success criterion |
|---|-----------|-------------------|
| M0 | Rig bring-up | 3 bands captured concurrently for 10 min with < 1% packet gaps; camera/CSI clock skew < 10 ms |
| M1 | Presence + position | Person (x, y) error < 0.5 m on held-out sessions |
| M2 | WiFiCam-style reconstruction | Depth silhouettes beat the mean-frame baseline PSNR on held-out sessions; tri-band beats best single band |
| M3 | 3D pose | MPJPE reported on held-out sessions; arms tracked well enough for M4 |
| M4 | Pointing | ≥ 80% correct target among anchors ≥ 30° apart, with an "ambiguous" fallback |
| M5 | Room map | Camera-scan map + anchors (calibration); research track: Wi-Fi-only wall/material map using Tier A/B material classification |
| M6 | Home automation | "Play that" / "turn that on/off" end-to-end through Home Assistant with < 1 s latency |

## Related work to read first

- WiFiCam (Strohmayer et al., ICIP 2024) — camera-supervised image reconstruction from CSI; the demo that inspired this.
- DensePose from WiFi (Geng, Huang, De la Torre, 2022) — dense body pose from CSI with camera supervision.
- Person-in-WiFi 3D (Yan et al., CVPR 2024) — multi-person 3D pose from Wi-Fi.
- SenseFi — open benchmark/library of deep models for Wi-Fi sensing.
