"""
feature_extraction.py

Extract hand-crafted features from RSSI and CSI data for material classification.

This module extracts single-band, dual-band, and tri-band features:

RSSI Features (per material phase):
  - mean_rssi_2g, std_rssi_2g, mean_rssi_5g, std_rssi_5g, mean_rssi_6g, std_rssi_6g
  - mean_attenuation_2g, mean_attenuation_5g, mean_attenuation_6g
  - delta_attenuation for all band pairs (5g-2g, 6g-2g, 6g-5g)
  - ratio_attenuation for all band pairs
  - spectral_curvature (tri-band non-linearity)
  - mean_snr_2g, mean_snr_5g, mean_snr_6g, delta_snr pairs
  - mean_ping_2g, mean_ping_5g, mean_ping_6g

CSI Features (per material phase, per band):
  - mean_amplitude_across_subcarriers
  - std_amplitude_across_subcarriers
  - max_amplitude, min_amplitude
  - amplitude_spread (max - min)
  - mean_phase_slope
  - rms_delay_spread_estimate
  - frequency_selectivity

Tri-band CSI Features:
  - Delta and ratio of each CSI feature for all band pairs
  - Spectral curvature features
  - Concatenated feature vector

Output:
  - Feature matrix (n_samples × n_features) with feature names
  - Feature importance rankings
  - Per-material feature means

Author: Wi-Fi Sensing Research Team
Date: 2026-03-21
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, Tuple, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RSSIFeatureExtractor:
    """
    Extract features from RSSI phase statistics.
    """

    def __init__(self):
        self.features = None
        self.feature_names = None

    def extract_rssi_features(self,
                              phase_stats_df: pd.DataFrame,
                              dual_band_df: Optional[pd.DataFrame] = None) -> Tuple[np.ndarray, List[str]]:
        """
        Extract RSSI-based features from phase statistics.

        Args:
            phase_stats_df: DataFrame from preprocess_rssi.compute_phase_statistics()
            dual_band_df: Optional DataFrame from preprocess_rssi.compute_dual_band_features()

        Returns:
            Tuple of (feature_matrix, feature_names)
        """
        logger.info("Extracting RSSI features...")

        feature_list = []
        feature_names = []

        # Group by trial, phase, material for consistent aggregation
        groupby_cols = ['trial_id', 'phase_label', 'material_class', 'environment_id']

        for group_key, group_df in phase_stats_df.groupby(groupby_cols):
            trial_id, phase_label, material_class, env_id = group_key

            features_row = {
                'trial_id': trial_id,
                'phase_label': phase_label,
                'material_class': material_class,
                'environment_id': env_id,
            }

            # Extract 2.4 GHz and 5 GHz rows
            row_2g = group_df[group_df['band'] == '2.4GHz']
            row_5g = group_df[group_df['band'] == '5GHz']

            # 2.4 GHz features
            if len(row_2g) > 0:
                row_2g = row_2g.iloc[0]
                features_row['rssi_mean_2g'] = row_2g['rssi_mean']
                features_row['rssi_std_2g'] = row_2g['rssi_std']
                features_row['rssi_median_2g'] = row_2g['rssi_median']
                features_row['snr_mean_2g'] = row_2g['snr_mean']
                features_row['snr_std_2g'] = row_2g['snr_std']
            else:
                features_row['rssi_mean_2g'] = np.nan
                features_row['rssi_std_2g'] = np.nan
                features_row['rssi_median_2g'] = np.nan
                features_row['snr_mean_2g'] = np.nan
                features_row['snr_std_2g'] = np.nan

            # 5 GHz features
            if len(row_5g) > 0:
                row_5g = row_5g.iloc[0]
                features_row['rssi_mean_5g'] = row_5g['rssi_mean']
                features_row['rssi_std_5g'] = row_5g['rssi_std']
                features_row['rssi_median_5g'] = row_5g['rssi_median']
                features_row['snr_mean_5g'] = row_5g['snr_mean']
                features_row['snr_std_5g'] = row_5g['snr_std']
            else:
                features_row['rssi_mean_5g'] = np.nan
                features_row['rssi_std_5g'] = np.nan
                features_row['rssi_median_5g'] = np.nan
                features_row['snr_mean_5g'] = np.nan
                features_row['snr_std_5g'] = np.nan

            # 6 GHz features
            row_6g = group_df[group_df['band'] == '6GHz']
            if len(row_6g) > 0:
                row_6g = row_6g.iloc[0]
                features_row['rssi_mean_6g'] = row_6g['rssi_mean']
                features_row['rssi_std_6g'] = row_6g['rssi_std']
                features_row['rssi_median_6g'] = row_6g['rssi_median']
                features_row['snr_mean_6g'] = row_6g['snr_mean']
                features_row['snr_std_6g'] = row_6g['snr_std']
            else:
                features_row['rssi_mean_6g'] = np.nan
                features_row['rssi_std_6g'] = np.nan
                features_row['rssi_median_6g'] = np.nan
                features_row['snr_mean_6g'] = np.nan
                features_row['snr_std_6g'] = np.nan

            feature_list.append(features_row)

        # Convert to DataFrame for easier manipulation
        features_df = pd.DataFrame(feature_list)

        # Compute dual-band differences if both bands present
        if 'rssi_mean_2g' in features_df.columns and 'rssi_mean_5g' in features_df.columns:
            features_df['delta_rssi_5g_minus_2g'] = features_df['rssi_mean_5g'] - features_df['rssi_mean_2g']
            features_df['ratio_rssi_5g_div_2g'] = features_df['rssi_mean_5g'] / features_df['rssi_mean_2g']
            features_df['delta_snr_5g_minus_2g'] = features_df['snr_mean_5g'] - features_df['snr_mean_2g']

        # Compute tri-band differences if 6 GHz data present
        if 'rssi_mean_6g' in features_df.columns and not features_df['rssi_mean_6g'].isna().all():
            features_df['delta_rssi_6g_minus_2g'] = features_df['rssi_mean_6g'] - features_df['rssi_mean_2g']
            features_df['delta_rssi_6g_minus_5g'] = features_df['rssi_mean_6g'] - features_df['rssi_mean_5g']
            features_df['ratio_rssi_6g_div_2g'] = features_df['rssi_mean_6g'] / features_df['rssi_mean_2g']
            features_df['ratio_rssi_6g_div_5g'] = features_df['rssi_mean_6g'] / features_df['rssi_mean_5g']
            features_df['delta_snr_6g_minus_2g'] = features_df['snr_mean_6g'] - features_df['snr_mean_2g']
            features_df['delta_snr_6g_minus_5g'] = features_df['snr_mean_6g'] - features_df['snr_mean_5g']
            # Spectral curvature: measures non-linearity of RSSI across the 3 bands
            features_df['spectral_curvature'] = (
                features_df['delta_rssi_6g_minus_5g'] - features_df['delta_rssi_5g_minus_2g']
            )

        # If dual_band_df provided, use computed attenuation features
        if dual_band_df is not None and len(dual_band_df) > 0:
            # Merge attenuation features
            merge_cols = ['trial_id', 'phase_label', 'material_class', 'environment_id']
            atten_cols = ['attenuation_2g', 'attenuation_5g',
                          'delta_attenuation_5g_minus_2g', 'ratio_attenuation_5g_div_2g']

            if all(col in dual_band_df.columns for col in atten_cols):
                atten_df = dual_band_df[merge_cols + atten_cols].copy()
                features_df = features_df.merge(atten_df, on=merge_cols, how='left')

        # Select numerical feature columns (exclude metadata)
        metadata_cols = ['trial_id', 'phase_label', 'material_class', 'environment_id']
        feature_cols = [col for col in features_df.columns if col not in metadata_cols]

        # Extract feature matrix
        X = features_df[feature_cols].values
        feature_names = feature_cols

        self.features = X
        self.feature_names = feature_names

        logger.info(f"Extracted {len(feature_names)} RSSI features from {len(X)} samples")

        return X, feature_names


class CSIFeatureExtractor:
    """
    Extract features from CSI (amplitude and phase).
    """

    def __init__(self):
        self.features = None
        self.feature_names = None

    def extract_csi_packet_features(self,
                                     amplitude: np.ndarray,
                                     phase: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        """
        Extract features from CSI amplitude and phase per packet.

        Args:
            amplitude: Array of shape (n_packets, n_subcarriers)
            phase: Array of shape (n_packets, n_subcarriers)

        Returns:
            Tuple of (feature_matrix, feature_names)
        """
        logger.info("Extracting CSI packet features...")

        n_packets = amplitude.shape[0]
        features_list = []

        for i in range(n_packets):
            amp_packet = amplitude[i, :]
            phase_packet = phase[i, :]

            features_row = {}

            # Amplitude features
            features_row['amp_mean'] = np.mean(amp_packet)
            features_row['amp_std'] = np.std(amp_packet)
            features_row['amp_max'] = np.max(amp_packet)
            features_row['amp_min'] = np.min(amp_packet)
            features_row['amp_spread'] = np.max(amp_packet) - np.min(amp_packet)
            features_row['amp_median'] = np.median(amp_packet)
            features_row['amp_q1'] = np.percentile(amp_packet, 25)
            features_row['amp_q3'] = np.percentile(amp_packet, 75)

            # Phase features
            phase_unwrapped = np.unwrap(phase_packet)
            subcarrier_idx = np.arange(len(phase_packet))

            # Phase slope (linear fit)
            if len(subcarrier_idx) > 1:
                coeffs = np.polyfit(subcarrier_idx, phase_unwrapped, 1)
                features_row['phase_slope'] = coeffs[0]
            else:
                features_row['phase_slope'] = 0.0

            features_row['phase_std'] = np.std(phase_packet)

            # RMS delay spread (time-domain from IFFT)
            csi_complex = amp_packet * np.exp(1j * phase_packet)
            h_time = np.fft.ifft(csi_complex)
            h_mag = np.abs(h_time)
            h_norm = h_mag / np.sum(h_mag)
            delay_idx = np.arange(len(h_norm))
            mean_delay = np.sum(h_norm * delay_idx)
            mean_delay_sq = np.sum(h_norm * delay_idx ** 2)
            features_row['rms_delay_spread'] = np.sqrt(max(0, mean_delay_sq - mean_delay ** 2))

            # Frequency selectivity
            features_row['freq_selectivity'] = np.var(amp_packet)

            # Sparsity (power concentration)
            amp_sorted = np.sort(amp_packet)[::-1]
            cumsum = np.cumsum(amp_sorted)
            cumsum = cumsum / cumsum[-1]
            # Find number of subcarriers containing 80% of power
            n_strong = np.argmax(cumsum >= 0.8) + 1
            features_row['sparsity'] = n_strong / len(amp_packet)

            features_list.append(features_row)

        features_df = pd.DataFrame(features_list)
        X = features_df.values
        feature_names = features_df.columns.tolist()

        self.features = X
        self.feature_names = feature_names

        logger.info(f"Extracted {len(feature_names)} CSI features from {n_packets} packets")

        return X, feature_names

    def extract_csi_phase_window_features(self,
                                          amplitude_by_phase: Dict[str, np.ndarray],
                                          phase_by_phase: Dict[str, np.ndarray]) -> Tuple[pd.DataFrame, List[str]]:
        """
        Extract aggregated CSI features per phase window.

        Each phase (e.g., 'baseline', 'material_A', etc.) contains multiple packets.
        Aggregate features across packets within each phase.

        Args:
            amplitude_by_phase: Dict mapping phase_name -> amplitude array (n_packets, n_subcarriers)
            phase_by_phase: Dict mapping phase_name -> phase array (n_packets, n_subcarriers)

        Returns:
            Tuple of (features_df, feature_names)
        """
        logger.info("Extracting phase-aggregated CSI features...")

        features_list = []

        for phase_name, amplitude in amplitude_by_phase.items():
            if phase_name not in phase_by_phase:
                logger.warning(f"Phase {phase_name} missing from phase_by_phase")
                continue

            phase = phase_by_phase[phase_name]

            # Extract packet-level features first
            packet_features, _ = self.extract_csi_packet_features(amplitude, phase)

            # Aggregate across packets (mean, std of packet features)
            features_row = {'phase_name': phase_name}

            for j, feat_name in enumerate(self.feature_names):
                features_row[f'{feat_name}_mean'] = np.mean(packet_features[:, j])
                features_row[f'{feat_name}_std'] = np.std(packet_features[:, j])
                features_row[f'{feat_name}_median'] = np.median(packet_features[:, j])

            features_list.append(features_row)

        features_df = pd.DataFrame(features_list)

        if len(features_df) > 0:
            # Get feature column names
            feature_cols = [col for col in features_df.columns if col != 'phase_name']
            X = features_df[feature_cols].values
        else:
            X = np.array([])
            feature_cols = []

        logger.info(f"Extracted {len(feature_cols)} aggregated CSI features for {len(features_list)} phases")

        return features_df, feature_cols


class TriBandFeatureExtractor:
    """
    Combine single-band RSSI and CSI features into tri-band feature vectors.
    Backward-compatible: works with 2 or 3 bands.
    """

    def __init__(self):
        self.features_2g = None
        self.features_5g = None
        self.features_6g = None
        self.combined_features = None
        self.feature_names = None

    def combine_multi_band_features(self,
                                     features_2g: np.ndarray,
                                     features_5g: np.ndarray,
                                     feature_names_2g: List[str],
                                     feature_names_5g: List[str],
                                     features_6g: Optional[np.ndarray] = None,
                                     feature_names_6g: Optional[List[str]] = None) -> Tuple[np.ndarray, List[str]]:
        """
        Combine 2.4 GHz, 5 GHz, and optionally 6 GHz features into a single feature vector.

        Creates:
          - Per-band features (2.4, 5, and optionally 6 GHz)
          - Delta features for all band pairs
          - Ratio features for all band pairs (safe division)
          - Spectral curvature (if 6 GHz present)

        Args:
            features_2g: Feature matrix (n_samples, n_features_2g)
            features_5g: Feature matrix (n_samples, n_features_5g)
            feature_names_2g: List of 2.4 GHz feature names
            feature_names_5g: List of 5 GHz feature names
            features_6g: Optional 6 GHz feature matrix (n_samples, n_features_6g)
            feature_names_6g: Optional list of 6 GHz feature names

        Returns:
            Tuple of (combined_feature_matrix, combined_feature_names)
        """
        has_6g = features_6g is not None and feature_names_6g is not None
        band_label = "tri-band" if has_6g else "dual-band"
        logger.info(f"Combining {band_label} features...")

        if features_2g.shape[0] != features_5g.shape[0]:
            logger.error("2.4 GHz and 5 GHz features have different sample counts")
            return np.array([]), []

        if has_6g and features_6g.shape[0] != features_2g.shape[0]:
            logger.error("6 GHz features have different sample count than 2.4/5 GHz")
            return np.array([]), []

        combined_cols = {}

        # 2.4 GHz features with suffix
        for j, name in enumerate(feature_names_2g):
            combined_cols[f"{name}_2g"] = features_2g[:, j]

        # 5 GHz features with suffix
        for j, name in enumerate(feature_names_5g):
            combined_cols[f"{name}_5g"] = features_5g[:, j]

        # 6 GHz features with suffix
        if has_6g:
            for j, name in enumerate(feature_names_6g):
                combined_cols[f"{name}_6g"] = features_6g[:, j]

        # Delta features (5g - 2g)
        for j, name in enumerate(feature_names_2g):
            if j < features_5g.shape[1]:
                combined_cols[f"delta_{name}_5g_minus_2g"] = features_5g[:, j] - features_2g[:, j]

        # Ratio features (5g / 2g) with safe division
        for j, name in enumerate(feature_names_2g):
            if j < features_5g.shape[1]:
                with np.errstate(divide='ignore', invalid='ignore'):
                    ratio = features_5g[:, j] / features_2g[:, j]
                    ratio = np.where(np.isfinite(ratio), ratio, np.nan)
                combined_cols[f"ratio_{name}_5g_div_2g"] = ratio

        # 6 GHz differential features
        if has_6g:
            # Delta features (6g - 2g)
            for j, name in enumerate(feature_names_2g):
                if j < features_6g.shape[1]:
                    combined_cols[f"delta_{name}_6g_minus_2g"] = features_6g[:, j] - features_2g[:, j]

            # Delta features (6g - 5g)
            for j, name in enumerate(feature_names_5g):
                if j < features_6g.shape[1]:
                    combined_cols[f"delta_{name}_6g_minus_5g"] = features_6g[:, j] - features_5g[:, j]

            # Ratio features (6g / 2g)
            for j, name in enumerate(feature_names_2g):
                if j < features_6g.shape[1]:
                    with np.errstate(divide='ignore', invalid='ignore'):
                        ratio = features_6g[:, j] / features_2g[:, j]
                        ratio = np.where(np.isfinite(ratio), ratio, np.nan)
                    combined_cols[f"ratio_{name}_6g_div_2g"] = ratio

            # Spectral curvature features (non-linearity across 3 frequency points)
            for j, name in enumerate(feature_names_2g):
                if j < min(features_5g.shape[1], features_6g.shape[1]):
                    curvature = (features_6g[:, j] - features_5g[:, j]) - (features_5g[:, j] - features_2g[:, j])
                    combined_cols[f"curvature_{name}"] = curvature

        # Create combined feature matrix
        feature_names_combined = list(combined_cols.keys())
        X_combined = np.column_stack([combined_cols[name] for name in feature_names_combined])

        self.features_2g = features_2g
        self.features_5g = features_5g
        self.features_6g = features_6g
        self.combined_features = X_combined
        self.feature_names = feature_names_combined

        logger.info(f"Created {band_label} feature vector with {len(feature_names_combined)} features")

        return X_combined, feature_names_combined


# Backward compatibility alias
DualBandFeatureExtractor = TriBandFeatureExtractor


class FeatureMatrix:
    """
    Container for feature matrix with metadata and utilities.
    """

    def __init__(self, X: np.ndarray, feature_names: List[str], labels: np.ndarray = None):
        """
        Initialize feature matrix.

        Args:
            X: Feature matrix (n_samples, n_features)
            feature_names: List of feature names
            labels: Optional material class labels
        """
        self.X = X
        self.feature_names = np.array(feature_names)
        self.labels = labels
        self.n_samples, self.n_features = X.shape

    def remove_nan_rows(self) -> 'FeatureMatrix':
        """
        Remove rows with NaN values.

        Returns:
            New FeatureMatrix with NaN rows removed
        """
        valid_rows = ~np.isnan(self.X).any(axis=1)
        X_clean = self.X[valid_rows, :]

        labels_clean = self.labels[valid_rows] if self.labels is not None else None

        logger.info(f"Removed {np.sum(~valid_rows)} rows with NaN values")

        return FeatureMatrix(X_clean, self.feature_names, labels_clean)

    def compute_per_material_statistics(self) -> pd.DataFrame:
        """
        Compute mean and std of features per material class.

        Returns:
            DataFrame with per-material statistics
        """
        if self.labels is None:
            logger.error("No labels available for per-material statistics")
            return pd.DataFrame()

        stats_list = []

        for material in np.unique(self.labels):
            mask = self.labels == material
            material_features = self.X[mask, :]

            stats_row = {'material': material}

            for j, feat_name in enumerate(self.feature_names):
                stats_row[f'{feat_name}_mean'] = np.mean(material_features[:, j])
                stats_row[f'{feat_name}_std'] = np.std(material_features[:, j])

            stats_list.append(stats_row)

        return pd.DataFrame(stats_list)

    def normalize_zscore(self) -> 'FeatureMatrix':
        """
        Z-score normalize features.

        Returns:
            New FeatureMatrix with normalized features
        """
        X_mean = np.nanmean(self.X, axis=0)
        X_std = np.nanstd(self.X, axis=0)

        # Avoid division by zero
        X_std = np.where(X_std > 0, X_std, 1.0)

        X_normalized = (self.X - X_mean) / X_std

        logger.info("Applied Z-score normalization")

        return FeatureMatrix(X_normalized, self.feature_names, self.labels)

    def save_to_csv(self, output_path: str, include_labels: bool = True) -> None:
        """
        Save feature matrix to CSV.

        Args:
            output_path: Path to save CSV
            include_labels: Whether to include label column
        """
        df_dict = {name: self.X[:, i] for i, name in enumerate(self.feature_names)}

        if include_labels and self.labels is not None:
            df_dict['material_class'] = self.labels

        df = pd.DataFrame(df_dict)
        df.to_csv(output_path, index=False)

        logger.info(f"Feature matrix saved to {output_path}")


def main():
    """
    Example usage of feature extractors.
    """
    logger.info("Feature extraction example")

    # Example: Load phase statistics from preprocess_rssi.py output
    phase_stats_path = None  # './output/phase_statistics.csv'

    if phase_stats_path and Path(phase_stats_path).exists():
        phase_stats_df = pd.read_csv(phase_stats_path)

        # Extract RSSI features
        rssi_extractor = RSSIFeatureExtractor()
        X_rssi, feat_names_rssi = rssi_extractor.extract_rssi_features(phase_stats_df)

        logger.info(f"RSSI features: {X_rssi.shape}")
        logger.info(f"Feature names: {feat_names_rssi}")

    else:
        logger.info("No phase statistics file provided. Update phase_stats_path in main().")

    # Example: Synthetic CSI data
    logger.info("\nCreating synthetic CSI data example...")

    csi_extractor = CSIFeatureExtractor()

    # Synthetic amplitude and phase
    amplitude_2g = np.random.rand(100, 52) * 0.1
    phase_2g = np.random.rand(100, 52) * 2 * np.pi

    amplitude_5g = np.random.rand(100, 64) * 0.1
    phase_5g = np.random.rand(100, 64) * 2 * np.pi

    # Extract features per packet
    X_csi_2g, feat_names_csi = csi_extractor.extract_csi_packet_features(amplitude_2g, phase_2g)

    logger.info(f"CSI features (2.4 GHz): {X_csi_2g.shape}")
    logger.info(f"Feature count: {len(feat_names_csi)}")

    # Create FeatureMatrix and demonstrate utilities
    fm = FeatureMatrix(X_csi_2g, feat_names_csi)

    logger.info(f"\nFeature matrix: {fm.n_samples} samples, {fm.n_features} features")

    # Example with labels
    synthetic_labels = np.random.choice(['material_A', 'material_B', 'material_C'], size=100)
    fm_labeled = FeatureMatrix(X_csi_2g, feat_names_csi, synthetic_labels)

    # Per-material statistics
    mat_stats = fm_labeled.compute_per_material_statistics()
    logger.info(f"\nPer-material statistics:\n{mat_stats}")

    # Save
    output_dir = Path('./output')
    output_dir.mkdir(exist_ok=True)
    fm_labeled.save_to_csv(str(output_dir / 'feature_matrix.csv'))


if __name__ == '__main__':
    main()
