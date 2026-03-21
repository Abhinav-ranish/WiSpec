# Quick Start Guide — Wi-Fi Sensing Analysis Pipeline

## Installation

```bash
# Install dependencies
pip install numpy pandas scipy scikit-learn matplotlib seaborn xgboost

# Optional: for Intel 5300 CSI support
pip install csiread
```

## Basic Usage (5 minutes)

### 1. Clean RSSI Data

```python
from preprocess_rssi import RSSIPreprocessor

preprocessor = RSSIPreprocessor(outlier_threshold=3.0)
data = preprocessor.load_csv_files(['your_rssi_data.csv'])
data_clean, _ = preprocessor.detect_and_remove_outliers()
phase_stats = preprocessor.compute_phase_statistics()
dual_features = preprocessor.compute_dual_band_features()

preprocessor.save_cleaned_data('output/rssi_cleaned.csv')
preprocessor.save_statistics('output/')
print(preprocessor.get_summary_report())
```

### 2. Extract Features

```python
import pandas as pd
from feature_extraction import RSSIFeatureExtractor, FeatureMatrix

# Load phase statistics
phase_stats = pd.read_csv('output/phase_statistics.csv')

# Extract RSSI features
extractor = RSSIFeatureExtractor()
X, feat_names = extractor.extract_rssi_features(phase_stats)

# Create feature matrix
fm = FeatureMatrix(X, feat_names, labels=material_labels)
fm_clean = fm.remove_nan_rows()
fm_normalized = fm_clean.normalize_zscore()
fm_normalized.save_to_csv('output/features.csv')
```

### 3. Run Ablation Study (CRITICAL)

```python
from classify_materials import AblationStudy

# Assume: X_2g, X_5g, X_dual shape (n_samples, n_features)
# Assume: y is material labels

ablation = AblationStudy(X_2g, X_5g, X_dual, y, classifier_name='random_forest')
results = ablation.run_ablation()

print(f"2.4 GHz:   {results['accuracy_2g_mean']:.4f} ± {results['accuracy_2g_std']:.4f}")
print(f"5 GHz:     {results['accuracy_5g_mean']:.4f} ± {results['accuracy_5g_std']:.4f}")
print(f"Dual-band: {results['accuracy_dual_mean']:.4f} ± {results['accuracy_dual_std']:.4f}")
print(f"Improvement: {results['accuracy_dual_mean'] - results['accuracy_2g_mean']:+.4f}")

# Check significance
if results['ttest_dual_vs_2g_pvalue'] < 0.05:
    print("✓ Dual-band is SIGNIFICANTLY BETTER (p < 0.05)")
```

### 4. Generate Figures

```python
from visualize_results import MaterialVisualization

viz = MaterialVisualization(output_dir='./figures')

# Key figures
viz.figure3_delta_attenuation(dual_band_df)      # Fingerprint plot
viz.figure6_ablation_comparison(                 # Accuracy comparison
    acc_2g=0.78, std_2g=0.04,
    acc_5g=0.82, std_5g=0.03,
    acc_dual=0.91, std_dual=0.02
)
viz.figure7_feature_importance(feature_names, importances)

# All figures saved as PDF + PNG in ./figures/
```

### 5. Statistical Validation

```python
from statistical_tests import StatisticalAnalyzer

analyzer = StatisticalAnalyzer(alpha=0.05)

# Group RSSI measurements by material
data_by_material = {
    'concrete': rssi_concrete,
    'drywall': rssi_drywall,
    'metal': rssi_metal
}

# Run analysis
norm_results = analyzer.normality_test(data_by_material)
anova_results = analyzer.anova_analysis(data_by_material)
pairwise = analyzer.pairwise_comparisons(data_by_material)
cis = analyzer.confidence_intervals(data_by_material)

# Check significant differences
for _, row in pairwise.iterrows():
    if row['significant']:
        d = row['cohens_d']
        print(f"{row['group1']} vs {row['group2']}: "
              f"d={d:.3f}, p={row['p_value']:.6f}")
```

---

## Input Data Format

### CSV for RSSI (required columns):
```
timestamp,trial_id,phase_label,material_class,band,channel,frequency_mhz,rssi_dbm,noise_dbm,snr_db,tx_bitrate_mbps,rx_bitrate_mbps,link_quality,ping_ms,ping_jitter_ms,environment_id,notes
2024-01-15T10:00:00.000Z,trial_001,baseline,baseline,2.4GHz,6,2437,-45,80,65,72.2,54.3,70,12.5,0.5,env_a,control
```

### CSI Format:
- **Intel 5300**: `.csi` binary files (requires `csiread` library)
- **PicoScenes**: `.picoscenes` JSON format (stub provided, see preprocess_csi.py)

---

## Understanding Outputs

### Phase Statistics (`phase_statistics.csv`)
One row per (trial, phase, band) group:
```
trial_id,phase_label,band,material_class,environment_id,n_samples,rssi_mean,rssi_std,...
trial_001,baseline,2.4GHz,baseline,env_a,500,-45.2,3.1,...
trial_001,material_A,2.4GHz,material_A,env_a,500,-52.3,2.8,...
```

### Dual-Band Features (`dual_band_features.csv`)
One row per trial-phase (both bands paired):
```
trial_id,phase_label,material_class,environment_id,delta_rssi_5g_minus_2g,delta_attenuation_5g_minus_2g,...
trial_001,material_A,material_A,env_a,-4.2,1.8,...
```

**KEY FEATURE**: `delta_attenuation_5g_minus_2g` — the core fingerprinting metric

### Feature Matrix (`feature_matrix.csv`)
One row per sample, columns are features:
```
rssi_mean_2g,rssi_std_2g,rssi_mean_5g,...,delta_rssi_5g_minus_2g,...,material_class
-45.2,2.8,-50.1,...,-4.9,...,concrete
```

### Ablation Results
Printed output from `AblationStudy.run_ablation()`:
```
2.4 GHz accuracy:   0.7823 ± 0.0412
5 GHz accuracy:     0.8157 ± 0.0338
Dual-band accuracy: 0.9087 ± 0.0245

McNemar test (Dual vs 2.4):
  p-value: 0.0012 **significant**

Paired t-test (Dual vs 2.4):
  t-statistic: 5.23
  p-value: 0.0021 **significant**
```

---

## Paper-Ready Outputs

**Publication checklist:**

- [ ] Figure 3 (Delta Attenuation) — shows material fingerprints
- [ ] Figure 6 (Ablation Comparison) — proves dual-band superiority
- [ ] Feature Importance table (from Random Forest)
- [ ] LaTeX tables (normality, pairwise, CIs)
- [ ] Ablation results (accuracies + p-values)
- [ ] Confusion matrices (PDF)

**Example results snippet for Methods section:**

> We evaluated three feature sets using stratified 5-fold cross-validation on 300 labeled samples (75 per material class):
> - **2.4 GHz only**: 78.2% ± 4.1% accuracy
> - **5 GHz only**: 81.6% ± 3.4% accuracy
> - **Dual-band (with differential features)**: 90.9% ± 2.5% accuracy
>
> McNemar's test confirmed the dual-band approach is statistically significantly superior (p = 0.0012). The key innovation is leveraging frequency-differential features (Δattenuation = atten₅ₘₕz - atten₂.₄ₘₕz) which capture material-specific frequency responses.

---

## Common Issues & Solutions

### Issue: "Module not found: numpy"
**Solution:**
```bash
pip install numpy pandas scipy scikit-learn matplotlib seaborn
```

### Issue: "No data loaded" in preprocess_rssi.py
**Solution:** Update CSV file path in main():
```python
csv_files = ['/absolute/path/to/your_data.csv']
```

### Issue: "csiread not installed" in preprocess_csi.py
**Solution:** Either install csiread or use PicoScenes format:
```bash
pip install csiread
# OR use preprocess_csi.load_csi_file(..., format='picoscenes')
```

### Issue: NaN values in feature matrix
**Solution:** Call `FeatureMatrix.remove_nan_rows()` before classification:
```python
fm = FeatureMatrix(X, feat_names, labels)
fm_clean = fm.remove_nan_rows()
```

### Issue: Imbalanced classes in ablation study
**Solution:** Use stratified k-fold (already default in AblationStudy)
```python
AblationStudy(..., n_splits=5)  # Uses StratifiedKFold automatically
```

---

## Performance Tips

1. **Feature normalization:** Always normalize before training
   ```python
   fm_normalized = fm.normalize_zscore()
   ```

2. **Remove outliers:** Use 3-sigma rule in preprocess_rssi
   ```python
   preprocessor.detect_and_remove_outliers()
   ```

3. **Ablation study:** Run with k=5 folds for stable estimates
   ```python
   ablation = AblationStudy(..., n_splits=5)
   ```

4. **Large datasets:** Process in chunks
   ```python
   for chunk in chunks_of(csv_files, size=10):
       preprocessor.load_csv_files(chunk)
       # Process...
   ```

---

## For Conference Paper Submission

**Required files:**

1. **Results tables** (from statistical_tests.py):
   - Table 1: Classifier performance (accuracy, F1, kappa)
   - Table 2: Pairwise material comparisons (Cohen's d, p-values)
   - Table 3: Ablation study results

2. **Figures**:
   - Fig 1: RSSI distributions
   - Fig 2: Attenuation per band
   - **Fig 3: Delta attenuation (HIGHLIGHT THIS)**
   - Fig 4: CSI heatmaps
   - Fig 5: Confusion matrix
   - **Fig 6: Ablation results (HIGHLIGHT THIS)**
   - Fig 7: Feature importance
   - Fig 8: Time series

3. **Supplementary**:
   - Feature list (with names & descriptions)
   - Hyperparameters used
   - Dataset statistics (n_materials, n_samples, n_features)

---

## Next Steps

1. **Load your data** → run preprocess_rssi.py
2. **Extract features** → run feature_extraction.py
3. **Run ablation study** → run classify_materials.py
4. **Generate figures** → run visualize_results.py
5. **Validate statistics** → run statistical_tests.py
6. **Write paper!** 📄

---

**Questions?** Check ANALYSIS_PIPELINE.md for detailed documentation.
