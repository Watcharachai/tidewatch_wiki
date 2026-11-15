"""Causal rolling features, fold-local seeds and gap-aware targets."""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "code"))
import prepare_baseline as b


def sample():
    times = pd.date_range("2025-12-29", periods=160, freq="h", tz="UTC")
    f = pd.DataFrame({"timestamp": times, "available_at": times+pd.Timedelta(hours=1),
                      "symbol": "GLD965", "close": 100*np.exp(np.sin(np.arange(160)/7)*.01)})
    for name in ("mts965", "mts9999", "mts_xauusd", "btcusdt"):
        f[name+"_60m_observed_at"] = times
        for lag in (1, 5, 30):
            f[f"{name}_60m_return_lag{lag}"] = f.close/f.close.shift(lag)-1
            f[f"{name}_60m_elapsed_min_lag{lag}"] = (f.timestamp-f.timestamp.shift(lag)).dt.total_seconds()/60
    return f


class BaselineTests(unittest.TestCase):
    def test_targets_and_new_year_are_preserved_without_fixed_year_split(self):
        raw = sample()
        f, groups = b.engineer(raw, "GLD965")
        self.assertAlmostEqual(f.y_next_log_return.iloc[40], np.log(raw.close.iloc[41]/raw.close.iloc[40]))
        self.assertAlmostEqual(f.y_model2_log_abs.iloc[40], np.log(1e-6+abs(f.y_next_log_return.iloc[40])))
        self.assertEqual(int(f.label_valid.sum()), len(f)-1)
        self.assertNotIn("split", f)
        self.assertLessEqual(len(groups["model1_core"]), 25)
        for cols in groups.values():
            self.assertFalse(any(c.startswith("y_") for c in cols))

    def test_rolling_features_have_no_future_dependency(self):
        raw = sample()
        f, groups = b.engineer(raw, "GLD965")
        changed = raw.copy()
        changed.loc[100:, "close"] *= 2
        later, _ = b.engineer(changed, "GLD965")
        pd.testing.assert_frame_equal(f.loc[:99, groups["engineered_numeric"]],
                                      later.loc[:99, groups["engineered_numeric"]])
        self.assertAlmostEqual(f.price_min7.iloc[50], raw.close.iloc[44:51].min())
        self.assertAlmostEqual(f.return_var15.iloc[50], f.own_log_return.iloc[36:51].var())

    def test_gap_labels_missing_but_return_windows_span_sessions(self):
        raw = sample().drop(index=50)
        f, _ = b.engineer(raw, "GLD965")
        self.assertTrue(pd.isna(f.y_next_log_return.iloc[49]))
        self.assertTrue(pd.isna(f.own_log_return.iloc[50]))
        self.assertEqual(f.session_open_flag.iloc[50], 1)
        self.assertAlmostEqual(f.return_var30.iloc[50], f.return_var30.iloc[49])

    def test_fold_seed_uses_train_only_and_embargo_is_enforced(self):
        f, _ = b.engineer(sample(), "GLD965")
        bounds = [f.available_at.iloc[i].isoformat() for i in (0, 70, 100, 150)]
        train, val, info = b.materialize_fold(f, *bounds)
        self.assertAlmostEqual(info["ewma_seed_variance"], f.own_log_return.iloc[:70].pow(2).mean())
        self.assertTrue(train.label_available_at.lt(pd.Timestamp(bounds[1])).all())
        changed = f.copy()
        changed.loc[100:, "own_log_return"] *= 100
        altered, _, new_info = b.materialize_fold(changed, *bounds)
        pd.testing.assert_frame_equal(train, altered)
        self.assertEqual(info["ewma_seed_variance"], new_info["ewma_seed_variance"])
        self.assertTrue(val.sigma_t.notna().all())
        with self.assertRaises(ValueError):
            b.materialize_fold(f, *bounds, embargo_bars=29)
        with self.assertRaises(ValueError):
            b.materialize_fold(f, bounds[0], bounds[1], f.available_at.iloc[99].isoformat(), bounds[3])


if __name__ == "__main__":
    unittest.main()
