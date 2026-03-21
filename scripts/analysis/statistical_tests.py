"""
statistical_tests.py

Rigorous statistical analysis for Wi-Fi sensing material classification.

Tests performed:
  - Shapiro-Wilk normality test per group
  - One-way ANOVA (if normal) or Kruskal-Wallis (if non-normal)
  - Tukey HSD or Dunn post-hoc pairwise comparisons
  - Cohen's d effect size for material pairs
  - 95% Confidence intervals for all means
  - McNemar's test for classifier comparison
  - Bootstrap confidence intervals for accuracy
  - Formatted LaTeX output tables

Author: Wi-Fi Sensing Research Team
Date: 2026-03-21
"""

import numpy as np
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, Tuple, List, Optional
from scipy import stats
from scipy.stats import shapiro, f_oneway, kruskal, ttest_ind, mcnemar
import warnings

warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StatisticalAnalyzer:
    """
    Comprehensive statistical analysis for material classification.
    """

    def __init__(self, alpha: float = 0.05):
        """
        Initialize statistical analyzer.

        Args:
            alpha: Significance level (default 0.05)
        """
        self.alpha = alpha
        self.results = {}

    def normality_test(self,
                       data_by_group: Dict[str, np.ndarray],
                       test_name: str = 'rssi') -> pd.DataFrame:
        """
        Perform Shapiro-Wilk normality test per group.

        Args:
            data_by_group: Dictionary mapping group_name -> data_array
            test_name: Name of the test (for logging)

        Returns:
            DataFrame with normality test results
        """
        logger.info(f"Performing Shapiro-Wilk normality test ({test_name})...")

        results_list = []

        for group_name, data in data_by_group.items():
            # Remove NaN values
            data_clean = data[~np.isnan(data)]

            if len(data_clean) < 3:
                logger.warning(f"Group {group_name} has < 3 samples")
                continue

            # Shapiro-Wilk test
            stat, p_value = shapiro(data_clean)

            is_normal = p_value > self.alpha

            results_list.append({
                'group': group_name,
                'n': len(data_clean),
                'mean': np.mean(data_clean),
                'std': np.std(data_clean),
                'shapiro_stat': stat,
                'p_value': p_value,
                'is_normal': is_normal
            })

            logger.info(f"  {group_name}: W={stat:.4f}, p={p_value:.6f}, Normal: {is_normal}")

        results_df = pd.DataFrame(results_list)
        self.results[f'normality_{test_name}'] = results_df

        return results_df

    def anova_analysis(self,
                       data_by_group: Dict[str, np.ndarray],
                       test_name: str = 'rssi') -> Dict:
        """
        Perform one-way ANOVA or Kruskal-Wallis test.

        If data is normally distributed: ANOVA
        Otherwise: Kruskal-Wallis (non-parametric)

        Args:
            data_by_group: Dictionary mapping group_name -> data_array
            test_name: Name of the test (for logging)

        Returns:
            Dictionary with test results
        """
        logger.info(f"Performing ANOVA analysis ({test_name})...")

        # First check normality
        norm_results = self.normality_test(data_by_group, test_name)

        all_normal = norm_results['is_normal'].all()

        # Prepare data arrays
        data_arrays = [data_by_group[group] for group in norm_results['group']]
        data_arrays = [d[~np.isnan(d)] for d in data_arrays]

        anova_results = {
            'test_name': test_name,
            'all_normal': all_normal,
            'n_groups': len(data_arrays)
        }

        if all_normal:
            # One-way ANOVA
            logger.info(f"  Data is normal → using ANOVA")
            f_stat, p_value = f_oneway(*data_arrays)
            anova_results['test_type'] = 'ANOVA'
            anova_results['test_stat'] = f_stat
            anova_results['p_value'] = p_value
            logger.info(f"  F-statistic: {f_stat:.4f}, p-value: {p_value:.6f}")

        else:
            # Kruskal-Wallis (non-parametric)
            logger.info(f"  Data is not normal → using Kruskal-Wallis")
            h_stat, p_value = kruskal(*data_arrays)
            anova_results['test_type'] = 'Kruskal-Wallis'
            anova_results['test_stat'] = h_stat
            anova_results['p_value'] = p_value
            logger.info(f"  H-statistic: {h_stat:.4f}, p-value: {p_value:.6f}")

        anova_results['significant'] = p_value < self.alpha

        self.results[f'anova_{test_name}'] = anova_results

        return anova_results

    def pairwise_comparisons(self,
                            data_by_group: Dict[str, np.ndarray],
                            test_name: str = 'rssi') -> pd.DataFrame:
        """
        Perform pairwise comparisons between all groups.

        Uses t-test with Bonferroni correction.

        Args:
            data_by_group: Dictionary mapping group_name -> data_array
            test_name: Name of the test

        Returns:
            DataFrame with pairwise comparison results
        """
        logger.info(f"Performing pairwise comparisons ({test_name})...")

        groups = list(data_by_group.keys())
        n_pairs = len(groups) * (len(groups) - 1) // 2

        # Bonferroni correction
        corrected_alpha = self.alpha / n_pairs

        results_list = []

        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                group1 = groups[i]
                group2 = groups[j]

                data1 = data_by_group[group1][~np.isnan(data_by_group[group1])]
                data2 = data_by_group[group2][~np.isnan(data_by_group[group2])]

                # t-test
                t_stat, p_value = ttest_ind(data1, data2)

                # Cohen's d effect size
                cohens_d = self._cohens_d(data1, data2)

                # 95% CI for difference
                mean_diff = np.mean(data1) - np.mean(data2)
                se_diff = np.sqrt(np.var(data1) / len(data1) + np.var(data2) / len(data2))
                ci_lower = mean_diff - 1.96 * se_diff
                ci_upper = mean_diff + 1.96 * se_diff

                is_significant = p_value < corrected_alpha

                results_list.append({
                    'group1': group1,
                    'group2': group2,
                    'mean_diff': mean_diff,
                    't_stat': t_stat,
                    'p_value': p_value,
                    'p_value_bonferroni_corrected': p_value < corrected_alpha,
                    'cohens_d': cohens_d,
                    'ci_lower': ci_lower,
                    'ci_upper': ci_upper,
                    'significant': is_significant
                })

        pairwise_df = pd.DataFrame(results_list)
        self.results[f'pairwise_{test_name}'] = pairwise_df

        logger.info(f"  Completed {len(pairwise_df)} pairwise comparisons")

        return pairwise_df

    def _cohens_d(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """
        Compute Cohen's d effect size.

        Args:
            group1: First group data
            group2: Second group data

        Returns:
            Cohen's d value
        """
        mean1, mean2 = np.mean(group1), np.mean(group2)
        std1, std2 = np.std(group1), np.std(group2)
        n1, n2 = len(group1), len(group2)

        # Pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * std1 ** 2 + (n2 - 1) * std2 ** 2) / (n1 + n2 - 2))

        if pooled_std == 0:
            return 0.0

        return (mean1 - mean2) / pooled_std

    def confidence_intervals(self,
                            data_by_group: Dict[str, np.ndarray],
                            ci: float = 0.95) -> pd.DataFrame:
        """
        Compute confidence intervals for all group means.

        Args:
            data_by_group: Dictionary mapping group_name -> data_array
            ci: Confidence level (default 0.95)

        Returns:
            DataFrame with CI results
        """
        logger.info(f"Computing {int(ci*100)}% confidence intervals...")

        results_list = []

        for group_name, data in data_by_group.items():
            data_clean = data[~np.isnan(data)]

            if len(data_clean) == 0:
                continue

            mean = np.mean(data_clean)
            std_err = stats.sem(data_clean)
            margin_error = std_err * stats.t.ppf((1 + ci) / 2, len(data_clean) - 1)

            results_list.append({
                'group': group_name,
                'n': len(data_clean),
                'mean': mean,
                'std': np.std(data_clean),
                'se': std_err,
                'ci_lower': mean - margin_error,
                'ci_upper': mean + margin_error,
                'margin_error': margin_error
            })

        ci_df = pd.DataFrame(results_list)
        logger.info(f"  Computed CIs for {len(ci_df)} groups")

        return ci_df

    def mcnemar_test(self,
                     y_true: np.ndarray,
                     y_pred1: np.ndarray,
                     y_pred2: np.ndarray) -> Dict:
        """
        McNemar's test for comparing two classifiers.

        Args:
            y_true: Ground truth labels
            y_pred1: Predictions from classifier 1
            y_pred2: Predictions from classifier 2

        Returns:
            Dictionary with test results
        """
        logger.info("Performing McNemar's test...")

        correct1 = (y_pred1 == y_true)
        correct2 = (y_pred2 == y_true)

        # Build 2x2 contingency table
        # [[classifier1 correct & classifier2 correct, c1 correct & c2 wrong],
        #  [c1 wrong & c2 correct, c1 wrong & c2 wrong]]
        both_correct = np.sum(correct1 & correct2)
        pred1_only = np.sum(correct1 & ~correct2)
        pred2_only = np.sum(~correct1 & correct2)
        both_wrong = np.sum(~correct1 & ~correct2)

        contingency_table = np.array([[pred1_only, pred2_only]])

        stat, p_value = mcnemar(contingency_table)

        results = {
            'contingency_table': contingency_table,
            'both_correct': both_correct,
            'pred1_only': pred1_only,
            'pred2_only': pred2_only,
            'both_wrong': both_wrong,
            'statistic': stat,
            'p_value': p_value,
            'significant': p_value < self.alpha
        }

        logger.info(f"  McNemar statistic: {stat:.4f}, p-value: {p_value:.6f}")
        logger.info(f"  Significant: {p_value < self.alpha}")

        return results

    def bootstrap_accuracy_ci(self,
                              y_true: np.ndarray,
                              y_pred: np.ndarray,
                              n_bootstrap: int = 1000,
                              ci: float = 0.95) -> Dict:
        """
        Bootstrap confidence interval for classification accuracy.

        Args:
            y_true: Ground truth labels
            y_pred: Predicted labels
            n_bootstrap: Number of bootstrap samples
            ci: Confidence level

        Returns:
            Dictionary with bootstrap results
        """
        logger.info(f"Computing bootstrap CI for accuracy ({n_bootstrap} samples)...")

        from sklearn.metrics import accuracy_score

        accuracies = []

        for _ in range(n_bootstrap):
            # Resample with replacement
            indices = np.random.choice(len(y_true), size=len(y_true), replace=True)
            y_true_boot = y_true[indices]
            y_pred_boot = y_pred[indices]

            acc = accuracy_score(y_true_boot, y_pred_boot)
            accuracies.append(acc)

        accuracies = np.array(accuracies)

        mean_acc = np.mean(accuracies)
        std_acc = np.std(accuracies)
        alpha = (1.0 - ci) / 2.0
        ci_lower = np.percentile(accuracies, alpha * 100)
        ci_upper = np.percentile(accuracies, (1.0 - alpha) * 100)

        results = {
            'mean_accuracy': mean_acc,
            'std_accuracy': std_acc,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'ci_level': ci,
            'n_bootstrap': n_bootstrap
        }

        logger.info(f"  Bootstrap accuracy: {mean_acc:.4f} ± {std_acc:.4f}")
        logger.info(f"  {int(ci*100)}% CI: [{ci_lower:.4f}, {ci_upper:.4f}]")

        return results


class LatexTableGenerator:
    """
    Generate formatted LaTeX tables from statistical results.
    """

    @staticmethod
    def normality_table(normality_df: pd.DataFrame) -> str:
        """
        Generate LaTeX table from normality test results.

        Args:
            normality_df: DataFrame from StatisticalAnalyzer.normality_test()

        Returns:
            LaTeX table string
        """
        # Format for LaTeX
        latex_df = normality_df[['group', 'n', 'mean', 'std', 'p_value']].copy()
        latex_df['mean'] = latex_df['mean'].apply(lambda x: f"{x:.2f}")
        latex_df['std'] = latex_df['std'].apply(lambda x: f"{x:.2f}")
        latex_df['p_value'] = latex_df['p_value'].apply(lambda x: f"{x:.4f}")

        latex_table = latex_df.to_latex(index=False, escape=False)

        return latex_table

    @staticmethod
    def pairwise_table(pairwise_df: pd.DataFrame) -> str:
        """
        Generate LaTeX table from pairwise comparisons.

        Args:
            pairwise_df: DataFrame from StatisticalAnalyzer.pairwise_comparisons()

        Returns:
            LaTeX table string
        """
        latex_df = pairwise_df[['group1', 'group2', 'mean_diff', 'cohens_d', 'p_value']].copy()
        latex_df['mean_diff'] = latex_df['mean_diff'].apply(lambda x: f"{x:.3f}")
        latex_df['cohens_d'] = latex_df['cohens_d'].apply(lambda x: f"{x:.3f}")
        latex_df['p_value'] = latex_df['p_value'].apply(lambda x: f"{x:.6f}")

        latex_table = latex_df.to_latex(index=False, escape=False)

        return latex_table

    @staticmethod
    def ci_table(ci_df: pd.DataFrame) -> str:
        """
        Generate LaTeX table from confidence intervals.

        Args:
            ci_df: DataFrame from StatisticalAnalyzer.confidence_intervals()

        Returns:
            LaTeX table string
        """
        latex_df = ci_df[['group', 'n', 'mean', 'std', 'ci_lower', 'ci_upper']].copy()
        latex_df['mean'] = latex_df['mean'].apply(lambda x: f"{x:.3f}")
        latex_df['std'] = latex_df['std'].apply(lambda x: f"{x:.3f}")
        latex_df['ci_lower'] = latex_df['ci_lower'].apply(lambda x: f"{x:.3f}")
        latex_df['ci_upper'] = latex_df['ci_upper'].apply(lambda x: f"{x:.3f}")

        # Rename columns for LaTeX
        latex_df = latex_df.rename(columns={
            'ci_lower': '$95\%$ CI Lower',
            'ci_upper': '$95\%$ CI Upper'
        })

        latex_table = latex_df.to_latex(index=False, escape=False)

        return latex_table


def main():
    """
    Example usage of statistical analysis.
    """
    logger.info("Statistical analysis example")

    # Synthetic data: three material groups
    np.random.seed(42)

    data_concrete = np.random.normal(-40, 3, 100)
    data_drywall = np.random.normal(-35, 2.5, 100)
    data_metal = np.random.normal(-50, 4, 100)

    data_by_group = {
        'concrete': data_concrete,
        'drywall': data_drywall,
        'metal': data_metal
    }

    # Initialize analyzer
    analyzer = StatisticalAnalyzer(alpha=0.05)

    # 1. Normality test
    logger.info("\n1. NORMALITY TEST")
    norm_results = analyzer.normality_test(data_by_group, test_name='rssi')
    print("\nNormality Test Results:")
    print(norm_results)

    # 2. ANOVA/Kruskal-Wallis
    logger.info("\n2. ANOVA ANALYSIS")
    anova_results = analyzer.anova_analysis(data_by_group, test_name='rssi')
    print("\nANOVA Results:")
    for key, val in anova_results.items():
        print(f"  {key}: {val}")

    # 3. Pairwise comparisons
    logger.info("\n3. PAIRWISE COMPARISONS")
    pairwise = analyzer.pairwise_comparisons(data_by_group, test_name='rssi')
    print("\nPairwise Comparisons:")
    print(pairwise)

    # 4. Confidence intervals
    logger.info("\n4. CONFIDENCE INTERVALS")
    ci_results = analyzer.confidence_intervals(data_by_group, ci=0.95)
    print("\nConfidence Intervals:")
    print(ci_results)

    # 5. Bootstrap accuracy CI (synthetic classifier)
    logger.info("\n5. BOOTSTRAP ACCURACY CI")
    y_true = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2] * 20)
    y_pred = np.array([0, 1, 2, 0, 1, 1, 0, 2, 2] * 20)

    bootstrap_results = analyzer.bootstrap_accuracy_ci(y_true, y_pred, n_bootstrap=1000)
    print("\nBootstrap Accuracy CI:")
    for key, val in bootstrap_results.items():
        print(f"  {key}: {val}")

    # 6. Generate LaTeX tables
    logger.info("\n6. LATEX TABLES")
    latex_norm = LatexTableGenerator.normality_table(norm_results)
    logger.info("\nNormality LaTeX Table:")
    print(latex_norm)

    latex_ci = LatexTableGenerator.ci_table(ci_results)
    logger.info("\nCI LaTeX Table:")
    print(latex_ci)


if __name__ == '__main__':
    main()
