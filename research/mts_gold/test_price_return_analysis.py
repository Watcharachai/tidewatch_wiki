"""Regression checks for gap-aware MTS price/return statistics."""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "code"))
import price_return_analysis as a


class PriceReturnAnalysisTests(unittest.TestCase):
    def test_gap_is_excluded_from_intraday_return_and_variance(self):
        frame = pd.DataFrame({"symbol": ["GLD965"] * 4, "timeframe": ["30m"] * 4,
                              "timestamp": pd.to_datetime(["2025-01-01T00:00Z", "2025-01-01T00:30Z",
                                                           "2025-01-01T02:00Z", "2025-01-01T02:30Z"], utc=True),
                              "close": [100., 101., 130., 132.]})
        result, level = a.analyze_group(frame, "30m")
        self.assertTrue(pd.isna(result.simple_return.iloc[2]))
        self.assertEqual(level["excluded_noncontiguous_pairs"], 1)
        self.assertEqual(a.summary(result, "all")["return_n"], 2)
        self.assertAlmostEqual(result.delta_close_thb.iloc[3], 2.)

    def test_log_return_and_drawdown_have_correct_peak_and_trough(self):
        times = pd.date_range("2025-01-01T00:00Z", periods=4, freq="60min")
        frame = pd.DataFrame({"symbol": ["GLD9999"] * 4, "timeframe": ["60m"] * 4,
                              "timestamp": times, "close": [100., 120., 90., 110.]})
        result, level = a.analyze_group(frame, "60m")
        self.assertAlmostEqual(result.log_return.iloc[2], np.log(90/120))
        self.assertAlmostEqual(level["max_drawdown_pct"], -25.)
        self.assertEqual(level["drawdown_peak_timestamp"], times[1].isoformat())
        self.assertEqual(level["drawdown_trough_timestamp"], times[2].isoformat())


if __name__ == "__main__":
    unittest.main()
