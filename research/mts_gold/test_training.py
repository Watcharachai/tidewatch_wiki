"""Checks for time alignment and leakage in model-ready MTS tables."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "code"))
import training as t
from features import asof_join


class TrainingTests(unittest.TestCase):
    def test_60m_aggregation_requires_two_completed_30m_bars(self):
        times = pd.to_datetime(["2025-01-01T00:00Z", "2025-01-01T00:30Z",
                                "2025-01-01T01:00Z"], utc=True)
        bars = pd.DataFrame({"timestamp": times, "available_at": times + pd.Timedelta(minutes=30),
                             "open": [100, 101, 102], "high": [102, 104, 105],
                             "low": [99, 100, 101], "close": [101, 103, 104],
                             "volume": [2, 3, 4]})
        result = t.aggregate_60m(bars)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.close.iloc[0], 103)
        self.assertEqual(result.volume.iloc[0], 5)
        self.assertEqual(result.available_at.iloc[0], pd.Timestamp("2025-01-01T01:00Z"))

    def test_xau_join_excludes_unclosed_and_stale_bars(self):
        source = pd.DataFrame({"timestamp": pd.to_datetime(["2025-01-01T00:00Z"], utc=True),
                               "available_at": pd.to_datetime(["2025-01-01T00:30Z"], utc=True),
                               "close": [100.], "volume": [2.]})
        targets = pd.DataFrame({"available_at": pd.to_datetime([
            "2025-01-01T00:15Z", "2025-01-01T00:30Z", "2025-01-01T01:00Z"], utc=True)})
        result = asof_join(targets, source, "xauusdt_30m", pd.Timedelta(minutes=30))
        self.assertTrue(pd.isna(result.xauusdt_30m_close.iloc[0]))
        self.assertEqual(result.xauusdt_30m_close.iloc[1], 100)
        self.assertTrue(pd.isna(result.xauusdt_30m_close.iloc[2]))

    def test_labels_require_exact_next_interval_and_same_year(self):
        times = pd.to_datetime(["2025-01-01T00:00Z", "2025-01-01T00:30Z",
                                "2025-01-01T01:30Z", "2025-12-31T16:00Z",
                                "2025-12-31T16:30Z"], utc=True)
        bars = pd.DataFrame({"symbol": ["GLD965"] * len(times), "timestamp": times,
                             "available_at": times + pd.Timedelta(minutes=30),
                             "close": [100., 101., 102., 103., 104.]})
        result, audit = t.attach_labels(bars, 30)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.y_next_close.iloc[0], 101)
        self.assertAlmostEqual(result.y_next_return.iloc[0], .01)
        self.assertEqual(audit["dropped_year_boundary"], 1)

    def test_xy_feature_list_excludes_identifiers_and_future_labels(self):
        frame = pd.DataFrame({"close": [100.], "symbol": ["GLD965"], "purity_pct": [96.5],
                              "mts965_30m_return_lag1": [.01], "y_next_close": [101.],
                              "y_next_return": [.01]})
        self.assertEqual(t.feature_columns(frame), ["close", "mts965_30m_return_lag1"])

    def test_load_xy_uses_recorded_training_only_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "training_30m_GLD965.csv.gz"
            pd.DataFrame({"close": [100.], "future_only": [101.], "y_next_return": [.01]}).to_csv(path, index=False)
            (Path(folder) / "manifest.json").write_text(json.dumps({"outputs": [
                {"file": path.name, "baseline_feature_columns": ["close"]}]}))
            x, y = t.load_xy(path)
            self.assertEqual(x.columns.tolist(), ["close"])
            self.assertEqual(y.tolist(), [.01])


if __name__ == "__main__":
    unittest.main()
