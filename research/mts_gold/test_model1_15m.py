"""Verify temporal feature provenance and next-bar labels for the 15m study."""
import sys
import importlib.util
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent/'code'))
if importlib.util.find_spec('lightgbm') is None:
 raise unittest.SkipTest('Install requirements-model1-15m.txt for this experiment')
from model1_15m_waterfall import prepare,labels

class TemporalTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.f,cls.cols,_,cls.source=prepare()
 def test_strict_source_shift(self):
  original=pd.read_csv(self.source,low_memory=False).query("symbol == 'GLD965'").sort_values('available_at').reset_index(drop=True)
  pd.testing.assert_series_equal(self.f.mts965_15m_return_lag5,original.mts965_15m_return_lag5.shift(1))
 def test_label_contiguity(self):
  f=self.f
  valid=f.next_return.notna()
  self.assertTrue((f.loc[valid,'label_at']-f.loc[valid,'decision_at']).eq(pd.Timedelta(minutes=15)).all())
  self.assertTrue(f.decision_at.is_unique)
 def test_future_values_cannot_change_training_target_or_predictors(self):
  n=1000;ids=np.arange(n)
  a,_=labels(self.f,ids);future=self.f.copy();future.loc[n:,'return']=1e4
  b,_=labels(future,ids)
  np.testing.assert_allclose(a.loc[:n-1,'y_z'],b.loc[:n-1,'y_z'],equal_nan=True)
  np.testing.assert_allclose(a.loc[:n-1,'Z_return_lag5'],b.loc[:n-1,'Z_return_lag5'],equal_nan=True)
 def test_features_have_explicit_positive_lag(self):
  self.assertTrue(all('_lag' in c for c in self.cols))
  self.assertFalse(any(c in self.cols for c in ['close','return','next_return','sigma','y_z']))

if __name__=='__main__':unittest.main()
