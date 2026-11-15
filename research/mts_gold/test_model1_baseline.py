"""Numerical diagnostics and no-drop behavior for the untuned baseline."""
from pathlib import Path
import importlib.util
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "code"))
if importlib.util.find_spec("varclushi") is None:
    raise unittest.SkipTest("Install requirements-model1.txt to run the Model 1 diagnostics tests")
import model1_baseline as m


class Model1Tests(unittest.TestCase):
    def test_null_threshold_zero_variance_and_all_null_are_distinct(self):
        x = pd.DataFrame({"boundary": [1., 2., 3., 4., np.nan], "constant": [3.]*5,
                          "absent": [np.nan]*5})
        result = m.null_variance(x).set_index("feature")
        self.assertTrue(result.loc["boundary", "null_ge_20pct"])
        self.assertTrue(result.loc["constant", "zero_variance"])
        self.assertTrue(result.loc["absent", "all_null"])
        self.assertFalse(result.loc["absent", "zero_variance"])
        self.assertEqual(len(result), 3)

    def test_vif_agrees_with_inverse_and_flags_redundancy_without_deleting(self):
        rng = np.random.default_rng(42)
        a = rng.normal(size=300)
        x = pd.DataFrame({"a": a, "b": .5*a+rng.normal(size=300)})
        expected = np.diag(np.linalg.inv(x.corr()))
        result = m.vif_diagnostics(x)
        np.testing.assert_allclose(result.vif, expected)
        x["duplicate_a"] = x.a
        x["constant"] = 1.
        result = m.vif_diagnostics(x).set_index("feature")
        self.assertTrue(np.isinf(result.loc["a", "vif"]))
        self.assertTrue(np.isinf(result.loc["duplicate_a", "vif"]))
        self.assertEqual(result.loc["constant", "vif_status"], "zero_variance")
        self.assertTrue(np.isfinite(result.loc["b", "vif"]))
        self.assertEqual(len(result), 4)

    def test_imputer_and_estimator_keep_all_columns(self):
        x = pd.DataFrame({"varying": [1., 2., 3., 4., np.nan], "empty": [np.nan]*5, "constant": [2.]*5})
        estimator, scaler, medians, info = m.fit_linear(x, pd.Series([1., 1., 2., 3., 2.]))
        self.assertEqual(len(estimator.coef_), 3)
        self.assertEqual(medians["varying"], 2.5)
        self.assertEqual(medians["empty"], 0.)
        self.assertEqual(estimator.coef_[1], 0.)
        self.assertTrue(info["converged"])

    def test_permutation_importance_detects_used_feature_and_preserves_zero(self):
        rng = np.random.default_rng(1)
        x = rng.normal(size=(300, 2))
        y = x[:, 0].copy()
        pi = m.block_permutation(x, y, y, np.array([1., 0.]), ["used", "unused"], 42).set_index("feature")
        self.assertGreater(pi.loc["used", "importance_mean"], 1.)
        self.assertEqual(pi.loc["unused", "importance_mean"], 0.)

    def test_bootstrap_is_paired_and_zero_baseline_r2_is_zero(self):
        predictions = pd.DataFrame({"fold": ["F1"]*120, "y_z": np.ones(120), "z_hat": np.ones(120)})
        result = m.block_bootstrap(predictions, repeats=100)
        self.assertEqual(result["mse_improvement_ci_low"], 1.)
        self.assertTrue(result["acceptance_ci_positive"])
        self.assertEqual(m.score(np.ones(10), np.zeros(10))["r2_vs_zero"], 0.)
        self.assertEqual(m.score(np.ones(10), np.zeros(10))["directional_coverage"], 0.)

    def test_varclus_keeps_ineligible_rows_and_does_not_change_input(self):
        rng = np.random.default_rng(10)
        x = pd.DataFrame(rng.normal(size=(100, 3)), columns=["a", "b", "c"])
        x["d"] = x.a + .01*x.b
        x["constant"] = 2.
        x["absent"] = np.nan
        original = x.copy(deep=True)
        members, clusters = m.varclus_diagnostics(x)
        pd.testing.assert_frame_equal(x, original)
        self.assertEqual(len(members), len(x.columns))
        self.assertEqual(members.loc[members.feature.eq("absent"), "cluster_status"].iloc[0], "all_null")
        self.assertEqual(members.representative_suggestion.sum(), len(clusters))


if __name__ == "__main__":
    unittest.main()
