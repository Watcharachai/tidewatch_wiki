# MTS gold analysis and documents

- [Untuned Model 1 and feature-review results](../training_artifacts/_training_baseline/Model1_Baseline_Summary.md): an executed notebook, Excel diagnostics and DOCX summary alongside the baseline tables. Feature selection remains manual.
- [Current all-date 60m two-model baseline](../training_artifacts/_training_baseline/README.md): feature groups, rolling-stat definitions, transformed targets and chronological-fold usage. This supersedes the fixed year split for the new experiment.
- [Model readiness summary](docs/MTS_Model_Readiness_Summary.md), also available as an editable [DOCX](docs/MTS_Model_Readiness_Summary.docx). It combines training statistics, missingness, price/return trends, histograms and the proposed first-model design.
- [Return analysis](reports/analysis.md), its [summary](reports/return_summary.csv), [coverage](reports/coverage.csv), [daily alignment gaps](reports/daily_alignment_gaps.csv), and charts in `reports/`.
- [Feature collection report](reports/feature_report.md) and the full [feature coverage table](../feature_artifacts/coverage.csv).
- [30m/60m training dataset report](reports/training_dataset_summary.md), with detailed [summary statistics](../training_artifacts/summary_statistics.csv) and [null rates](../training_artifacts/null_rates.csv).
- [Price, return, extrema and variance analysis](reports/price_return_modeling.md), with [one-period return statistics](reports/one_period_return_statistics.csv), [peak/drawdown dates](reports/price_extrema_drawdown.csv), [monthly trends](reports/monthly_price_trend.csv) and a [trend/volatility chart](reports/price_return_modeling.png).
- [Return histograms: central range](reports/return_histograms_central.png) and [full range with rare extremes](reports/return_histograms_full_range.png), for GLD965 and GLD9999 at 30m, 60m and daily intervals.
- [Forecast architecture](docs/Gold_Price_Predictive_Model_Architecture.md), also available as [DOCX](docs/Gold_Price_Predictive_Model_Architecture.docx).
- [Feature source and export specification](docs/feature_sources.md).

The executable target and feature collectors live together in `../code/`. Generated target data and reference caches remain in `../data/` and `../feature_data/`; versioned snapshots and feature tables remain in `../snapshots/` and `../feature_artifacts/`.
