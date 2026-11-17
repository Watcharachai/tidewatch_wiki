"""MA horizon, contiguity, train-only target scaling and structural baseline checks."""
import unittest,sys,importlib.util
from pathlib import Path
from unittest.mock import patch
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent/'code'))
if importlib.util.find_spec('lightgbm') is None:raise unittest.SkipTest('Install requirements-model1-15m.txt')
import model1_15m_priceMA as m

class MATests(unittest.TestCase):
 def frame(self):
  f=pd.DataFrame({'close':np.arange(100.,120.),'decision_at':pd.date_range('2025-01-01',periods=20,freq='15min',tz='UTC')})
  f['return']=np.log(f.close/f.close.shift());f['next_return']=f['return'].shift(-1);f['label_at']=f.decision_at.shift(-1)
  return f
 def prepare(self,f):
  with patch.object(m,'prepare_returns',return_value=(f,[],[],Path('source'))):return m.prepare()[0]
 def test_forecast_is_next_trailing_average(self):
  f=self.prepare(self.frame());self.assertEqual(f.loc[4,'ma5_current'],102.);self.assertEqual(f.loc[4,'y_ma5'],103.)
  self.assertTrue(pd.isna(f.loc[3,'y_ma5']));self.assertTrue(pd.isna(f.iloc[-1].y_ma5))
 def test_gap_excludes_windows(self):
  f=self.frame();f.loc[8:,'decision_at']+=pd.Timedelta(hours=1);f=self.prepare(f)
  self.assertTrue(f.loc[7:11,'y_ma5'].isna().all());self.assertTrue(pd.notna(f.loc[12,'y_ma5']))
 def test_structural_error_is_one_fifth_next_price_error(self):
  f=self.prepare(self.frame());valid=f.y_ma5.notna()
  np.testing.assert_allclose((f.y_ma5-f.structural_persistence)[valid],((f.close.shift(-1)-f.close)/5)[valid])
 def test_scaling_fits_training_only_and_inverts(self):
  f=self.prepare(self.frame());ids=np.arange(4,10);a,_=m.labels(f,ids)
  future=f.copy();future.loc[10:,'y_ma5']+=1e6;b,_=m.labels(future,ids)
  self.assertEqual(a.attrs['target_mean'],b.attrs['target_mean']);self.assertEqual(a.attrs['target_scale'],b.attrs['target_scale'])
  np.testing.assert_allclose(a.loc[ids,'y_scaled'].mean(),0,atol=1e-12)
  np.testing.assert_allclose(a.y_scaled*a.attrs['target_scale']+a.attrs['target_mean'],a.y_ma5,equal_nan=True)

if __name__=='__main__':unittest.main()
