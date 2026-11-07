"""Run: python -m unittest discover -s research/mts_gold -v"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

import numpy as np
import pandas as pd

import pipeline as p


def candles(times, closes=None):
    ts = pd.to_datetime(times, utc=True)
    prices = np.array(closes if closes is not None else np.arange(len(ts)) + 100, dtype=float)
    return pd.DataFrame({"timestamp": ts, "open": prices, "high": prices + 2,
                         "low": prices - 2, "close": prices + 1, "source_count": 1})


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.start = p.utc("2025-01-01T00:00:00Z")
        self.end = self.start + pd.Timedelta(days=1)
        self.payload = {"s": "ok", "t": [int(self.start.timestamp())],
                        "o": [100], "h": [110], "l": [90], "c": [105]}

    def test_valid_ohlc_and_exclusive_end(self):
        frame = p.parse_history(self.payload, self.start, self.end)
        self.assertEqual(frame.close.tolist(), [105])
        self.assertTrue(p.parse_history(self.payload, self.start - pd.Timedelta(days=1), self.start).empty)

    def test_no_data_not_forward_filled(self):
        self.assertTrue(p.parse_history({"s": "no_data", "nextTime": 100}, self.start, self.end).empty)

    def test_bad_status_and_lengths_fail(self):
        with self.assertRaises(ValueError):
            p.parse_history({"s": "error", "errmsg": "invalid resolution"}, self.start, self.end)
        self.payload["c"] = []
        with self.assertRaises(ValueError):
            p.parse_history(self.payload, self.start, self.end)

    def test_impossible_and_nonfinite_prices_fail(self):
        for close in (120, 0, float("nan"), float("inf")):
            self.payload["c"] = [close]
            with self.subTest(close=close), self.assertRaises(ValueError):
                p.parse_history(self.payload, self.start, self.end)

    def test_duplicate_conflict_and_closed_bar_cutoff(self):
        frame = p.parse_history(self.payload, self.start, self.end)
        result = p.clean_bars([frame, frame], pd.Timedelta(minutes=15), self.start + pd.Timedelta(minutes=15))
        self.assertEqual(len(result), 1)
        self.assertTrue(p.clean_bars([frame], pd.Timedelta(minutes=15), self.start).empty)
        changed = frame.assign(close=104)
        with self.assertRaises(ValueError):
            p.clean_bars([frame, changed], pd.Timedelta(minutes=15), self.end)

    def test_full_page_splits_and_does_not_discard_old_history(self):
        with tempfile.TemporaryDirectory() as directory:
            client = p.MTSClient(Path(directory), pause=0)
            full_page = {"t": [0] * 1000}
            with patch.object(client, "get", side_effect=[full_page, self.payload, {"s": "no_data"}]) as get:
                frame = client.history("GLD965", "15", self.start, self.end)
            self.assertEqual(len(frame), 1)
            self.assertEqual(get.call_count, 3)

    def test_resume_uses_cache_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            client = p.MTSClient(Path(directory), pause=0)
            class Response:
                def __enter__(self): return self
                def __exit__(self, *args): return None
                def read(self): return json.dumps({"hello": "world"}).encode()
            with patch.object(p, "urlopen", return_value=Response()) as request:
                self.assertEqual(client.get("config"), {"hello": "world"})
                self.assertEqual(client.get("config"), {"hello": "world"})
            self.assertEqual(request.call_count, 1)
            self.assertFalse(client.audit[0]["cache_hit"])
            self.assertTrue(client.audit[1]["cache_hit"])

    def test_transient_network_errors_back_off_and_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            client = p.MTSClient(Path(directory), pause=0)
            with patch.object(p, "urlopen", side_effect=URLError("temporary failure")) as request:
                with patch.object(p.time, "sleep") as sleep, self.assertRaises(URLError):
                    client.get("config")
            self.assertEqual(request.call_count, 5)
            self.assertEqual(sleep.call_count, 4)
            self.assertGreaterEqual(sleep.call_args_list[0].args[0], 1)

    def test_fetch_queries_only_finished_candles(self):
        class FakeClient:
            audit = []
            queries = []
            def get(self, endpoint, params=None):
                return {} if endpoint == "config" else {"name": params["symbol"], "currency_code": "THB"}
            def history(self, symbol, resolution, start, end):
                self.queries.append((resolution, start, end))
                return p.parse_history({"s": "no_data"}, start, end)
        client = FakeClient()
        cutoff = self.start + pd.Timedelta(days=2, hours=8, minutes=7)
        with tempfile.TemporaryDirectory() as directory:
            p.fetch_dataset(client, self.start, self.end + pd.Timedelta(days=3), cutoff, Path(directory))
        for resolution, _, end in client.queries:
            self.assertEqual(end, cutoff.floor("15min" if resolution == "15" else "1D"))


class AggregationTests(unittest.TestCase):
    def setUp(self):
        self.frame = candles(pd.date_range("2025-01-02T00:00Z", periods=8, freq="15min"))

    def test_ohlc_aggregation(self):
        bars, dropped = p.aggregate(self.frame, "60min", 60)
        self.assertEqual(len(bars), 2)
        self.assertEqual(dropped, 0)
        self.assertEqual(bars.iloc[0][list(p.OHLC)].tolist(), [100, 105, 98, 104])
        self.assertEqual(bars.source_count.tolist(), [4, 4])
        self.assertEqual(bars.available_at.iloc[0], p.utc("2025-01-02T01:00Z"))

    def test_missing_constituent_drops_incomplete_bucket(self):
        bars, dropped = p.aggregate(self.frame.drop(index=1), "60min", 60)
        self.assertEqual(len(bars), 1)
        self.assertEqual(dropped, 1)
        self.assertEqual(bars.timestamp.iloc[0], p.utc("2025-01-02T01:00Z"))

    def test_week_is_anchored_to_monday_not_seven_observations(self):
        daily = candles(pd.to_datetime(["2025-01-06", "2025-01-07", "2025-01-10", "2025-01-13"], utc=True))
        weekly, _ = p.aggregate(daily, "W-MON")
        self.assertEqual(weekly.timestamp.tolist(), list(pd.to_datetime(["2025-01-06", "2025-01-13"], utc=True)))
        self.assertEqual(weekly.source_count.tolist(), [3, 1])
        self.assertEqual(weekly.available_at.iloc[0], p.utc("2025-01-13T00:00Z"))

    def test_partial_first_and_last_week_excluded(self):
        daily = candles(pd.date_range("2025-01-01T00:00Z", periods=15, freq="D"))
        daily = daily.assign(symbol="GLD965", timeframe="1d", available_at=daily.timestamp + pd.Timedelta(days=1))
        bars, _ = p.build_timeframes(daily, p.utc("2025-01-01T00:00Z"), p.utc("2025-01-16T00:00Z"), p.utc("2025-01-16T00:00Z"))
        weekly = bars.loc[bars.timeframe == "7d"]
        self.assertEqual(weekly.timestamp.tolist(), [p.utc("2025-01-06T00:00Z")])
        self.assertEqual(weekly.source_count.tolist(), [7])


class ReturnTests(unittest.TestCase):
    def test_known_returns_and_no_imputation(self):
        frame = candles(pd.date_range("2025-01-01T00:00Z", periods=35, freq="D"))
        frame["close"] = 100 * (1.01 ** np.arange(35))
        frame = frame.assign(symbol="GLD965", timeframe="1d")
        returns = p.add_returns(frame)
        for lag in p.LAGS:
            self.assertTrue(returns[f"return_{lag}"].iloc[:lag].isna().all())
            self.assertAlmostEqual(returns[f"return_{lag}"].iloc[-1], 1.01 ** lag - 1)
            self.assertAlmostEqual(returns[f"log_return_{lag}"].iloc[-1], lag * np.log(1.01))

    def test_elapsed_minutes_exposes_weekend_gap(self):
        frame = candles(["2025-01-03T10:00Z", "2025-01-06T10:00Z"], [99, 109])
        returns = p.add_returns(frame.assign(symbol="GLD965", timeframe="15m"))
        self.assertAlmostEqual(returns.return_1.iloc[-1], .1)
        self.assertEqual(returns.elapsed_minutes_1.iloc[-1], 4320)

    def test_series_are_never_shifted_across_symbol_or_timeframe(self):
        base = candles(pd.date_range("2025-01-01T00:00Z", periods=4, freq="D"))
        bars = pd.concat([base.assign(symbol=s, timeframe=tf) for s in p.SYMBOLS for tf in ("15m", "1d")])
        returns = p.add_returns(bars)
        self.assertEqual(returns.return_1.isna().sum(), 4)

    def test_summary_percentage_units_and_observation_counts(self):
        frame = candles(pd.date_range("2025-01-01T00:00Z", periods=4, freq="D"))
        frame["close"] = [100, 110, 121, 133.1]
        summary = p.summarize(p.add_returns(frame.assign(symbol="GLD965", timeframe="1d")))
        row = summary.loc[(summary.year == "all") & (summary.lag_bars == 1)].iloc[0]
        self.assertEqual(row.n, 3)
        self.assertAlmostEqual(row.mean_pct, 10)
        self.assertAlmostEqual(row.median_elapsed_minutes, 1440)

    def test_naive_dates_mean_bangkok(self):
        self.assertEqual(p.utc("2025-01-01"), pd.Timestamp("2024-12-31T17:00:00Z"))


if __name__ == "__main__":
    unittest.main()
