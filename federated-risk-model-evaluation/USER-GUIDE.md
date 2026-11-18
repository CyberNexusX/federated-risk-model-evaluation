# Federated Risk Model Evaluation — User Guide

Read the [project homepage](README.md) for the study design, results, and sample use cases.

## Install and run

Use Python 3.11 or 3.12. From the repository root, run `python -m venv .venv`. Activate the environment with `source .venv/bin/activate` on macOS or Linux or `.\.venv\Scripts\Activate.ps1` on Windows PowerShell. Run:

```sh
python -m pip install -r requirements.txt
python evaluate.py --seed 42 --out build/evaluation.json
python -m unittest discover -s tests -v
```

The default seed is 42 and the default output is `build/evaluation.json`. Use different output paths for multiple runs.

## Report contract

| Field | Meaning |
|---|---|
| `training_n` | Eligible North and South patients from the earlier period |
| `horizon_days` | Fixed 365-day outcome window |
| `score_bin_edges` | Shared probability boundaries for every clinic |
| `site_payloads.<site>` | One entry per bin, including empty bins |
| `sites.<site>` | Local metrics derived from the clinic payload |
| `network` | Patient-weighted metrics derived from the sum of clinic payloads |

The score bins are left-inclusive and right-exclusive, except that the final bin includes 1.0. A score of 0.10 belongs to the second bin. The payload retains empty bins to keep positions aligned, while derived calibration reports show populated bins.

| Field in each payload bin | Calculation |
|---|---|
| `n` | Number of eligible evaluation patients whose scores fall in the bin |
| `events` | Number of patients with a recorded outcome |
| `score_sum` | Sum of predicted probabilities |
| `squared_error_sum` | Sum of squared differences between probabilities and binary outcomes |

Add the four quantities across sites. Derive the observed rate as events divided by patient count, the mean prediction as score sum divided by patient count, and the Brier score as squared error sum divided by patient count. Calibration gap is mean prediction minus observed rate. Network results reproduce the patient-level calculations for the same bins, subject to floating-point rounding. Direct averaging of clinic-level rates would give clinics equal weight regardless of cohort size.

## Verify the result

The tests cover equivalence to a direct pooled calculation with unequal clinic sizes, inclusion of a probability of exactly 1.0, rejection of invalid scores, and network count reconciliation.

On macOS or Linux, run `cmp docs/sample-evaluation.json build/evaluation.json`. On Windows PowerShell, run `Get-FileHash docs/sample-evaluation.json, build/evaluation.json` and compare the hashes. The sample report reproduced byte for byte in the development environment. Exact bytes can vary with numerical libraries across environments.

## Data handling

This code shares aggregate fields across a simulated boundary. It expects summaries created internally with the same bin edges and field layout. A real service would need a versioned schema, authenticated payloads, common eligibility and label definitions, and a disclosure policy for small counts and overlapping reports. Secure aggregation and differential privacy require separate mechanisms and evaluation.
