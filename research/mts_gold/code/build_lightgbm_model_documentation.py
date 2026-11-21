"""Build the audited GLD965 MA5 LightGBM/calibration model document; no model refit."""
from pathlib import Path
import hashlib
import json
import re

import numpy as np
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

REPO = Path(__file__).resolve().parents[3]
BASE = REPO / 'research/mts_gold/training_artifacts/_training_baseline/model1_15m_priceMA'
FINAL = BASE / '_final_basemod'
OUT = BASE / 'model_documentation'
SOURCE_REV = 'd6df6078b410df5cf4753180abd85c358a609c87'
URL = f'https://github.com/Watcharachai/tidewatch_wiki/blob/{SOURCE_REV}/'
INPUTS = {}


def read(path):
    p = BASE / path
    INPUTS[str(p.relative_to(REPO))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return pd.read_csv(p)


def fmt(x):
    if pd.isna(x):
        return '—'
    if isinstance(x, (float, np.floating)):
        if x != 0 and (abs(x) < .001 or abs(x) >= 1e7):
            return f'{x:.3e}'
        return f'{x:,.3f}'
    return str(x)


def link(paragraph, text, target):
    h = OxmlElement('w:hyperlink')
    h.set(qn('r:id'), paragraph.part.relate_to(target,
        'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True))
    r = OxmlElement('w:r'); prop = OxmlElement('w:rPr')
    color = OxmlElement('w:color'); color.set(qn('w:val'), '176B87'); prop.append(color)
    underline = OxmlElement('w:u'); underline.set(qn('w:val'), 'single'); prop.append(underline)
    r.append(prop); t = OxmlElement('w:t'); t.text = text; r.append(t); h.append(r); paragraph._p.append(h)


def build():
    OUT.mkdir(exist_ok=True)
    d = Document()
    s = d.sections[0]
    s.page_width, s.page_height = Inches(8.27), Inches(11.69)
    s.top_margin = s.bottom_margin = Inches(.65)
    s.left_margin = s.right_margin = Inches(.65)
    normal = d.styles['Normal']; normal.font.name = 'Calibri'; normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.08
    for name in ['Title', 'Heading 1', 'Heading 2', 'Heading 3']:
        d.styles[name].font.color.rgb = RGBColor.from_string('173B53')
    s.header.paragraphs[0].text = 'TIDEWATCH RESEARCH  |  GLD965 · 15 MINUTES · MA5'
    s.header.paragraphs[0].style = d.styles['Caption']
    foot = s.footer.paragraphs[0]; foot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    foot.add_run('Research documentation · 21 November 2026  |  ')
    field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'), 'PAGE'); foot._p.append(field)

    def p(text, style=None):
        return d.add_paragraph(text, style)

    def h(text, level=2):
        d.add_heading(text, level)

    def page(title):
        d.add_page_break(); h(title, 1)

    def table(frame, title=None, size=8, widths=None):
        if title:
            p(title, 'Caption')
        t = d.add_table(rows=1, cols=len(frame.columns)); t.style = 'Light Shading Accent 1'
        if widths is None and len(frame.columns) == 2:
            widths = [1.8, 5.17]
        if widths:
            t.autofit = False
            for col, width in zip(t.columns, widths):
                col.width = Inches(width)
        for c, name in zip(t.rows[0].cells, frame.columns):
            c.text = str(name)
        repeat = OxmlElement('w:tblHeader'); t.rows[0]._tr.get_or_add_trPr().append(repeat)
        for row in frame.itertuples(index=False, name=None):
            for cell, val in zip(t.add_row().cells, row):
                cell.text = fmt(val)
        for row in t.rows:
            if widths:
                for cell, width in zip(row.cells, widths):
                    cell.width = Inches(width)
            no_split = OxmlElement('w:cantSplit'); row._tr.get_or_add_trPr().append(no_split)
            for cell in row.cells:
                for para in cell.paragraphs:
                    para.paragraph_format.space_after = Pt(2)
                    for run in para.runs:
                        run.font.size = Pt(size)
        p('')

    def image(path, caption, width=6.8):
        path = Path(path)
        INPUTS[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
        d.add_picture(str(path), width=Inches(width)); p(caption, 'Caption')

    def ref(label, path, note=''):
        path = Path(path)
        assert path.exists(), path
        q = p(''); link(q, label, URL + str(path.relative_to(REPO)))
        if note:
            q.add_run(' — ' + note)

    folds = read('lightgbm_analysis/Fold_performance.csv')
    schedule = read('schedule.csv')
    importance = read('lightgbm_analysis/Feature_importance.csv')
    winners = read('lightgbm_analysis/Tuning_winners.csv')
    trials = read('lightgbm_analysis/Tuning_trials.csv')
    calibration = read('_try_calibration/Performance_by_fold.csv')
    regression = read('_try_calibration/Regression_statistics.csv')
    coef = read('_try_calibration/Regression_coefficients.csv')
    perf = read('_final_basemod/performance.csv')
    ci = read('_final_basemod/paired_comparison_CI.csv')
    schema = read('_final_basemod/feature_schema.csv')
    predictions = read('_final_basemod/all_time_predictions.csv.gz')
    preds = predictions[predictions.y_ma5.notna()].copy()
    preds['year'] = pd.to_datetime(preds.decision_at, utc=True).dt.tz_convert('Asia/Bangkok').dt.year
    names = {'prediction_lightgbm': 'Raw LightGBM', 'prediction_isotonic': 'Isotonic',
             'prediction_linear': 'Linear', 'structural_persistence': 'Structural'}
    years = []
    for year, group in preds.groupby('year'):
        for key, name in names.items():
            e = group[key] - group.y_ma5
            years.append(dict(year=year, model=name, rows=len(group), RMSE=np.sqrt(np.mean(e**2)),
                              MAE=np.mean(abs(e)), R2=1-np.sum(e**2)/np.sum((group.y_ma5-group.y_ma5.mean())**2)))
    years = pd.DataFrame(years); years.to_csv(OUT / 'Calendar_year_metrics.csv', index=False)

    d.add_heading('MTS Gold Forecasting\nModel Development Documentation', 0)
    p('GLD965 · 15-minute bars · Next-bar trailing five-price moving average', 'Subtitle')
    p('LightGBMRegressor, isotonic calibration and linear calibration')
    p('Version 1.0 | 21 November 2026 | Asia/Bangkok')
    p(f'Evidence snapshot: Git commit {SOURCE_REV}\nMarket snapshot: 1 January 2025–7 November 2026. Documentation date is not a market-data refresh.')
    h('Decision summary')
    p('The selected fold 3 LightGBM model and its two calibrators are reproducible research artifacts. Calibration reduces the base model’s price-level error in the later evaluation window. It does not establish useful incremental forecasting skill: structural persistence remains substantially more accurate in every reported comparison relevant to deployment.')
    table(pd.DataFrame([
        ['DEV: calibration fit', 4030, 1025.764267, 1209.612390, 27.069272],
        ['OOT1: later evaluation', 4001, 790.289929, 870.511778, 17.334534],
        ['Post-fold-3 backtest', 8051, 1249.717355, 763.333499, 15.444615],
    ], columns=['Period', 'Rows', 'Isotonic RMSE', 'Linear RMSE', 'Structural RMSE']), 'Errors are in original THB chart-quote units.')
    p('Recommendation: retain the frozen models for comparison and learning. Use structural persistence as the benchmark and operational fallback. Prioritize forecasting the unknown next-price innovation rather than fitting the entire MA5 level. Linear calibration is the simpler, more stable challenger on the later saved period; neither calibrator qualifies as an accepted predictive model against the structural benchmark.')
    h('Document map')
    for text in ['1. General Purpose', '2. Assumption and Model Setting (data + model)',
                 '3. Model Development (LightGBMRegressor and Calibration)', '4. Result Implementation',
                 '5. Limitation and Further Improvement', '6. GitHub File References',
                 'Appendix A. All 32 LightGBM tuning trials', 'Appendix B. Frozen 45-feature dictionary',
                 'Appendix C. Quarterly and DEV charts']:
        p(text)

    page('1. General Purpose')
    h('1.1 Research objective and project evolution')
    p('The original project concerns direct MTS Thailand chart prices for 96.5% gold (GLD965) and 99.99% gold (GLD9999), with intraday and daily horizons. The architecture separates quantitative market forecasts from proposed news-based forecast adjustments. An MDP remains a proposed forecast-adjustment component, never a trade-position sizing mechanism.')
    p('The research moved from data collection and return diagnostics to scaled-return baselines, then to the present GLD965 15-minute moving-average price experiment. This document traces the data and feature preparation relevant to that experiment, and documents only LightGBM and its calibration models. Lasso appears solely as the existing feature-selection tool. The broader volatility/direction decomposition, other symbols/horizons, MDP and news fusion are not implemented by this frozen MA5 package.')
    p('The earlier plan to reserve all of 2026 as a final test was superseded in the saved 15-minute experiment by four time-ordered folds spanning 2025–2026. Fold 3 itself trained on 2025 plus early 2026. This report therefore describes development and backtesting, not an untouched 2026 final test.')
    h('1.2 Prediction contract')
    p('At decision time t, after the GLD965 bar completes, predict the trailing five-close average that will exist when the next contiguous 15-minute bar completes. This is not the average of the next five future bars and is not a next-bar return prediction.')
    p('Y(t+1) = [P(t−3) + P(t−2) + P(t−1) + P(t) + P(t+1)] / 5')
    p('B(t) = [P(t−3) + P(t−2) + P(t−1) + 2P(t)] / 5')
    p('Y(t+1) − B(t) = [P(t+1) − P(t)] / 5')
    p('B is structural persistence: assume the next close equals the current close. Four components of the MA5 label are already known. Price-level R² can be high simply because prices move slowly relative to their absolute level. Incremental skill against B, rather than a large R², is the principal acceptance criterion.')
    h('1.3 Intended use')
    p('Research comparison, reproducible local inference, feature diagnostics and forecast monitoring. No trade execution, position sizing, transaction-cost model or profitability claim is part of this deliverable. The source is a chart-price feed; bid/ask side, executable liquidity and weight-basis details should be verified before mapping errors into business costs.')

    page('2. Assumption and Model Setting (data + model)')
    h('2.1 Data lineage and snapshot')
    p('The experiment reads feature_artifacts/market_features_15m.csv.gz, filters GLD965 and sorts by available_at. Raw MTS bars and reference data are assembled by the repository feature pipeline. Backward as-of joins restrict each row to information considered available by the decision time; age limits mask stale observations. The model-preparation layer then shifts every inherited source-lag field one additional MTS row.')
    table(pd.DataFrame([
        ['Target', 'GLD965 direct MTS 96.5% chart close; THB quote units'],
        ['Sampling', 'Observed 15-minute completed bars; gaps retained, not interpolated'],
        ['Context', '42,803 rows; 40,226 scoreable labels; 2,577 null labels'],
        ['Snapshot', '2025-01-01 00:15 to 2026-11-07 05:00, Asia/Bangkok'],
        ['Frozen base model', 'Fold 3; 24,087 matured training rows; 45 features'],
        ['Original validation', '8,062 rows; subdivided for calibration and evaluation'],
        ['Price target transformation', 'Training mean/std standardization; inverse transform before calibration'],
        ['Source hash', 'c86355c3622c6a97139a1e9774ccff90aba6f726a6a1cfe2d9a1150d980a08b1'],
    ], columns=['Item', 'Specification']))
    p('Source families include own and cross-purity MTS prices, MTS XAU/USD, BTC/USDT, XAUT/USDT where available, S&P 500, Nasdaq, DJIA, US yields, VIX, USD/THB and WTI oil. Presence in the candidate universe does not imply inclusion in the selected model. The frozen fold 3 schema contains no XAUT, S&P 500, WTI, SET, silver or gold-futures feature. Its volume features are BTC/USDT volumes; MTS does not expose volume through the current chart feed. No MTS volume has been invented.')
    p('XAUT/USDT is a tokenized-gold reference and should not be conflated with an uploaded XAU/USDT series or spot XAU/USD. The earlier uploaded 30/60-minute reference is not an input in the final 15-minute schema. Daily FRED availability is approximated as observation date plus two UTC days, not verified publication or vintage time. This remains a material data assumption.')
    h('2.2 Label and timing rules')
    p('Own log returns require adjacent timestamps exactly 15 minutes apart. Both the current and next MA5 windows must be contiguous; missing bars, warm-up and unmatured final labels are excluded from scoring. The final context is retained for audit even when Y is null. Each fold/inner segment uses labels that mature within its allowed boundary. Timestamps are stored in UTC; period definitions and quarterly charts use Asia/Bangkok. Some older overview figures retain UTC axes.')
    p('Unlike the earliest year-held-out protocol, this experiment does not reserve the year boundary as a train/test boundary. Where actual bars are contiguous, the saved MA5 definition can cross a calendar-year boundary; segment maturity rules determine eligibility. Do not apply the older return-label assumptions to this different target.')
    h('2.3 Preprocessing and feature timing')
    p('All diagnostics and preprocessing are fitted within the appropriate training segment. Missing values use training medians; X uses training mean/std scaling. Outer models refit these statistics on their own matured training rows. Y uses training mean and population standard deviation and is inverted to THB before all reported price metrics and calibration. Feature scaling is retained to reproduce the shared selection pipeline, although trees do not require it.')
    p('Historical Z_return_lag5 is clip[r(t−5)/sigma(t−5), −5, 5]. sigma is an EWMA scale with half-life 30 bars, seeded from the fold-training mean of squared own log returns. It is an input, not this experiment’s Y. The frozen package retains the original fold 3 seed. Training-seeded backcasts are retrospective preprocessing, not a simulation of a model already deployed at the first historical bar.')
    h('2.4 Chronological validation design')
    p('Four expanding TimeSeriesSplit folds use a 30-context-row gap. Inside outer training, the first 60% fits feature diagnostics and candidate models; the next 20% ranks features using Lasso block permutations; the final 20% evaluates parameter candidates. There are additional 30-row inner gaps and label-maturity filters. Thirty observed bars need not equal 7.5 clock hours across a closure. No random train/test shuffle is used.')
    sched = schedule[['fold', 'train_rows', 'selection_fit_rows', 'permutation_rows', 'tuning_rows', 'test_rows']]
    table(sched.rename(columns={'fold':'Fold','train_rows':'Train','selection_fit_rows':'Inner fit','permutation_rows':'PI block','tuning_rows':'Tune','test_rows':'Validate'}))
    times = folds[['fold','test_start_Bangkok','test_end_Bangkok']].copy()
    for c in times.columns[1:]: times[c] = times[c].str.replace('+07:00','', regex=False)
    table(times.rename(columns={'fold':'Fold','test_start_Bangkok':'Validation start (Bangkok)','test_end_Bangkok':'Validation end (Bangkok)'}))
    p('Folds are sequential periods with different training sizes and market regimes. Their RMSEs are descriptive comparisons, not paired tests of identical samples. Pooled out-of-fold metrics combine four separately fitted models, whereas the all-time package applies one frozen fold 3 model. These are different estimands and must not be compared as if only the calibration changed.')

    page('3. Model Development (LightGBMRegressor and Calibration)')
    h('3.1 Feature definitions and selection waterfall')
    table(pd.DataFrame([
        ['Source close_lagK', 'Source close K source observations earlier; then shifted one MTS row after joining.'],
        ['Source return_lagK', 'Simple cumulative return C(s)/C(s−K)−1, ending at source s; then shifted one MTS row. Not a one-bar log-return lag.'],
        ['Source elapsed_min_lagK', 'Elapsed minutes between source s and s−K; gap/context proxy, not source age.'],
        ['Source volume_lagK', 'Source volume K source observations earlier, followed by extra MTS-row shift. Units remain source-specific.'],
        ['own_return_lagK', 'Single-bar GLD965 log return shifted K observed MTS rows; gap returns null.'],
        ['own_return_STATw_lag1', 'Statistic of preceding w own log returns, excluding decision-bar return; w = 7, 15, 30.'],
        ['Z_return_lag5', 'Clipped EWMA-scaled own one-bar log return five observed bars earlier.'],
    ], columns=['Feature family','Definition']))
    p('Rolling statistics are minimum, maximum, mean, sample variance (ddof=1), pandas bias-corrected skewness and excess kurtosis (normal reference = 0). Every window requires w valid observations. A gap-return null therefore invalidates any window containing it. Source 1d lags are daily source observations, not 15-minute lags. Own lag features and cumulative source returns intentionally have different definitions.')
    p('The inherited numeric fields plus new candidates total 246 unique fields at the first screen. Fifty non-lag/current or label-related fields are excluded, leaving 196 strictly lagged candidates. The selection waterfall is recomputed separately for every fold:')
    for text in [
        'Remove features with null fraction ≥20% in the inner diagnostic-fit sample.',
        'Remove features with at most one non-null unique value (zero variance).',
        'Run VARCLUS on median-imputed data (maxeigval2=1.0, n_rs=0); keep up to three per cluster with the smallest R² ratio. This is cluster representation, not target relevance.',
        'Recompute VIF iteratively and remove the largest value above 10 until all remaining features pass. Singular collinearity is handled explicitly.',
        'Fit Lasso with alpha=0.01 on standardized X/Y; rank features on the separate selection block using 20 block-permutation repetitions with 30-row blocks. Keep up to 45; the fixed cap does not require positive importance.',
        'Tune LightGBM using these selected features, then refit the winning specification and preprocessing on the full outer training period.'
    ]: p(text, 'List Number')
    waterfall = read('waterfall.csv').pivot(index='stage', columns='fold', values='after').reset_index()
    waterfall.columns = ['Stage','Fold 1','Fold 2','Fold 3','Fold 4']; table(waterfall)
    h('3.2 Feature results and stability')
    p('All four models retain 45 columns; not all are used in splits. Fold 3 uses 36. The dominant feature changes substantially between folds. This instability is consistent with shifting price regimes, correlated reference levels and the hard representative-selection rules. The selection procedure is valid as an experimental rule, but is not evidence that all retained features predict future innovations.')
    top = importance.sort_values(['fold','gain_rank']).groupby('fold').head(3).copy()
    top['Gain %'] = top.gain_share * 100
    table(top[['fold','feature','Gain %','permutation_MSE_increase']].rename(columns={'fold':'Fold','feature':'Feature','permutation_MSE_increase':'Validation PI ΔMSE'}), 'Top three by training gain in each fold. Positive permutation ΔMSE means shuffling worsens the model.')
    p('Fold 3 assigns 99.403% of split gain to mts_xauusd_15m_close_lag1. This is primarily a price-level mapping. US yields and daily XAU returns receive small gain shares, and several have negative validation permutation importance. Fold 2 assigns 99.848% of gain to the own lagged close, yet its validation permutation effect is zero: the later regime can map observations into the same saturated tree region. Gain is not incremental out-of-sample information.')
    p('Reported importance has three meanings: split gain describes training loss reduction; mean absolute TreeSHAP describes the size of model contributions on validation rows, not predictive utility or causality; block permutation measures change in validation MSE when a feature is disturbed. Permutation repetition percentiles quantify perturbation variability, not a population confidence interval. Correlated features and implausible shuffled combinations limit all rankings.')
    overlap = read('lightgbm_analysis/Fold_overlap.csv')
    table(overlap[['first_fold','second_fold','selected_intersection','selected_Jaccard','top10_gain_intersection']].rename(columns={'first_fold':'Fold A','second_fold':'Fold B','selected_intersection':'Shared / 45','selected_Jaccard':'Jaccard','top10_gain_intersection':'Shared top 10'}))
    p('Selected-feature Jaccard overlap ranges from 0.286 to 0.579. The complete frozen 45-feature dictionary and fold 3 gain/permutation results are in Appendix B. Full diagnostics, discarded-feature lineage and all 180 fold-feature importance records remain in the linked Excel/CSV files.')

    h('3.3 LightGBM parameters and tuning')
    table(pd.DataFrame([
        ['Estimator / objective','LGBMRegressor; Huber loss'],['Fixed structure','max_depth=3; num_leaves=7'],
        ['Reproducibility','random_state=42; n_jobs=1; verbosity=−1'],
        ['Grid','learning_rate ∈ {0.03, 0.07}; n_estimators ∈ {100, 250}; min_child_samples ∈ {50, 150}'],
        ['Selection loss','MSE of standardized Y on the chronological inner tuning block'],
        ['Trials','8 configurations × 4 folds = 32; no new tuning in this documentation'],
        ['Stopping','Fixed tree counts in the grid; no early-stopping callback in this MA5 implementation'],
        ['Other parameters','Library defaults from LightGBM 4.7.0; serialized Booster captures trained state'],
    ], columns=['Setting','Value']))
    table(winners[['fold','learning_rate','min_child_samples','n_estimators','tuning_RMSE_THB']].rename(columns={'fold':'Fold','learning_rate':'Learning rate','min_child_samples':'Min child','n_estimators':'Trees','tuning_RMSE_THB':'Inner RMSE'}))
    p('The original conceptual baseline proposed early stopping, but the saved MA5 experiment actually uses a fixed 8-point grid. Appendix A records every tried configuration and its tuning error. The highest-R² fold is not automatically the model with the lowest RMSE, and selecting a fold after observing its validation score adds selection optimism.')
    evidence = read('lightgbm_analysis/Tuning_decision_evidence.csv')
    table(evidence[['fold','runnerup_pct_MSE_above_winner','winner_advantage_CI_low','winner_advantage_CI_high']].rename(columns={'fold':'Fold','runnerup_pct_MSE_above_winner':'Runner-up excess MSE %','winner_advantage_CI_low':'Gain CI low','winner_advantage_CI_high':'Gain CI high'}))
    p('For fold 3, the runner-up differs by only 0.0205% MSE and the paired interval includes zero. The chosen parameter set is the empirical minimum, not a statistically established unique optimum. These tuning-block comparisons are conditional on selection and have no multiple-comparison adjustment.')

    h('3.4 Statistical metrics and base-model validation')
    p('RMSE = sqrt(mean[(prediction−actual)²]); MAE = mean absolute error; conventional R² = 1−SSE/SST about the evaluated sample mean. Structural skill = 1−MSE(model)/MSE(structural). Negative skill means the model is worse. Mean error is prediction minus actual. All price metrics are calculated after inverse target scaling.')
    p('Paired MSE improvement = MSE(reference)−MSE(model), so positive favors the model. The saved 95% intervals use 1,000 paired circular bootstrap resamples of 30 observations, stratified by fold for the original experiment and by provenance in the all-time package. Serial dependence, changing regimes and many comparisons mean these intervals are exploratory; acceptance requires an improvement interval wholly above zero on genuinely later data.')
    table(folds[['fold','train_RMSE','RMSE','MAE','R2','baseline_RMSE','validation_train_RMSE_ratio']].rename(columns={'fold':'Fold','train_RMSE':'Train RMSE','RMSE':'Val RMSE','MAE':'Val MAE','R2':'Val R²','baseline_RMSE':'Struct. RMSE','validation_train_RMSE_ratio':'Val/train'}))
    table(folds[['fold','mse_improvement_ci_low','mse_improvement_ci_high']].rename(columns={'fold':'Fold','mse_improvement_ci_low':'Structural MSE gain: lower 95%','mse_improvement_ci_high':'Upper 95%'}))
    p('Pooled original LightGBM out-of-fold RMSE is 5,117.16, versus 18.53 for structural persistence. Every fold has a negative structural-gain interval. Train-to-validation degradation is large, especially fold 2 (246.94× RMSE). In that fold, 99.900% of validation targets exceed the training maximum, exposing the inability of a piecewise tree level mapping to extrapolate into the new price regime. This is both a generalization failure and a distribution-shift problem; it should not be attributed solely to excess tree complexity.')
    p('Fold 3 has the highest original validation R² (0.6797), and fold 1 has the lowest absolute validation RMSE (1,578.42). Fold 3 was highlighted post hoc and exported at the user’s request; it was not selected by a prespecified independent final-test rule.')

    h('3.5 Calibration design and parameters')
    p('Calibration uses X = the frozen base prediction in THB and Y = observed next-bar MA5. In each original validation fold, the first 50% of available predictions fits a calibrator, the next 30 prediction observations form an embargo, and the remaining observations evaluate it. Labels must mature before the fit boundary. Base LightGBM models are unchanged. Fold 3 has 4,030 fit rows, 31 excluded/context rows and 4,001 evaluation rows after maturity handling.')
    table(pd.DataFrame([
        ['Isotonic','Monotone least-squares mapping g(X); increasing=True; out_of_bounds=clip.'],
        ['Linear','Y = b0 + b1 X. Two coefficients.'],
        ['Quadratic','Y = b0 + b1 X + b2 X². Three coefficients.'],
        ['Cubic','Y = b0 + b1 X + b2 X² + b3 X³. Four coefficients.'],
    ], columns=['Calibrator','Specification']))
    p('Polynomial regression is fitted using standardized X powers for numerical stability, with raw-X coefficients also exported. HAC covariance uses 30 observed lags for descriptive regression inference. Isotonic has no OLS coefficient standard errors, conventional F-test or OLS AIC/BIC. Its 119 stored thresholds in fold 3 are not comparable to 119 free regression coefficients; the fitted threshold outputs contain 67 unique levels and prediction interpolates monotonically between stored thresholds.')
    split = read('_try_calibration/Chronological_split.csv')
    table(split[['fold','fit_rows','evaluation_rows','fit_start_Bangkok','evaluation_end_Bangkok']].rename(columns={'fold':'Fold','fit_rows':'Fit N','evaluation_rows':'Eval N','fit_start_Bangkok':'Fit start (Bangkok)','evaluation_end_Bangkok':'Eval end (Bangkok)'}))
    p('Frozen fold 3 DEV: 12 February 2026 12:45–21 April 2026 22:15. OOT1: 22 April 2026 08:45–26 June 2026 20:15, Bangkok time. The raw-prediction calibration input range is 64,283.119–77,513.468. Isotonic clips outside this range, producing a bounded output even when earlier or later price regimes need a different level.')
    c3 = coef.query('fold == 3 and model == "linear" and basis == "raw_X"')
    table(c3[['term','coefficient','HAC_standard_error','HAC_p_value','HAC_CI_low','HAC_CI_high']].rename(columns={'term':'Term','coefficient':'Coefficient','HAC_standard_error':'HAC SE','HAC_p_value':'HAC p','HAC_CI_low':'95% low','HAC_CI_high':'95% high'}))
    p('Fold 3 linear mapping: calibrated MA5 ≈ 10,501.301260 + 0.877323 × raw LightGBM MA5. Use the saved full-precision coefficients for inference. Small p-values describe association in the fit block; they do not establish future forecasting skill.')
    stats = regression.query('fold == 3 and model != "isotonic"')
    table(stats[['model','R2_fit','adjusted_R2','AIC','BIC','Durbin_Watson','JB_p']].rename(columns={'model':'Model','R2_fit':'Fit R²','adjusted_R2':'Adj. R²','Durbin_Watson':'DW','JB_p':'JB p'}))
    p('The linear residual Durbin–Watson statistic is 0.048, indicating strong positive serial dependence; normality is rejected by the Jarque–Bera diagnostic. HAC addresses a chosen dependence horizon, not nonstationarity or selection bias. Slightly better polynomial fit R² and AIC/BIC did not translate into the best later prediction error.')

    h('3.6 Calibration performance and model choice')
    ev = calibration.query('partition == "later_evaluation" and calibrator != "MA_persistence"')
    pivot = ev.pivot(index='calibrator', columns='fold', values='RMSE').reset_index()
    pivot.columns = ['Model','Fold 1','Fold 2','Fold 3','Fold 4']; table(pivot, 'Later-block RMSE: each fold uses its own base model and earlier calibrator fit.')
    pooled = read('_try_calibration/Pooled_later_evaluation.csv')
    table(pooled[pooled.calibrator.ne('MA_persistence')][['calibrator','RMSE','R2','gain_vs_raw_CI_low','gain_vs_raw_CI_high']].rename(columns={'calibrator':'Model','R2':'R²','gain_vs_raw_CI_low':'Gain vs raw: CI low','gain_vs_raw_CI_high':'CI high'}))
    p('On the pooled later calibration blocks (15,973 rows), all four calibrators improve materially over the raw LightGBM predictions. None beats structural persistence: its RMSE is 18.73, compared with 4,150.15 for isotonic and 4,287.12 for linear. Calibration repairs systematic level bias; it cannot recover missing next-bar information from a single inadequate base prediction.')
    highlight = ev.query('fold == 3')
    table(highlight[['calibrator','RMSE','MAE','R2','gain_vs_structural_CI_low','gain_vs_structural_CI_high']].rename(columns={'calibrator':'Fold 3 OOT1','R2':'R²','gain_vs_structural_CI_low':'Structural gain CI low','gain_vs_structural_CI_high':'CI high'}))
    p('For the frozen export, retain isotonic as the empirical OOT1 winner and linear as the lower-complexity challenger. Quadratic and cubic are not chosen: their fold 3 OOT1 RMSEs (1,305.87 and 1,019.52) are worse than both simpler retained alternatives. More curvature also makes extrapolation fragile. This is a research choice, not production acceptance.')
    image(BASE/'_try_calibration/calibration_fitted_lines.png', 'Calibration functions and fit/evaluation data for the four original base folds. Source: calibration experiment.')

    h('3.7 Frozen-model validation, overfitting and period provenance')
    pp = perf.query('slice_type == "period"').copy(); pp = pp[pp.model.isin(names)]
    pp['model'] = pp.model.map(names)
    table(pp.pivot(index='period',columns='model',values='RMSE').reset_index(), 'Frozen fold 3 RMSE by named period; ALL mixes fitted and later observations.')
    table(years, 'Bangkok calendar-year metrics recomputed from unchanged saved predictions; not independent year holdouts.')
    p('REST_2025 is a base-training backcast, with 2026-fitted calibrators applied retrospectively. DEV is calibration training. OOT1 is its original later evaluation. REST_2026 mixes early base training, boundary/embargo rows and post-fold-3 data; use provenance to isolate the later backtest. All periods have already been inspected. A better ALL score cannot be interpreted as better future performance.')
    later = perf.query('slice_type == "provenance" and period == "post_fold3_backtest"').copy()
    table(later[later.model.isin(names)][['model','rows','RMSE','MAE','R2']].replace({'model':names}), 'Post-fold-3 frozen-model backtest: later than the original fold 3 evaluation.')
    selected_ci = ci[(ci['first']=='prediction_isotonic') & (ci.second=='prediction_linear') &
                     (((ci.slice_type=='period') & ci.period.isin(['DEV','OOT1'])) | (ci.period=='post_fold3_backtest'))]
    table(selected_ci[['period','MSE_gain_first','CI_low','CI_high']].rename(columns={'period':'Period','MSE_gain_first':'Isotonic MSE advantage','CI_low':'95% low','CI_high':'95% high'}))
    p('Isotonic beats linear descriptively on DEV, where it was fitted. Its OOT1 advantage is not statistically resolved: the paired 95% interval includes zero. Later, linear is clearly better within the saved paired-bootstrap analysis. Isotonic’s DEV-to-OOT1 error does not increase, so there is no simple immediate overfitting collapse. Its later instability and severe 2025 failure instead reveal range clipping, fit-period specificity and regime mismatch. The distinction matters when choosing the next experiment.')
    p('Raw base predictions fall outside isotonic’s fitted input range for 17.92% of OOT1 and 62.02% of the later backtest. Linear extrapolates smoothly and has only two fitted coefficients, but cannot restore information lost when the base tree saturates. Structural persistence has no fitted regression parameters; its strength comes from the MA5 target identity, not from high model complexity.')

    h('3.8 Prediction bands and quarterly validation')
    p('Each model’s DEV residuals e = actual−prediction define frozen empirical quantiles. The central 90% band is prediction + [q05(e), q95(e)]; the separate 95% band is prediction + [q025(e), q975(e)]. P05/P95 are percentile endpoints, not “5% and 95% confidence” measures. These are residual prediction bands, not confidence intervals for a conditional mean.')
    p('DEV residuals are in-sample for the calibrators; coverage there is optimistic by construction. Constant-width bands assume a residual distribution that does not change over time, although the data show regime changes. Serial dependence and retrospective use of 2026 calibration parameters in 2025 preclude a guaranteed coverage claim. Bootstrap intervals for model MSE differences are a separate calculation.')
    band = read('_final_basemod/quarterly_plots/Quarterly_band_coverage.csv')
    cov = band[band.model.isin(['Isotonic','Linear'])].copy()
    cov['90% coverage'] = 100*cov.empirical_coverage_90
    cov['95% coverage'] = 100*cov.empirical_coverage_95
    table(cov[['period','model','scored_rows','90% coverage','95% coverage']].rename(columns={'period':'Period','model':'Model','scored_rows':'Scored N'}), 'Empirical coverage in percent; Q4 2026 is partial through 7 November.')
    p('The first three quarters of 2025 have zero coverage for both calibrated models, confirming invalid cross-regime backcasting with these bands. In 2026 Q3, isotonic’s central 90% band covers about 83.71%, while linear covers 99.89%; undercoverage and excessive width are both calibration problems. All eight quarterly charts and the exact DEV chart appear in Appendix C.')

    page('4. Result Implementation')
    h('4.1 Frozen inference contract')
    for text in [
        'Prepare a completed-bar context using the original market-feature pipeline. Preserve source timestamps, lag definitions, source availability, gap rules and the frozen historical EWMA state. Do not shift the supplied prepared CSVs again.',
        'Require the exact 45 feature names and saved order. Replace infinities with nulls, impute using saved medians, then standardize using saved means/scales. Do not fit preprocessing on live or evaluation data.',
        'Load the native LightGBM Booster. Its output is standardized Y; invert with target_scale and target_mean from preprocessing.json.',
        'Pass the price-unit base prediction to isotonic (1-D input) or linear (n×1 input). The calibrated output is next-bar MA5 in THB quote units.',
        'Compute structural persistence alongside each forecast; add residual bands only with the documented coverage caveats. Log decision and expected-label timestamps, model/source versions, range flags and feature health.',
        'Score only after the next contiguous MA5 label matures. Keep gap/unmatured forecasts in the audit log but exclude them from model-error denominators.'
    ]: p(text, 'List Bullet')
    p('The desktop package scores prepared rows; it is not an end-to-end live ingestion service. All-time historical predictions were generated without refitting the model or calibrators. The latest snapshot ends 7 November 2026, not the documentation date.')
    h('4.2 Local execution')
    p('Extract Final_BaseModel_Desktop.zip. Use Python 3.12 and the pinned requirements. On Windows:')
    for line in ['py -3.12 -m venv .venv', '.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt', '.\\.venv\\Scripts\\python.exe predict_local.py']:
        p(line, 'No Spacing')
    p('On macOS/Linux, use python3.12 and .venv/bin/python. Open Final_BaseModel_Local.ipynb using the same environment. Run python quarterly_bands.py for the quarterly reports. Report scripts regenerate derived outputs; they do not train models. Only load pickle files from the trusted repository/package; native model text and JSON alternatives are included.')
    table(pd.DataFrame([
        ['prediction_bundle.pkl','Base Booster + both calibrators + preprocessing; complete frozen inference bundle.'],
        ['lightgbm_fold3.pkl / .txt','Base model; requires ordered, transformed features and target inverse scaling.'],
        ['isotonic_fold3.pkl / linear_fold3.pkl','Price-unit calibration models; reconstructed from original saved parameters.'],
        ['feature_schema.csv / preprocessing.json','45 columns and fitted numerical transforms.'],
        ['base_training_X_y.csv.gz','24,087 original base-training labeled rows.'],
        ['base_validation_X_y.csv.gz','8,062 original validation rows, including calibration fit/evaluation contexts.'],
        ['calibration_dev_X_y.csv.gz','4,030 calibrator-fit rows.'],
        ['validation_oot1_X_y.csv.gz','4,001 later calibration-evaluation rows.'],
        ['post_fold3_backtest_X_y.csv.gz','Later context; 8,051 scoreable labels.'],
        ['all_time_X_y_context.csv.gz','42,803 contexts, X/Y, timestamps, baselines and provenance.'],
        ['checksums.json / verification.json','Artifact identity and prediction-reproduction checks.'],
    ], columns=['Package file','Use']))
    h('4.3 Monitoring and acceptance gate (proposed)')
    p('Monitor feature null/stale rates, schema/order, predicted-input range violations, rolling bias, RMSE versus structural persistence, empirical band coverage/width, and error by Bangkok hour and volatility regime. Daily reference publication timing and model/source version must be logged. The current package contains batch inference and reports; automated retraining, alert thresholds and production fallback routing are recommendations, not implemented services.')
    p('Before replacing persistence, freeze a candidate and a genuinely new future evaluation window. Require a positive lower 95% block-bootstrap bound for MSE gain versus structural persistence, consistent behavior across regimes, and no operational timing violations. Preserve a rollback version and structural fallback. Neither current calibrator passes this predictive-skill gate on the saved comparisons.')

    page('5. Limitation and Further Improvement')
    h('5.1 Benefits and limitations by model')
    table(pd.DataFrame([
        ['LightGBM','Captures nonlinear interactions; small depth; fast frozen inference; auditable gain/SHAP.','Poor price-level extrapolation; large train/validation gaps; dominant proxy levels; failure versus structural baseline.'],
        ['Isotonic','Flexible monotone bias correction; best fold 3 OOT1 point RMSE.','Fit-period dependent; clips out of range; cannot infer new information; can overfit residual shape and fails across historical regimes.'],
        ['Linear calibration','Two coefficients; interpretable; smooth extrapolation; best later frozen calibrated-model RMSE.','Assumes stable affine correction; base prediction saturation remains; strong residual dependence; still far worse than persistence.'],
        ['Quadratic/cubic','Allow smooth nonlinear correction and provide regression diagnostics.','Small fit gains did not win fold 3 evaluation; unstable extrapolation and unnecessary flexibility.'],
        ['Structural persistence','No fitted coefficients; causal completed-price construction; strongest empirical benchmark.','Assumes zero next-price change; does not demonstrate directional skill; requires valid recent closes and same target contract.'],
    ], columns=['Model','Benefits','Limitations']))
    h('5.2 Cross-cutting limitations')
    for text in [
        'Target overlap and high persistence: adjacent MA5 labels share four prices, inducing serial dependence and making price-level R² visually impressive without forecasting the unknown move.',
        'Development contamination: 2026 participates in training, tuning/calibration and repeated inspection. No claim of a pristine held-out 2026 test remains. Fold 3 selection was post hoc.',
        'Feature timing tradeoff: the strict lag-only rule removes current completed information and adds one MTS-row delay to already lagged references. This is conservative but can materially reduce useful short-horizon information.',
        'Selection limitations: VIF is a linear-design diagnostic, not a requirement for trees. VARCLUS can discard a useful price anchor. Lasso ranking can suppress nonlinear interactions, and a fixed top 45 includes nonpositive importance.',
        'Data quality and measurement: sparse gold proxies, unavailable MTS volume, uncertain daily publication/vintage times and different source calendars. Source returns are cumulative simple returns, while own features use one-bar log returns.',
        'Inference limits: trend-driven OLS association, non-Gaussian dependent errors, arbitrary 30-row bootstrap/HAC horizon, post-selection comparisons and no multiplicity adjustment. Tiny provenance slices cannot support reliable bootstrap inference.',
        'Uncertainty limits: DEV-fit constant residual bands are neither conditional-volatility forecasts nor validated conformal intervals. Future coverage must be tested on genuinely later residuals.',
        'Scope limits: no validated news/MDP layer, no independent volatility model, no live pipeline or executable-price backtest. The frozen artifacts concern one symbol, interval and target.'
    ]: p(text, 'List Bullet')
    h('5.3 Prioritized development plan')
    table(pd.DataFrame([
        ['1','Reformulate Y as the innovation','Fit d(t+1)=P(t+1)−P(t), or Y−B=d/5. Reconstruct MA5 as B+d_hat/5. This prevents the learner from relearning four known prices.'],
        ['2','Restore a clean evaluation','Lock a future period after all saved inspected dates; run nested expanding/rolling training with purged labels and explicit availability. Fit calibration on earlier out-of-fold predictions only.'],
        ['3','Run timing and selection ablations','Compare freshest completed-bar features with the current extra-shift design. Compare compact own-return/fair-value features, tree-specific selection, and no VIF screen, using training folds only.'],
        ['4','Improve target-relative features','Use price ratios/gaps and returns rather than absolute levels; synchronized MTS/XAU/USD/USDTHB fair-value deviations; volatility, session flags and source freshness. Verify units and point-in-time FX.'],
        ['5','Simplify and validate calibration','Start with no calibration versus affine residual/bias correction on earlier out-of-fold predictions; retain isotonic only if stable later gains survive range and regime checks.'],
        ['6','Model uncertainty separately','Return to the proposed EWMA/HAR magnitude model, then compare volatility-scaled residual intervals or rolling conformal/quantile methods under dependent-data validation.'],
        ['7','Acquire and audit better data','Verify release timestamps/vintages; investigate licensed gold futures/volume and USDTHB intraday sources. Add news/MDP forecast adjustments only after a quantitative improvement is demonstrated.'],
    ], columns=['Priority','Action','Rationale / experiment']))
    p('Do not interpret better calibration fit statistics or more hyperparameter searches as a solution to the target problem. The next decisive experiment is whether a causal residual/return model improves on zero innovation. If it does not, retain persistence and concentrate on uncertainty estimation and data quality.')

    page('6. GitHub File References')
    p(f'Links below are pinned to evidence commit {SOURCE_REV[:7]} so the results remain reproducible. The new document is saved separately from the frozen desktop package; neither original models nor notebooks are modified by this documentation build. File hashes used by this report are recorded in documentation_manifest.json.')
    refs = [
        ('6.1 Purpose, architecture and earlier data study', [
            ('Architecture DOCX', REPO/'research/mts_gold/analysis/docs/Gold_Price_Predictive_Model_Architecture.docx', 'Original project framework; broader than this MA5 experiment.'),
            ('Model-readiness DOCX', REPO/'research/mts_gold/analysis/docs/MTS_Model_Readiness_Summary.docx', 'Earlier 30/60-minute statistics and modeling rationale; do not substitute for 15-minute results.'),
            ('Feature preparation source', REPO/'research/mts_gold/code/features.py', 'Source availability, as-of joins and feature formulas.'),
            ('15-minute feature dataset', REPO/'research/mts_gold/feature_artifacts/market_features_15m.csv.gz', 'Underlying saved market-feature table.'),
        ]),
        ('6.2 Feature selection and LightGBM development', [
            ('Executed training notebook', BASE/'GLD965_15m_priceMA_Training.ipynb', 'Fold preparation, waterfall and modeling results.'),
            ('Training review Excel', BASE/'GLD965_15m_priceMA_Review.xlsx', 'Null/variance, VARCLUS, VIF, permutation, tuning and scores.'),
            ('Original experiment DOCX', BASE/'GLD965_15m_priceMA_Report.docx', 'Contemporaneous MA5 report; broader model-family comparison.'),
            ('LightGBM analysis Excel', BASE/'LightGBM_Fold_Analysis.xlsx', 'All importance, tuning and comparison tables.'),
            ('Feature importance CSV', BASE/'lightgbm_analysis/Feature_importance.csv', 'Gain, SHAP and validation block permutation for each fold.'),
            ('Selection lineage CSV', BASE/'lightgbm_analysis/Selection_lineage.csv', 'Retained/discarded status for all 196 candidates in each fold.'),
            ('Full tuning trials CSV', BASE/'lightgbm_analysis/Tuning_trials.csv', '32 trials and paired statistical evidence.'),
            ('MA5 experiment source', REPO/'research/mts_gold/code/model1_15m_priceMA.py', 'Exact target, splits and estimator parameters.'),
        ]),
        ('6.3 Calibration and regression statistics', [
            ('Calibration analysis Excel', BASE/'_try_calibration/LightGBM_Calibration_Analysis.xlsx', 'Performance, coefficients, HAC statistics, splits and fitted curves.'),
            ('Calibration source', REPO/'research/mts_gold/code/calibrate_priceMA_lightgbm.py', 'Reproducible calibration experiment.'),
            ('Regression coefficients CSV', BASE/'_try_calibration/Regression_coefficients.csv', 'Every fold and polynomial coefficient in both bases.'),
            ('Regression statistics CSV', BASE/'_try_calibration/Regression_statistics.csv', 'Fit diagnostics for all calibrators.'),
            ('Calibration parameters JSON', BASE/'_try_calibration/calibrator_parameters.json', 'Full-precision coefficients and isotonic knots for all folds.'),
        ]),
        ('6.4 Frozen implementation and later validation', [
            ('Latest executed local notebook', FINAL/'Final_BaseModel_Local.ipynb', 'Frozen inference, period comparison and quarterly charts.'),
            ('Final comparison Excel', FINAL/'Final_BaseModel_Comparison.xlsx', 'ALL/DEV/OOT1/rest/provenance metrics and predictions.'),
            ('Quarterly bands Excel', FINAL/'Quarterly_Prediction_Bands.xlsx', 'Eight quarters plus DEV, residual quantiles and empirical coverage.'),
            ('Desktop ZIP', FINAL/'Final_BaseModel_Desktop.zip', 'Models, prepared datasets, notebook, dependencies and reports.'),
            ('Standalone inference script', FINAL/'predict_local.py', 'Exact frozen preprocessing and model invocation.'),
            ('Feature schema', FINAL/'feature_schema.csv', 'Exact feature order and fitted scaling.'),
            ('All-time training/context dataset', FINAL/'all_time_X_y_context.csv.gz', 'X/Y and period/provenance flags; not a single training split.'),
            ('All-time predictions', FINAL/'all_time_predictions.csv.gz', 'Unchanged row-level evidence used by this report.'),
            ('Package metadata', FINAL/'package_metadata.json', 'Version, provenance, split definitions and source hash.'),
            ('Package README', FINAL/'README.md', 'Desktop commands, file contracts and interpretation.'),
        ]),
    ]
    for title, rows in refs:
        h(title)
        for label, path, note in rows: ref(label, path, note)
    p('There is no separate calibration DOCX in the saved calibration folder; the present document consolidates those findings. The latest local notebook and the calibration Excel/source are the reproducible records for that stage.')

    page('Appendix A. All 32 LightGBM Tuning Trials')
    p('No additional tuning was run. Each table reports the original eight candidates for one fold. Rank is within the chronological inner tuning block. The selected configuration has rank 1. Fixed parameters: Huber objective, max_depth=3, num_leaves=7, random_state=42, n_jobs=1; other parameters use the saved LightGBM 4.7.0 defaults.')
    for fold, group in trials.groupby('fold'):
        h(f'A.{fold} Fold {fold}')
        table(group.sort_values('rank')[['rank','learning_rate','min_child_samples','n_estimators','tuning_mse_scaled','tuning_RMSE_THB']].rename(columns={'rank':'Rank','learning_rate':'Rate','min_child_samples':'Min child','n_estimators':'Trees','tuning_mse_scaled':'Scaled MSE','tuning_RMSE_THB':'THB RMSE'}))

    page('Appendix B. Frozen 45-Feature Dictionary')
    p('Listed in the exact frozen preprocessing order. Source-family features were additionally shifted one MTS row after as-of joining. Source return_lagK denotes a K-observation cumulative simple return; own_return_lagK denotes a shifted single-bar log return. Gain % refers to training split gain. Validation PI is the 20-repeat mean increase in MSE when the feature is block-permuted; a negative value is not evidence of predictive usefulness.')
    def describe(name):
        if name == 'Z_return_lag5': return 'Own one-bar log return / historical EWMA sigma, clipped ±5; shift 5.'
        if name.startswith('own_return_'):
            stem = name.removeprefix('own_return_')
            if stem.startswith('lag'): return f'Own single-bar log return shifted {stem[3:]} observed bars.'
            stat, window = re.match(r'([a-z]+)(\d+)_lag1', stem).groups()
            return f'Own log-return {stat} over preceding {window} bars; excludes bar t.'
        market, tf, measure, lag = re.match(r'(.+)_(15m|1d)_(.+)_lag(\d+)', name).groups()
        labels = {'close': 'lagged level', 'return': 'cumulative simple return', 'volume':'lagged volume', 'elapsed_min':'source elapsed minutes'}
        return f'{market}; {tf}; {labels[measure]}; K={lag} source observations.'
    imp3 = importance.query('fold == 3').set_index('feature')
    dictionary = schema[['feature']].copy()
    dictionary['Definition'] = dictionary.feature.map(describe)
    dictionary['Gain %'] = dictionary.feature.map(imp3.gain_share)*100
    dictionary['PI ΔMSE'] = dictionary.feature.map(imp3.permutation_MSE_increase)
    dictionary.insert(0,'Order',range(1,46))
    dictionary.to_csv(OUT/'Frozen_feature_dictionary.csv',index=False)
    table(dictionary.rename(columns={'feature':'Feature'}), size=8, widths=[.42,2.25,2.4,.85,1.05])
    p('The numerical training medians, means and standard deviations are not rounded into this document; use feature_schema.csv and preprocessing.json for exact inference. All 45 prepared features remain in the supplied datasets, even when the fitted Booster does not use them in a split.')

    page('Appendix C. Quarterly and DEV Charts')
    p('Nine charts follow, each pairing actual MA5 with isotonic, linear, structural persistence and raw LightGBM predictions. Shaded bands are frozen DEV empirical residual bands: P05–P95 (90%) and P2.5–P97.5 (95%). Axes use Bangkok decision time. Actual refers to the next-bar label aligned with that decision. Charts show unsmoothed saved bars; 2025 is retrospective and 2026 Q4 is partial.')
    for period in ['2025Q1','2025Q2','2025Q3','2025Q4','2026Q1','2026Q2','2026Q3','2026Q4','DEV']:
        if period != '2025Q1':
            d.add_page_break()
        h(f'C. {period}')
        image(FINAL/f'quarterly_plots/{period}_actual_vs_models.png',
              f'{period}: pairwise actual/predicted MA5. Bands are empirical prediction bands, not confidence intervals for a mean.')
        if period.startswith('2025'):
            p('Retrospective base-training backcast with calibrators and bands estimated in 2026; not a forecast available during 2025.')
        elif period == 'DEV':
            p('Exact calibrator-fit period. Isotonic/linear fit and band coverage are in-sample.')
        elif period == '2026Q4':
            p('Partial quarter through 7 November 2026. No newer observations were fetched for this documentation.')
        else:
            p('Calendar quarter is not itself a validation role. DEV/OOT1 boundary lines mark only true boundaries within this quarter; use the provenance flags for statistical comparisons.')

    d.core_properties.title = 'MTS GLD965 15m MA5: LightGBM and Calibration Model Documentation'
    d.core_properties.subject = 'Data, features, tuning, validation, calibration, inference and limitations'
    d.core_properties.author = 'Tidewatch Research'
    d.core_properties.keywords = 'MTS; GLD965; LightGBM; calibration; time series; MA5'
    file = OUT/'MTS_GLD965_15m_LightGBM_Calibration_Model_Documentation.docx'
    d.save(file)
    manifest = {'documentation_date_Bangkok':'2026-11-21','evidence_commit':SOURCE_REV,
        'models_refitted':False,'original_artifacts_modified':False,
        'input_sha256':INPUTS,'document_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
        'validation':{'source_rows':len(predictions),'scoreable_rows':len(preds),'tuning_trials':len(trials),
        'features':len(schema),'embedded_figures':len(d.inline_shapes),'tables':len(d.tables),
        'github_links':sum('hyperlink' in rel.reltype for rel in d.part.rels.values()),
        'calendar_year_metrics':'Recomputed from unchanged predictions; descriptive, not holdout results.'}}
    assert len(predictions)==42803 and len(preds)==40226 and len(trials)==32 and len(schema)==45
    assert len(d.inline_shapes)==10
    (OUT/'documentation_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'docx':str(file),'validation':manifest['validation']},indent=2))


if __name__ == '__main__':
    build()
