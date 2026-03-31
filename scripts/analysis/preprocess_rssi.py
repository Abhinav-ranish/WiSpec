"""
preprocess_rssi.py

Load, clean, and compute tri-band RSSI statistics from Wi-Fi sensing experiments.

This module:
  - Loads CSV data from dual_band_rssi_collector.py (supports 2.4, 5, and 6 GHz)
  - Removes outliers (3-sigma rule per phase)
  - Computes per-phase statistics (mean, std, median, IQR)
  - Derives tri-band features (pairwise delta_rssi, ratio_rssi, attenuation, spectral curvature)
  - Outputs cleaned DataFrame and summary statistics

Author: Wi-Fi Sensing Research Team
Date: 2026-03-21
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Tuple, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RSSIPreprocessor:
    """
    Preprocessor for tri-band Wi-Fi RSSI measurements (2.4, 5, and 6 GHz).

    Handles loading, cleaning, and feature engineering on raw RSSI CSV data.
    Backward-compatible with dual-band (2.4 + 5 GHz) data.
    """

    EXPECTED_COLUMNS = [
        'timestamp', 'trial_id', 'phase_label', 'material_class', 'band',
        'channel', 'frequency_mhz', 'rssi_dbm', 'noise_dbm', 'snr_db',
        'tx_bitrate_mbps', 'rx_bitrate_mbps', 'link_quality', 'ping_ms',
        'ping_jitter_ms', 'environment_id', 'notes'
    ]

    def __init__(self, outlier_threshold: float = 3.0):
        """
        Initialize the RSSI preprocessor.

        Args:
            outlier_threshold: Number of standard deviations for outlier detection (default: 3.0)
        """
        self.outlier_threshold = outlier_threshold
        self.raw_data = None
        self.cleaned_data = None
        self.statistics = {}

    def load_csv_files(self, csv_paths: List[str]) -> pd.DataFrame:
        """
        Load one or more CSV files from RSSI measurements.

        Args:
            csv_paths: List of paths to CSV files

        Returns:
            Concatenated DataFrame from all CSV files
        """
        dataframes = []

        for path in csv_paths:
            try:
                logger.info(f"Loading CSV: {path}")
                df = pd.read_csv(path)

                # Validate schema
                missing_cols = set(self.EXPECTED_COLUMNS) - set(df.columns)
                if missing_cols:
                    logger.warning(f"Missing columns in {path}: {missing_cols}")

                # Convert timestamp to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

                # Ensure numeric columns are proper type
                numeric_cols = ['rssi_dbm', 'noise_dbm', 'snr_db', 'frequency_mhz',
                                'tx_bitrate_mbps', 'rx_bitrate_mbps', 'ping_ms',
                                'ping_jitter_ms', 'link_quality']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                dataframes.append(df)
                logger.info(f"Loaded {len(df)} records from {path}")

            except Exception as e:
                logger.error(f"Error loading {path}: {e}")

        if not dataframes:
            raise ValueError("No valid CSV files loaded")

        self.raw_data = pd.concat(dataframes, ignore_index=True)
        logger.info(f"Total records loaded: {len(self.raw_data)}")

        return self.raw_data

    def detect_and_remove_outliers(self) -> Tuple[pd.DataFrame, Dict]:
        """
        Remove RSSI outliers using 3-sigma rule per phase.

        Computes mean and std of RSSI within each (trial_id, phase_label, band)
        group, then flags values beyond mean ± threshold*std.

        Returns:
            Tuple of (cleaned_data, outlier_stats)
        """
        if self.raw_data is None:
            raise ValueError("No data loaded. Call load_csv_files() first.")

        cleaned = self.raw_data.copy()
        outlier_stats = {
            'total_records': len(cleaned),
            'outliers_removed': 0,
            'outlier_indices': []
        }

        # Group by trial, phase, and band
        groupby_cols = ['trial_id', 'phase_label', 'band']

        for group_key, group_df in cleaned.groupby(groupby_cols):
            if len(group_df) < 3:  # Need at least 3 points for sigma
                continue

            idx = group_df.index
            rssi_values = group_df['rssi_dbm'].values

            # Compute mean and std
            mean_rssi = np.nanmean(rssi_values)
            std_rssi = np.nanstd(rssi_values)

            # Flag outliers
            lower_bound = mean_rssi - self.outlier_threshold * std_rssi
            upper_bound = mean_rssi + self.outlier_threshold * std_rssi

            outlier_mask = (rssi_values < lower_bound) | (rssi_values > upper_bound)
            outlier_idx = idx[outlier_mask]

            outlier_stats['outliers_removed'] += len(outlier_idx)
            outlier_stats['outlier_indices'].extend(outlier_idx.tolist())

        # Remove outliers
        cleaned = cleaned.drop(outlier_stats['outlier_indices'], errors='ignore')
        self.cleaned_data = cleaned.reset_index(drop=True)

        logger.info(f"Removed {outlier_stats['outliers_removed']} outliers "
                    f"({100*outlier_stats['outliers_removed']/outlier_stats['total_records']:.2f}%)")

        return self.cleaned_data, outlier_stats

    def compute_phase_statistics(self) -> pd.DataFrame:
        """
        Compute per-phase statistics: mean, std, median, IQR for RSSI and SNR.

        Returns:
            DataFrame with one row per (trial, phase, band) group
        """
        if self.cleaned_data is None:
            raise ValueError("Data not cleaned. Call detect_and_remove_outliers() first.")

        groupby_cols = ['trial_id', 'phase_label', 'band', 'material_class', 'environment_id']

        stats_list = []

        for group_key, group_df in self.cleaned_data.groupby(groupby_cols):
            rssi = group_df['rssi_dbm'].values
            snr = group_df['snr_db'].values

            # Remove NaN values
            rssi_clean = rssi[~np.isnan(rssi)]
            snr_clean = snr[~np.isnan(snr)]

            if len(rssi_clean) == 0:
                continue

            stats_row = {
                'trial_id': group_key[0],
                'phase_label': group_key[1],
                'band': group_key[2],
                'material_class': group_key[3],
                'environment_id': group_key[4],
                'n_samples': len(rssi_clean),
                'rssi_mean': np.mean(rssi_clean),
                'rssi_std': np.std(rssi_clean),
                'rssi_median': np.median(rssi_clean),
                'rssi_q1': np.percentile(rssi_clean, 25),
                'rssi_q3': np.percentile(rssi_clean, 75),
                'rssi_iqr': np.percentile(rssi_clean, 75) - np.percentile(rssi_clean, 25),
                'snr_mean': np.mean(snr_clean),
                'snr_std': np.std(snr_clean),
                'snr_median': np.median(snr_clean),
            }

            stats_list.append(stats_row)

        stats_df = pd.DataFrame(stats_list)
        self.statistics['phase_stats'] = stats_df

        logger.info(f"Computed statistics for {len(stats_df)} phase groups")

        return stats_df

    def compute_dual_band_features(self) -> pd.DataFrame:
        """
        Compute tri-band differential features (backward-compatible: works with 2 or 3 bands).

        For each trial and phase, pair measurements across available bands:
          Pairwise differentials:
          - delta_rssi_5g_minus_2g = rssi_5g - rssi_2.4g
          - delta_rssi_6g_minus_2g = rssi_6g - rssi_2.4g (if 6 GHz available)
          - delta_rssi_6g_minus_5g = rssi_6g - rssi_5g (if 6 GHz available)
          Attenuation relative to baseline:
          - attenuation_2g, attenuation_5g, attenuation_6g
          - delta_attenuation for all band pairs
          Tri-band spectral curvature:
          - spectral_curvature = (atten_6g - atten_5g) - (atten_5g - atten_2g)

        Returns:
            DataFrame with tri-band features
        """
        if self.statistics.get('phase_stats') is None:
            raise ValueError("Phase statistics not computed. Call compute_phase_statistics() first.")

        phase_stats = self.statistics['phase_stats']

        # Detect available bands
        available_bands = phase_stats['band'].unique().tolist()
        has_6g = '6GHz' in available_bands
        logger.info(f"Available bands: {available_bands}")

        # Find baseline (control) phase for each trial/material/environment
        baseline_stats = phase_stats[phase_stats['phase_label'] == 'baseline'].copy()

        if len(baseline_stats) == 0:
            logger.warning("No baseline phase found. Using overall mean RSSI as baseline.")
            baseline_rssi_2g = phase_stats[phase_stats['band'] == '2.4GHz']['rssi_mean'].mean()
            baseline_rssi_5g = phase_stats[phase_stats['band'] == '5GHz']['rssi_mean'].mean()
            baseline_rssi_6g = phase_stats[phase_stats['band'] == '6GHz']['rssi_mean'].mean() if has_6g else np.nan
        else:
            baseline_rssi_2g = baseline_stats[baseline_stats['band'] == '2.4GHz']['rssi_mean'].mean()
            baseline_rssi_5g = baseline_stats[baseline_stats['band'] == '5GHz']['rssi_mean'].mean()
            baseline_rssi_6g = baseline_stats[baseline_stats['band'] == '6GHz']['rssi_mean'].mean() if has_6g else np.nan

        # Pivot to get all bands side by side
        pivot_cols = ['trial_id', 'phase_label', 'material_class', 'environment_id']

        rssi_pivot = phase_stats.pivot_table(
            index=pivot_cols,
            columns='band',
            values='rssi_mean',
            aggfunc='first'
        ).reset_index()

        rssi_pivot.columns.name = None

        # Ensure required bands present
        required_bands = ['2.4GHz', '5GHz']
        if not all(b in rssi_pivot.columns for b in required_bands):
            logger.warning("Not all trials have both 2.4 GHz and 5 GHz measurements")
            rssi_pivot = rssi_pivot.dropna(subset=required_bands)

        # --- Dual-band features (always computed) ---
        rssi_pivot['delta_rssi_5g_minus_2g'] = rssi_pivot['5GHz'] - rssi_pivot['2.4GHz']

        rssi_pivot['ratio_rssi_5g_div_2g'] = np.where(
            rssi_pivot['2.4GHz'] != 0,
            rssi_pivot['5GHz'] / rssi_pivot['2.4GHz'],
            np.nan
        )

        # Attenuation (positive values = signal loss relative to baseline)
        rssi_pivot['attenuation_2g'] = baseline_rssi_2g - rssi_pivot['2.4GHz']
        rssi_pivot['attenuation_5g'] = baseline_rssi_5g - rssi_pivot['5GHz']

        rssi_pivot['delta_attenuation_5g_minus_2g'] = rssi_pivot['attenuation_5g'] - rssi_pivot['attenuation_2g']

        rssi_pivot['ratio_attenuation_5g_div_2g'] = np.where(
            rssi_pivot['attenuation_2g'] != 0,
            rssi_pivot['attenuation_5g'] / rssi_pivot['attenuation_2g'],
            np.nan
        )

        # --- 6 GHz features (computed if 6 GHz data available) ---
        if has_6g and '6GHz' in rssi_pivot.columns:
            logger.info("Computing 6 GHz tri-band features...")

            rssi_pivot['delta_rssi_6g_minus_2g'] = rssi_pivot['6GHz'] - rssi_pivot['2.4GHz']
            rssi_pivot['delta_rssi_6g_minus_5g'] = rssi_pivot['6GHz'] - rssi_pivot['5GHz']

            rssi_pivot['ratio_rssi_6g_div_2g'] = np.where(
                rssi_pivot['2.4GHz'] != 0,
                rssi_pivot['6GHz'] / rssi_pivot['2.4GHz'],
                np.nan
            )
            rssi_pivot['ratio_rssi_6g_div_5g'] = np.where(
                rssi_pivot['5GHz'] != 0,
                rssi_pivot['6GHz'] / rssi_pivot['5GHz'],
                np.nan
            )

            # 6 GHz attenuation
            rssi_pivot['attenuation_6g'] = baseline_rssi_6g - rssi_pivot['6GHz']

            rssi_pivot['delta_attenuation_6g_minus_2g'] = rssi_pivot['attenuation_6g'] - rssi_pivot['attenuation_2g']
            rssi_pivot['delta_attenuation_6g_minus_5g'] = rssi_pivot['attenuation_6g'] - rssi_pivot['attenuation_5g']

            rssi_pivot['ratio_attenuation_6g_div_2g'] = np.where(
                rssi_pivot['attenuation_2g'] != 0,
                rssi_pivot['attenuation_6g'] / rssi_pivot['attenuation_2g'],
                np.nan
            )

            # Tri-band spectral curvature: measures non-linearity of attenuation across frequency
            # Positive curvature = attenuation accelerates at higher freq (e.g., concrete)
            # Negative curvature = attenuation decelerates (e.g., glass)
            rssi_pivot['spectral_curvature'] = (
                rssi_pivot['delta_attenuation_6g_minus_5g'] -
                rssi_pivot['delta_attenuation_5g_minus_2g']
            )

        self.statistics['dual_band_features'] = rssi_pivot

        n_bands = 3 if has_6g else 2
        logger.info(f"Computed {n_bands}-band features for {len(rssi_pivot)} trial phases")

        return rssi_pivot

    def save_cleaned_data(self, output_path: str) -> None:
        """
        Save cleaned data to CSV.

        Args:
            output_path: Path to save cleaned CSV
        """
        if self.cleaned_data is None:
            raise ValueError("Data not cleaned. Call detect_and_remove_outliers() first.")

        self.cleaned_data.to_csv(output_path, index=False)
        logger.info(f"Cleaned data saved to {output_path}")

    def save_statistics(self, output_dir: str) -> None:
        """
        Save all summary statistics to CSV files.

        Args:
            output_dir: Directory to save statistics files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if 'phase_stats' in self.statistics:
            phase_stats_path = output_path / 'phase_statistics.csv'
            self.statistics['phase_stats'].to_csv(phase_stats_path, index=False)
            logger.info(f"Phase statistics saved to {phase_stats_path}")

        if 'dual_band_features' in self.statistics:
            dual_band_path = output_path / 'dual_band_features.csv'
            self.statistics['dual_band_features'].to_csv(dual_band_path, index=False)
            logger.info(f"Dual-band features saved to {dual_band_path}")

    def get_summary_report(self) -> str:
        """
        Generate a summary report of preprocessing results.

        Returns:
            Formatted string report
        """
        report = []
        report.append("=" * 70)
        report.append("RSSI PREPROCESSING SUMMARY")
        report.append("=" * 70)

        if self.raw_data is not None:
            report.append(f"\nRaw data records: {len(self.raw_data)}")

        if self.cleaned_data is not None:
            report.append(f"Cleaned data records: {len(self.cleaned_data)}")
            report.append(f"Outliers removed: {len(self.raw_data) - len(self.cleaned_data)}")

        if 'phase_stats' in self.statistics:
            phase_stats = self.statistics['phase_stats']
            report.append(f"\nPhase groups: {len(phase_stats)}")
            report.append(f"Unique materials: {phase_stats['material_class'].nunique()}")
            report.append(f"Unique environments: {phase_stats['environment_id'].nunique()}")
            report.append(f"Bands: {phase_stats['band'].unique().tolist()}")

        if 'dual_band_features' in self.statistics:
            dual_features = self.statistics['dual_band_features']
            report.append(f"\nMulti-band feature samples: {len(dual_features)}")
            report.append(f"\nDelta RSSI (5G - 2.4G) statistics:")
            report.append(f"  Mean: {dual_features['delta_rssi_5g_minus_2g'].mean():.2f} dBm")
            report.append(f"  Std:  {dual_features['delta_rssi_5g_minus_2g'].std():.2f} dBm")
            report.append(f"  Min:  {dual_features['delta_rssi_5g_minus_2g'].min():.2f} dBm")
            report.append(f"  Max:  {dual_features['delta_rssi_5g_minus_2g'].max():.2f} dBm")

            report.append(f"\nDelta Attenuation (5G - 2.4G) statistics:")
            report.append(f"  Mean: {dual_features['delta_attenuation_5g_minus_2g'].mean():.2f} dBm")
            report.append(f"  Std:  {dual_features['delta_attenuation_5g_minus_2g'].std():.2f} dBm")

            # 6 GHz features if available
            if 'delta_rssi_6g_minus_2g' in dual_features.columns:
                report.append(f"\nDelta RSSI (6G - 2.4G) statistics:")
                report.append(f"  Mean: {dual_features['delta_rssi_6g_minus_2g'].mean():.2f} dBm")
                report.append(f"  Std:  {dual_features['delta_rssi_6g_minus_2g'].std():.2f} dBm")
                report.append(f"\nDelta RSSI (6G - 5G) statistics:")
                report.append(f"  Mean: {dual_features['delta_rssi_6g_minus_5g'].mean():.2f} dBm")
                report.append(f"  Std:  {dual_features['delta_rssi_6g_minus_5g'].std():.2f} dBm")
                report.append(f"\nSpectral Curvature statistics:")
                report.append(f"  Mean: {dual_features['spectral_curvature'].mean():.2f} dBm")
                report.append(f"  Std:  {dual_features['spectral_curvature'].std():.2f} dBm")

        report.append("=" * 70)

        return "\n".join(report)


def main():
    """
    Example usage of RSSIPreprocessor.
    """
    # Example: Load CSV files
    csv_files = [
        # '/path/to/rssi_data_trial_1.csv',
        # '/path/to/rssi_data_trial_2.csv',
    ]

    if not csv_files or not all(Path(f).exists() for f in csv_files):
        logger.error("No valid CSV files found. Update csv_files in main().")
        return

    # Initialize preprocessor
    preprocessor = RSSIPreprocessor(outlier_threshold=3.0)

    # Load data
    raw_df = preprocessor.load_csv_files(csv_files)

    # Clean outliers
    cleaned_df, outlier_stats = preprocessor.detect_and_remove_outliers()

    # Compute statistics
    phase_stats = preprocessor.compute_phase_statistics()

    # Compute dual-band features
    dual_band = preprocessor.compute_dual_band_features()

    # Save outputs
    output_dir = Path('./output')
    output_dir.mkdir(exist_ok=True)

    preprocessor.save_cleaned_data(str(output_dir / 'rssi_cleaned.csv'))
    preprocessor.save_statistics(str(output_dir))

    # Print summary
    print(preprocessor.get_summary_report())


if __name__ == '__main__':
    main()
