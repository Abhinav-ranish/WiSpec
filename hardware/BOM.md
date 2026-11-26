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

## What we already have

| Item | Role |
|------|------|
| Dell Precision 3551 laptop (i7-10875H, 8C/16T, 32 GB RAM, Ubuntu) | Dev machine; single-band pilot with one AX210 swapped into its Wi-Fi slot; also a traffic client. It has no PCIe slots, so it can't be the capture box. Its 4 GB Quadro P620 is too small for training. |
| AWS credits, with SageMaker GPU spot quota approved | All model training (`cloud/aws/README.md`) |

## Sponsorship budget — $4,000

This is everything still needed for the full rig, including the optional 4th
band. Prices allow for late-2026 SSD and RAM pricing, which is well above
historical levels.

| # | Item | Qty | Why | Budget |
|---|------|-----|-----|-------:|
| 1 | **Capture tower PC**: recent Intel/AMD desktop in a full tower (not SFF), **≥4 PCIe slots**, 32 GB RAM, USB 3.x, runs the Ubuntu LTS release PicoScenes supports. No GPU needed. | 1 | Holds all receiver cards plus the camera on one clock; stays fixed in the room | $1,200 |
| 2 | **Storage**: 4 TB NVMe SSD (capture) + 8 TB HDD (archive/backup) | 1 + 1 | Raw CSI is ~40–70 GB per recorded hour | $500 |
| 3 | **Intel AX210** cards: 4 on PCIe x1 adapter boards (2.4 / 5 / 6 / top-6 GHz) + 1 bare M.2 card for the laptop pilot. Genuine AX210, not AX211. | 5 | CSI receivers, one per band | $200 |
| 4 | **6 GHz-rated tri-band antennas** (2.4/5/6–7.1 GHz, RP-SMA) + MHF4 pigtails + rigid bracket and tripods | 8 + mounts | Fixed, measured antenna geometry across every session | $250 |
| 5 | **Tri-band Wi-Fi 7 router with OpenWrt support**: pinnable channels, 160 MHz on 5/6 GHz, fixed TX power, MLO/band steering off | 1 | Transmitter | $350 |
| 6 | **Second Wi-Fi 6E/7 AP** that can be pinned to 6 GHz ch 207 | 1 | Transmitter for the top-of-6-GHz band (one AP radio serves only one 6 GHz channel) | $200 |
| 7 | **Orbbec Femto Bolt** depth camera | 1 | Training labels: depth frames, room scan, 3D body joints | $420 |
| 8 | **2× Raspberry Pi 5** kits (PSU, case, microSD) | 2 | Traffic clients that keep each band at a steady 200–500 frames/s | $200 |
| 9 | Home Assistant voice satellite | 1 | "Play that" / "turn that on" | $60 |
| 10 | Cables, PoE/power, UPS, spare parts, shipping and tax (~15%) | — | Contingency | $620 |
| | **Total** | | | **$4,000** |

Not in the ask: model training runs on AWS SageMaker credits, and software
is open source or free for research.

## Requirements summary

**Hardware**
- Capture host: x86 desktop with ≥4 PCIe slots (x1 is enough), 32 GB RAM,
  ≥4 TB fast storage, USB 3 for the depth camera. No GPU.
- One Intel AX210 per captured band (3 for tri-band, 4 with the top-6-GHz band).
- Antennas rated for 6–7.1 GHz, mounted rigidly; the geometry must not change
  between sessions.
- Tri-band OpenWrt router (+ a second 6 GHz AP for the 4th band).
- One traffic client per band (laptop, Raspberry Pis, or spare devices).
- Orbbec Femto Bolt depth camera, mounted to see the whole room, with its pose
  measured relative to the antenna bracket.

**Software / accounts**
- Ubuntu LTS (the release PicoScenes currently supports) on the capture host.
- PicoScenes and the PicoScenes Python Toolbox (free for research use).
- Orbbec SDK (`pyorbbecsdk`). Body tracking via the Azure Kinect Body
  Tracking SDK if it installs; otherwise an RGB-D pose model run on SageMaker.
- AWS account: SageMaker GPU spot quota (done), S3 bucket, execution role,
  GitHub OIDC role (`cloud/aws/README.md`).
- Home Assistant instance for the automation demo.

**Room setup**
- Router channels pinned to match `configs/rig_tri_band.json` /
  `configs/rig_quad_band.json`.
- Consent from anyone recorded; sessions varied (walking, sitting, pointing,
  empty room, different times of day).

## Phase 1 — Core rig (detail)

| # | Item | Qty | Purpose |
|---|------|-----|---------|
| 1 | Intel AX210 on a PCIe x1 adapter card (M.2 E-key → PCIe, MHF4 pigtails) | 3 | Receiver: one card per band (2.4/40, 5/160, 6/160) |
| 2 | 6 GHz-rated tri-band antennas. The antennas bundled with most adapter kits are not rated for 6 GHz. | 6 | RX antennas |
| 3 | Rigid antenna bracket / rail + tripod | 1 | Fixed, measured antenna geometry |
| 4 | Tri-band Wi-Fi 6E/7 router with OpenWrt support | 1 | Transmitter |
| 5 | Traffic clients, one associated per band | 3 | Steady packet rate |
| 6 | Orbbec Femto Bolt | 1 | Teacher |
| 7 | Capture tower PC | 1 | Capture on one clock, CPU body tracking |
| 8 | Voice front-end (Home Assistant satellite) | 1 | Commands |

**Buy in this order:**
1. One bare AX210 for the laptop (~$20). Confirm PicoScenes captures CSI.
2. Tower PC, storage, 3 AX210 kits, antennas, router, traffic clients.
3. Femto Bolt once capture works.
4. The 4th-band upgrade (AX210 + second AP) once the 3-band models work.

## Phase 1b — Optional 4th band: top of 6 GHz (~7 GHz)

The 6 GHz Wi-Fi band runs up to 7.125 GHz. The base rig captures only its
bottom (ch 15, centre 6025 MHz). Adding a capture at the top (ch 207,
6905–7065 MHz, centre 6985 MHz) spreads the measurements ~1 GHz further
across frequency, which is most of what a future "7 GHz" band would add,
and it's legal today. Config: `configs/rig_quad_band.json`.

| Item | Qty | Purpose | Approx. cost |
|------|-----|---------|-------------:|
| Intel AX210 PCIe kit + 2 tri-band antennas (RX host, 4th slot) | 1 | Receives ch 207 | ~$55–60 |
| Second Wi-Fi 6E/7 AP that can be pinned to 6 GHz ch 207 at 160 MHz (a tri-band router has only one 6 GHz radio, so it can't serve two 6 GHz channels at once) | 1 | Transmits on ch 207 | ~$120–250 |
| AX210 kit for the traffic node | 1 | Keeps the ch 207 AP busy | ~$40 |

Do this **after** the 3-band rig works. Then use the per-band ablation in
`python -m wispec.train eval` to measure whether `6g_hi` adds information
beyond `6g`. If it doesn't, drop it. The genuinely new 7.125+ GHz spectrum is
not open for Wi-Fi yet (the lower-7 GHz band is still at the proposal stage),
so there is nothing to buy for it.

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
