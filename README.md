# Intelligent Candidate Discovery & Ranking System (Redrob Challenge)

Welcome to the **Antigravity** candidate ranking system repository. This solution ranks **100,000 candidate profiles** against the **Senior AI Engineer — Founding Team** Job Description (JD) within strict hardware and runtime limits.

---

## 🚀 One-Command Reproduction

To run the candidate ranker on the full dataset and generate the validated output CSV:

```bash
# 1. Activate your virtual environment and install requirements
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt

# 2. Run the end-to-end ranking pipeline offline
python -m src.redrob_ranker.rank --candidates data/candidates.jsonl --out outputs/team_xxx.csv
```

This single command completes in **~87 seconds** on a standard 8-core CPU, consuming only **~0.32 GB RAM** and **~0.31 GB Disk**, with **zero network requests** (completely offline execution).

To validate the generated output:
```bash
python validate_submission.py outputs/team_xxx.csv
```

---

## 🎯 Architecture & Design Methodology

Our solution utilizes an **interpretable, four-layer, vectorized scoring pipeline** designed to satisfy strict compute bounds and filter adversarial profiles (such as keyword stuffers and honeypots):

```
                 ┌─────────────────────────────────────────────────────────┐
                 │  candidates.jsonl (100,000 records)                     │
                 └───────────────────────────┬─────────────────────────────┘
                                             │
                 ┌───────────────────────────▼─────────────────────────────┐
                 │ LAYER 1 — Hard Filters & Honeypots                      │
                 │  • Disqualifiers: pure research, title-chasers, CV      │
                 │    without NLP/IR exposure.                             │
                 │  • Internal consistency checks (overlap roles, impossible│
                 │    experience/expert years) flag honeypots.             │
                 │  → output: eligible (bool) + honeypot_flag (bool)       │
                 └───────────────────────────┬─────────────────────────────┘
                                             │ eligible only
                 ┌───────────────────────────▼─────────────────────────────┐
                 │ LAYER 2 — Hybrid Retrieval (Offline precompute)         │
                 │  • Lexical similarity: BM25 Okapi index                 │
                 │  • Semantic similarity: MiniLM-L6-v2 embeddings         │
                 │  → Normalized & fused: semantic_score                   │
                 └───────────────────────────┬─────────────────────────────┘
                                             │
                 ┌───────────────────────────▼─────────────────────────────┐
                 │ LAYER 3 — Structured Scoring                            │
                 │  • Pinned 47-title lookup taxonomy weighting            │
                 │  • Endorsement & duration-weighted skill trust scoring  │
                 │  • city match (Noida/Pune) & notice period penalties    │
                 │  → output: structured_score                             │
                 └───────────────────────────┬─────────────────────────────┘
                                             │
                 ┌───────────────────────────▼─────────────────────────────┐
                 │ LAYER 4 — Platform Availability Modifier                │
                 │  • Recency activity decay (exponential half-life)       │
                 │  • Recruiter response & offer acceptance rates          │
                 │  → output: availability_multiplier ∈ [0.3, 1.0]         │
                 └───────────────────────────┬─────────────────────────────┘
                                             │
                 ┌───────────────────────────▼─────────────────────────────┐
                 │ LAYER 5 & 6 — Composite & Reasoning                     │
                 │  • score = (0.6*semantic + 0.4*structured) * avail      │
                 │  • Consulting-firm service rules (Tier C/D exclusions)  │
                 │  • Strictly decreasing float adjustments (no ties)      │
                 │  • Slot-filled factual rank-aware reasoning templates   │
                 │  → output: outputs/team_xxx.csv                         │
                 └─────────────────────────────────────────────────────────┘
```

---

## 📊 Measured Compliance Footprint

Verified by Phase 7 automated compliance tests and monitored using cross-platform `psutil` background tracking:

| Constraint | Limit | Measured | Status |
|---|---|---|---|
| **Wall-Clock Runtime (Scoring)** | ≤ 300.0 seconds | **89.66 seconds** | **PASS** |
| **Peak RAM (RSS)** | ≤ 16.0 GB | **0.3194 GB** | **PASS** |
| **Disk Footprint** | ≤ 5.0 GB | **0.3115 GB** | **PASS** |
| **Offline Execution** | No Network Access | Verified Offline (`HF_HUB_OFFLINE=1`) | **PASS** |
| **Honeypot Gate** | ≤ 10% in Top 100 | **0% (0 honeypots present)** | **PASS** |
| **Validator Compliance** | Valid Schema | **PASS (Submission is valid)** | **PASS** |

---

## 📂 Repository Structure

* `config/weights.yaml` — Scoring weights, penalties, and threshold configurations.
* `data/` — Contains job description, schema, and sample datasets.
* `src/redrob_ranker/` — Central ranking engine package (filters, features, retrieval, scoring, reasoning).
* `scripts/` — EDA parsing, offline embedding precomputation, and compliance profiling tools.
* `artifacts/` — Local binary caches (precomputed sentence embeddings, BM25 indices).
* `sandbox/` — Streamlit interactive web application files.
* `tests/` — Full testing suite (25 tests covering schema, logic, speeds, and compliance).

---

## 🧪 Testing Suite

To run all 25 automated tests (unit logic, retrieval performance, scoring, schema streaming, compliance):
```bash
pytest -v
```

---

## 🎨 Interactive Sandbox Web App

We created a custom Streamlit web interface for visual auditing and dynamic parameter weighting. It accepts candidate file uploads (capped at 100 records for memory efficiency), calculates features and retrieval embeddings **on-the-fly**, generates candidate leaderboards, and provides dynamic detail card inspectors.

### 1. Run the Sandbox Locally
```bash
streamlit run sandbox/app.py
```
Open `http://localhost:8501` to access.

### 2. Deploy to Streamlit Community Cloud (Hosted App)
1. Sign in to [share.streamlit.io](https://share.streamlit.io) via GitHub.
2. Click **New App** and select this repository.
3. Set **Main File Path** to `sandbox/app.py`.
4. Deploy and check progress in the build log! Pinned CPU-only wheels inside `sandbox/requirements.txt` prevent deployment timeouts.
