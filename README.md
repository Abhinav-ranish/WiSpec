# WiSpec — Commodity Tri-Band Wi-Fi 6E Spectroscopy for Material Classification and Structural Reconnaissance

**Author:** Abhinav Ranish — Arizona State University
**Status:** Active research project — seeking $4,000 in hardware sponsorship

## Looking for Sponsors — $4,000

WiSpec is looking for **$4,000 in sponsorship** to build the full tri-band
capture rig: a capture tower PC, storage, Intel AX210 receivers, 6 GHz
antennas, a Wi-Fi 7 router, a depth camera for training labels, and traffic
clients. Model training is already covered by AWS credits. The itemized
budget is in [hardware/BOM.md](hardware/BOM.md#sponsorship-budget--4000).

Sponsors will be acknowledged in the repository and in resulting publications. To sponsor or donate hardware, reach out: chatgpt@asu.edu

### Open to Collaborators

This is an active research project and we're looking for collaborators — whether you're into wireless systems, signal processing, machine learning, or just curious about RF sensing. If you want to contribute or discuss ideas, reach out: chatgpt@asu.edu

### Tactical Applications

WiSpec enables several practical applications across different domains:
- **Building Reconnaissance:** Using Wi-Fi reflections to characterize interior layouts, wall composition, and structural elements without visual access
- **Search and Rescue:** Rapid structural assessment to identify building composition, floor materials, and potential hazards during emergency operations
- **Smart Building Automation:** Material-aware building systems that adapt HVAC, lighting, and comfort systems based on wall and floor composition

### Tier C: Room Mapping & Point-and-Say Automation (new)

WiSpec is growing from material classification into a room-scale sensor:
**where people are, what pose they're in, and what they're pointing at**,
using only the home's Wi-Fi at runtime. The goal is home automation without
extra sensors: point at the TV and say "play that". See
[docs/VISION.md](docs/VISION.md) for the architecture, milestones and honest
limitations, and [hardware/BOM.md](hardware/BOM.md) for the recommended rig
(3x Intel AX210 for concurrent 2.4/5/6 GHz capture, tri-band AP, Orbbec
Femto Bolt depth camera as the training teacher). An optional 4th band at the
top of 6 GHz (~7 GHz) is in `configs/rig_quad_band.json`. Training runs on AWS
SageMaker spot instances, launched by hand or by agents via GitHub Actions; see
[cloud/aws/README.md](cloud/aws/README.md).

The approach follows camera-supervised Wi-Fi imaging (WiFiCam, Strohmayer et
al., ICIP 2024): a depth camera labels training data, a frame autoencoder
compresses each frame to 32 numbers, and a tri-band 1D-CNN learns to predict
those numbers, 3D body joints and presence from 1.5 s of CSI. The camera is
not used at inference.

```bash
pip install -e ".[train,dev]"
python -m pytest                          # unit + end-to-end smoke tests
# Full pipeline on synthetic data (no hardware needed):
python -m wispec.train synth  --out data/synth --sessions 8 --seconds 150
python -m wispec.train stage1 --data data/synth --run runs/synth
python -m wispec.train stage2 --data data/synth --run runs/synth
python -m wispec.train eval   --data data/synth --run runs/synth --room configs/room_example.json
# On the rig:
python -m wispec.capture.session --out data/sessions/walk_01 --duration 600 --activity walking --convert
```

## Quick Start

### Your Hardware

> For Tier C (room mapping / pointing), use the multi-NIC rig in
> [hardware/BOM.md](hardware/BOM.md) instead of a single adapter.

| Device | Chipset | Bands | CSI? | Role |
|--------|---------|-------|------|------|
| Wi-Fi 6E Tri-Band AP | Any 6E router | 2.4 + 5 + 6 GHz | No | Tier A TX (tri-band beacons) |
| Linux Desktop | Intel AX210/AX211 | 2.4 + 5 + 6 GHz | **Yes** (PicoScenes) | Tier A RX (RSSI) / Tier B (CSI) |
| **Recommended: Intel AX210 M.2** | Intel AX210 | 2.4 + 5 + 6 GHz | **Yes** (PicoScenes) | Full tri-band CSI extraction |

### CRITICAL: You Need Wi-Fi 6E Hardware
The research now requires **tri-band (2.4 + 5 + 6 GHz)** support. The Intel AX210/AX211 is the recommended adapter — it supports all three bands with PicoScenes CSI extraction. The 6 GHz band (UNII-5 through UNII-8, 5.925–7.125 GHz) provides up to 996 subcarriers on 160 MHz channels.

Older dual-band adapters (AX200/AX201) can still be used for 2.4 + 5 GHz experiments but miss the 6 GHz band.

### What You Can Do RIGHT NOW
1. Run Tier A RSSI tri-band pilot with a Wi-Fi 6E router and AX210/AX211
2. Run dual-band subset experiments with older hardware
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
├── wispec/                               # Tier C package (room mapping / pointing)
│   ├── capture/                           # multi-NIC PicoScenes + teacher camera recording
│   ├── data/                              # CSI cleaning, windowing, synthetic sessions
│   ├── models/                            # frame autoencoder + tri-band CSINet
│   ├── room/                              # room map, pointing rays, target resolution
│   ├── automation/                        # intents -> Home Assistant service calls
│   └── train.py                           # train / eval CLI (baseline + band ablation)
├── configs/                               # rig + room map configs
├── hardware/BOM.md                        # recommended hardware
├── docs/VISION.md                         # architecture + milestones
├── tests/                                 # pytest suite
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

### Phase 2: Tri-Band RSSI (Wi-Fi 6E hardware)
```bash
# Set up your Wi-Fi 6E router with separate SSIDs for 2.4, 5, and 6 GHz
# Then:
python3 experiment_controller.py --mode tri_band \
  --interface wlan0 \
  --ssid-2g "YourNetwork_2G" \
  --ssid-5g "YourNetwork_5G" \
  --ssid-6g "YourNetwork_6G" \
  --target-ip 192.168.1.1
```

### Phase 3: CSI (AX210 with PicoScenes)
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

## Citation and Licensing

### License

WiSpec is **source-available under a noncommercial license**. This is NOT open source (not MIT, not Apache, not GPL). You can read, learn from, and use the code for academic research — but commercial use requires a separate paid license. See [LICENSE.md](LICENSE.md) for the full terms and [COMMERCIAL-LICENSING.md](COMMERCIAL-LICENSING.md) for commercial inquiries.

| Use | Allowed? |
|-----|----------|
| Academic research | Yes (with citation) |
| Personal learning | Yes (with attribution) |
| Student thesis | Yes (with citation) |
| Commercial product/service | No — requires paid license |
| For-profit internal use | No — requires paid license |

### How to Cite

If you use WiSpec in your research, please cite both the repository and the paper.

**Repository:**
```
A. Ranish, "WiSpec: Commodity Tri-Band Wi-Fi 6E Spectroscopy for Material
Classification and Structural Reconnaissance," GitHub, 2026.
https://github.com/abhinav-ranish/WiSpec
```

**Paper (update venue/DOI when published):**
```
A. Ranish, "WiSpec: Commodity Tri-Band Wi-Fi 6E Spectroscopy for Material
Classification and Structural Reconnaissance," [Venue TBD], 2026.
```

**BibTeX:**
```bibtex
@software{ranish2026wispec,
  author       = {Ranish, Abhinav},
  title        = {{WiSpec}: Commodity Tri-Band Wi-Fi 6E Spectroscopy for
                  Material Classification and Structural Reconnaissance},
  year         = {2026},
  url          = {https://github.com/abhinav-ranish/WiSpec},
  note         = {Source-available, noncommercial license}
}

@inproceedings{ranish2026wispec_paper,
  author    = {Ranish, Abhinav},
  title     = {{WiSpec}: Commodity Dual-Band Wi-Fi Spectroscopy for
               Material Classification and Structural Reconnaissance},
  booktitle = {[Venue TBD]},
  year      = {2026},
  note      = {Preprint / under review}
}
```

GitHub also renders a "Cite this repository" button from the [CITATION.cff](CITATION.cff) file.

### Attribution Requirements

Academic and research users **must** cite WiSpec in any publication, thesis, report, or presentation that uses this code, methods, or datasets. This is a condition of the license, not just a polite request.

Commercial use of any kind requires prior written permission. Contact: chatgpt@asu.edu

## Key References for WiSpec

See `paper/references.bib` for complete bibliography. Essential reading:
1. Chen et al., "A Survey on Radio Frequency Sensing: From Wi-Fi to 6G," IEEE COMST, 2025
2. Wilson & Patwari, "Propagation Losses in Building Materials: Measurements and Prediction at 915 MHz and 2.4 GHz," IEEE AWPL, 2002
3. Wilson & Patwari, "Radio Tomographic Imaging with Wireless Networks," IEEE TMC, 2010
