# Compliance Report: Candidate Discovery & Ranking System

This report outlines the verified compute footprint of the candidate ranking pipeline, run on the target reproduction environment.

## 1. Resource Consumption Summary

| Constraint | Limit | Measured | Status |
|---|---|---|---|
| **Wall-Clock Runtime (Scoring)** | ≤ 300.0 seconds | 91.37 seconds | **PASS** |
| **Peak RAM (RSS)** | ≤ 16.0 GB | 0.3249 GB | **PASS** |
| **Disk Footprint** | ≤ 5.0 GB | 0.3115 GB | **PASS** |

---

## 2. Submission Format Validation

* **Validator Status**: **PASS**
* **Validator Output**:
```
Submission is valid.
```

---

## 3. Constraint Compliance Matrix Check

| Constraint Checklist | Verification Method | Status |
|---|---|---|
| Runtime ≤ 5 minutes | Subprocess execution timer | **PASS** |
| Memory usage ≤ 16 GB | Background process RSS monitoring thread | **PASS** |
| Disk space ≤ 5 GB | Combined artifacts/ and outputs/ directory byte count | **PASS** |
| Offline execution compliance | verified with HF_HUB_OFFLINE=1 & TRANSFORMERS_OFFLINE=1 | **PASS** |
| Exactly 100 unique data rows | Checked via validate_submission.py | **PASS** |
| Ranks 1-100 unique & strictly ordered | Checked via validate_submission.py | **PASS** |
| Scores non-increasing by rank | Checked via validate_submission.py | **PASS** |
| Equal score sorting alphabetically | Checked via validate_submission.py | **PASS** |
| Honeypots rate ≤ 10% in top 100 | Verified zero honeypots present in output | **PASS** |
| Reasoning justifications populated | Checked via validate_submission.py | **PASS** |
