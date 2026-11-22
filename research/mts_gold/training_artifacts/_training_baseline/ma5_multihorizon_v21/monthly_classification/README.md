# Monthly MA5 direction results

This folder summarizes the frozen v2.1 GLD965 classifiers by **Asia/Bangkok decision month**, partition (TRAIN, TEST, OOT), and direct horizon h=1..5 (15–75 minutes). The source is the saved `Predictions.csv.gz`; no model was retrained and no new market prices were fetched.

Class 1 means the future trailing MA5 exceeds the **current observed MA5**. Class 0 includes ties and decreases. Precision and recall refer to class 1. The structural benchmark uses the same rows. Partial months at split boundaries contain fewer observations, especially November 2026; compare their sample sizes before interpreting variation.

Files:

- `Monthly_Classification_Analysis.xlsx`: read-me, all 500 monthly model/partition/horizon rows, and five sheets containing the metric and actual-price charts.
- `monthly_metrics_with_baseline.csv`: all monthly accuracy, precision, recall, balanced accuracy, confusion counts and accuracy differences from structural persistence. `monthly_metrics.csv` is the same table without the benchmark join.
- `h1_monthly_metrics.png` through `h5_monthly_metrics.png`: accuracy, positive precision and positive recall for Structural, Logistic and LightGBM, with TEST and OOT boundaries.
- `h1_oot_actual_price_and_errors.png` through `h5_oot_actual_price_and_errors.png`: actual MTS close and actual future MA5, with Logistic false positives (red) and false negatives (purple) at the relevant decision time. Lines break at missing/noncontiguous bars.
- `oot_logistic_price_and_signals.csv.gz`: exact chart rows, close and class calls.

Reproduce with `python monthly_classification.py` from the parent v2.1 directory. The monthly counts and weighted accuracies have been checked against the original `Metrics.csv` for every partition, horizon and classifier.

OOT covers 7 September–7 November 2026 in the saved snapshot. These dates were previously inspected in earlier work, so OOT is a chronological evaluation period, not a pristine independent test. MA5 overlaps known prices; apparent directional accuracy must be judged relative to structural persistence.
