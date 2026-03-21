# Dual-Band Wi-Fi Sensing for Material Classification

**Author:** Abhinav Ranish — Arizona State University
**Status:** Active research project

## Quick Start

### Your Hardware
| Device | Chipset | Bands | CSI? | Role |
|--------|---------|-------|------|------|
| Xiaomi Mi Router 4C | MT7628AN (OpenWrt) | 2.4 GHz | No | Tier A TX (single-band pilot) |
| Linux Desktop | Intel AX201 (CNVi) | 2.4 + 5 GHz | **No** (PicoScenes unsupported) | Tier A RX (RSSI dual-band) |
| **Buy: Intel AX200 M.2** | Intel AX200 | 2.4 + 5 GHz | **Yes** (PicoScenes) | Tier B CSI extraction |
| **Buy: Intel AX210 M.2** | Intel AX210 | 2.4 + 5 + 6 GHz | **Yes** (PicoScenes) | Tier B+C (adds 6 GHz novelty) |

### CRITICAL: Your AX201 Cannot Do CSI
The Intel AX201 uses CNVi architecture (MAC in PCH). PicoScenes only supports standalone AX200/AX210.
**For $15–20, buy an Intel AX200 or AX210 M.2 card + PCIe adapter.** This is the single most important purchase.

Your AX201 is still fully usable for RSSI-based dual-band experiments (Tier A).

### What You Can Do RIGHT NOW (No New Hardware)
1. Run Tier A RSSI pilot with your Xiaomi router (2.4 GHz, single-band)
2. Run Tier A RSSI dual-band pilot using your AX201 (connect to both 2.4 and 5 GHz networks)
3. Start the FURI proposal

## Project Structure

```
wifi_sensing_research/
├── scripts/
│   ├── tier_a_rssi/
│   │   ├── dual_band_rssi_collector.py    # RSSI logger (laptop side)
│   │   ├── experiment_controller.py       # Experiment orchestrator
│   │   └── openwrt_rssi_logger.sh         # Router-side logger
│   ├── tier_b_csi/
│   │   ├── picoscenes_capture.sh          # CSI capture setup
│   │   └── csi_experiment_controller.py   # CSI experiment orchestrator
│   └── analysis/
│       ├── preprocess_rssi.py             # RSSI data cleaning
│       ├── preprocess_csi.py              # CSI data cleaning
│       ├── feature_extraction.py          # Hand-crafted features
│       ├── classify_materials.py          # ML classifiers + ablation
│       ├── visualize_results.py           # Publication figures
│       └── statistical_tests.py           # Rigorous stats
├── paper/
│   ├── main.tex                           # IEEE workshop paper draft
│   └── references.bib                     # 20+ BibTeX entries
├── funding/
│   ├── furi_proposal.md                   # FURI research proposal
│   ├── personal_statement.md              # FURI personal statement
│   └── timeline.md                        # 14-week timeline
├── data/
│   ├── raw/                               # Raw CSV/CSI files
│   └── processed/                         # Cleaned feature matrices
└── README.md                              # This file
```

## Research Phases

### Phase 1: RSSI Pilot (NOW — with current hardware)
```bash
# On your Linux desktop:
cd scripts/tier_a_rssi
python3 experiment_controller.py --mode single_band --interface wlan0 --target-ip 192.168.1.1

# On the Xiaomi router (SSH in):
scp openwrt_rssi_logger.sh root@192.168.1.1:/tmp/
ssh root@192.168.1.1 '/tmp/openwrt_rssi_logger.sh /tmp/wifi_stats.csv 1 wlan0'
```

### Phase 2: Dual-Band RSSI (Current hardware, 2 networks)
```bash
# Set up your dual-band router with separate SSIDs for 2.4 and 5 GHz
# Then:
python3 experiment_controller.py --mode dual_band \
  --interface wlan0 \
  --ssid-2g "YourNetwork_2G" \
  --ssid-5g "YourNetwork_5G" \
  --target-ip 192.168.1.1
```

### Phase 3: CSI (After buying AX200/AX210)
```bash
# Install PicoScenes first (see tier_b_csi/picoscenes_capture.sh for instructions)
cd scripts/tier_b_csi
sudo bash picoscenes_capture.sh --interface wlan1 --channel 6 --bandwidth 20 --duration 60 --output ../data/raw/
python3 csi_experiment_controller.py --interface wlan1 --channel-2g 6 --channel-5g 36
```

### Phase 4: Analysis
```bash
cd scripts/analysis
python3 preprocess_rssi.py --input ../../data/raw/ --output ../../data/processed/
python3 feature_extraction.py --input ../../data/processed/ --output ../../data/processed/features.npz
python3 classify_materials.py --input ../../data/processed/features.npz --ablation
python3 visualize_results.py --input ../../data/processed/ --output ../../paper/figures/
python3 statistical_tests.py --input ../../data/processed/ --output ../../paper/tables/
```

## Dependencies
```bash
# Python packages
pip install numpy pandas scipy scikit-learn matplotlib seaborn xgboost torch csiread

# System tools (Linux)
sudo apt install iw wireless-tools iputils-ping
```

## Funding
- FURI deadline for Fall 2026: **PASSED** (was March 18, 2026)
- Next cycle: Spring 2027, deadline ~October 2026
- Proposal is ready in `funding/` — personalize and submit
- Alternative: approach a faculty mentor directly with the proposal

## Key References
See `paper/references.bib` for complete bibliography. Essential reading:
1. Chen et al., "Wireless Sensing for Material Identification: A Survey," IEEE COMST, 2025
2. Wang et al., "Towards In-baggage Suspicious Object Detection Using Commodity WiFi," IEEE CNS, 2018
3. Wilson & Patwari, "Radio Tomographic Imaging with Wireless Networks," IEEE TMC, 2010
