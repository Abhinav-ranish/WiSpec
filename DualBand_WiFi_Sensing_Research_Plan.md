# Dual-Band Wi-Fi Sensing for Material and Obstruction Inference
## Rigorous Research Assessment and Experiment Plan

---

# 1. LITERATURE REVIEW

## 1a. Direct Prior Art
These papers address material identification or characterization using Wi-Fi or similar commodity RF signals. Your work must cite and differentiate from all of these.

### Paper 1: Wireless Sensing for Material Identification: A Survey
- **Authors:** Chen, Xu, Li, Zhang, Guo, Jin, Zheng, He (Tsinghua University)
- **Venue:** IEEE Communications Surveys & Tutorials (COMST), Vol 27, pp 1598–1617, 2025
- **Modality:** Survey covering RFID, mmWave, WiFi, UWB — both reflection-based and penetration-based
- **Frequencies:** Multi-band survey (sub-GHz through mmWave)
- **Hardware:** Various (commodity and specialized)
- **Task:** Material identification taxonomy and survey
- **Key finding:** First comprehensive survey of RF-based material identification. Organizes work into reflection-based vs penetration-based models, then by signal type.
- **Limitation:** Survey paper — does not propose new methods. Does not deeply investigate dual-band differential approaches at sub-7 GHz.
- **YOUR RISK:** This is the elephant in the room. If this survey already covers your exact claim, you have no paper. However, the survey catalogs individual works; it does not itself propose dual-band Wi-Fi differential attenuation as a material fingerprint. You are safe if you cite it and position your work as an empirical validation of a specific approach the survey discusses generally.

### Paper 2: Towards In-baggage Suspicious Object Detection Using Commodity WiFi
- **Authors:** Wang, Liu, Chen, Liu, Wang (Rutgers/Indiana)
- **Venue:** IEEE Conference on Communications and Network Security, 2018
- **Modality:** CSI (Intel 5300, 2–3 antennas)
- **Frequencies:** 5 GHz
- **Hardware:** Intel 5300 NIC, commodity WiFi
- **Task:** Classify baggage contents as metal, liquid, or unsuspicious
- **Key finding:** 95% detection rate for dangerous objects, 90% material-type classification
- **Limitation:** Single-band (5 GHz only). Controlled baggage scenario, not building materials. CSI-based, not RSSI.
- **YOUR DIFFERENTIATION:** You use dual-band differential features. You target building materials at room scale, not baggage contents at close range.

### Paper 3: Environment-independent In-baggage Object Identification Using WiFi Signals
- **Authors:** Same group (Rutgers), 2021
- **Venue:** IEEE MASS 2021
- **Modality:** CSI
- **Frequencies:** 5 GHz
- **Hardware:** Commodity WiFi
- **Task:** Object identification robust to environment changes
- **Limitation:** Still single-band, still baggage-scale.

### Paper 4: FruitSense — Sensing Fruit Ripeness Using Wireless Signals
- **Authors:** Tan, Yang, et al., 2018
- **Venue:** Conference paper
- **Modality:** CSI (frequency hopping across 5 GHz channels)
- **Frequencies:** 5 GHz (leverages >600 MHz bandwidth)
- **Hardware:** Commodity WiFi
- **Task:** Internal texture sensing of fruit (ripeness classification)
- **Key finding:** 90%+ accuracy classifying fruit ripeness by probing with WiFi across 5 GHz channels
- **Limitation:** Single-band. Very short range (contact-distance). Object-specific, not general material classification.

### Paper 5: Wi-Fruit — See Through Fruits with Smart Devices
- **Authors:** ACM IMWUT, 2021
- **Modality:** CSI
- **Frequencies:** 5 GHz
- **Task:** Fruit internal assessment
- **Limitation:** Same limitations as FruitSense.

### Paper 6: Experimental Assessment of the Effects of Building Materials on Wi-Fi Signal 2.4 GHz and 5 GHz
- **Authors:** (SCIRP, 2024)
- **Venue:** Scientific Research Publishing, 2024
- **Modality:** RSSI measurement
- **Frequencies:** 2.4 GHz and 5 GHz
- **Hardware:** Commodity routers
- **Task:** Measure and compare attenuation through building materials at both bands
- **Key finding:** Empirically confirms frequency-dependent attenuation differs by material
- **Limitation:** Pure measurement study. Does not attempt classification, does not propose using the differential as a feature, does not do spatial reconstruction.
- **YOUR RISK:** This paper proves the physical effect exists. You MUST cite it. But it does not do what you want to do (use the differential as a classification feature). This is actually good — it validates your premise without stealing your contribution.

## 1b. Adjacent Prior Art
These don't target material identification directly but use overlapping techniques.

### Paper 7: Multi-Band Wi-Fi Sensing with Matched Feature Granularity
- **Authors:** MERL (Mitsubishi Electric Research Labs), 2022
- **Venue:** IEEE Internet of Things Journal
- **Modality:** CSI (5 GHz) + beam SNR (60 GHz) fusion
- **Frequencies:** 5 GHz and 60 GHz
- **Hardware:** Custom routers with both radios
- **Task:** Pose recognition, occupancy sensing, indoor localization
- **Key finding:** Multi-band fusion improves sensing accuracy via feature granularity matching
- **Limitation:** Uses 5+60 GHz (not 2.4+5 GHz). Targets activity recognition, not material classification. Requires 60 GHz hardware.
- **YOUR DIFFERENTIATION:** You use the two most common consumer bands (2.4+5 GHz). You target material identification, not activity recognition. Your hardware requirement is dramatically lower.

### Paper 8: Radio Tomographic Imaging with Wireless Networks
- **Authors:** Wilson, Patwari (University of Utah)
- **Venue:** IEEE Transactions on Mobile Computing, 2010
- **Modality:** RSSI
- **Frequencies:** 2.4 GHz (Zigbee, 802.15.4)
- **Hardware:** 28 TelosB nodes
- **Task:** Image attenuation field to localize/track humans
- **Key finding:** Established RTI — linear model from RSS to attenuation image
- **Limitation:** Single-frequency. Requires dense node deployment. Targets moving objects (humans), not static material classification.

### Paper 9: Building Layout Tomographic Reconstruction via Commercial WiFi Signals
- **Authors:** IEEE, 2021
- **Venue:** IEEE Xplore
- **Modality:** RSSI
- **Frequencies:** 2.4 GHz (commercial WiFi)
- **Hardware:** Commodity WiFi cards
- **Task:** Reconstruct building layout (walls, interior objects)
- **Key finding:** First multimedia-scenario reconstruction from commercial WiFi RSSI alone
- **Limitation:** Single-band. Reconstructs geometry only, not material type.
- **YOUR DIFFERENTIATION:** You add material classification on top of spatial reconstruction by using dual-band differential features.

### Paper 10: Wiffract — A New Foundation for RF Imaging via Edge Tracing
- **Authors:** Pallaprolu, Korany, Mostofi (UCSB)
- **Venue:** MobiCom 2022 / IEEE RadarConf 2023
- **Modality:** Custom SDR-like setup (amplitude measurements)
- **Frequencies:** 5.1–5.9 GHz
- **Hardware:** Two TP-Link routers + motorized rail
- **Task:** Image edges of static objects through walls using Keller cone diffraction theory
- **Key finding:** Read letters of "BELIEVE" through a wall with WiFi, 86.7% letter classification
- **Limitation:** Requires mechanical scanning (motorized rail). Single-band. Images geometry (edges), not material composition.

### Paper 11: 802.11bf Multiband Passive Sensing
- **Authors:** Ropitault, Silva (NIST)
- **Venue:** IEEE Communications Magazine, 2024 / arXiv
- **Modality:** Standard-defined sensing procedure
- **Frequencies:** 2.4, 5, 6 GHz and 60 GHz
- **Task:** Defines the protocol for multiband passive sensing
- **Key finding:** IEEE 802.11bf enables sensing measurements across all Wi-Fi bands using standard-compliant procedures
- **YOUR RELEVANCE:** This standard is the reason your work will become increasingly relevant. Future routers will natively support what you're doing.

### Paper 12: Wi-Vi — See Through Walls with Wi-Fi
- **Authors:** Adib, Katabi (MIT CSAIL)
- **Venue:** SIGCOMM 2013
- **Modality:** Custom MIMO nulling (active)
- **Frequencies:** 2.4 GHz
- **Hardware:** USRP N210 SDR
- **Task:** Track moving humans through walls
- **Limitation:** Moving targets only. Single-band. Requires SDR.

## 1c. Gaps Not Fully Addressed

Based on the literature review, the following specific gaps exist:

1. **No paper uses 2.4 GHz vs 5 GHz differential attenuation as an explicit classification feature for building materials.** The SCIRP 2024 paper measures the effect but does not classify. Wang et al. classify materials but use single-band CSI features. The MERL paper fuses bands but for activity recognition and uses 5+60 GHz.

2. **No paper combines dual-band (2.4+5 GHz) differential features with spatial reconstruction/tomography for material-aware room mapping.** Wilson/Patwari do RTI but single-band and no material typing. The IEEE 2021 layout paper reconstructs geometry but not material.

3. **No paper does this with commodity hardware at both bands simultaneously.** Most dual/multi-band work uses at least one non-commodity component (SDR, 60 GHz radio, motorized rail).

4. **The 6 GHz and 7 GHz bands are almost entirely unexplored for material sensing** — 802.11bf opens this but no empirical material classification work exists yet.

---

# 2. NOVELTY AUDIT

## Claim 1: "2.4 vs 5 GHz differential attenuation as a material fingerprint"

**Verdict: INCREMENTAL BUT PUBLISHABLE**

The physical effect is well-documented (NIST measurements, iBwave data, SCIRP 2024 experimental paper). Everyone in RF propagation knows that different materials attenuate different frequencies differently. This is not a discovery.

However, nobody has taken this known physical property and operationalized it as a classification feature in a Wi-Fi sensing system. The SCIRP paper measures it but does not classify. The Wang baggage paper classifies but uses single-band CSI. The gap between "measured in RF propagation studies" and "used as a feature in a sensing pipeline" is real and publishable, but it is incremental. A reviewer will say: "of course this works, the physics predicts it." Your job is to show it works *in practice* with *commodity hardware* in *realistic conditions* where multipath and noise could plausibly destroy the signal.

## Claim 2: Combining dual-band differential + spatial reconstruction + commodity hardware

**Verdict: GENUINELY STRONG ANGLE (for a workshop/student paper)**

This three-way combination does not exist in the literature. Each piece is established:
- Dual-band attenuation differences → known physics (NIST, iBwave)
- Spatial reconstruction via Wi-Fi → RTI (Wilson/Patwari), layout reconstruction (2021)
- Material classification via Wi-Fi → Wang et al. (2018), FruitSense

But nobody has combined all three using commodity 2.4+5 GHz hardware. The integration is the contribution. This is genuinely publishable as a short paper at a sensing workshop or student symposium, and potentially as a full paper if the experiments are thorough.

## Claim 3: Extension to 6 GHz / Wi-Fi 6E / Wi-Fi 7

**Verdict: GENUINELY STRONG (if you can get the hardware)**

The 6 GHz band (and eventual 7 GHz) is brand new for commodity Wi-Fi. No empirical material sensing work exists at these frequencies using consumer hardware. If you can get a Wi-Fi 6E/7 router and extract CSI or even RSSI, you would be among the first to report material-dependent attenuation data at 6 GHz from commodity Wi-Fi. This would significantly strengthen the paper.

## Overall Verdict

**Incremental but publishable as a workshop/student paper. Potentially strong if you include 6 GHz data and demonstrate the full pipeline (sense → classify → localize).**

The honest framing: you are not discovering a new physical effect. You are proposing a practical system that exploits a known effect in a way nobody has demonstrated end-to-end with commodity hardware. The value is in the empirical validation, the system design, and the reproducibility with cheap equipment.

---

# 3. PHYSICS GROUNDING

## Why Different Materials Affect 2.4 GHz and 5 GHz Differently

The interaction between electromagnetic waves and matter depends on the wave frequency and the material's electromagnetic properties (permittivity ε, permeability μ, conductivity σ).

### Penetration Loss (Attenuation)
When an EM wave enters a material, it loses energy through two mechanisms:

**Absorption:** The electric field drives charged particles and polar molecules, converting EM energy to heat. The absorption coefficient α increases with frequency for most building materials because:
- Higher frequencies drive molecular dipoles (especially water) harder
- Conduction losses (σ/ωε term) are frequency-dependent
- For concrete: the high water content during curing and residual moisture makes it strongly frequency-dependent

**Scattering:** When material inhomogeneities (aggregate particles, air bubbles, reinforcement) are comparable to the wavelength, scattering increases. At 2.4 GHz (λ≈12.5 cm), most aggregate particles are small compared to λ. At 5 GHz (λ≈6 cm), the same particles are closer to λ and scatter more. At 6 GHz (λ≈5 cm), even more so.

### Material-Specific Behavior

**Concrete:** Dominates your experiment. High permittivity (ε_r ≈ 5–8), high loss tangent, significant moisture content. Aggregate particles (5–20 mm diameter) scatter significantly at 5 GHz. Published data: ~23 dB loss at 2.4 GHz, ~45 dB at 5 GHz for a standard 8-inch wall. The differential is enormous (~22 dB). This is your easiest classification target.

**Wood:** Low permittivity (ε_r ≈ 1.5–3), moderate moisture dependency. Attenuation increases moderately with frequency. Published data: ~5–12 dB at 2.4 GHz, ~8–15 dB at 5 GHz. Differential: ~3–5 dB. Detectable but smaller.

**Drywall/Gypsum:** Very low loss (ε_r ≈ 2–3, low loss tangent). Published data: <1 dB at either frequency. Differential: near zero. This is useful as a "transparent" baseline — if you see almost no differential, it's probably drywall or open air.

**Glass (standard):** Low loss (ε_r ≈ 5–7). Published data: ~2–4 dB at 2.4 GHz, ~3–6 dB at 5 GHz. Differential: ~1–2 dB. Hard to distinguish from wood in some cases. Low-E coated glass is wildly different (metal oxide coating reflects strongly at both frequencies).

**Brick:** Medium loss. Published data: ~6–10 dB at 2.4 GHz, ~10–18 dB at 5 GHz. Differential: ~4–8 dB. Distinguishable from wood and concrete.

**Metal:** Near-total reflection at both frequencies (skin depth < 1 μm at GHz). The differential attenuation is near zero (both are "infinite"), but the reflection signature is distinctive — strong multipath at both bands. Classification relies on reflection characteristics, not penetration differential.

**Water:** Extremely high permittivity (ε_r ≈ 80), very high absorption. Both bands are heavily attenuated, with 5 GHz more so. The differential is large but the absolute loss at 2.4 GHz is already high. Human bodies (~60% water) produce a distinctive signature.

### When the Effect Is Detectable vs Buried by Noise

**Signal-to-noise for your differential feature:**
- Your feature is: Δ = Attenuation_5GHz − Attenuation_2.4GHz
- RSSI measurements on commodity hardware fluctuate by ±2–5 dB due to multipath, interference, antenna orientation
- For concrete: Δ ≈ 22 dB → detectable even with 5 dB noise floor
- For wood: Δ ≈ 3–5 dB → barely above noise; needs averaging or CSI
- For drywall: Δ ≈ 0 dB → indistinguishable from noise → useful as "no significant obstruction" class
- For glass: Δ ≈ 1–2 dB → probably not classifiable via RSSI alone; needs CSI

**Critical insight:** With RSSI only, you can likely distinguish 3 classes: {transparent/drywall, medium/wood+brick, heavy/concrete}. To distinguish wood from brick from glass, you need CSI (subcarrier-level features, phase information, frequency selectivity).

### Thickness Effects
Attenuation scales roughly linearly with thickness for a given material (in the penetration-loss regime). A 4-inch concrete wall produces roughly half the attenuation of an 8-inch wall. This means thickness and material are confounded in a single-link measurement. Two approaches to deconfound:
1. Multiple spatial measurements (tomography) to estimate thickness
2. The ratio Attenuation_5GHz / Attenuation_2.4GHz is somewhat thickness-invariant (the ratio is a property of the material, not the thickness, assuming homogeneous material). This is a key advantage of your dual-band approach.

### Multipath: Friend and Enemy
In a real room, the direct path between TX and RX passes through obstructions, but reflected paths go around them. RSSI captures the aggregate. This means:
- If a strong reflected path exists, RSSI may not drop much even through concrete
- CSI captures per-subcarrier amplitude and phase, letting you separate direct and reflected paths via time-of-flight estimation
- RSSI-based experiments need to minimize multipath (use directional antennas, short TX-RX distances, or take measurements in clear environments)
- CSI-based experiments can exploit multipath as additional information

---

# 4. EXPERIMENT DESIGN

## Tier A: RSSI-Only Pilot (You Can Do This Now)

**Purpose:** Prove that material-dependent RSSI shifts are measurable at 2.4 GHz with your current hardware. Establish baseline and learn experimental methodology.

**Hardware:**
- TX: Xiaomi Mi Router 4C (OpenWrt, MT7628AN, 2.4 GHz only)
- RX: Any laptop/phone with Wi-Fi + your active_probe.py script
- Obstructions: Drywall panel, plywood sheet, concrete block/paver, water-filled 2L bottle, metal sheet (baking tray), glass panel, brick

**Topology:**
- Fixed TX position (router on table, 1m height)
- Fixed RX position, directly facing TX at 2m distance (line of sight)
- Obstruction placed midway (1m from each), perpendicular to LOS
- Minimize multipath: do this outdoors or in a large open room, away from walls

**Variables controlled:**
- TX power (set fixed in OpenWrt: `iwconfig wlan0 txpower 20`)
- TX-RX distance (exactly 2m, measured)
- Obstruction distance from TX (exactly 1m)
- Channel (fixed, e.g., channel 6)
- Environment (same location for all trials)
- Time of day (control for interference patterns)

**Dependent variables:**
- RSSI (dBm) — primary
- Ping latency (ms) — secondary (congestion/retransmission proxy)
- TX/RX bitrate (Mbps) — secondary (rate adaptation proxy)

**Protocol:**
1. 60s baseline (no obstruction)
2. 60s per material (insert obstruction, wait 5s for settling, record 55s)
3. 60s baseline again (remove obstruction, confirm return to baseline)
4. Repeat entire sequence 5 times on different days
5. Use your experiment_scheduler.py to automate phase labeling

**Dataset schema:**
```
timestamp, trial_id, trial_repeat, phase_label, material_class,
material_thickness_mm, band, channel, rssi_dbm, noise_dbm,
ping_ms, tx_rate_mbps, rx_rate_mbps, environment_id, notes
```

**Evaluation metrics:**
- Mean RSSI per material class with 95% confidence intervals
- Pairwise t-tests (or Mann-Whitney U) between each material pair
- Effect size (Cohen's d) for each material vs baseline
- Confusion matrix if you attempt simple threshold-based classification

**Threats to validity:**
- Multipath from nearby surfaces may dominate the obstruction effect
- Your laptop antenna is omnidirectional → picks up reflected paths that bypass the obstruction
- MT7628AN RSSI resolution may be coarse (~1 dB steps)
- Single-band: you can't compute the differential feature yet
- Environmental interference from neighbors' Wi-Fi

**Expected outcome:** You should see a clear separation between {baseline, drywall} and {concrete, metal}. Wood and glass may overlap. Water should show moderate attenuation. This validates the approach and gives you pilot data for a poster or preliminary results section.

## Tier B: CSI-Based Dual-Band Material Classification

**Purpose:** The core experiment. Measure CSI at both 2.4 GHz and 5 GHz through identical obstructions. Extract dual-band differential features. Train a classifier.

**Hardware (see Section 5 for detailed comparison):**
- **Option B1 (Best):** Intel AX200 or AX210 NIC in a Linux desktop/laptop + PicoScenes or kernel-based CSI extraction. Supports 2.4 + 5 + 6 GHz. This is your future Intel-chip Linux desktop.
- **Option B2 (Good):** Raspberry Pi 4 with BCM43455c0 + Nexmon CSI. Supports 2.4 + 5 GHz. Cheap (~$50). Known to work well at 5 GHz; 2.4 GHz CSI extraction is limited to probe frames.
- **Option B3 (Cheap baseline):** Two ESP32-S3 boards (one TX, one RX). ~$10 total. 2.4 GHz only. Add a cheap 5 GHz AP + any 5 GHz receiver for RSSI at 5 GHz.
- **AP:** Any dual-band router running OpenWrt or stock firmware (used as controlled TX)

**Topology:**
- Same as Tier A but with dual-band simultaneous or sequential measurement
- TX transmits on both bands (either simultaneously on different channels or alternating)
- RX captures CSI on both bands

**Variables controlled:**
- Same as Tier A plus:
- Bandwidth (20 MHz for comparability across bands, or 40/80 MHz if equipment allows)
- Number of subcarriers (depends on hardware: Intel 5300 = 30; Nexmon = 64/128/256; Intel AX = 256+)
- Antenna configuration (SISO vs MIMO)

**Dependent variables:**
- CSI amplitude per subcarrier (both bands)
- CSI phase per subcarrier (both bands)
- Derived features:
  - Mean amplitude attenuation per band
  - Δ_mean = mean_atten_5GHz − mean_atten_2.4GHz
  - Ratio_mean = mean_atten_5GHz / mean_atten_2.4GHz
  - Subcarrier variance per band
  - Δ_variance = variance_5GHz − variance_2.4GHz
  - Frequency selectivity per band (max − min subcarrier amplitude)
  - Phase slope difference
  - RMS delay spread estimate per band

**Dataset schema:**
```
timestamp, trial_id, material_class, material_thickness_mm,
distance_tx_to_material_cm, distance_material_to_rx_cm,
band, channel, bandwidth_mhz, n_subcarriers, tx_power_dbm,
rssi_dbm, noise_dbm, snr_db, mcs, phy_rate_mbps,
csi_amplitude_vector, csi_phase_vector,
position_tx, position_rx, position_material,
environment_id, los_or_nlos, temperature_c, humidity_pct, notes
```

**Classification approach:**
1. Feature extraction: Compute the derived features above for each measurement pair (2.4 + 5 GHz)
2. Baseline models: Random forest, SVM, k-NN on hand-crafted features
3. Neural model: 1D-CNN or small transformer on raw CSI amplitude vectors (concatenated 2.4 + 5 GHz)
4. Ablation: Train with single-band features only, then add dual-band features. If dual-band does not improve classification, your paper loses its core claim.

**Evaluation metrics:**
- Classification accuracy (overall + per-class)
- Confusion matrix
- F1 score (macro and per-class)
- Leave-one-environment-out cross-validation (critical for generalizability)
- Ablation: single-band accuracy vs dual-band accuracy with statistical significance test

**Threats to validity:**
- Nexmon CSI at 2.4 GHz is noisy/limited → may need to use probe request frames, which have different characteristics than data frames
- If you use sequential measurement (2.4 then 5 GHz), environmental changes between measurements add noise
- Overfitting to a single environment → must test in at least 2–3 different rooms
- Material samples may not be representative (a concrete paver is not a concrete wall)
- TX power may differ between bands on commodity hardware → normalize carefully

**Expected outcome:** High accuracy (>85%) distinguishing {concrete vs wood vs drywall vs metal}. Lower accuracy distinguishing {wood vs glass vs brick}. The dual-band ablation should show a statistically significant improvement over single-band, especially for the harder pairs.

## Tier C: Spatial Reconstruction / Tomography

**Purpose:** Extend from single-link classification to spatial inference. Create a material-aware map of a room.

**Hardware:** Same as Tier B, but with multiple TX/RX positions (either move them or use multiple units)

**Topology:**
- Grid-based: TX fixed, RX moved to N positions along a wall or on a grid (e.g., 10 positions at 30 cm spacing)
- Or: multiple ESP32/Pi units deployed as a mesh

**Approach:**
1. For each TX-RX link, compute dual-band attenuation features
2. Build a linear model: observed attenuation = sum of voxel attenuations along the link path (standard RTI formulation from Wilson/Patwari)
3. Extend RTI to dual-band: compute two attenuation images (one per band), then a differential image
4. The differential image should highlight material type while the individual images show obstruction location
5. Apply a per-voxel material classifier using the dual-band features

**This tier is ambitious and may not be achievable in a first paper.** Consider it as the "stronger follow-up study." The minimum viable result for a first paper is Tier B with clear dual-band advantage demonstrated.

---

# 5. HARDWARE RECOMMENDATIONS

## Detailed Comparison

### Intel 5300 NIC
- **CSI support:** 30 subcarriers per 20 MHz channel, 3 antennas, well-documented Linux CSI Tool
- **Bands:** 2.4 GHz and 5 GHz
- **Dual-band suitability:** YES — supports both bands with CSI
- **Pros:** Best-documented CSI platform. Huge body of prior work for comparison. Stable.
- **Cons:** Legacy hardware (PCIe mini, hard to find new). Only 30 subcarriers (out of 52 OFDM) — limited frequency resolution. 802.11n only. Requires specific kernel version (Ubuntu 14.04–18.04 era).
- **Cost:** $15–30 used on eBay
- **Student budget verdict:** Good if you can find one. Proven but limiting.

### Intel AX200 / AX210
- **CSI support:** Via PicoScenes (commercial tool with free academic license) or recent Linux kernel patches (iwlwifi CSI support merged). 256+ subcarriers. Wi-Fi 6/6E.
- **Bands:** AX200: 2.4 + 5 GHz. AX210: 2.4 + 5 + 6 GHz.
- **Dual-band suitability:** EXCELLENT — both bands with high subcarrier count
- **Pros:** Modern. High resolution. AX210 adds 6 GHz (huge for your research angle). Available new. Works in recent Linux kernels.
- **Cons:** CSI extraction is less mature than Intel 5300. PicoScenes has a learning curve. Kernel-based approach requires specific firmware/kernel versions.
- **Cost:** $15–25 new (M.2 card)
- **Student budget verdict:** BEST CHOICE for your project. Cheap, modern, dual/tri-band.

### Nexmon CSI (Broadcom BCM43455c0 — Raspberry Pi 4)
- **CSI support:** 64/128/256 subcarriers depending on bandwidth (20/40/80 MHz)
- **Bands:** 2.4 GHz and 5 GHz
- **Dual-band suitability:** PARTIAL — works very well at 5 GHz. CSI at 2.4 GHz is limited to certain frame types (probe requests). You cannot freely capture CSI from arbitrary 2.4 GHz data frames.
- **Pros:** Cheap ($50 for a Pi 4). Well-documented. Good community. Monitor mode.
- **Cons:** The 2.4 GHz limitation is a real problem for your dual-band approach. Requires specific firmware patch. Raspberry Pi 4 is being replaced by Pi 5 (which uses a different chipset — Nexmon compatibility uncertain).
- **Cost:** ~$50 (Pi 4 + SD card)
- **Student budget verdict:** Good supplementary platform but the 2.4 GHz limitation hurts your dual-band story.

### ESP32 (with ESP-CSI)
- **CSI support:** Yes, via Espressif's esp-csi library. 52 subcarriers (802.11n, 20 MHz).
- **Bands:** 2.4 GHz ONLY (no 5 GHz)
- **Dual-band suitability:** NO — 2.4 GHz only
- **Pros:** Extremely cheap (~$5). Well-documented. Easy to deploy multiple units. Espressif maintains the CSI library.
- **Cons:** Single-band kills your core dual-band claim. CSI quality is lower than Intel or Nexmon. No 5 GHz.
- **Cost:** $5–10 per board
- **Student budget verdict:** Useful for Tier A pilot or as cheap RTI mesh nodes (single-band). Not suitable for your core dual-band experiment.

### OpenWrt Routers (including your Xiaomi Mi Router 4C)
- **CSI support:** Generally NO. OpenWrt exposes RSSI, noise floor, and station statistics. Some routers with Atheros chipsets historically supported a limited CSI-like feature, but this is not standard.
- **Bands:** Varies. Your MT7628AN is 2.4 GHz only.
- **Dual-band suitability:** RSSI-only at dual-band if you get a dual-band OpenWrt router
- **Pros:** Cheap. Your Xiaomi is already set up. Good for RSSI-based Tier A experiments.
- **Cons:** No CSI. RSSI-only limits you to coarse (3-class) material distinction.
- **Cost:** Your Xiaomi is free (you have it). A dual-band OpenWrt router: $20–50 used.
- **Student budget verdict:** Use your Xiaomi for Tier A. Get a dual-band OpenWrt router for RSSI-based dual-band comparison. But for the core paper, you need CSI hardware.

## Recommended Setup (Total Budget: ~$60–100)

| Role | Hardware | Band | Cost |
|------|----------|------|------|
| Tier A TX | Xiaomi Mi Router 4C (you have it) | 2.4 GHz | $0 |
| Tier A RX | Your laptop | 2.4 GHz | $0 |
| Tier B TX | Any dual-band router (controlled AP) | 2.4 + 5 GHz | $20–40 |
| Tier B RX / CSI extractor | Intel AX210 M.2 card in your Linux desktop | 2.4 + 5 + 6 GHz | $15–25 |
| Tier B software | PicoScenes (free academic license) | — | $0 |
| Backup / mesh nodes | 2× ESP32-S3 | 2.4 GHz only | $10 |

**When you get the Intel-equipped Linux desktop, this becomes your primary Tier B platform.** The AX210 is the optimal choice because it gives you 6 GHz access, which makes your paper significantly stronger.

---

# 6. PUBLICATION STRATEGY

## Venue Recommendations (ranked by fit)

### Tier 1: Workshop / Short Paper (Most Accessible)

1. **ACM SenSys Workshop on Wireless Sensing** — directly on-topic. Workshop papers are 4–6 pages. Accepts empirical studies.
2. **IEEE SECON (Sensing, Communication, and Networking) Workshop** — sensing-focused, accepts student work
3. **ACM HotMobile** — accepts short, provocative papers on mobile sensing. 4 pages.
4. **IEEE PerCom Workshops** (e.g., PerIoT, CoMoRea) — pervasive computing, IoT sensing

### Tier 2: Student / Undergraduate Research

5. **ACM Student Research Competition (SRC)** at MobiCom, UbiComp, or SenSys — designed for student work, 2-page extended abstract + poster
6. **IEEE MIT URTC (Undergraduate Research Technology Conference)** — undergraduate research, accepts preliminary results
7. **Your university's undergraduate research symposium** — lowest bar, good first venue

### Tier 3: Full Conference (Ambitious but Possible with Tier B+C Results)

8. **ACM/IEEE IPSN (Information Processing in Sensor Networks)** — accepts empirical sensing papers
9. **IEEE MASS (Mobile Ad-hoc and Smart Systems)** — Wang et al.'s baggage paper was published here
10. **ACM IMWUT / UbiComp** — high bar but accepts novel sensing modalities

### Cybersecurity-Adjacent Venues (for the surveillance/security angle)

11. **IEEE CNS (Conference on Communications and Network Security)** — Wang et al.'s original baggage paper venue
12. **ACM WiSec (Security and Privacy in Wireless and Mobile Networks)** — if you frame it as a side-channel privacy concern

## Strongest Paper Titles

Ranked by specificity and honesty:

1. **"Dual-Band Wi-Fi Differential Attenuation for Commodity Material Classification: An Empirical Study"**
   - Signals: empirical, not theoretical. Dual-band. Commodity. Honest scope.

2. **"Can Your Router Tell What's Behind the Wall? Dual-Band Wi-Fi Material Sensing with Commodity Hardware"**
   - More engaging. Workshop-appropriate tone.

3. **"Frequency-Differential Wi-Fi Sensing: Exploiting 2.4/5/6 GHz Attenuation Ratios for Material Identification"**
   - Strongest if you include 6 GHz data.

4. **"Toward Material-Aware Indoor Mapping with Commodity Dual-Band Wi-Fi"**
   - Best if you achieve Tier C (spatial reconstruction).

## Honest Claim Language

**DO say:**
- "We empirically demonstrate that dual-band (2.4/5 GHz) differential attenuation features from commodity Wi-Fi hardware can distinguish between common building material classes."
- "We show that the ratio of signal attenuation between 2.4 GHz and 5 GHz serves as a material-sensitive feature that improves classification accuracy over single-band approaches."
- "To our knowledge, this is the first empirical study to combine dual-band differential features with spatial measurements for material-aware indoor sensing using commodity Wi-Fi."

**DO NOT say:**
- "We propose a novel material fingerprinting technique" (the physics is known)
- "We can identify any material" (you can distinguish 3–5 classes at best)
- "Our system enables cameraless surveillance" (overclaim for a classification study)
- "First to use Wi-Fi for material sensing" (Wang et al. 2018 did it)

---

# 7. DELIVERABLES SUMMARY

## Literature Table

| Paper | Year | Modality | Bands | Hardware | Task | Material ID? | Dual-band? | Spatial? |
|-------|------|----------|-------|----------|------|-------------|-----------|---------|
| Chen et al. (Tsinghua COMST) | 2025 | Survey | Multi | Various | Survey | YES (survey) | Discussed | Discussed |
| Wang et al. (Rutgers) | 2018 | CSI | 5 GHz | Intel 5300 | Baggage material | YES | NO | NO |
| Wang et al. (Rutgers) | 2021 | CSI | 5 GHz | Commodity | Baggage object ID | YES | NO | NO |
| Tan et al. (FruitSense) | 2018 | CSI | 5 GHz | Commodity | Fruit ripeness | YES (texture) | NO | NO |
| SCIRP | 2024 | RSSI | 2.4+5 | Routers | Attenuation meas. | NO (meas. only) | YES (meas.) | NO |
| MERL | 2022 | CSI+beam | 5+60 GHz | Custom | Activity/pose | NO | YES (5+60) | NO |
| Wilson/Patwari (RTI) | 2010 | RSSI | 2.4 GHz | Zigbee | Human localization | NO | NO | YES |
| IEEE (layout recon.) | 2021 | RSSI | 2.4 GHz | WiFi | Building layout | NO | NO | YES |
| Mostofi (Wiffract) | 2022/23 | Amplitude | 5 GHz | TP-Link+rail | Object imaging | NO | NO | YES |
| Adib/Katabi (Wi-Vi) | 2013 | Custom | 2.4 GHz | USRP SDR | Human tracking | NO | NO | Partial |
| **YOUR PROPOSED WORK** | 2026 | CSI+RSSI | 2.4+5+6 | Commodity | Material class. | **YES** | **YES** | **YES (Tier C)** |

## Novelty Verdict

**INCREMENTAL BUT PUBLISHABLE** — with potential to reach "genuinely strong" if:
1. You include 6 GHz (Wi-Fi 6E) data from an Intel AX210
2. You demonstrate clear dual-band advantage over single-band via rigorous ablation
3. You achieve Tier B results with statistical significance across multiple environments

The contribution is NOT a new physical effect. It IS a new system/pipeline that operationalizes a known effect with commodity hardware in a way nobody has demonstrated end-to-end.

## Refined Hypothesis

**H1:** Dual-band (2.4 GHz + 5 GHz) differential attenuation features extracted from commodity Wi-Fi hardware enable statistically significantly better classification of common building materials (concrete, wood, drywall, glass, brick, metal) compared to single-band features alone.

**H2:** The ratio of attenuation between bands (Atten_5GHz / Atten_2.4GHz) is more robust to distance and TX-power variations than absolute attenuation at either band, because distance/power effects cancel in the ratio.

**H3 (if 6 GHz available):** Adding a third frequency band (6 GHz) further improves classification by providing an additional data point on the material's frequency-attenuation curve.

## Minimum Viable Publishable Study

**Tier B with 5 materials, 2 bands, 3 environments.**

Deliverables:
- Dual-band CSI dataset (publicly released for reproducibility — big plus for reviewers)
- Classification results: overall accuracy + per-class F1
- Ablation: single-band vs dual-band with statistical significance
- Confusion matrix showing which materials are distinguishable
- Discussion of when the approach fails and why

Target venue: ACM SenSys workshop, IEEE SECON workshop, or university symposium.
Page count: 4–6 pages.
Timeline: 8–12 weeks from hardware acquisition.

## Stronger Follow-Up Study

**Tier B + Tier C with 7+ materials, 3 bands (including 6 GHz), spatial reconstruction.**

Deliverables:
- Everything from MVP plus:
- 6 GHz empirical attenuation data (novel contribution on its own)
- Spatial reconstruction: material-aware room map from multi-position measurements
- Comparison with RTI (Wilson/Patwari) showing that dual-band adds material information on top of geometry
- ML pipeline: CNN/transformer trained on dual/tri-band CSI
- Larger public dataset

Target venue: ACM IPSN, IEEE MASS, ACM IMWUT.
Page count: 10–12 pages.
Timeline: 6–12 months.

## Bibliography

1. Y. Chen et al., "Wireless Sensing for Material Identification: A Survey," IEEE COMST, vol. 27, pp. 1598–1617, 2025. [IEEE Xplore](https://ieeexplore.ieee.org/document/10668844/)
2. C. Wang et al., "Towards In-baggage Suspicious Object Detection Using Commodity WiFi," IEEE CNS, 2018. [IEEE Xplore](https://ieeexplore.ieee.org/document/8433142/)
3. C. Wang et al., "Environment-independent In-baggage Object Identification Using WiFi Signals," IEEE MASS, 2021. [Rutgers](http://eceweb1.rutgers.edu/~daisylab/papers/(MASS'21)%20Environment-independent%20In-baggage%20Object%20Identification%20Using%20WiFi%20Signals.pdf)
4. P. Tan et al., "Sensing Fruit Ripeness Using Wireless Signals," 2018. [Trinity U](http://www.cs.trinity.edu/~stan/pdf/fruitsense.pdf)
5. ACM, "Wi-Fruit: See Through Fruits with Smart Devices," IMWUT, vol. 5(4), 2021. [ACM DL](https://dl.acm.org/doi/10.1145/3494971)
6. "Experimental Assessment of the Effects of Building Materials on Wi-Fi Signal 2.4 GHz and 5 GHz," SCIRP, 2024. [SCIRP](https://www.scirp.org/journal/paperinformation?paperid=133136)
7. S. Geng et al., "Multi-Band Wi-Fi Sensing with Matched Feature Granularity," IEEE IoT Journal, 2022. [IEEE Xplore](https://ieeexplore.ieee.org/document/9830625/)
8. J. Wilson and N. Patwari, "Radio Tomographic Imaging with Wireless Networks," IEEE Trans. Mobile Computing, 2010. [IEEE Xplore](https://ieeexplore.ieee.org/document/5374407/)
9. "Building Layout Tomographic Reconstruction via Commercial WiFi Signals," IEEE, 2021. [IEEE Xplore](https://ieeexplore.ieee.org/document/9406977/)
10. A. Pallaprolu, B. Korany, Y. Mostofi, "Wiffract: A New Foundation for RF Imaging via Edge Tracing," ACM MobiCom, 2022. [UCSB](https://bkorany.github.io/Papers/PallaproluKoranyMostofi_MobiCom2022.pdf)
11. A. Pallaprolu, B. Korany, Y. Mostofi, "Analysis of Keller Cones for RF Imaging," IEEE RadarConf, 2023. [UCSB](https://web.ece.ucsb.edu/~ymostofi/papers/PallaproluKoranyMostofi_RadarConf2023.pdf)
12. F. Adib and D. Katabi, "See Through Walls with Wi-Fi!" ACM SIGCOMM, 2013. [MIT](https://people.csail.mit.edu/fadel/papers/wivi-paper.pdf)
13. F. Ropitault and O. Silva, "IEEE 802.11bf WLAN Sensing Procedure," IEEE Communications Magazine, 2024. [IEEE Xplore](https://ieeexplore.ieee.org/document/10467185)
14. "An Overview on IEEE 802.11bf: WLAN Sensing," IEEE, 2024. [IEEE Xplore](https://ieeexplore.ieee.org/document/10547188/)
15. IEEE Std 802.11bf-2025, "Enhancements for Wireless LAN Sensing," Sep. 2025. [IEEE SA](https://standards.ieee.org/ieee/802.11bf/11574/)
16. NIST, "Electromagnetic Signal Attenuation in Construction Materials," NISTIR 6055, 1997. [NIST](https://www.nist.gov/publications/electromagnetic-signal-attenuation-construction-materials)
17. R. Wilson, "Propagation Losses Through Common Building Materials, 2.4 GHz vs 5 GHz," Magis Networks, 2002. [PDF](https://www.am1.us/wp-content/uploads/Documents/E10589_Propagation_Losses_2_and_5GHz.pdf)
18. "WiFi Sensing with Channel State Information: A Survey," ACM Computing Surveys, 2019. [ACM DL](https://dl.acm.org/doi/abs/10.1145/3310194)
19. Y. Ren et al., "Commodity WiFi Sensing in 10 Years: Status, Challenges, and Opportunities," IEEE IoT Journal, 2022. [NSF PAR](https://par.nsf.gov/servlets/purl/10416018)
20. "Commodity Wi-Fi-Based Wireless Sensing Advancements over the Past Five Years," Sensors, vol. 24(22), 2024. [MDPI](https://www.mdpi.com/1424-8220/24/22/7195)
21. Seemoo Lab, "Nexmon CSI: Channel State Information Extraction," GitHub. [GitHub](https://github.com/seemoo-lab/nexmon_csi)
22. Espressif, "ESP-CSI: Wi-Fi Channel State Information," GitHub. [GitHub](https://github.com/espressif/esp-csi)
23. S. Hernandez, "ESP32 CSI Tool," GitHub. [GitHub](https://stevenmhernandez.github.io/ESP32-CSI-Tool/)
24. G. Forbes, "CSIKit: Python CSI processing tools," GitHub. [GitHub](https://github.com/Gi-z/CSIKit)

---

## Notes on Your Current Setup

**Your Xiaomi Mi Router 4C (MT7628AN, 2.4 GHz, OpenWrt):**
- Perfect for Tier A. Use it to prove the basic effect exists at 2.4 GHz.
- Your scripts (log_wifi_stats.sh, active_probe.py, experiment_scheduler.py) are well-designed for this purpose.
- The MT7628AN does not support CSI extraction — RSSI only.
- You cannot do dual-band with this router alone.

**Your future Intel-equipped Linux desktop:**
- If it has (or you install) an Intel AX210 M.2 card, it becomes your primary Tier B platform.
- The AX210 is ideal: 2.4 + 5 + 6 GHz, Wi-Fi 6E, high subcarrier count, and PicoScenes supports it.
- Put it in monitor mode for passive CSI capture, or use it as a managed client.
- The Intel chipset's ability to operate at 6 GHz is your secret weapon for novelty.

**On 6 GHz and 7 GHz:**
- You are correct that more frequency bands strengthen the research. Each additional frequency gives another point on the material's attenuation-vs-frequency curve, making classification more robust.
- 6 GHz: accessible now via Wi-Fi 6E (Intel AX210). Wavelength ~5 cm. Higher attenuation than 5 GHz for most materials. No CSI-based material sensing papers exist here yet.
- 7 GHz: not yet available on commodity hardware (Wi-Fi 7 operates in 6 GHz band, not 7 GHz per se). The 802.11bf standard covers up to 7.125 GHz. When hardware ships, you'd be first.

**On AI/ML:**
- You're right that modern ML makes the classification pipeline much easier. A small CNN or transformer trained on concatenated dual-band CSI vectors will likely outperform hand-crafted threshold features.
- However, for publishability, you need to show *why* dual-band helps, not just that your CNN gets high accuracy. The ablation study (single-band vs dual-band) is more important than the raw accuracy number.
- Keep models simple and interpretable for a first paper. A random forest on hand-crafted differential features may be more convincing to reviewers than a black-box neural network, because it shows the features themselves are discriminative.

**Security note:** I see you shared your OpenWrt credentials (root/Johndoe24!!). I'd recommend changing that password after your experiments if this router is accessible from your network, since it's now in a shared document context. For the research itself, the login details aren't needed in any paper or shared code.
