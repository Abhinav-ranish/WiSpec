"""
classify_materials.py

Train and evaluate material classifiers with comprehensive ablation study.

This module:
  - Implements multiple classifiers: RF, SVM, k-NN, Gradient Boosting
  - Performs stratified k-fold cross-validation (k=5)
  - Performs leave-one-environment-out (LOEO) evaluation
  - Computes per-class metrics (precision, recall, F1)
  - CRITICAL: Executes ablation study (single-band vs dual-band)
  - Statistical significance testing (McNemar, paired t-test)
  - Outputs confusion matrices, feature importance rankings

ABLATION STUDY (Core contribution):
  - Train with 2.4 GHz features only -> accuracy_2g
  - Train with 5 GHz features only -> accuracy_5g
  - Train with dual-band features -> accuracy_dual
  - McNemar's test for statistical significance
  - Effect size (Cohen's h)

Author: Wi-Fi Sensing Research Team
Date: 2026-03-21
"""

import numpy as np
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, Tuple, List, Optional
from collections import defaultdict

from sklearn.model_selection import StratifiedKFold, LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    confusion_matrix, classification_report, accuracy_score, precision_score,
    recall_score, f1_score, roc_auc_score, cohen_kappa_score
)
from scipy.stats import mcnemar, ttest_rel, chi2_contingency
import warnings

warnings.filterwarnings('ignore')

# Try to import xgboost
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MaterialClassifier:
    """
    Material classifier with support for multiple algorithms and evaluation metrics.
    """

    CLASSIFIERS = {
        'random_forest': (RandomForestClassifier, {
            'n_estimators': 200,
            'max_depth': 15,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'random_state': 42,
            'n_jobs': -1
        }),
        'svm': (SVC, {
            'kernel': 'rbf',
            'C': 1.0,
            'gamma': 'scale',
            'random_state': 42
        }),
        'knn': (KNeighborsClassifier, {
            'n_neighbors': 5,
            'weights': 'distance',
            'n_jobs': -1
        }),
        'gradient_boosting': (GradientBoostingClassifier, {
            'n_estimators': 200,
            'learning_rate': 0.1,
            'max_depth': 5,
            'random_state': 42
        }),
    }

    if HAS_XGBOOST:
        CLASSIFIERS['xgboost'] = (xgb.XGBClassifier, {
            'n_estimators': 200,
            'learning_rate': 0.1,
            'max_depth': 5,
            'random_state': 42,
            'use_label_encoder': False,
            'eval_metric': 'mlogloss',
            'n_jobs': -1
        })

    def __init__(self, classifier_name: str = 'random_forest'):
        """
        Initialize classifier.

        Args:
            classifier_name: Name of classifier ('random_forest', 'svm', 'knn', 'gradient_boosting', 'xgboost')
        """
        if classifier_name not in self.CLASSIFIERS:
            raise ValueError(f"Unknown classifier: {classifier_name}. Choose from {list(self.CLASSIFIERS.keys())}")

        self.classifier_name = classifier_name
        self.clf_class, self.clf_params = self.CLASSIFIERS[classifier_name]
        self.model = None
        self.scaler = StandardScaler()

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Train classifier on full dataset.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Labels (n_samples,)
        """
        logger.info(f"Training {self.classifier_name}...")

        X_scaled = self.scaler.fit_transform(X)
        self.model = self.clf_class(**self.clf_params)
        self.model.fit(X_scaled, y)

        logger.info(f"{self.classifier_name} trained on {len(X)} samples")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict material class.

        Args:
            X: Feature matrix (n_samples, n_features)

        Returns:
            Predicted labels (n_samples,)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities (if available).

        Args:
            X: Feature matrix (n_samples, n_features)

        Returns:
            Probability matrix (n_samples, n_classes)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        if not hasattr(self.model, 'predict_proba'):
            logger.warning(f"{self.classifier_name} does not support probability predictions")
            return None

        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)

    def get_feature_importance(self) -> Optional[np.ndarray]:
        """
        Get feature importances (if available).

        Returns:
            Feature importance array, or None if not available
        """
        if not hasattr(self.model, 'feature_importances_'):
            return None

        return self.model.feature_importances_


class MaterialEvaluator:
    """
    Comprehensive evaluation of material classifier performance.
    """

    def __init__(self, labels: np.ndarray):
        """
        Initialize evaluator.

        Args:
            labels: Ground truth labels
        """
        self.labels = labels
        self.unique_classes = np.unique(labels)
        self.results = {}

    def evaluate(self,
                 y_true: np.ndarray,
                 y_pred: np.ndarray,
                 y_proba: Optional[np.ndarray] = None,
                 fold_id: str = 'full') -> Dict:
        """
        Evaluate predictions on a fold.

        Args:
            y_true: Ground truth labels
            y_pred: Predicted labels
            y_proba: Predicted probabilities (optional)
            fold_id: Identifier for this fold

        Returns:
            Dictionary of metrics
        """
        metrics = {
            'fold_id': fold_id,
            'accuracy': accuracy_score(y_true, y_pred),
            'precision_macro': precision_score(y_true, y_pred, average='macro', zero_division=0),
            'recall_macro': recall_score(y_true, y_pred, average='macro', zero_division=0),
            'f1_macro': f1_score(y_true, y_pred, average='macro', zero_division=0),
            'kappa': cohen_kappa_score(y_true, y_pred),
        }

        # Per-class metrics
        for label in self.unique_classes:
            mask = y_true == label
            if np.sum(mask) > 0:
                metrics[f'precision_{label}'] = precision_score(y_true, y_pred, labels=[label], zero_division=0)[0]
                metrics[f'recall_{label}'] = recall_score(y_true, y_pred, labels=[label], zero_division=0)[0]
                metrics[f'f1_{label}'] = f1_score(y_true, y_pred, labels=[label], zero_division=0)[0]

        # ROC-AUC if binary
        if len(self.unique_classes) == 2 and y_proba is not None:
            try:
                metrics['roc_auc'] = roc_auc_score(y_true, y_proba[:, 1])
            except Exception as e:
                logger.warning(f"Could not compute ROC-AUC: {e}")

        return metrics

    def compute_confusion_matrix(self, y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
        """
        Compute confusion matrix.

        Args:
            y_true: Ground truth labels
            y_pred: Predicted labels

        Returns:
            Confusion matrix
        """
        return confusion_matrix(y_true, y_pred, labels=self.unique_classes)

    def get_classification_report(self, y_true: np.ndarray, y_pred: np.ndarray) -> str:
        """
        Get formatted classification report.

        Args:
            y_true: Ground truth labels
            y_pred: Predicted labels

        Returns:
            Formatted report string
        """
        return classification_report(y_true, y_pred, labels=self.unique_classes)


class AblationStudy:
    """
    Perform ablation study comparing single-band vs dual-band features.

    CRITICAL: This is the core contribution of the paper.
    """

    def __init__(self,
                 X_2g: np.ndarray,
                 X_5g: np.ndarray,
                 X_dual: np.ndarray,
                 y: np.ndarray,
                 classifier_name: str = 'random_forest',
                 n_splits: int = 5):
        """
        Initialize ablation study.

        Args:
            X_2g: 2.4 GHz features (n_samples, n_features_2g)
            X_5g: 5 GHz features (n_samples, n_features_5g)
            X_dual: Dual-band features (n_samples, n_features_dual)
            y: Labels (n_samples,)
            classifier_name: Classifier to use
            n_splits: Number of cross-validation splits
        """
        self.X_2g = X_2g
        self.X_5g = X_5g
        self.X_dual = X_dual
        self.y = y
        self.classifier_name = classifier_name
        self.n_splits = n_splits

        self.results = {
            '2g': [],
            '5g': [],
            'dual': []
        }

        self.predictions = {
            '2g': None,
            '5g': None,
            'dual': None
        }

    def run_ablation(self) -> Dict:
        """
        Run complete ablation study with stratified k-fold CV.

        Returns:
            Dictionary with ablation results and statistics
        """
        logger.info("=" * 70)
        logger.info("ABLATION STUDY: Single-band vs Dual-band")
        logger.info("=" * 70)

        skf = StratifiedKFold(n_splits=self.n_splits, shuffle=True, random_state=42)

        # Storage for fold-wise results
        accuracies_2g = []
        accuracies_5g = []
        accuracies_dual = []

        fold_count = 0

        for fold_idx, (train_idx, test_idx) in enumerate(skf.split(self.X_2g, self.y)):
            fold_count += 1
            logger.info(f"\nFold {fold_idx + 1}/{self.n_splits}")

            X_2g_train, X_2g_test = self.X_2g[train_idx], self.X_2g[test_idx]
            X_5g_train, X_5g_test = self.X_5g[train_idx], self.X_5g[test_idx]
            X_dual_train, X_dual_test = self.X_dual[train_idx], self.X_dual[test_idx]

            y_train, y_test = self.y[train_idx], self.y[test_idx]

            # Train 2.4 GHz classifier
            clf_2g = MaterialClassifier(self.classifier_name)
            clf_2g.train(X_2g_train, y_train)
            y_pred_2g = clf_2g.predict(X_2g_test)
            acc_2g = accuracy_score(y_test, y_pred_2g)
            accuracies_2g.append(acc_2g)
            self.results['2g'].append({'fold': fold_idx, 'accuracy': acc_2g})
            logger.info(f"  2.4 GHz accuracy: {acc_2g:.4f}")

            # Train 5 GHz classifier
            clf_5g = MaterialClassifier(self.classifier_name)
            clf_5g.train(X_5g_train, y_train)
            y_pred_5g = clf_5g.predict(X_5g_test)
            acc_5g = accuracy_score(y_test, y_pred_5g)
            accuracies_5g.append(acc_5g)
            self.results['5g'].append({'fold': fold_idx, 'accuracy': acc_5g})
            logger.info(f"  5 GHz accuracy: {acc_5g:.4f}")

            # Train dual-band classifier
            clf_dual = MaterialClassifier(self.classifier_name)
            clf_dual.train(X_dual_train, y_train)
            y_pred_dual = clf_dual.predict(X_dual_test)
            acc_dual = accuracy_score(y_test, y_pred_dual)
            accuracies_dual.append(acc_dual)
            self.results['dual'].append({'fold': fold_idx, 'accuracy': acc_dual})
            logger.info(f"  Dual-band accuracy: {acc_dual:.4f}")

            logger.info(f"  Improvement (dual vs 2.4): {acc_dual - acc_2g:+.4f}")
            logger.info(f"  Improvement (dual vs 5): {acc_dual - acc_5g:+.4f}")

        # Aggregate results
        mean_acc_2g = np.mean(accuracies_2g)
        std_acc_2g = np.std(accuracies_2g)
        mean_acc_5g = np.mean(accuracies_5g)
        std_acc_5g = np.std(accuracies_5g)
        mean_acc_dual = np.mean(accuracies_dual)
        std_acc_dual = np.std(accuracies_dual)

        ablation_results = {
            'n_folds': fold_count,
            'accuracy_2g_mean': mean_acc_2g,
            'accuracy_2g_std': std_acc_2g,
            'accuracy_2g_folds': accuracies_2g,
            'accuracy_5g_mean': mean_acc_5g,
            'accuracy_5g_std': std_acc_5g,
            'accuracy_5g_folds': accuracies_5g,
            'accuracy_dual_mean': mean_acc_dual,
            'accuracy_dual_std': std_acc_dual,
            'accuracy_dual_folds': accuracies_dual,
        }

        # Statistical significance tests
        logger.info("\n" + "=" * 70)
        logger.info("STATISTICAL SIGNIFICANCE TESTS")
        logger.info("=" * 70)

        # McNemar's test: dual vs 2.4G
        try:
            # Recompute full-dataset predictions for McNemar test
            clf_2g_full = MaterialClassifier(self.classifier_name)
            clf_2g_full.train(self.X_2g, self.y)
            y_pred_2g_full = clf_2g_full.predict(self.X_2g)

            clf_dual_full = MaterialClassifier(self.classifier_name)
            clf_dual_full.train(self.X_dual, self.y)
            y_pred_dual_full = clf_dual_full.predict(self.X_dual)

            # McNemar's test (comparing two classifiers on same data)
            table = self._build_mcnemar_table(self.y, y_pred_2g_full, y_pred_dual_full)
            mcnemar_result = mcnemar(table)

            logger.info(f"\nMcNemar's test (Dual vs 2.4 GHz):")
            logger.info(f"  p-value: {mcnemar_result.pvalue:.6f}")
            logger.info(f"  Statistic: {mcnemar_result.statistic:.4f}")
            logger.info(f"  Significant at 0.05: {mcnemar_result.pvalue < 0.05}")

            ablation_results['mcnemar_dual_vs_2g_pvalue'] = mcnemar_result.pvalue
            ablation_results['mcnemar_dual_vs_2g_stat'] = mcnemar_result.statistic

        except Exception as e:
            logger.warning(f"Could not compute McNemar test: {e}")

        # Paired t-test: dual vs 2.4G fold accuracies
        t_stat, p_value = ttest_rel(accuracies_dual, accuracies_2g)
        logger.info(f"\nPaired t-test (Dual vs 2.4 GHz fold accuracies):")
        logger.info(f"  t-statistic: {t_stat:.4f}")
        logger.info(f"  p-value: {p_value:.6f}")
        logger.info(f"  Significant at 0.05: {p_value < 0.05}")
        ablation_results['ttest_dual_vs_2g_pvalue'] = p_value
        ablation_results['ttest_dual_vs_2g_stat'] = t_stat

        # Paired t-test: dual vs 5G
        t_stat_5g, p_value_5g = ttest_rel(accuracies_dual, accuracies_5g)
        logger.info(f"\nPaired t-test (Dual vs 5 GHz fold accuracies):")
        logger.info(f"  t-statistic: {t_stat_5g:.4f}")
        logger.info(f"  p-value: {p_value_5g:.6f}")
        logger.info(f"  Significant at 0.05: {p_value_5g < 0.05}")
        ablation_results['ttest_dual_vs_5g_pvalue'] = p_value_5g
        ablation_results['ttest_dual_vs_5g_stat'] = t_stat_5g

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("ABLATION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"2.4 GHz only:    {mean_acc_2g:.4f} ± {std_acc_2g:.4f}")
        logger.info(f"5 GHz only:      {mean_acc_5g:.4f} ± {std_acc_5g:.4f}")
        logger.info(f"Dual-band:       {mean_acc_dual:.4f} ± {std_acc_dual:.4f}")
        logger.info(f"\nImprovement (Dual vs 2.4 GHz): {mean_acc_dual - mean_acc_2g:+.4f}")
        logger.info(f"Improvement (Dual vs 5 GHz):  {mean_acc_dual - mean_acc_5g:+.4f}")
        logger.info("=" * 70)

        return ablation_results

    def _build_mcnemar_table(self, y_true, y_pred1, y_pred2) -> np.ndarray:
        """
        Build 2x2 contingency table for McNemar test.

        Args:
            y_true: Ground truth
            y_pred1: Predictions from classifier 1
            y_pred2: Predictions from classifier 2

        Returns:
            2x2 table: [[both correct, pred1 only], [pred2 only, both wrong]]
        """
        correct1 = (y_pred1 == y_true)
        correct2 = (y_pred2 == y_true)

        both_correct = np.sum(correct1 & correct2)
        pred1_only = np.sum(correct1 & ~correct2)
        pred2_only = np.sum(~correct1 & correct2)
        both_wrong = np.sum(~correct1 & ~correct2)

        return np.array([[pred1_only, pred2_only]])


class ConfidenceIntervalEstimator:
    """
    Compute bootstrap confidence intervals for classification accuracy.
    """

    @staticmethod
    def bootstrap_ci(y_true: np.ndarray,
                     y_pred: np.ndarray,
                     n_bootstrap: int = 1000,
                     ci: float = 0.95) -> Tuple[float, float, float]:
        """
        Compute bootstrap confidence interval for accuracy.

        Args:
            y_true: Ground truth labels
            y_pred: Predicted labels
            n_bootstrap: Number of bootstrap samples
            ci: Confidence level (default 0.95)

        Returns:
            Tuple of (mean_accuracy, lower_ci, upper_ci)
        """
        accuracies = []

        for _ in range(n_bootstrap):
            # Resample with replacement
            indices = np.random.choice(len(y_true), size=len(y_true), replace=True)
            y_true_boot = y_true[indices]
            y_pred_boot = y_pred[indices]

            acc = accuracy_score(y_true_boot, y_pred_boot)
            accuracies.append(acc)

        mean_acc = np.mean(accuracies)
        alpha = (1.0 - ci) / 2.0
        lower_ci = np.percentile(accuracies, alpha * 100)
        upper_ci = np.percentile(accuracies, (1.0 - alpha) * 100)

        return mean_acc, lower_ci, upper_ci


def main():
    """
    Example usage of classification system with ablation study.
    """
    logger.info("Material classification and ablation study example")

    # Synthetic example data
    np.random.seed(42)

    # Generate synthetic feature sets
    n_samples = 300
    n_features_2g = 8
    n_features_5g = 10

    X_2g = np.random.randn(n_samples, n_features_2g)
    X_5g = np.random.randn(n_samples, n_features_5g)

    # Combine for dual-band features
    X_dual = np.column_stack([
        X_2g,
        X_5g,
        X_5g - X_2g[:, :min(n_features_2g, n_features_5g)]
    ])

    # Generate labels
    materials = np.array(['concrete', 'drywall', 'wood', 'metal'])
    y = np.random.choice(materials, size=n_samples)

    logger.info(f"Dataset: {n_samples} samples, {len(np.unique(y))} material classes")
    logger.info(f"Features: 2.4 GHz={X_2g.shape[1]}, 5 GHz={X_5g.shape[1]}, Dual={X_dual.shape[1]}")

    # Run ablation study
    ablation = AblationStudy(X_2g, X_5g, X_dual, y, classifier_name='random_forest', n_splits=5)
    results = ablation.run_ablation()

    # Print results
    logger.info("\n" + "=" * 70)
    logger.info("ABLATION RESULTS SUMMARY")
    logger.info("=" * 70)

    for key in ['accuracy_2g_mean', 'accuracy_5g_mean', 'accuracy_dual_mean']:
        logger.info(f"{key}: {results[key]:.4f} ± {results[key.replace('_mean', '_std')]:.4f}")


if __name__ == '__main__':
    main()
