"""Rig configuration (bands, NICs, windowing, teacher camera)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BandConfig:
    name: str                 # "2g" | "5g" | "6g"
    phy: str                  # PicoScenes PHY/NIC id
    primary_mhz: int
    bandwidth_mhz: int
    center_mhz: int
    model_subcarriers: int = 128   # subcarriers after grouping, fed to the model


@dataclass
class RigConfig:
    bands: list[BandConfig] = field(default_factory=list)
    rx_antennas: int = 2
    csi_rate_hz: float = 100.0
    window_s: float = 1.5
    teacher: str = "depth"         # "depth" | "rgb"
    teacher_device: str = "orbbec"  # "orbbec" | "opencv"
    frame_size: int = 64
    latent_dim: int = 32
    max_depth_mm: int = 6000

    @property
    def window_len(self) -> int:
        return int(round(self.csi_rate_hz * self.window_s))

    @property
    def frame_channels(self) -> int:
        return 1 if self.teacher == "depth" else 3

    def band_channels(self) -> list[int]:
        """Model input channels per band: amplitude per RX antenna + one antenna-ratio phase map."""
        per_sc = self.rx_antennas + (1 if self.rx_antennas > 1 else 0)
        return [per_sc * b.model_subcarriers for b in self.bands]

    @classmethod
    def from_dict(cls, d: dict) -> "RigConfig":
        d = {k: v for k, v in d.items() if not k.startswith("_")}
        bands = [BandConfig(**b) for b in d.pop("bands", [])]
        return cls(bands=bands, **d)

    @classmethod
    def from_json(cls, path: str | Path) -> "RigConfig":
        return cls.from_dict(json.loads(Path(path).read_text()))

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)
