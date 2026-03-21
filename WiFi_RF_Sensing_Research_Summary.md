# Wi-Fi / RF Sensing as Cameraless Surveillance: Feasibility Research

## TL;DR — Is It Possible?

**Yes, and it's further along than most people realize.** Wi-Fi-based room imaging, object detection, and even material classification are all demonstrated in peer-reviewed research. The IEEE published a dedicated standard for it in 2025 (802.11bf). Your dual-band idea (2.4 GHz + 5 GHz) for material differentiation is scientifically grounded and represents a genuinely interesting research angle.

---

## 1. Core Concept: How Wi-Fi Signals "See"

The fundamental mechanism you're describing is real and well-studied. It works via **Channel State Information (CSI)** — fine-grained measurements of how Wi-Fi signals propagate between a transmitter and receiver across multiple subcarriers.

When radio waves travel through a room, they reflect off walls, diffract around edges, scatter off furniture, and attenuate through materials. Each of these interactions leaves a measurable fingerprint in the CSI data. By analyzing amplitude, phase shifts, time-of-flight, and signal attenuation across many subcarrier frequencies simultaneously, you can reconstruct information about the physical environment.

**Three main sensing paradigms exist:**

- **Passive sensing** — hijack existing Wi-Fi signals already in the environment (exactly what you're describing). No special hardware needed beyond commodity receivers that can extract CSI.
- **Active monostatic** — a device transmits and listens to its own reflections (like radar).
- **Bistatic/multistatic** — coordinated transmitter-receiver pairs placed around a space, measuring how signals between them are disturbed.

---

## 2. What Has Actually Been Demonstrated

### Through-Wall Human Tracking (MIT, 2013–present)
Fadel Adib and Dina Katabi at MIT CSAIL built **Wi-Vi**, which uses 2.4 GHz Wi-Fi to track moving humans through walls. The trick: two transmit antennas send inverted copies of the same signal, causing reflections from static objects (including the wall itself) to cancel out. Only reflections from moving objects survive. Their follow-up system **WiTrack** achieved 10–20 cm 3D tracking accuracy through walls using specialized wideband radio signals.

### Reading Through Walls (UCSB, 2023)
Yasamin Mostofi's lab at UC Santa Barbara demonstrated **Wiffract**, which images the edges of static objects using Wi-Fi by exploiting the Geometrical Theory of Diffraction (Keller cones). They successfully imaged and *read* the letters of the word "BELIEVE" through a wall — detail previously considered impossible for Wi-Fi frequencies. Published at IEEE RadarConf 2023.

### Room Layout Reconstruction (Radio Tomographic Imaging)
Joey Wilson and Neal Patwari's work on **Radio Tomographic Imaging (RTI)** uses a mesh of simple wireless nodes to reconstruct 2D attenuation images of a room. By measuring received signal strength (RSS) across many intersecting link paths, they create heat-map style images showing where objects are located. An IEEE Xplore paper from 2021 demonstrated full building layout reconstruction from commercial Wi-Fi RSSI alone.

### Material Detection via CSI
Wang et al. (2018) demonstrated using reconstructed CSI complex values to detect the *type* of material inside baggage — specifically distinguishing metal and liquid objects, then estimating object dimensions. This directly validates your intuition about using signal characteristics for material classification.

### Human Activity and Gesture Recognition
This is the most mature application area. CSI-based systems can now detect not just walking and large movements, but breathing, chewing, and fine-grained gestures. A 2024 study achieved 87.3% room-level occupancy estimation across a five-room residential setting.

---

## 3. Your Dual-Band Idea: 2.4 GHz + 5 GHz for Material Identification

This is where your research angle gets particularly interesting. The physics supports it:

### Wavelength and Resolution
- **2.4 GHz** → ~12.5 cm wavelength → better penetration, lower spatial resolution
- **5 GHz** → ~6 cm wavelength → worse penetration, higher spatial resolution

Objects smaller than roughly half the wavelength become difficult to resolve. So 5 GHz can "see" objects down to ~3 cm, while 2.4 GHz bottoms out around ~6 cm. Using both bands gives you two different "views" of the same space.

### Differential Attenuation = Material Fingerprint

Different materials attenuate 2.4 GHz and 5 GHz signals by dramatically different amounts:

| Material | ~2.4 GHz Loss | ~5 GHz Loss | Ratio Pattern |
|----------|--------------|-------------|---------------|
| Drywall/plasterboard | 3–5 dB | 4–7 dB | Low, mild increase |
| Wood | 5–12 dB | 8–15 dB | Low-medium, moderate increase |
| Brick | 6–10 dB | 10–18 dB | Medium, significant increase |
| Concrete (no rebar) | ~23 dB | ~45 dB | Very high, nearly doubles |
| Metal | Near-total reflection | Near-total reflection | Distinctive reflection signature |
| Water | High absorption | Higher absorption | Characteristic absorption curve |
| Glass (clear) | 2–4 dB | 3–6 dB | Low, mild increase |

The key insight: **the ratio of attenuation between bands is material-dependent.** Concrete nearly doubles its attenuation from 2.4 to 5 GHz, while drywall barely changes. Metal reflects almost everything at both frequencies but creates distinctive multipath signatures. Water absorbs with a characteristic frequency-dependent profile.

By comparing how the same signal path behaves at both frequency bands, you could potentially build a material classifier. This is supported by the dual-band permittivity sensor research (Sciencedirect, 2023) that showed multicascode T-shaped resonators at 2.45 GHz and nearby frequencies can simultaneously determine permittivity of solid materials.

### What This Means for Your Research
You could potentially create a "radio map" where each voxel in the room has not just a position but a material classification based on its dual-band attenuation signature. This goes beyond what most current WiFi sensing papers attempt, which typically focus on a single band.

---

## 4. The IEEE 802.11bf Standard (Published September 2025)

The Wi-Fi industry has formalized all of this. **IEEE 802.11bf (Wi-Fi SENS)** defines MAC and PHY enhancements specifically for sensing in the 2.4, 5, and 6 GHz bands. It passed ballot with 96% approval. This means future commodity routers will have built-in support for CSI extraction and sensing procedures — making passive sensing with off-the-shelf hardware dramatically easier.

This is significant for your research because it means the infrastructure you'd need is being baked into consumer hardware. You won't need custom firmware hacks or specialized SDR equipment for much longer.

---

## 5. Practical Implementation Approaches

### Hardware You Could Use Today
- **ESP32 with ESP-CSI** — Espressif provides open-source CSI extraction firmware (github.com/espressif/esp-csi). Cheap (~$5/board), supports 2.4 GHz.
- **Raspberry Pi 4 + Nexmon CSI** — The BCM43455c0 chipset supports CSI extraction via the Nexmon firmware patch. 2.4 GHz and 5 GHz capable.
- **Intel 5300 NIC** — The classic research platform for CSI extraction. Linux CSI Tool provides 30 subcarrier measurements per antenna pair.
- **Software Defined Radio (SDR)** — For maximum flexibility, USRP or HackRF devices let you control everything, but at higher cost and complexity.

### Software/Algorithm Pipeline
1. **CSI Collection** — Extract amplitude and phase across all subcarriers from both bands
2. **Preprocessing** — Noise reduction (Butterworth filtering, PCA), phase sanitization (linear phase correction), outlier removal
3. **Feature Extraction** — Statistical features (mean, variance, skewness), frequency-domain features (FFT), time-frequency features (wavelet transform)
4. **Spatial Reconstruction** — Inverse methods (tomographic reconstruction), beamforming, diffraction-based imaging (Wiffract approach)
5. **Classification** — Machine learning (CNN, LSTM, transformer architectures) trained on dual-band features to classify materials

---

## 6. Key Limitations and Challenges

### Fundamental Physics Constraints
- **Diffraction-limited resolution**: Wi-Fi images are inherently blurry compared to optical or even mmWave. Objects appear as Airy disk patterns rather than sharp points. At 5 GHz you're looking at ~6 cm minimum resolvable feature size.
- **Multipath complexity**: Indoor environments produce massive multipath — every wall, floor, ceiling, and piece of furniture creates reflections. Separating useful reflections from noise is the core algorithmic challenge.
- **Static object imaging is harder than moving objects**: Most impressive demos (MIT Wi-Vi) work by subtracting static background. Imaging objects that don't move requires more sophisticated approaches like Mostofi's diffraction-based method.

### Practical Challenges
- **Environment sensitivity**: A CSI model trained in one room often fails in another. This "domain gap" is the biggest practical barrier to deployment.
- **Calibration**: Accurate material classification requires knowing the transmit power, antenna gains, and precise geometry — or clever differential measurements that cancel these out (which is where your dual-band approach helps).
- **Computational cost**: Real-time tomographic reconstruction with machine learning classification is computationally expensive.
- **Interference from other Wi-Fi networks**: In apartment buildings or offices, neighboring networks add noise.

---

## 7. Key References for Your Paper

### Foundational
- Adib & Katabi, "See Through Walls with Wi-Fi!" — SIGCOMM 2013 (MIT Wi-Vi)
- Adib et al., "3D Tracking via Body Radio Reflections" — NSDI 2014 (WiTrack)
- Wilson & Patwari, "Radio Tomographic Imaging with Wireless Networks" — IEEE Trans. Mobile Computing, 2010

### Room/Object Imaging
- Pallaprolu, Korany & Mostofi, "Wiffract" — IEEE RadarConf 2023 (UCSB reading through walls)
- "Building Layout Tomographic Reconstruction via Commercial WiFi Signals" — IEEE Xplore, 2021

### CSI Sensing Surveys
- "WiFi Sensing with Channel State Information: A Survey" — ACM Computing Surveys, Vol 52, No 3 (comprehensive overview)
- "Commodity WiFi Sensing in 10 Years: Status, Challenges, and Opportunities" — IEEE IoT Journal, 2022
- "Commodity Wi-Fi-Based Wireless Sensing Advancements over the Past Five Years" — Sensors, 2024

### Material Sensing
- Wang et al. (2018) — CSI-based dangerous material detection in baggage
- "Multifunctional dual-band permittivity sensors" — Measurement, 2023 (dual-band material characterization)

### Standards
- IEEE 802.11bf-2025 — WLAN Sensing standard (published September 2025)
- Ropitault & Silva, "IEEE 802.11bf WLAN Sensing Procedure" — IEEE Communications Magazine, 2024

---

## 8. Assessment: Where Your Idea Sits

| Aspect | Feasibility | Maturity |
|--------|-------------|----------|
| Room-level presence detection | Fully feasible | Commercial products exist |
| Human tracking through walls | Demonstrated | Research prototypes, ~20 cm accuracy |
| Static object imaging | Feasible with advanced methods | Cutting-edge research (Wiffract) |
| Room layout reconstruction | Demonstrated | Multiple research implementations |
| Material classification (single band) | Demonstrated for some materials | Early research (metal/liquid detection) |
| Dual-band material fingerprinting | Theoretically sound, limited direct work | **Novel research opportunity** |
| Object identification by material + shape | Speculative but grounded | **Open research question** |

Your idea of combining dual-band attenuation signatures with spatial reconstruction to both locate and identify objects is at the frontier of this field. The individual pieces (spatial imaging, material-dependent attenuation, dual-band sensing) are all proven — the combination into a unified system for object identification is where the novelty lives.

---

*Research compiled March 2026. All referenced work is from peer-reviewed venues or IEEE standards.*
