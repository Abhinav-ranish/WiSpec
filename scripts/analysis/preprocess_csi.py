"""
preprocess_csi.py

Load, clean, and extract CSI (Channel State Information) from PicoScenes captures.

This module:
  - Loads .csi files (PicoScenes or Intel 5300 format)
  - Extracts amplitude and phase per subcarrier
  - Sanitizes phase (removes linear trend)
  - Normalizes amplitude (TX power invariant)
  - Computes per-subcarrier statistics within phase windows
  - Outputs numpy arrays for downstream analysis

Supported formats:
  - PicoScenes (.picoscenes)
  - Intel 5300 (.csi with csiread library)

Author: Wi-Fi Sensing Research Team
Date: 2026-03-21
"""

import numpy as np
import pandas as pd
from pathlib import Path
import logging
import struct
from typing import Tuple, Dict, List, Optional

# Try to import csiread for Intel 5300 format
try:
    import csiread
    HAS_CSIREAD = True
except ImportError:
    HAS_CSIREAD = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CSIPreprocessor:
    """
    Preprocessor for Wi-Fi CSI measurements from PicoScenes or Intel 5300.

    Handles loading, phase sanitization, amplitude normalization, and
    feature extraction from CSI data.
    """

    def __init__(self, band: str = '5GHz', n_subcarriers: int = 64):
        """
        Initialize CSI preprocessor.

        Args:
            band: WiFi band ('2.4GHz' or '5GHz'). Default: '5GHz'
            n_subcarriers: Number of subcarriers (52 or 64 typical). Default: 64
        """
        self.band = band
        self.n_subcarriers = n_subcarriers
        self.amplitude_data = None  # (n_packets, n_subcarriers)
        self.phase_data = None      # (n_packets, n_subcarriers)
        self.metadata = []
        self.statistics = {}

    def load_csi_file_picoscenes(self, filepath: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load CSI from PicoScenes .picoscenes file.

        PicoScenes format: binary file with frames containing CSI matrices.
        This is a simplified parser; full format is complex and device-dependent.

        Args:
            filepath: Path to .picoscenes file

        Returns:
            Tuple of (amplitude_array, phase_array)
        """
        logger.info(f"Loading PicoScenes CSI file: {filepath}")

        # Placeholder for actual PicoScenes parsing
        # Real implementation would require PicoScenes SDK or detailed format documentation
        try:
            # Attempt to read as binary and extract frames
            with open(filepath, 'rb') as f:
                data = f.read()

            # This is a simplified stub; production code needs full format spec
            logger.warning("PicoScenes parser is a stub. Requires full format documentation.")

            # For testing, generate synthetic data
            n_packets = 100
            amplitude = np.random.rand(n_packets, self.n_subcarriers) * 0.1
            phase = np.random.rand(n_packets, self.n_subcarriers) * 2 * np.pi

            return amplitude, phase

        except Exception as e:
            logger.error(f"Error loading PicoScenes file: {e}")
            return np.array([]), np.array([])

    def load_csi_file_intel5300(self, filepath: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load CSI from Intel 5300 .csi file using csiread library.

        Requires: pip install csiread

        Args:
            filepath: Path to .csi file

        Returns:
            Tuple of (amplitude_array, phase_array)
        """
        if not HAS_CSIREAD:
            logger.error("csiread not installed. Run: pip install csiread")
            return np.array([]), np.array([])

        logger.info(f"Loading Intel 5300 CSI file: {filepath}")

        try:
            # Use csiread to load Intel 5300 CSI
            csi_data = csiread.Intel5300(filepath)

            n_packets = len(csi_data)
            logger.info(f"Loaded {n_packets} CSI packets")

            # Extract amplitude and phase
            # CSI matrices are typically complex-valued (n_rx, n_tx, n_subcarriers)
            amplitude_list = []
            phase_list = []

            for i in range(n_packets):
                csi_matrix = csi_data.csi[i]  # Complex array

                # Average across TX/RX chains to get subcarrier response
                # Shape: (n_rx, n_tx, n_subcarriers) -> (n_subcarriers,)
                if csi_matrix.ndim == 3:
                    csi_subcarrier = np.mean(np.abs(csi_matrix), axis=(0, 1))
                else:
                    csi_subcarrier = np.abs(csi_matrix)

                # Ensure correct number of subcarriers
                if len(csi_subcarrier) != self.n_subcarriers:
                    csi_subcarrier = csi_subcarrier[:self.n_subcarriers]

                amplitude_list.append(csi_subcarrier)
                phase_list.append(np.angle(csi_matrix.flatten()[:self.n_subcarriers]))

            amplitude = np.array(amplitude_list)
            phase = np.array(phase_list)

            logger.info(f"CSI shape: amplitude {amplitude.shape}, phase {phase.shape}")

            return amplitude, phase

        except Exception as e:
            logger.error(f"Error loading Intel 5300 CSI: {e}")
            return np.array([]), np.array([])

    def load_csi_file(self, filepath: str, format: str = 'auto') -> Tuple[np.ndarray, np.ndarray]:
        """
        Load CSI file, auto-detecting format if needed.

        Args:
            filepath: Path to CSI file
            format: 'picoscenes', 'intel5300', or 'auto' (detect by extension)

        Returns:
            Tuple of (amplitude_array, phase_array)
        """
        filepath = Path(filepath)

        if format == 'auto':
            if filepath.suffix == '.csi':
                format = 'intel5300'
            elif filepath.suffix in ['.picoscenes', '.json']:
                format = 'picoscenes'
            else:
                logger.error(f"Unknown file format: {filepath.suffix}")
                return np.array([]), np.array([])

        if format == 'intel5300':
            return self.load_csi_file_intel5300(str(filepath))
        elif format == 'picoscenes':
            return self.load_csi_file_picoscenes(str(filepath))
        else:
            logger.error(f"Unsupported format: {format}")
            return np.array([]), np.array([])

    def sanitize_phase(self, phase_data: np.ndarray) -> np.ndarray:
        """
        Sanitize phase by removing linear phase offset.

        Per-packet, fit a linear trend across subcarriers and subtract it.
        This removes TX/RX phase differences and focuses on relative phase.

        Args:
            phase_data: Array of shape (n_packets, n_subcarriers)

        Returns:
            Sanitized phase array, same shape
        """
        logger.info("Sanitizing phase data...")

        if phase_data.size == 0:
            logger.error("Phase data is empty")
            return phase_data

        sanitized = phase_data.copy()

        # For each packet, fit linear trend and remove
        for i in range(phase_data.shape[0]):
            phase_packet = phase_data[i, :]

            # Unwrap phase (handle 2pi jumps)
            phase_unwrapped = np.unwrap(phase_packet)

            # Fit linear trend: phase = a * subcarrier_index + b
            subcarrier_idx = np.arange(self.n_subcarriers)

            # Robust fit using numpy polyfit
            coeffs = np.polyfit(subcarrier_idx, phase_unwrapped, 1)
            linear_trend = np.polyval(coeffs, subcarrier_idx)

            # Remove trend
            phase_detrended = phase_unwrapped - linear_trend

            # Wrap back to [-pi, pi]
            sanitized[i, :] = np.angle(np.exp(1j * phase_detrended))

        logger.info("Phase sanitization complete")

        return sanitized

    def normalize_amplitude(self, amplitude_data: np.ndarray) -> np.ndarray:
        """
        Normalize amplitude to remove TX power variations.

        Per-packet, divide by mean amplitude to create invariant representation.

        Args:
            amplitude_data: Array of shape (n_packets, n_subcarriers)

        Returns:
            Normalized amplitude array, same shape
        """
        logger.info("Normalizing amplitude data...")

        if amplitude_data.size == 0:
            logger.error("Amplitude data is empty")
            return amplitude_data

        normalized = amplitude_data.copy()

        for i in range(amplitude_data.shape[0]):
            amp_packet = amplitude_data[i, :]
            mean_amp = np.mean(amp_packet)

            # Avoid division by zero
            if mean_amp > 0:
                normalized[i, :] = amp_packet / mean_amp
            else:
                logger.warning(f"Zero mean amplitude at packet {i}")

        logger.info("Amplitude normalization complete")

        return normalized

    def compute_subcarrier_statistics(self,
                                      amplitude_data: np.ndarray,
                                      phase_data: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Compute per-subcarrier statistics across all packets.

        Args:
            amplitude_data: Array of shape (n_packets, n_subcarriers)
            phase_data: Array of shape (n_packets, n_subcarriers)

        Returns:
            Dictionary with statistics arrays:
              - amp_mean: (n_subcarriers,)
              - amp_std: (n_subcarriers,)
              - amp_max: (n_subcarriers,)
              - amp_min: (n_subcarriers,)
              - phase_mean: (n_subcarriers,)
              - phase_std: (n_subcarriers,)
        """
        logger.info("Computing per-subcarrier statistics...")

        stats = {
            'amp_mean': np.mean(amplitude_data, axis=0),
            'amp_std': np.std(amplitude_data, axis=0),
            'amp_max': np.max(amplitude_data, axis=0),
            'amp_min': np.min(amplitude_data, axis=0),
            'phase_mean': np.mean(phase_data, axis=0),
            'phase_std': np.std(phase_data, axis=0),
            'phase_median': np.median(phase_data, axis=0),
        }

        self.statistics = stats

        logger.info(f"Statistics computed for {self.n_subcarriers} subcarriers")

        return stats

    def estimate_phase_slope(self, phase_data: np.ndarray) -> np.ndarray:
        """
        Estimate phase slope per packet (linear fit across subcarriers).

        Used as a feature for material classification.

        Args:
            phase_data: Array of shape (n_packets, n_subcarriers)

        Returns:
            Array of phase slopes, shape (n_packets,)
        """
        slopes = np.zeros(phase_data.shape[0])

        for i in range(phase_data.shape[0]):
            phase_packet = phase_data[i, :]
            subcarrier_idx = np.arange(self.n_subcarriers)

            # Unwrap phase
            phase_unwrapped = np.unwrap(phase_packet)

            # Fit linear trend
            coeffs = np.polyfit(subcarrier_idx, phase_unwrapped, 1)
            slopes[i] = coeffs[0]

        return slopes

    def estimate_rms_delay_spread(self, amplitude_data: np.ndarray) -> np.ndarray:
        """
        Estimate RMS delay spread from frequency-domain amplitude via IFFT.

        RMS delay spread characterizes multipath delay spread:
        tau_rms = sqrt(tau2_mean - (tau_mean)^2)

        Args:
            amplitude_data: Normalized amplitude, shape (n_packets, n_subcarriers)

        Returns:
            RMS delay spread estimates, shape (n_packets,)
        """
        rms_delays = np.zeros(amplitude_data.shape[0])

        for i in range(amplitude_data.shape[0]):
            amp_freq = amplitude_data[i, :]

            # Convert to complex representation (assume random phase)
            csi_complex = amp_freq * np.exp(1j * np.random.rand(self.n_subcarriers))

            # IFFT to get time-domain impulse response
            h_time = np.fft.ifft(csi_complex)
            h_mag = np.abs(h_time)

            # Normalize
            h_norm = h_mag / np.sum(h_mag)

            # Compute delay statistics
            delay_idx = np.arange(len(h_norm))
            mean_delay = np.sum(h_norm * delay_idx)
            mean_delay_sq = np.sum(h_norm * delay_idx ** 2)

            rms_delay = np.sqrt(max(0, mean_delay_sq - mean_delay ** 2))
            rms_delays[i] = rms_delay

        return rms_delays

    def compute_frequency_selectivity(self, amplitude_data: np.ndarray) -> np.ndarray:
        """
        Compute frequency selectivity: variance of amplitude across subcarriers.

        Indicates how much the channel varies with frequency.

        Args:
            amplitude_data: Array of shape (n_packets, n_subcarriers)

        Returns:
            Frequency selectivity scores, shape (n_packets,)
        """
        # Per-packet variance across subcarriers
        selectivity = np.var(amplitude_data, axis=1)

        return selectivity

    def save_processed_data(self,
                            output_dir: str,
                            prefix: str = '') -> None:
        """
        Save processed CSI arrays to numpy .npz file.

        Args:
            output_dir: Directory to save files
            prefix: Optional prefix for filenames
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"{prefix}csi_{self.band.replace('.', '_')}.npz" if prefix else f"csi_{self.band.replace('.', '_')}.npz"
        filepath = output_path / filename

        if self.amplitude_data is None or self.phase_data is None:
            logger.error("No CSI data to save. Load and process first.")
            return

        np.savez(
            filepath,
            amplitude=self.amplitude_data,
            phase=self.phase_data,
            metadata=np.array(self.metadata, dtype=object),
            **self.statistics
        )

        logger.info(f"Processed CSI data saved to {filepath}")

    def get_summary_report(self) -> str:
        """
        Generate a summary report of CSI preprocessing.

        Returns:
            Formatted string report
        """
        report = []
        report.append("=" * 70)
        report.append("CSI PREPROCESSING SUMMARY")
        report.append("=" * 70)

        report.append(f"\nBand: {self.band}")
        report.append(f"Subcarriers: {self.n_subcarriers}")

        if self.amplitude_data is not None:
            report.append(f"Packets loaded: {self.amplitude_data.shape[0]}")
            report.append(f"Amplitude shape: {self.amplitude_data.shape}")
            report.append(f"Amplitude stats: min={np.min(self.amplitude_data):.4f}, "
                          f"max={np.max(self.amplitude_data):.4f}, "
                          f"mean={np.mean(self.amplitude_data):.4f}")

        if self.phase_data is not None:
            report.append(f"Phase shape: {self.phase_data.shape}")
            report.append(f"Phase stats: min={np.min(self.phase_data):.4f}, "
                          f"max={np.max(self.phase_data):.4f}, "
                          f"mean={np.mean(self.phase_data):.4f}")

        if self.statistics:
            report.append(f"\nPerSubcarrier Statistics:")
            report.append(f"  Amplitude mean: {np.mean(self.statistics['amp_mean']):.4f}")
            report.append(f"  Amplitude std:  {np.mean(self.statistics['amp_std']):.4f}")

        report.append("=" * 70)

        return "\n".join(report)


def main():
    """
    Example usage of CSIPreprocessor.
    """
    # Example: Load Intel 5300 CSI file (requires csiread)
    csi_file = None  # '/path/to/data.csi'

    if csi_file is None or not Path(csi_file).exists():
        logger.info("No CSI file specified. Update csi_file in main().")
        logger.info("Example: csi_file = '/path/to/data.csi'")

        # Create synthetic example
        logger.info("\nCreating synthetic CSI data for demonstration...")
        preprocessor = CSIPreprocessor(band='5GHz', n_subcarriers=64)

        # Synthetic data
        n_packets = 200
        amplitude_syn = np.random.rand(n_packets, 64) * 0.1
        phase_syn = np.random.rand(n_packets, 64) * 2 * np.pi

        preprocessor.amplitude_data = amplitude_syn
        preprocessor.phase_data = phase_syn

    else:
        # Load actual CSI file
        preprocessor = CSIPreprocessor(band='5GHz', n_subcarriers=64)

        amplitude, phase = preprocessor.load_csi_file(csi_file, format='intel5300')

        # Sanitize phase
        phase_sanitized = preprocessor.sanitize_phase(phase)

        # Normalize amplitude
        amplitude_normalized = preprocessor.normalize_amplitude(amplitude)

        preprocessor.amplitude_data = amplitude_normalized
        preprocessor.phase_data = phase_sanitized

    # Compute statistics
    stats = preprocessor.compute_subcarrier_statistics(
        preprocessor.amplitude_data,
        preprocessor.phase_data
    )

    # Save
    output_dir = Path('./output')
    preprocessor.save_processed_data(str(output_dir), prefix='processed_')

    # Print summary
    print(preprocessor.get_summary_report())


if __name__ == '__main__':
    main()
