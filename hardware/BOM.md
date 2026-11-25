# WiSpec Hardware — Recommended Rig (Tier C: Room Mapping & Pointing)

This is the hardware to build the room-scale WiSpec rig: concurrent
**tri-band** CSI capture (2.4 + 5 + 6 GHz), a depth-camera "teacher" for
training labels, and the compute to train models. It supersedes the
single-AX210 setup in the main README for Tier C work. Tiers A/B (material
classification) keep working on the same hardware.

> Prices are rough US street prices (late 2026) for budgeting only — check
> before buying. Items marked **verify** depend on vendor support that could
> not be confirmed from the PicoScenes manual at time of writing.

## Design decisions (why this rig)

1. **One Intel AX210 per band, all in the same receiver host.** A single
   AX210 only tunes one channel at a time. Hopping between bands breaks the
   continuous 1.5 s CSI windows the models need. Three cards on one host give
   simultaneous 2.4/5/6 GHz capture and — because they share one host clock —
   CSI from all bands and the camera are timestamped against the same clock.
   PicoScenes supports multiple NICs per host with concurrent capture, and the
   AX210 supports 2.4/5/6 GHz at 20/40/80/160 MHz.
2. **160 MHz on 5 and 6 GHz.** Range resolution scales with bandwidth
   (~c / 2B ≈ 0.9 m at 160 MHz vs ~3.7 m at 40 MHz). This is WiSpec's main
   advantage over 40 MHz router setups like the one in the WiFiCam-style demo.
3. **Depth camera as teacher, not a webcam.** Wi-Fi senses geometry, not
   colour or texture. A ToF depth camera gives depth maps (the reconstruction
   target), a point cloud of the room (the map), and 3D body joints via body
   tracking (the labels for pose and **pointing**).
4. **Transmit from a real tri-band AP, not client-to-client injection on
   6 GHz.** FCC rules require 6 GHz client devices to operate under the
   control of an access point, so AX210 packet injection on 6 GHz is a
   regulatory grey area. A tri-band AP on pinned channels, kept busy by
   traffic clients, gives a controlled, high, steady packet rate legally and
   matches how the end product will work (the user's own router).
5. **Commodity everything, SDR later only if needed.** A USRP that covers
   6–7 GHz with 400 MHz bandwidth (e.g. X410-class) costs tens of thousands of
   dollars and PicoScenes support for it is unverified. Only consider it if
   the AX210 rig demonstrably hits a resolution ceiling.

## Phase 1 — Core rig

| # | Item | Qty | Purpose | Approx. cost |
|---|------|-----|---------|-------------:|
| 1 | **Intel AX210** on a desktop PCIe x1 adapter card (M.2 E-key → PCIe, with MHF4 pigtails) — buy genuine Intel AX210 (not AX211, which is CNVio and Intel-platform-only) | 3 | Receiver: one card per band (2.4/40, 5/160, 6/160) | $35–45 ea → ~$120 |
| 2 | **6 GHz-rated tri-band antennas** (2.4/5/6–7.1 GHz, RP-SMA) — the antennas bundled with most adapter kits are not rated for 6 GHz | 6 (2 per card) | RX antennas | ~$80–120 |
| 3 | Rigid antenna bracket / rail + tripod | 1 | Fixed, measured antenna geometry (keep it identical across all sessions) | ~$60–100 |
| 4 | **Tri-band Wi-Fi 6E/7 router with OpenWrt support** | 1 | Transmitter. Must allow pinning channels, 160 MHz on 5 and 6 GHz, fixed TX power, and disabling band steering / MLO / auto-channel / DFS hopping | ~$200–350 |
| 5 | **Traffic node**: any small Linux PC with 3 Wi-Fi 6E clients (3× AX210 again is simplest) — one client associated per band, generating traffic so the AP transmits at a steady 200–500 frames/s per band | 1 PC + 3 AX210 kits | Packet-rate control | ~$300–500 (used SFF PC) + ~$120 |
| 6 | **Orbbec Femto Bolt** (ToF depth + RGB, 120° FOV, Azure Kinect-compatible; body tracking via the Kinect Body Tracking SDK wrapper) | 1 | Teacher: depth frames, room point cloud, 3D skeleton joints | ~$350–420 |
| 7 | **Receiver / training host**: x86 desktop running the Ubuntu LTS release PicoScenes currently supports; ≥3 free PCIe slots (x1 is fine); 64 GB RAM; 4 TB NVMe; NVIDIA RTX 4090/5090-class GPU (24–32 GB) | 1 | Capture (3 NICs + camera on one clock), body tracking, training | reuse existing, or ~$2.5–3.5k new |
| 8 | Voice front-end: a Home Assistant Assist satellite (e.g. HA Voice Preview Edition) or a USB mic array | 1 | "Play that" / "turn that on" commands | ~$60 |

**Phase 1 total:** ~$1.3–1.8k if you reuse a GPU workstation, ~$4–5k with
a new one.

### Why not cheaper or newer parts

| Option | Verdict |
|--------|---------|
| Intel AX200 / AX201 | No 6 GHz. Fine for Tier A/B dual-band only. |
| Intel AX211 | CNVio2 — only works in Intel-platform laptop/desktop slots; no PCIe adapters. |
| Intel BE200 (Wi-Fi 7, 320 MHz) | Tempting (2× bandwidth), but PicoScenes' documented commodity-NIC CSI path names AX200/AX210, not BE200. **Verify** before buying; revisit if support lands. |
| ESP32-S3 / C5 / C6 CSI | Cheap and easy, but 20 MHz (40 MHz at best), ≤5 GHz, noisy CSI. Good later as a *product* deployment target, not for the research rig. |
| Nexmon (Broadcom) routers / Raspberry Pi | ≤80 MHz, no 6 GHz. |
| USRP X410-class SDR | Covers 6 GHz with 400 MHz bandwidth, but far more expensive; PicoScenes support **unverified**. Phase 3 at the earliest. |
| Webcam as teacher | Works (that's what the WiFiCam-style demo used), but RGB targets waste model capacity on colour/texture and give no 3D joints. Supported in the code as a fallback. |

## Phase 2 — Multi-view (after Phase 1 models work)

Room-scale localization and pointing improve a lot with a second viewpoint
(the reference demo used two routers).

| Item | Qty | Purpose | Approx. cost |
|------|-----|---------|-------------:|
| Second receiver node (SFF PC + 3× AX210 kits + 6 tri-band antennas + bracket) | 1 | Second CSI viewpoint on the opposite side of the room | ~$600–900 |
| Second Femto Bolt | 1 | Fewer occluded labels (body tracking from two angles) | ~$350–420 |
| PTP-capable NICs or a small PTP/NTP switch setup (chrony is fine to start) | — | Cross-host clock sync, target < 1 ms | ~$0–150 |

## Data volume planning

160 MHz AX210 CSI is large: roughly 1–2k subcarriers × 2 RX antennas
per frame. At ~200 frames/s per band × 3 bands, raw CSI is on the order of
**10–20 MB/s (~40–70 GB per recorded hour)**, plus depth/RGB video. A 4 TB
NVMe holds roughly 50 hours of sessions. Training uses downsampled
subcarriers (see `configs/rig_tri_band.json`), so models stay small.

## Setup checklist

1. Install the AX210s and antennas; label every card with its PHY id and band.
2. Install PicoScenes; confirm all three cards are listed (`array_status`).
3. Configure the router: separate SSIDs per band, pinned channels matching
   `configs/rig_tri_band.json`, 160 MHz on 5/6 GHz, fixed TX power, MLO and
   band steering off.
4. Associate one traffic client per band and start the traffic generator.
5. Mount the Femto Bolt so it sees the whole room; record its pose relative
   to the antenna bracket (needed to put Wi-Fi and camera in one coordinate
   frame).
6. Dry-run a capture: `python -m wispec.capture.session --config configs/rig_tri_band.json --out data/sessions/test --duration 30 --dry-run`
