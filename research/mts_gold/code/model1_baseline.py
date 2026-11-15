#!/usr/bin/env python3
"""Untuned Model 1, expanding-fold diagnostics, and manual feature review exports."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.linalg import eigh
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import ElasticNet
from sklearn.preprocessing import StandardScaler
from varclushi import VarClusHi

from prepare_baseline import materialize_fold

ROOT = Path(__file__).resolve().parent.parent
CONFIG = {"alpha": .01, "l1_ratio": .5, "max_iter": 10000, "tol": 1e-5,
          "half_life": 30, "embargo_min_bars": 30, "null_flag_threshold": .20,
          "vif_warning_threshold": 5, "vif_severe_threshold": 10,
          "varclus_maxeigval2": 1.0, "near_zero_z_band": .05,
          "permutation_repeats": 20, "block_bars": 30, "bootstrap_repeats": 1000,
          "random_seed": 42, "vif_eigen_tolerance": 1e-10}
FOLDS = [
    ("F1", "2025-07-01", "2025-07-08", "2025-10-01"),
    ("F2", "2025-10-01", "2025-10-08", "2026-01-01"),
    ("F3", "2026-01-01", "2026-01-08", "2026-04-01"),
    ("F4", "2026-04-01", "2026-04-08", "2026-07-01"),
    ("F5", "2026-07-01", "2026-07-08", "2026-10-01"),
    ("F6", "2026-10-01", "2026-10-08", "2026-11-08"),
]
LOG = logging.getLogger("model1_baseline")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bangkok(day: str) -> str:
    return day + "T00:00:00+07:00"


def null_variance(x: pd.DataFrame) -> pd.DataFrame:
    count = x.count()
    unique = x.nunique(dropna=True)
    return pd.DataFrame({"feature": x.columns, "train_rows": len(x),
                         "observed_count": count.to_numpy(), "null_count": x.isna().sum().to_numpy(),
                         "null_rate": x.isna().mean().to_numpy(),
                         "null_ge_20pct": x.isna().mean().ge(.2).to_numpy(),
                         "unique_count": unique.to_numpy(), "sample_variance": x.var().to_numpy(),
                         "zero_variance": (unique.eq(1)).to_numpy(), "all_null": count.eq(0).to_numpy(),
                         "action": "REVIEW_ONLY_NO_DROP"})


def impute_train(x: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    # Preserve all columns, including all-null and zero-variance features.
    medians = x.median().fillna(0.)
    return x.fillna(medians), medians


def vif_diagnostics(x: pd.DataFrame) -> pd.DataFrame:
    """VIF from the correlation inverse; mark numerical null-space participants infinite."""
    active = x.columns[x.nunique(dropna=True).gt(1)]
    output = pd.DataFrame({"feature": x.columns, "vif": np.nan,
                           "vif_status": np.where(x.notna().sum().eq(0), "all_null", "zero_variance")})
    if len(active):
        z, _ = impute_train(x[active])
        corr = np.atleast_2d(np.corrcoef(z.to_numpy(), rowvar=False))
        values, vectors = eigh(corr)
        tolerance = CONFIG["vif_eigen_tolerance"] * max(values[-1], 1.)
        positive = values > tolerance
        null_loading = np.square(vectors[:, ~positive]).sum(axis=1)
        diagonal = (np.square(vectors[:, positive]) / values[positive]).sum(axis=1)
        infinite = null_loading > 1e-8
        lookup = pd.DataFrame({"feature": active,
                               "vif_value": np.where(infinite, np.inf, np.maximum(diagonal, 1.)),
                               "status": np.where(infinite, "numerical_collinearity", "finite"),
                               "null_space_loading": null_loading})
        output = output.merge(lookup, on="feature", how="left")
        good = output.status.notna()
        output.loc[good, "vif"] = output.loc[good, "vif_value"]
        output.loc[good, "vif_status"] = output.loc[good, "status"]
        output = output.drop(columns=["status", "vif_value"])
        output["correlation_rank"] = int(positive.sum())
        output["estimable_column_count"] = len(active)
        output["eigenvalue_cutoff"] = tolerance
    output["vif_ge_5"] = output.vif.ge(5)
    output["vif_ge_10"] = output.vif.ge(10)
    return output


def varclus_diagnostics(x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    active = x.columns[x.nunique(dropna=True).gt(1)]
    status = pd.DataFrame({"feature": x.columns,
                           "cluster_status": np.where(x.notna().sum().eq(0), "all_null", "zero_variance")})
    if len(active) < 2:
        return status, pd.DataFrame()
    filled, _ = impute_train(x[active])
    cluster = VarClusHi(filled, maxeigval2=CONFIG["varclus_maxeigval2"], maxclus=None, n_rs=0).varclus()
    values = cluster.rsquare.rename(columns={"Variable": "feature", "Cluster": "cluster",
                                            "RS_Own": "r2_own", "RS_NC": "r2_next_cluster",
                                            "RS_Ratio": "r2_ratio"})
    # The representative is a review suggestion; every candidate remains in the exports.
    values["representative_suggestion"] = False
    for _, group in values.groupby("cluster"):
        ordered = group.sort_values(["r2_ratio", "feature"], na_position="last")
        if pd.notna(ordered.r2_ratio.iloc[0]):
            values.loc[ordered.index[0], "representative_suggestion"] = True
    status = status.merge(values, on="feature", how="left")
    status.loc[status.feature.isin(active), "cluster_status"] = "clustered"
    status["representative_suggestion"] = status.representative_suggestion.eq(True)
    return status, cluster.info.copy()


def fit_linear(x: pd.DataFrame, y: pd.Series) -> tuple[ElasticNet, StandardScaler, pd.Series, dict]:
    filled, medians = impute_train(x)
    scaler = StandardScaler()
    standardized = scaler.fit_transform(filled)
    model = ElasticNet(alpha=CONFIG["alpha"], l1_ratio=CONFIG["l1_ratio"],
                       max_iter=CONFIG["max_iter"], tol=CONFIG["tol"], selection="cyclic",
                       random_state=CONFIG["random_seed"])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(standardized, y)
    info = {"iterations": int(model.n_iter_), "dual_gap": float(model.dual_gap_),
            "converged": not any(issubclass(w.category, ConvergenceWarning) for w in caught),
            "nonzero_coefficients": int(np.count_nonzero(model.coef_))}
    if not info["converged"]:
        raise RuntimeError("Fixed baseline did not converge; investigate before exporting scores")
    return model, scaler, medians, info


def score(y, prediction) -> dict:
    y, prediction = np.asarray(y), np.asarray(prediction)
    mse = float(np.mean((y-prediction)**2))
    zero = float(np.mean(y**2))
    covered = (np.abs(prediction) > CONFIG["near_zero_z_band"]) & (y != 0)
    return {"rows": len(y), "mse_z": mse, "mae_z": float(np.mean(np.abs(y-prediction))),
            "zero_baseline_mse": zero, "r2_vs_zero": 1-mse/zero if zero else np.nan,
            "mse_improvement_vs_zero": zero-mse,
            "directional_rows": int(covered.sum()), "directional_coverage": float(covered.mean()),
            "directional_accuracy": float(np.mean(np.sign(y[covered]) == np.sign(prediction[covered])))
                if covered.any() else np.nan}


def block_permutation(x: np.ndarray, y: np.ndarray, prediction: np.ndarray,
                      coefficients: np.ndarray, names: list[str], seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    blocks = [np.arange(start, min(start+CONFIG["block_bars"], len(y)))
              for start in range(0, len(y), CONFIG["block_bars"])]
    permutations = np.array([np.concatenate([blocks[i] for i in rng.permutation(len(blocks))])
                             for _ in range(CONFIG["permutation_repeats"])])
    residual = y-prediction
    base_mse = np.mean(residual**2)
    rows = []
    for j, name in enumerate(names):
        contribution = x[:, j]*coefficients[j]
        # Exact prediction update for a linear estimator after its train-fitted preprocessing.
        changed = contribution[permutations]-contribution[None, :]
        importance = np.mean((residual[None, :]-changed)**2, axis=1)-base_mse
        rows.append({"feature": name, "validation_rows": len(y), "importance_mean": importance.mean(),
                     "importance_std": importance.std(ddof=1), "importance_p05": np.quantile(importance, .05),
                     "importance_p95": np.quantile(importance, .95),
                     "positive_repeat_fraction": np.mean(importance > 0),
                     "coefficient_zero": bool(coefficients[j] == 0),
                     "importance_definition": "increase_in_validation_MSE_z"})
    return pd.DataFrame(rows)


def block_bootstrap(predictions: pd.DataFrame, repeats: int | None = None) -> dict:
    rng = np.random.default_rng(CONFIG["random_seed"])
    blocks = []
    for _, group in predictions.groupby("fold", sort=True):
        y, p = group.y_z.to_numpy(), group.z_hat.to_numpy()
        blocks.append((y**2, y**2-(y-p)**2))
    draws, r2_draws = [], []
    for _ in range(repeats or CONFIG["bootstrap_repeats"]):
        improvement_sum, baseline_sum, n = 0., 0., 0
        for baseline, difference in blocks:
            length = len(baseline)
            starts = rng.integers(0, length, size=int(np.ceil(length/CONFIG["block_bars"])))
            indices = ((starts[:, None]+np.arange(CONFIG["block_bars"])) % length).ravel()[:length]
            improvement_sum += difference[indices].sum()
            baseline_sum += baseline[indices].sum()
            n += length
        draws.append(improvement_sum/n)
        r2_draws.append(improvement_sum/baseline_sum if baseline_sum else np.nan)
    lo, hi = np.quantile(draws, [.025, .975])
    rlo, rhi = np.quantile(r2_draws, [.025, .975])
    return {"mse_improvement_ci_low": lo, "mse_improvement_ci_high": hi,
            "r2_ci_low": rlo, "r2_ci_high": rhi, "acceptance_ci_positive": bool(lo > 0),
            "bootstrap_method": "paired circular 30-observation blocks, stratified by fold"}


def add_context(frame: pd.DataFrame, symbol: str, fold: str, **kwargs) -> pd.DataFrame:
    return frame.assign(symbol=symbol, fold=fold, **kwargs)


def run_experiment(baseline: Path | None = None) -> dict[str, pd.DataFrame]:
    baseline = baseline or ROOT/"training_artifacts"/"_training_baseline"
    out = baseline/"model1_results"
    out.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(out/"progress.log", mode="w")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    LOG.addHandler(handler)
    LOG.setLevel(logging.INFO)
    manifest_path = baseline/"manifest.json"
    manifest = json.loads(manifest_path.read_text())
    tables = {key: [] for key in ("null_variance", "vif", "varclus_features", "varclus_clusters",
                                  "coefficients", "permutation", "fold_metrics", "fold_schedule", "predictions")}
    bundles, inputs = [], []
    for task in manifest["outputs"]:
        symbol = task["symbol"]
        source = baseline/task["file"]
        if sha(source) != task["sha256"]:
            raise ValueError(f"Input checksum mismatch: {source}")
        inputs.append({"file": source.name, "sha256": sha(source)})
        frame = pd.read_csv(source, low_memory=False)
        candidates = task["groups"]["existing_numeric"]+task["groups"]["engineered_numeric"]
        core = task["groups"]["model1_core"]
        if len(set(candidates)) != len(candidates) or len(core) > 25:
            raise ValueError("Invalid candidate/core feature schema")
        if any(c.startswith("y_") or c == "sigma_ewma_hl30_causal" for c in candidates):
            raise ValueError("Target/reference sigma leaked into X")
        for fold_number, (fold, train_end, val_start, val_end) in enumerate(FOLDS):
            LOG.info("%s %s: materializing fold and profiling %s candidates", symbol, fold, len(candidates))
            train, validation, fold_info = materialize_fold(frame, bangkok("2025-01-01"), bangkok(train_end),
                bangkok(val_start), bangkok(val_end), half_life=CONFIG["half_life"], embargo_bars=30)
            x_all = train[candidates]
            profile = null_variance(x_all)
            tables["null_variance"].append(add_context(profile, symbol, fold))
            for scope, features in (("all_candidates", candidates), ("core23", core)):
                tables["vif"].append(add_context(vif_diagnostics(train[features]), symbol, fold, scope=scope))
            LOG.info("%s %s: running VARCLUS on train-only correlation structure", symbol, fold)
            cluster_features, cluster_info = varclus_diagnostics(x_all)
            tables["varclus_features"].append(add_context(cluster_features, symbol, fold))
            tables["varclus_clusters"].append(add_context(cluster_info, symbol, fold))
            threshold = float(train.sigma_t.median())
            tables["fold_schedule"].append(pd.DataFrame([dict(symbol=symbol, fold=fold,
                train_start=bangkok("2025-01-01"), train_end=bangkok(train_end),
                validation_start=bangkok(val_start), validation_end=bangkok(val_end),
                training_sigma_median=threshold, **fold_info)]))
            for name, features in (("zero", []), ("elasticnet_core23", core),
                                   ("elasticnet_all313_diagnostic", candidates)):
                predictions = {}
                if features:
                    estimator, scaler, medians, fitted = fit_linear(train[features], train.y_model1_z)
                    tables["coefficients"].append(add_context(pd.DataFrame({"feature": features,
                        "coefficient_standardized_x": estimator.coef_, "impute_median": medians.to_numpy(),
                        "all_null_train_imputed_zero": train[features].isna().all().to_numpy(),
                        "scale_mean": scaler.mean_, "scale_std": scaler.scale_}), symbol, fold, model=name))
                    bundle = dict(symbol=symbol, fold=fold, model=name, feature_names=features,
                                  intercept=float(estimator.intercept_), coefficients=estimator.coef_.tolist(),
                                  impute_medians=medians.to_list(), scale_means=scaler.mean_.tolist(),
                                  scale_stds=scaler.scale_.tolist(), **fold_info, **fitted)
                    bundles.append(bundle)
                    for part, values in (("train", train), ("validation", validation)):
                        standardized = scaler.transform(values[features].fillna(medians))
                        predictions[part] = estimator.predict(standardized)
                        if part == "validation":
                            pi = block_permutation(standardized, values.y_model1_z.to_numpy(), predictions[part],
                                                   estimator.coef_, features, CONFIG["random_seed"]+fold_number)
                            tables["permutation"].append(add_context(pi, symbol, fold, model=name))
                else:
                    fitted = {"iterations": 0, "dual_gap": 0., "converged": True, "nonzero_coefficients": 0}
                    predictions = {"train": np.zeros(len(train)), "validation": np.zeros(len(validation))}
                for part, values in (("train", train), ("validation", validation)):
                    tables["fold_metrics"].append(pd.DataFrame([dict(symbol=symbol, fold=fold, model=name,
                        partition=part, features=len(features), **score(values.y_model1_z, predictions[part]), **fitted)]))
                p = validation[["timestamp", "available_at", "label_available_at", "close", "y_next_close",
                                "y_next_log_return", "sigma_t", "y_model1_z"]].copy()
                p = p.rename(columns={"available_at": "decision_at", "y_model1_z": "y_z"})
                p["z_hat"] = predictions["validation"]
                p["r_hat_using_trailing_sigma"] = p.z_hat*p.sigma_t
                p["price_hat_using_trailing_sigma"] = p.close*np.exp(p.r_hat_using_trailing_sigma)
                p["volatility_regime"] = np.where(p.sigma_t.gt(threshold), "above_train_median", "at_or_below_train_median")
                p["bangkok_hour"] = p.decision_at.dt.tz_convert("Asia/Bangkok").dt.hour
                p["model2_is_fitted"] = False
                tables["predictions"].append(add_context(p, symbol, fold, model=name))
            LOG.info("%s %s complete", symbol, fold)
    results = {key: pd.concat(value, ignore_index=True) for key, value in tables.items()}
    results.update(aggregate_results(results))
    results.update(extrapolation_diagnostics(baseline, bundles, results))
    for name, frame in results.items():
        path = out/(name+".csv.gz" if name == "predictions" else name+".csv")
        frame.to_csv(path, index=False, compression={"method": "gzip", "mtime": 0} if name == "predictions" else None)
    (out/"model_bundles.json").write_text(json.dumps(bundles, indent=2, allow_nan=False)+"\n")
    versions = {name: importlib.metadata.version(name) for name in
                ("numpy", "pandas", "scipy", "scikit-learn", "varclushi", "openpyxl", "nbformat", "nbclient")}
    audit = {"config": CONFIG, "inputs": inputs, "baseline_manifest_sha256": sha(manifest_path),
             "versions": versions, "feature_removal": "none", "hyperparameter_search": False,
             "evaluation": "expanding time-fold CV across 2025 and 2026; not an untouched final holdout",
             "artifacts": {p.name: sha(p) for p in sorted(out.iterdir())
                           if p.suffix in (".csv", ".gz", ".json") and p.name != "run_manifest.json"}}
    export_workbook(baseline, results, audit)
    from model1_report import export_report
    export_report(baseline, results, audit)
    audit["deliverables"] = {name: sha(baseline/name) for name in
                             ("Model1_Baseline_Review.xlsx", "Model1_Baseline_Summary.md", "Model1_Baseline_Summary.docx")}
    (out/"run_manifest.json").write_text(json.dumps(audit, indent=2, allow_nan=False)+"\n")
    LOG.info("Experiment complete; notebook/Excel/document outputs ready")
    LOG.removeHandler(handler)
    handler.close()
    return results


def aggregate_results(results: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    predictions = results["predictions"]
    summaries, regimes, hours = [], [], []
    for (symbol, model), frame in predictions.groupby(["symbol", "model"], sort=True):
        row = dict(symbol=symbol, model=model, **score(frame.y_z, frame.z_hat))
        if model != "zero":
            row.update(block_bootstrap(frame))
        summaries.append(row)
        for key, destination in (("volatility_regime", regimes), ("bangkok_hour", hours)):
            for value, group in frame.groupby(key):
                destination.append(dict(symbol=symbol, model=model, **{key: value}, **score(group.y_z, group.z_hat)))
    importance_rows = []
    for (symbol, model, feature), group in results["permutation"].groupby(["symbol", "model", "feature"]):
        importance_rows.append({"symbol": symbol, "model": model, "feature": feature,
            "weighted_mean_importance": np.average(group.importance_mean, weights=group.validation_rows),
            "positive_folds": int(group.importance_mean.gt(0).sum()), "folds": len(group),
            "min_fold_importance": group.importance_mean.min(), "max_fold_importance": group.importance_mean.max(),
            "zero_coefficient_folds": int(group.coefficient_zero.sum())})
    importance = pd.DataFrame(importance_rows)
    review = results["null_variance"].groupby(["symbol", "feature"], as_index=False).agg(
        folds=("fold", "count"), null_rate_min=("null_rate", "min"), null_rate_max=("null_rate", "max"),
        null_flag_folds=("null_ge_20pct", "sum"), all_null_folds=("all_null", "sum"),
        zero_variance_folds=("zero_variance", "sum"))
    vif = results["vif"].query("scope == 'all_candidates'").copy()
    vif["infinite"] = np.isinf(vif.vif)
    vif_summary = vif.groupby(["symbol", "feature"], as_index=False).agg(
        vif_infinite_folds=("infinite", "sum"), vif_max=("vif", "max"), vif_ge_10_folds=("vif_ge_10", "sum"))
    clusters = results["varclus_features"].groupby(["symbol", "feature"], as_index=False).agg(
        representative_suggestion_folds=("representative_suggestion", "sum"),
        r2_ratio_min=("r2_ratio", "min"), r2_ratio_max=("r2_ratio", "max"))
    review = review.merge(vif_summary, on=["symbol", "feature"]).merge(clusters, on=["symbol", "feature"])
    for model, prefix in (("elasticnet_core23", "core"), ("elasticnet_all313_diagnostic", "diagnostic")):
        pi = importance.loc[importance.model.eq(model), ["symbol", "feature", "weighted_mean_importance", "positive_folds"]]
        pi = pi.rename(columns={"weighted_mean_importance": prefix+"_permutation_mean",
                                "positive_folds": prefix+"_permutation_positive_folds"})
        review = review.merge(pi, on=["symbol", "feature"], how="left")
    review["manual_decision"] = ""
    review["manual_notes"] = ""
    return {"cv_summary": pd.DataFrame(summaries), "regime_metrics": pd.DataFrame(regimes),
            "hour_metrics": pd.DataFrame(hours), "permutation_summary": importance, "manual_review": review}


def extrapolation_diagnostics(baseline: Path, bundles: list[dict], results: dict) -> dict:
    """Explain out-of-range validation inputs without fitting or changing predictions."""
    cached, ranges, worst = {}, [], []
    for bundle in bundles:
        symbol, fold, model = bundle["symbol"], bundle["fold"], bundle["model"]
        if symbol not in cached:
            f = pd.read_csv(baseline/f"baseline_60m_{symbol}.csv.gz", low_memory=False)
            f.available_at = pd.to_datetime(f.available_at, utc=True)
            f.label_available_at = pd.to_datetime(f.label_available_at, utc=True)
            cached[symbol] = f.set_index("available_at")
        f = cached[symbol]
        plan = results["fold_schedule"].loc[lambda d: d.symbol.eq(symbol) & d.fold.eq(fold)].iloc[0]
        mask = (f.index >= pd.Timestamp(plan.train_start)) & (f.index < pd.Timestamp(plan.train_end)) & f.label_available_at.lt(pd.Timestamp(plan.train_end))
        train = f.loc[mask, bundle["feature_names"]]
        p = results["predictions"].loc[lambda d: d.symbol.eq(symbol) & d.fold.eq(fold) & d.model.eq(model)].copy()
        validation = f.loc[pd.to_datetime(p.decision_at, utc=True), bundle["feature_names"]]
        medians = pd.Series(bundle["impute_medians"], index=bundle["feature_names"])
        scaled = (validation.fillna(medians).to_numpy()-np.array(bundle["scale_means"]))/np.array(bundle["scale_stds"])
        outside = validation.lt(train.min()) | validation.gt(train.max())
        fractions = outside.sum()/validation.count().replace(0, np.nan)
        ranges.append(add_context(pd.DataFrame({"feature": bundle["feature_names"],
            "train_observed_count": train.count().to_numpy(), "train_min": train.min().to_numpy(),
            "train_max": train.max().to_numpy(), "validation_min": validation.min().to_numpy(),
            "validation_max": validation.max().to_numpy(), "validation_outside_train_range_fraction": fractions.to_numpy(),
            "max_abs_standardized_validation": np.abs(scaled).max(axis=0),
            "fraction_abs_standardized_gt5": (np.abs(scaled)>5).mean(axis=0)}), symbol, fold, model=model))
        j = int(np.argmax((p.y_z.to_numpy()-p.z_hat.to_numpy())**2))
        contributions = scaled[j]*np.array(bundle["coefficients"])
        for k in np.argsort(np.abs(contributions))[::-1][:5]:
            worst.append({"symbol": symbol, "fold": fold, "model": model,
                "decision_at": str(p.decision_at.iloc[j]), "actual_z": p.y_z.iloc[j], "predicted_z": p.z_hat.iloc[j],
                "feature": bundle["feature_names"][k], "standardized_value": scaled[j, k],
                "coefficient": bundle["coefficients"][k], "prediction_contribution": contributions[k]})
    return {"extrapolation": pd.concat(ranges, ignore_index=True), "worst_prediction_contributions": pd.DataFrame(worst)}


def refresh_exports(baseline: Path) -> dict[str, pd.DataFrame]:
    """Rebuild diagnostic reports from the already-fitted parameters; no model refit."""
    out = baseline/"model1_results"
    results = {p.stem: pd.read_csv(p) for p in out.glob("*.csv")}
    results["predictions"] = pd.read_csv(out/"predictions.csv.gz")
    bundles = json.loads((out/"model_bundles.json").read_text())
    results.update(extrapolation_diagnostics(baseline, bundles, results))
    for name in ("extrapolation", "worst_prediction_contributions"):
        results[name].to_csv(out/(name+".csv"), index=False)
    audit = json.loads((out/"run_manifest.json").read_text())
    audit["artifacts"] = {p.name: sha(p) for p in sorted(out.iterdir())
                          if p.suffix in (".csv", ".gz", ".json") and p.name != "run_manifest.json"}
    export_workbook(baseline, results, audit)
    from model1_report import export_report
    export_report(baseline, results, audit)
    audit["deliverables"] = {name: sha(baseline/name) for name in
                             ("Model1_Baseline_Review.xlsx", "Model1_Baseline_Summary.md", "Model1_Baseline_Summary.docx")}
    (out/"run_manifest.json").write_text(json.dumps(audit, indent=2, allow_nan=False)+"\n")
    return results


def export_workbook(baseline: Path, results: dict, audit: dict) -> None:
    notes = [
        ("Purpose", "Manual feature review. No input feature was deleted. Empty decision/notes columns are yours to fill."),
        ("Primary model", "Elastic Net on the predefined 23-feature Model 1 core. No tuning or screen-driven removal."),
        ("Diagnostic model", "Same fixed Elastic Net on all 313 candidates solely to provide all-candidate importance."),
        ("Preprocessing", "Train-fold median imputation; all-null columns filled with zero; StandardScaler fitted on train only. Constants retained."),
        ("Null threshold", "Flag >=20%, including exactly20%. Flag is advisory, not removal."),
        ("VIF", "Train-imputed correlation inverse. All-null/constant columns: undefined, retained in results. Numerical null-space dependencies: inf."),
        ("VARCLUS", "varclushi PCA/quartimax clustering; split while second eigenvalue >1; no random starts. Smaller R2 ratio suggests representative."),
        ("Undefined correlations", "Constant/all-null columns excluded only from correlation computations, never from original datasets or fitted diagnostic input schema."),
        ("Permutation", "Validation 30-observation block permutations,20 repeats. Positive means MSE worsens when permuted. Correlated features share importance."),
        ("Permutation intervals", "p05/p95 describe permutation-repeat dispersion, NOT an inferential confidence interval or significance test."),
        ("Extrapolation", "Additional post-fit diagnostics identify validation values outside training ranges and the largest terms in each fold's worst forecast; no refit or clipping."),
        ("Model acceptance", "95% paired block-bootstrap CI of MSE improvement over zero must have lower bound >0. Purities are dependent evidence."),
        ("Direction", "Sign accuracy only where abs(z_hat)>0.05 and realized z!=0; coverage is reported."),
        ("Time folds", "Six expanding windows across2025–2026 with7 calendar days embargo, checked >=30 observed bars. These are development folds."),
        ("Model2", "Not fitted. Price/return predictions use trailing sigma only and are labeled accordingly."),
        ("Next step", "Review Manual_Review sheet; select manually; later re-evaluate selected features on fresh/nested chronological evidence."),
    ]
    path = baseline/"Model1_Baseline_Review.xlsx"
    with pd.ExcelWriter(path, engine="xlsxwriter", engine_kwargs={"options": {"strings_to_formulas": False, "strings_to_urls": False}}) as writer:
        pd.DataFrame(notes, columns=["topic", "explanation"]).to_excel(writer, sheet_name="Read_Me", index=False)
        pd.DataFrame(list(CONFIG.items()), columns=["setting", "value"]).to_excel(writer, sheet_name="Run_Config", index=False)
        pd.DataFrame(audit["inputs"]).to_excel(writer, sheet_name="Source_Hashes", index=False)
        for name, frame in results.items():
            export = frame.copy()
            for c in export:
                if isinstance(export[c].dtype, pd.DatetimeTZDtype):
                    export[c] = export[c].astype(str)
            export.to_excel(writer, sheet_name=name[:31], index=False, inf_rep="inf")
        book = writer.book
        header = book.add_format({"bold": True, "bg_color": "#244875", "font_color": "white", "text_wrap": True})
        for name, sheet in writer.sheets.items():
            sheet.freeze_panes(1, 0)
            if name in results:
                data = results[name]
                sheet.autofilter(0, 0, len(data), len(data.columns)-1)
                for j, column in enumerate(data.columns):
                    sheet.write(0, j, column, header)
                    sheet.set_column(j, j, 42 if column in ("feature", "manual_notes") else 23)
                if name == "manual_review":
                    j = list(data.columns).index("manual_decision")
                    sheet.data_validation(1, j, len(data), j, {"validate": "list", "source": ["keep", "drop", "review"]})
            else:
                sheet.set_column(0, 0, 28)
                sheet.set_column(1, 1, 110)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=ROOT/"training_artifacts"/"_training_baseline")
    args = parser.parse_args()
    run_experiment(args.baseline)
