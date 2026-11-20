"""Polynomial calibration numerical stability and covariance checks."""
import sys,unittest,importlib.util
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent/'code'))
if any(importlib.util.find_spec(p) is None for p in ['statsmodels','lightgbm']):raise unittest.SkipTest('Install requirements-calibration.txt')
from calibrate_priceMA_lightgbm import fit_polynomial,polynomial_predict,polynomial_transform

class CalibrationTests(unittest.TestCase):
 def test_raw_and_standardized_cubic_represent_same_curve(self):
  x=np.linspace(10000,20000,300);z=(x-x.mean())/x.std();y=50000+1200*z-50*z**2+20*z**3
  fit,hac,center,scale,_=fit_polynomial(x,y,3)
  raw=polynomial_transform(center,scale,3)@fit.params
  query=np.linspace(9000,21000,40)
  expected=polynomial_predict(fit,center,scale,3,query)
  np.testing.assert_allclose(np.polynomial.polynomial.polyval(query,raw),expected,rtol=1e-12,atol=1e-7)
  self.assertEqual(hac.cov_params().shape,(4,4))
 def test_degenerate_predictions_rejected(self):
  with self.assertRaises(ValueError):fit_polynomial(np.ones(100),np.arange(100),2)
 def test_HAC_accounts_for_correlated_residuals(self):
  rng=np.random.default_rng(42);noise=np.zeros(2000)
  for i in range(1,len(noise)):noise[i]=.9*noise[i-1]+rng.normal()
  x=np.linspace(1,20,len(noise));fit,hac,_,_,_=fit_polynomial(x,2+3*x+noise,1)
  self.assertGreater(hac.bse[1],fit.bse[1])
  self.assertTrue(np.isfinite(hac.pvalues).all())

if __name__=='__main__':unittest.main()
