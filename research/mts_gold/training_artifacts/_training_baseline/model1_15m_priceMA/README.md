# GLD965 15m: next-bar five-period average price

This experiment changes Y to the next completed bar's trailing five-period average price:

`Y(t+1) = (P[t-3] + P[t-2] + P[t-1] + P[t] + P[t+1]) / 5`.

It uses the previous lag-only waterfall and nested four-fold selection/tuning protocol. Windows crossing gaps are excluded. Target standardization is fitted on each training segment and inverted for every price forecast.

- [Executed notebook](GLD965_15m_priceMA_Training.ipynb)
- [Excel results and selection diagnostics](GLD965_15m_priceMA_Review.xlsx)
- [DOCX report](GLD965_15m_priceMA_Report.docx) and [Markdown report](GLD965_15m_priceMA_Report.md)
- [Predicted versus actual plots](predicted_actual.png)

Four target prices are known at decision time. The principal baseline assumes the next close equals the current close, then computes the resulting next MA. High conventional price R² alone cannot establish forecasting skill. Positive `skill_vs_structural` improves on that baseline; the paired block-bootstrap gain interval must exclude zero on the positive side.

All generated datasets, diagnostics, predictions, model/preprocessing files and the driver snapshot are in this folder. `prepared_X_y_context.csv.gz` preserves the lagged candidate context and raw MA labels; use the driver's `labels()` helper to materialize training-fold target scaling and `Z_return_lag5`. These fold-specific fields are not globally fitted in the context table.

Run from the repository root:

```bash
pip install -r research/mts_gold/requirements-model1-15m.txt
python research/mts_gold/code/model1_15m_priceMA.py
# Or regenerate and execute the notebook:
python research/mts_gold/code/build_model1_15m_priceMA_notebook.py
```

The canonical driver imports shared repository helpers; `experiment_source.py` is an audit snapshot. Rerunning replaces derived artifacts. The earlier return experiments and original datasets remain available. Set `MTS_NOTEBOOK_KERNEL` when using a kernel other than python3.
