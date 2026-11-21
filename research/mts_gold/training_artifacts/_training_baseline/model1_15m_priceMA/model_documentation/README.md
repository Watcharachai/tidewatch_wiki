# LightGBM and calibration model documentation

[Download the DOCX](MTS_GLD965_15m_LightGBM_Calibration_Model_Documentation.docx).

Prepared 21 November 2026 for the GLD965 15-minute next-bar trailing MA5 experiment. Evidence is pinned to repository commit `d6df6078b410df5cf4753180abd85c358a609c87`; the market snapshot ends 7 November 2026 Bangkok time.

The document covers the six requested topics, all 32 LightGBM tuning trials, the frozen 45-feature dictionary, calibration regression statistics, quarterly/DEV charts, implementation instructions and linked notebook/Excel/DOCX references. Calibration improves the selected base model but does not beat structural persistence. Historical backcasts, calibration-fit results and later evaluations are distinguished throughout.

Supporting files:

- `Calendar_year_metrics.csv`: descriptive calendar-year scores recomputed from unchanged frozen-model predictions; neither year is an untouched holdout.
- `Frozen_feature_dictionary.csv`: exact feature order, definitions, gain shares and validation permutation effects.
- `documentation_manifest.json`: evidence hashes and structural checks.
- `document_verification.json`: render and content verification.

Rebuild from the repository root using Python with `python-docx`, `numpy` and `pandas`:

```bash
python research/mts_gold/code/build_lightgbm_model_documentation.py
```

The build reads saved results and does not train models or modify the frozen desktop package. Original notebooks, Excel workbooks and model artifacts remain the underlying experimental record.
