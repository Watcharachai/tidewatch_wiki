"""Point-in-time and completeness checks for the reference feature pipeline."""

import tempfile
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "code"))
import features as f


def sample(times, volume=False):
    frame = pd.DataFrame({"timestamp": pd.to_datetime(times, utc=True), "close": np.arange(len(times)) + 100.})
    frame["available_at"] = frame.timestamp + pd.Timedelta(minutes=15)
    if volume:
        frame["volume"] = np.arange(len(times)) + 1.
        frame["open"] = frame.close
        frame["high"] = frame.close + 1
        frame["low"] = frame.close - 1
    return frame


class FeatureTests(unittest.TestCase):
    def test_lags_are_past_observations_and_record_elapsed_time(self):
        times = pd.date_range("2025-01-01T00:00Z", periods=32, freq="15min")
        frame = sample(times)
        lagged = f.lagged(frame, "mts965_15m")
        self.assertEqual(lagged.mts965_15m_close_lag30.iloc[30], 100)
        self.assertAlmostEqual(lagged.mts965_15m_return_lag5.iloc[30], 130 / 125 - 1)
        self.assertEqual(lagged.mts965_15m_elapsed_min_lag30.iloc[30], 450)
        self.assertTrue(lagged.mts965_15m_close_lag30.iloc[:30].isna().all())

    def test_asof_never_reads_future_or_stale_source(self):
        source = sample(["2025-01-01T00:00Z"])
        target = pd.DataFrame({"available_at": pd.to_datetime([
            "2025-01-01T00:10Z", "2025-01-01T00:15Z", "2025-01-02T00:15Z"], utc=True)})
        joined = f.asof_join(target, source, "xaut_15m", pd.Timedelta(hours=1))
        self.assertTrue(pd.isna(joined.xaut_15m_close.iloc[0]))
        self.assertEqual(joined.xaut_15m_close.iloc[1], 100)
        self.assertTrue(pd.isna(joined.xaut_15m_close.iloc[2]))

    def test_incomplete_binance_bucket_is_dropped(self):
        source = sample(pd.date_range("2025-01-01T00:00Z", periods=8, freq="15min"), volume=True)
        full = f.aggregate_binance(source, "60m")
        self.assertEqual(full.volume.tolist(), [10, 26])
        partial = f.aggregate_binance(source.drop(index=1), "60m")
        self.assertEqual(len(partial), 1)
        self.assertEqual(partial.timestamp.iloc[0], pd.Timestamp("2025-01-01T01:00Z"))

    def test_volume_and_availability_are_required_when_declared(self):
        source = sample(["2025-01-01T00:00Z"])
        with self.assertRaises(ValueError):
            f.validate(source, "xaut", requires_volume=True)
        with self.assertRaises(ValueError):
            f.validate(source.assign(available_at=source.timestamp - pd.Timedelta(minutes=1)), "late")

    def test_external_export_requires_explicit_availability(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "us_gold_future.csv"
            path.write_text("timestamp,close\n2025-01-01T00:00:00Z,2700\n")
            with self.assertRaises(ValueError):
                f.read_external(Path(folder), pd.Timestamp("2025-01-02T00:00Z"))
            path.write_text("timestamp,available_at,close,volume\n2025-01-01T00:00:00Z,2025-01-01T01:00:00Z,2700,100\n")
            result = f.read_external(Path(folder), pd.Timestamp("2025-01-02T00:00Z"))
            self.assertEqual(result[("us_gold_future", "1d")].volume.iloc[0], 100)
            intraday = Path(folder) / "us_gold_future_15m.csv"
            intraday.write_text("timestamp,available_at,close,volume\n2025-01-01T00:00:00Z,2025-01-01T00:15:00Z,2701,25\n")
            result = f.read_external(Path(folder), pd.Timestamp("2025-01-02T00:00Z"))
            self.assertEqual(result[("us_gold_future", "15m")].volume.iloc[0], 25)
            daily_alias = Path(folder) / "us_gold_future_1d.csv"
            daily_alias.write_text(path.read_text())
            with self.assertRaises(ValueError):
                f.read_external(Path(folder), pd.Timestamp("2025-01-02T00:00Z"))


if __name__ == "__main__":
    unittest.main()
