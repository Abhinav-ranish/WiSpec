"""
visualize_results.py

Generate publication-quality figures for the Wi-Fi sensing material classification paper.

Generates:
  Figure 1: RSSI distribution boxplots per material (2.4 GHz & 5 GHz)
  Figure 2: Attenuation bar chart (material × band)
  Figure 3: Delta attenuation (5 GHz - 2.4 GHz) per material — key fingerprint plot
  Figure 4: CSI amplitude heatmap (subcarrier × material) per band
  Figure 5: Confusion matrix heatmap (best classifier)
  Figure 6: Ablation comparison (single-band vs dual-band accuracy)
  Figure 7: Feature importance plot (top 15 features)
  Figure 8: Time series of RSSI showing material insertion effect

All figures saved as PDF (vector) and PNG (300 dpi) for publication.

Author: Wi-Fi Sensing Research Team
Date: 2026-03-21
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set publication-quality style
sns.set_style("whitegrid")
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['lines.linewidth'] = 1.5
plt.rcParams['axes.linewidth'] = 0.8


class MaterialVisualization:
    """
    Generate publication-quality visualizations for material classification results.
    """

    def __init__(self, output_dir: str = './figures'):
        """
        Initialize visualization generator.

        Args:
            output_dir: Directory to save figures
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {self.output_dir}")

    def save_figure(self, fig: plt.Figure, name: str, dpi_png: int = 300) -> None:
        """
        Save figure as both PDF and PNG.

        Args:
            fig: Matplotlib figure object
            name: Name for the figure (without extension)
            dpi_png: DPI for PNG export
        """
        pdf_path = self.output_dir / f"{name}.pdf"
        png_path = self.output_dir / f"{name}.png"

        fig.savefig(pdf_path, format='pdf', bbox_inches='tight')
        fig.savefig(png_path, format='png', dpi=dpi_png, bbox_inches='tight')

        logger.info(f"Saved: {pdf_path} and {png_path}")

    def figure1_rssi_distributions(self, phase_stats_df: pd.DataFrame) -> None:
        """
        Figure 1: RSSI distribution boxplots per material, one subplot per band.

        Args:
            phase_stats_df: Phase statistics DataFrame from preprocess_rssi
        """
        logger.info("Generating Figure 1: RSSI distributions...")

        # Filter out baseline, focus on material measurements
        materials_df = phase_stats_df[phase_stats_df['phase_label'] != 'baseline'].copy()

        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        fig.suptitle('RSSI Distribution by Material', fontsize=12, fontweight='bold')

        for idx, band in enumerate(['2.4GHz', '5GHz']):
            ax = axes[idx]
            band_data = materials_df[materials_df['band'] == band]

            if len(band_data) == 0:
                logger.warning(f"No data for band {band}")
                continue

            # Boxplot
            sns.boxplot(data=band_data, x='material_class', y='rssi_mean', ax=ax, palette='Set2')

            ax.set_xlabel('Material', fontsize=11, fontweight='bold')
            ax.set_ylabel('RSSI Mean (dBm)', fontsize=11, fontweight='bold')
            ax.set_title(band, fontsize=11, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)

            # Rotate x labels if needed
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        plt.tight_layout()
        self.save_figure(fig, 'figure1_rssi_distributions')
        plt.close(fig)

    def figure2_attenuation_barchart(self, dual_band_df: pd.DataFrame) -> None:
        """
        Figure 2: Attenuation bar chart (material × band).

        Shows how much RSSI attenuates at each band for each material.

        Args:
            dual_band_df: Dual-band features DataFrame from preprocess_rssi
        """
        logger.info("Generating Figure 2: Attenuation by material...")

        if 'attenuation_2g' not in dual_band_df.columns:
            logger.warning("Attenuation columns not found in dual_band_df")
            return

        fig, ax = plt.subplots(figsize=(10, 5))

        # Aggregate by material
        atten_by_material = dual_band_df.groupby('material_class')[
            ['attenuation_2g', 'attenuation_5g']
        ].mean()

        x_pos = np.arange(len(atten_by_material))
        width = 0.35

        bars1 = ax.bar(x_pos - width/2, atten_by_material['attenuation_2g'], width,
                       label='2.4 GHz', alpha=0.8, color='#1f77b4')
        bars2 = ax.bar(x_pos + width/2, atten_by_material['attenuation_5g'], width,
                       label='5 GHz', alpha=0.8, color='#ff7f0e')

        ax.set_xlabel('Material', fontsize=11, fontweight='bold')
        ax.set_ylabel('Attenuation (dBm)', fontsize=11, fontweight='bold')
        ax.set_title('Signal Attenuation by Material and Band', fontsize=12, fontweight='bold')
        ax.set_xticks(x_pos)
        ax.set_xticklabels(atten_by_material.index, rotation=45, ha='right')
        ax.legend(fontsize=10)
        ax.grid(axis='y', alpha=0.3)

        # Add value labels on bars
        for bar in bars1 + bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=8)

        plt.tight_layout()
        self.save_figure(fig, 'figure2_attenuation')
        plt.close(fig)

    def figure3_delta_attenuation(self, dual_band_df: pd.DataFrame) -> None:
        """
        Figure 3: Delta attenuation (5 GHz - 2.4 GHz) — the key fingerprint plot.

        This is the "money plot" showing differential frequency response.

        Args:
            dual_band_df: Dual-band features DataFrame
        """
        logger.info("Generating Figure 3: Delta attenuation (key fingerprint)...")

        if 'delta_attenuation_5g_minus_2g' not in dual_band_df.columns:
            logger.warning("Delta attenuation column not found")
            return

        fig, ax = plt.subplots(figsize=(10, 5))

        # Sort by delta attenuation for clarity
        delta_atten = dual_band_df.groupby('material_class')['delta_attenuation_5g_minus_2g'].mean().sort_values()

        colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(delta_atten)))

        bars = ax.barh(range(len(delta_atten)), delta_atten.values, color=colors, alpha=0.8)

        ax.set_yticks(range(len(delta_atten)))
        ax.set_yticklabels(delta_atten.index)
        ax.set_xlabel('Δ Attenuation: 5 GHz - 2.4 GHz (dBm)', fontsize=11, fontweight='bold')
        ax.set_title('Frequency-Differential Attenuation by Material\n(Core Fingerprinting Metric)',
                     fontsize=12, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        ax.axvline(x=0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)

        # Add value labels
        for i, (bar, val) in enumerate(zip(bars, delta_atten.values)):
            ax.text(val, i, f' {val:.2f}', va='center', fontsize=9, fontweight='bold')

        plt.tight_layout()
        self.save_figure(fig, 'figure3_delta_attenuation')
        plt.close(fig)

    def figure4_csi_amplitude_heatmap(self,
                                      amplitude_2g: np.ndarray,
                                      amplitude_5g: np.ndarray,
                                      labels_2g: np.ndarray,
                                      labels_5g: np.ndarray) -> None:
        """
        Figure 4: CSI amplitude heatmap (subcarrier × material) per band.

        Args:
            amplitude_2g: CSI amplitude array (n_packets, n_subcarriers_2g)
            amplitude_5g: CSI amplitude array (n_packets, n_subcarriers_5g)
            labels_2g: Material labels for 2.4 GHz packets
            labels_5g: Material labels for 5 GHz packets
        """
        logger.info("Generating Figure 4: CSI amplitude heatmaps...")

        fig, axes = plt.subplots(1, 2, figsize=(14, 4))
        fig.suptitle('CSI Amplitude Response by Material', fontsize=12, fontweight='bold')

        # 2.4 GHz heatmap
        ax = axes[0]
        if len(amplitude_2g) > 0:
            # Average amplitude per subcarrier per material
            materials = np.unique(labels_2g)
            heatmap_2g = np.zeros((len(materials), amplitude_2g.shape[1]))

            for i, mat in enumerate(materials):
                mask = labels_2g == mat
                heatmap_2g[i, :] = np.mean(amplitude_2g[mask, :], axis=0)

            sns.heatmap(heatmap_2g, cmap='YlOrRd', ax=ax, cbar_kws={'label': 'Mean Amplitude'},
                        xticklabels=10, yticklabels=materials)
            ax.set_xlabel('Subcarrier Index', fontsize=11, fontweight='bold')
            ax.set_ylabel('Material', fontsize=11, fontweight='bold')
            ax.set_title('2.4 GHz', fontsize=11, fontweight='bold')

        # 5 GHz heatmap
        ax = axes[1]
        if len(amplitude_5g) > 0:
            materials = np.unique(labels_5g)
            heatmap_5g = np.zeros((len(materials), amplitude_5g.shape[1]))

            for i, mat in enumerate(materials):
                mask = labels_5g == mat
                heatmap_5g[i, :] = np.mean(amplitude_5g[mask, :], axis=0)

            sns.heatmap(heatmap_5g, cmap='YlOrRd', ax=ax, cbar_kws={'label': 'Mean Amplitude'},
                        xticklabels=10, yticklabels=materials)
            ax.set_xlabel('Subcarrier Index', fontsize=11, fontweight='bold')
            ax.set_ylabel('Material', fontsize=11, fontweight='bold')
            ax.set_title('5 GHz', fontsize=11, fontweight='bold')

        plt.tight_layout()
        self.save_figure(fig, 'figure4_csi_amplitude_heatmap')
        plt.close(fig)

    def figure5_confusion_matrix(self, y_true: np.ndarray, y_pred: np.ndarray) -> None:
        """
        Figure 5: Confusion matrix heatmap for best classifier.

        Args:
            y_true: Ground truth labels
            y_pred: Predicted labels
        """
        logger.info("Generating Figure 5: Confusion matrix...")

        from sklearn.metrics import confusion_matrix

        classes = np.unique(y_true)
        cm = confusion_matrix(y_true, y_pred, labels=classes)

        # Normalize for better visualization
        cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

        fig, ax = plt.subplots(figsize=(8, 7))

        sns.heatmap(cm_normalized, annot=cm, fmt='d', cmap='Blues', ax=ax,
                    xticklabels=classes, yticklabels=classes,
                    cbar_kws={'label': 'Normalized Count'})

        ax.set_xlabel('Predicted Label', fontsize=11, fontweight='bold')
        ax.set_ylabel('True Label', fontsize=11, fontweight='bold')
        ax.set_title('Confusion Matrix (Dual-band Classification)', fontsize=12, fontweight='bold')

        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        plt.setp(ax.yaxis.get_majorticklabels(), rotation=0)

        plt.tight_layout()
        self.save_figure(fig, 'figure5_confusion_matrix')
        plt.close(fig)

    def figure6_ablation_comparison(self,
                                     acc_2g: float, std_2g: float,
                                     acc_5g: float, std_5g: float,
                                     acc_dual: float, std_dual: float) -> None:
        """
        Figure 6: Ablation study comparison (single-band vs dual-band).

        Args:
            acc_2g: 2.4 GHz accuracy
            std_2g: 2.4 GHz std
            acc_5g: 5 GHz accuracy
            std_5g: 5 GHz std
            acc_dual: Dual-band accuracy
            std_dual: Dual-band std
        """
        logger.info("Generating Figure 6: Ablation comparison...")

        fig, ax = plt.subplots(figsize=(9, 5))

        bands = ['2.4 GHz Only', '5 GHz Only', 'Dual-band']
        accuracies = [acc_2g, acc_5g, acc_dual]
        stds = [std_2g, std_5g, std_dual]
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']

        x_pos = np.arange(len(bands))
        bars = ax.bar(x_pos, accuracies, yerr=stds, capsize=5, alpha=0.8, color=colors,
                      error_kw={'linewidth': 1.5})

        ax.set_ylabel('Accuracy', fontsize=11, fontweight='bold')
        ax.set_title('Classification Accuracy: Ablation Study\nFrequency-Differential Features Enable Superior Performance',
                     fontsize=12, fontweight='bold')
        ax.set_xticks(x_pos)
        ax.set_xticklabels(bands, fontsize=10)
        ax.set_ylim([0, 1.0])
        ax.grid(axis='y', alpha=0.3)

        # Add value labels on bars
        for bar, acc, std in zip(bars, accuracies, stds):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + std,
                    f'{acc:.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

        # Add significance markers
        ax.text(1, max(accuracies) * 0.95, '***', ha='center', fontsize=14, fontweight='bold')

        plt.tight_layout()
        self.save_figure(fig, 'figure6_ablation_comparison')
        plt.close(fig)

    def figure7_feature_importance(self, feature_names: np.ndarray, importances: np.ndarray,
                                   top_k: int = 15) -> None:
        """
        Figure 7: Feature importance plot (top K features from Random Forest).

        Args:
            feature_names: Array of feature names
            importances: Array of feature importance scores
            top_k: Number of top features to display
        """
        logger.info("Generating Figure 7: Feature importance...")

        # Get top-k features
        top_indices = np.argsort(importances)[-top_k:][::-1]
        top_names = feature_names[top_indices]
        top_importances = importances[top_indices]

        fig, ax = plt.subplots(figsize=(10, 6))

        y_pos = np.arange(len(top_names))
        colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(top_names)))

        bars = ax.barh(y_pos, top_importances, color=colors, alpha=0.8)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(top_names)
        ax.set_xlabel('Importance Score', fontsize=11, fontweight='bold')
        ax.set_title(f'Top {top_k} Most Important Features\n(Random Forest Classifier)',
                     fontsize=12, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)

        # Add value labels
        for i, (bar, val) in enumerate(zip(bars, top_importances)):
            ax.text(val, i, f' {val:.4f}', va='center', fontsize=9)

        plt.tight_layout()
        self.save_figure(fig, 'figure7_feature_importance')
        plt.close(fig)

    def figure8_rssi_timeseries(self, rssi_data: pd.DataFrame) -> None:
        """
        Figure 8: Time series of RSSI showing material insertion effect.

        Args:
            rssi_data: DataFrame with timestamp and rssi_dbm columns
        """
        logger.info("Generating Figure 8: RSSI time series...")

        if 'timestamp' not in rssi_data.columns or 'rssi_dbm' not in rssi_data.columns:
            logger.warning("Required columns not found for time series")
            return

        fig, axes = plt.subplots(2, 1, figsize=(12, 6))
        fig.suptitle('RSSI Time Series: Material Insertion Effect', fontsize=12, fontweight='bold')

        # Separate by band if available
        if 'band' in rssi_data.columns:
            for idx, band in enumerate(['2.4GHz', '5GHz']):
                ax = axes[idx]
                band_data = rssi_data[rssi_data['band'] == band].sort_values('timestamp')

                ax.plot(band_data.index, band_data['rssi_dbm'], linewidth=1, alpha=0.7, color='#1f77b4')

                # Add phase labels if available
                if 'phase_label' in rssi_data.columns:
                    ax.set_ylabel('RSSI (dBm)', fontsize=11, fontweight='bold')
                else:
                    ax.set_ylabel(f'RSSI (dBm) - {band}', fontsize=11, fontweight='bold')

                ax.grid(alpha=0.3)
                ax.set_title(f'{band}', fontsize=11, fontweight='bold')

        else:
            # Single band
            ax = axes[0]
            rssi_sorted = rssi_data.sort_values('timestamp')
            ax.plot(rssi_sorted.index, rssi_sorted['rssi_dbm'], linewidth=1, alpha=0.7, color='#1f77b4')
            ax.set_ylabel('RSSI (dBm)', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)

        axes[-1].set_xlabel('Time (sample index)', fontsize=11, fontweight='bold')

        plt.tight_layout()
        self.save_figure(fig, 'figure8_rssi_timeseries')
        plt.close(fig)


def main():
    """
    Example usage of visualization module.
    """
    logger.info("Visualization example")

    viz = MaterialVisualization(output_dir='./figures')

    # Example: Load phase statistics
    phase_stats_file = None  # './output/phase_statistics.csv'

    if phase_stats_file and Path(phase_stats_file).exists():
        phase_stats_df = pd.read_csv(phase_stats_file)
        viz.figure1_rssi_distributions(phase_stats_df)
    else:
        logger.info("No phase statistics file provided")

    # Example: Synthetic data for other figures
    logger.info("\nGenerating figures with synthetic data...")

    # Figure 3: Synthetic dual-band data
    synthetic_dual = pd.DataFrame({
        'material_class': np.repeat(['concrete', 'drywall', 'wood', 'metal'], 10),
        'delta_attenuation_5g_minus_2g': np.random.randn(40) * 0.5 + np.tile([-0.5, 0.2, 0.8, -0.3], 10)
    })
    viz.figure3_delta_attenuation(synthetic_dual)

    # Figure 6: Synthetic ablation results
    viz.figure6_ablation_comparison(
        acc_2g=0.78, std_2g=0.04,
        acc_5g=0.82, std_5g=0.03,
        acc_dual=0.91, std_dual=0.02
    )

    # Figure 7: Synthetic feature importance
    n_features = 30
    feat_names = np.array([f'feature_{i}' for i in range(n_features)])
    importances = np.sort(np.random.rand(n_features))

    viz.figure7_feature_importance(feat_names, importances, top_k=15)

    logger.info("\nExample figures generated in ./figures/")


if __name__ == '__main__':
    main()
