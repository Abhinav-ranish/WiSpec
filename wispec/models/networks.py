"""Models.

Stage 1 — ``FrameAutoencoder``: compresses teacher frames (depth or RGB) to a
small latent vector (32 numbers by default).

Stage 2 — ``CSINet``: predicts that latent, plus 3D joints and presence, from a
tri-band CSI window. Each band has its own stem (bands differ in subcarrier
count and physics); stems are fused and processed with temporal convolutions.
``band_dropout`` randomly blanks whole bands during training so the model
tolerates a missing band and per-band ablations are meaningful.
"""

from __future__ import annotations

import torch
from torch import nn


class FrameAutoencoder(nn.Module):
    def __init__(self, in_ch: int = 1, latent_dim: int = 32, size: int = 64):
        super().__init__()
        assert size % 16 == 0
        self.size = size
        w = [32, 64, 128, 128]
        self.enc = nn.Sequential(
            nn.Conv2d(in_ch, w[0], 4, 2, 1), nn.ReLU(),
            nn.Conv2d(w[0], w[1], 4, 2, 1), nn.BatchNorm2d(w[1]), nn.ReLU(),
            nn.Conv2d(w[1], w[2], 4, 2, 1), nn.BatchNorm2d(w[2]), nn.ReLU(),
            nn.Conv2d(w[2], w[3], 4, 2, 1), nn.BatchNorm2d(w[3]), nn.ReLU(),
        )
        s = size // 16
        self.to_z = nn.Linear(w[3] * s * s, latent_dim)
        self.from_z = nn.Linear(latent_dim, w[3] * s * s)
        self.dec = nn.Sequential(
            nn.ConvTranspose2d(w[3], w[2], 4, 2, 1), nn.BatchNorm2d(w[2]), nn.ReLU(),
            nn.ConvTranspose2d(w[2], w[1], 4, 2, 1), nn.BatchNorm2d(w[1]), nn.ReLU(),
            nn.ConvTranspose2d(w[1], w[0], 4, 2, 1), nn.BatchNorm2d(w[0]), nn.ReLU(),
            nn.ConvTranspose2d(w[0], in_ch, 4, 2, 1), nn.Sigmoid(),
        )
        self._s, self._c = s, w[3]

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.to_z(self.enc(x).flatten(1))

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        h = self.from_z(z).view(-1, self._c, self._s, self._s)
        return self.dec(h)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        z = self.encode(x)
        return self.decode(z), z


class _TBlock(nn.Module):
    def __init__(self, ch: int, k: int = 5, dilation: int = 1, p: float = 0.1):
        super().__init__()
        pad = (k - 1) // 2 * dilation
        self.net = nn.Sequential(
            nn.Conv1d(ch, ch, k, padding=pad, dilation=dilation), nn.BatchNorm1d(ch), nn.GELU(),
            nn.Dropout(p),
            nn.Conv1d(ch, ch, k, padding=pad, dilation=dilation), nn.BatchNorm1d(ch),
        )
        self.act = nn.GELU()

    def forward(self, x):
        return self.act(x + self.net(x))


class CSINet(nn.Module):
    def __init__(self, band_channels: list[int], latent_dim: int = 32, n_joints: int = 9,
                 width: int = 128, band_dropout: float = 0.15):
        super().__init__()
        self.band_dropout = band_dropout
        stem_w = width // 2
        self.stems = nn.ModuleList([
            nn.Sequential(
                nn.Conv1d(c, stem_w, 1), nn.BatchNorm1d(stem_w), nn.GELU(),   # subcarrier mixing
                nn.Conv1d(stem_w, stem_w, 5, padding=2), nn.BatchNorm1d(stem_w), nn.GELU(),
            ) for c in band_channels
        ])
        self.fuse = nn.Sequential(nn.Conv1d(stem_w * len(band_channels), width, 1),
                                  nn.BatchNorm1d(width), nn.GELU())
        self.temporal = nn.Sequential(*[_TBlock(width, dilation=d) for d in (1, 2, 4, 8)])
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head_latent = nn.Linear(width, latent_dim)
        self.head_joints = nn.Linear(width, n_joints * 3)
        self.head_presence = nn.Linear(width, 1)
        self.n_joints = n_joints

    def forward(self, xs: list[torch.Tensor], band_mask: torch.Tensor | None = None) -> dict:
        """xs: per band [B, C_b, T]. band_mask: [B, n_bands] (1 = use band)."""
        b = xs[0].shape[0]
        if band_mask is None:
            band_mask = torch.ones(b, len(xs), device=xs[0].device)
        if self.training and self.band_dropout > 0 and len(xs) > 1:
            drop = (torch.rand_like(band_mask) < self.band_dropout).float()
            keep_one = torch.nn.functional.one_hot(torch.randint(len(xs), (b,), device=drop.device),
                                                   len(xs)).float()
            band_mask = band_mask * torch.clamp(1 - drop + keep_one, max=1)
        feats = [stem(x) * band_mask[:, i, None, None] for i, (stem, x) in enumerate(zip(self.stems, xs))]
        h = self.temporal(self.fuse(torch.cat(feats, dim=1)))
        h = self.pool(h).squeeze(-1)
        return {
            "latent": self.head_latent(h),
            "joints": self.head_joints(h).view(b, self.n_joints, 3),
            "presence": self.head_presence(h).squeeze(-1),
        }
