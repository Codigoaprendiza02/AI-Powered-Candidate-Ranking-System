# PRD — Redrob Hackathon: Intelligent Candidate Discovery & Ranking System

**Document type:** Product Requirements Document for an AI coding agent ("vibe coding" agent) executing a phased build, with human checkpoints.
**Target output:** A spec-compliant `team_xxx.csv` submission + GitHub repo + hosted sandbox for the *Intelligent Candidate Discovery & Ranking Challenge* (Redrob AI), ranking 100,000 candidates against the **Senior AI Engineer — Founding Team** JD.
**Reference documents (must be re-read by the agent before the corresponding phase):** `job_description.md`, `submission_spec.md`, `redrob_signals_doc.md`, `candidate_schema.json`, `validate_submission.py`, `submission_metadata_template.yaml`.
**Dev environment:** Windows 11, PowerShell 7+, Python 3.11, CPU-only, 16 GB RAM machine (this is also the target reproduction environment, per spec Section 3).

---

## 0. How to use this PRD

This document is written for an AI coding agent to execute **phase by phase**. Each phase has a fixed gate:

> **A phase is not complete until (a) all automated/unit tests for that phase pass, AND (b) all human-based tests for that phase are explicitly signed off by the human operator.** The agent must not begin the next phase's implementation until both conditions are met. If a human test fails, the agent returns to the current phase, fixes the issue, and re-runs both automated and human tests.

Every phase lists: **Objective**, **Why this architecture choice**, **Agent tasks**, **Deliverables**, **Automated tests**, **Human-based tests (with what they verify)**, **PowerShell commands**, **Exit criteria**, and **Human action items**.

---

## 1. Problem Statement

Redrob AI (a Series A talent-intelligence platform) needs a ranking system for its **Senior AI Engineer — Founding Team** role. The hackathon provides:

- A pool of **100,000 candidate profiles** (`candidates.jsonl`, ~487 MB, 100,000 lines, schema in `candidate_schema.json`), each with a resume-shaped profile (`profile`, `career_history`, `education`, `skills`, `certifications`, `languages`) plus a `redrob_signals` object of 23 platform-behavior metrics.
- One fixed JD whose final section is itself part of the spec: **pure keyword/skill-list matching is an explicitly-built trap**. The "right" ranking requires reasoning about the gap between what a profile *says* (skills list) and what a career *shows* (career history, descriptions, behavior).
- A dataset containing **deliberate adversarial profiles**: keyword-stuffers, plain-language Tier-5 fits, "behavioral twins" (identical skills, different engagement), and ~80 **honeypots** with internally-impossible profiles.
- A **hard compute envelope** for the ranking step: ≤5 min wall-clock, ≤16 GB RAM, CPU-only, **no network**, ≤5 GB disk (`submission_spec.md` §3). This single constraint eliminates "call an LLM per candidate" as an option and is the dominant architectural driver.
- A **multi-stage evaluation pipeline** (format validation → composite scoring → code reproduction + honeypot check → manual reasoning review → defend-your-work interview), where a >10% honeypot rate in the top 100 is an automatic disqualification *regardless of score*.

**Deliverable:** a CSV (`team_xxx.csv`) with exactly 100 ranked rows (`candidate_id,rank,score,reasoning`), plus a GitHub repo (full pipeline, tests, README, `submission_metadata.yaml`), plus a hosted sandbox demo — all reproducible by a third party inside the stated compute envelope.

### 1.1 Confirmed dataset facts (from EDA on the real 100,000-row file — baseline for Phase 1)

| Fact | Value |
|---|---|
| Total candidates / unique `candidate_id`s | 100,000 / 100,000 (no duplicates) |
| Unique `current_title` values | **47** (small, enumerable taxonomy) |
| Avg skills per candidate | 9.60 |
| Candidates whose entire career is at a "consulting-only" firm (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, Tech Mahindra, Mindtree, HCL) | 8,991 (~9.0%) |
| Candidates with `current_title` in the ML/AI/Search/Ranking title set (20 titles, see Appendix A) | 1,179 (~1.2%) |
| Candidates where some `skills[].duration_months` exceeds `years_of_experience × 12` | 13,449 (~13.5%) — **too high to be the honeypot signal alone; likely synthetic noise** |
| Candidates with an `expert`-proficiency skill at `duration_months == 0` | 21 |
| Candidates where `sum(career_history[].duration_months) > years_of_experience × 12 + 12` | 24 |
| Time to stream-parse all 100K JSON lines (no retention) | ~4.0 s |
| Time + peak RSS to load all 100K as Python dicts in memory | ~18 s / ~1.6 GB |

These numbers anchor the Phase 1 exit criteria and the honeypot-threshold design in Phase 2.

---

## 2. Proposed Solution & Thought Process

### 2.1 Why not a single ML model or an LLM-per-candidate approach?

- **No GPU, no network** rules out hosted LLMs and most fine-tuned local LLMs at 100K-row scale within 5 minutes.
- A single learned ranker trained on this dataset risks overfitting to synthetic-generation artifacts (e.g., the duration-month noise above) rather than the *reasoning* the JD asks for, and is harder to "defend" in the Stage 5 interview ("why did the model rank X above Y?").
- The JD is explicit that the answer is **reasoning about the gap between stated skills and demonstrated career**, plus **behavioral availability as a multiplier**. This is naturally a **layered, interpretable scoring pipeline** — each layer is auditable, testable in isolation, and directly traceable to a sentence in the JD or spec. Interpretability is also what makes reasoning-column generation (Section 3, Phase 6) tractable without an LLM.

### 2.2 The four-layer architecture

```
                ┌─────────────────────────────────────────────────────────┐
                │  candidates.jsonl (100,000 records)                       │
                └───────────────────────────┬───────────────────────────────┘
                                              │
                ┌─────────────────────────────▼───────────────────────────────┐
                │ LAYER 1 — Hard Filters / Honeypot Detection (Phase 2)        │
                │  • JD disqualifiers (consulting-only, pure-research,         │
                │    CV/speech/robotics w/o NLP, title-chasers, etc.)          │
                │  • Internal-consistency / honeypot checks (self-contained,   │
                │    no external lookups — see Appendix C)                     │
                │  → boolean `eligible` + `honeypot_flag` per candidate        │
                └───────────────────────────┬───────────────────────────────┘
                                              │ eligible candidates only
                ┌─────────────────────────────▼───────────────────────────────┐
                │ LAYER 2 — Hybrid Retrieval (Phase 4, offline precompute)     │
                │  • BM25 lexical score (candidate text vs JD text)            │
                │  • Dense embedding cosine similarity (MiniLM, precomputed)   │
                │  • Combined via weighted hybrid / RRF → `semantic_score`     │
                └───────────────────────────┬───────────────────────────────┘
                                              │
                ┌─────────────────────────────▼───────────────────────────────┐
                │ LAYER 3 — Structured Feature Scoring (Phase 3)               │
                │  • Title-tier score (47-title taxonomy, Appendix A)          │
                │  • Skill-trust score (proficiency × endorsements ×           │
                │    duration × redrob skill_assessment_scores)                │
                │  • Location / relocation / notice-period match               │
                │  • Education tier (minor weight)                             │
                │  → `structured_score`                                        │
                └───────────────────────────┬───────────────────────────────┘
                                              │
                ┌─────────────────────────────▼───────────────────────────────┐
                │ LAYER 4 — Behavioral Availability Multiplier (Phase 3)       │
                │  • last_active_date recency decay                            │
                │  • open_to_work_flag, recruiter_response_rate,               │
                │    interview_completion_rate, offer_acceptance_rate (-1      │
                │    handled as neutral), search/saved counts                  │
                │  → `availability_multiplier` ∈ [0.3, 1.0]                    │
                └───────────────────────────┬───────────────────────────────┘
                                              │
                ┌─────────────────────────────▼───────────────────────────────┐
                │ COMPOSITE SCORING & RANKING (Phase 5)                         │
                │  score = (w2·semantic_score + w3·structured_score)           │
                │          × availability_multiplier   [if eligible, else 0]   │
                │  → sort desc, tie-break candidate_id asc, take top 100        │
                └───────────────────────────┬───────────────────────────────┘
                                              │
                ┌─────────────────────────────▼───────────────────────────────┐
                │ REASONING GENERATION (Phase 6)                                │
                │  Template + slot-filled from real extracted features —       │
                │  no LLM call needed, guarantees no hallucination              │
                └───────────────────────────┬───────────────────────────────┘
                                              │
                                       team_xxx.csv
```

### 2.3 Why this is time/memory efficient

- All of Layers 1, 3, 4 and the final composite are **vectorized pandas/numpy operations over the full 100K dataframe** — no per-row Python loops except for the final top-100 reasoning step (100 rows).
- Layer 2's expensive part (sentence-embedding inference) is **precomputed offline**, outside the 5-minute window (spec §10.3 explicitly allows this). The 5-minute ranking step only does `embeddings @ jd_embedding` (one matrix-vector product, <50 ms for 100K×384) and a BM25 score lookup against precomputed term statistics.
- Memory: full in-memory load of 100K records is ~1.6 GB; precomputed embeddings add ~150 MB (100,000 × 384 × 4 bytes); BM25 index over short documents is tens of MB. Total well under 16 GB with headroom for pandas overhead.
- Disk: candidates data + precomputed artifacts stay under 1 GB, well under the 5 GB cap.

### 2.4 Why BM25 + embeddings instead of a vector database (ChromaDB)

The ranking step is **one query (the fixed JD) against 100,000 precomputed vectors, computed once**. That is a single matrix-vector cosine-similarity product — exact, not approximate, and faster than building/loading an HNSW index. ChromaDB is not prohibited, but for this exact problem it adds a dependency and index-build time without functional benefit, and its default embedding function silently calls out to HuggingFace (a network-rule violation) unless precomputed embeddings are passed explicitly. **Decision: use `numpy` for dense similarity and `rank_bm25` for lexical scoring, combined as a hybrid score.** This also directly demonstrates the "hybrid vs dense retrieval, with opinions you can defend" competency the JD asks for — the architecture choice doubles as evidence of the skill being hired for.

### 2.5 Why a fixed title taxonomy instead of fuzzy/NLP title classification

EDA confirms only **47 unique `current_title` values** across the entire 100K pool (Appendix A). A hand-reviewed, human-approved lookup table from title → tier is deterministic, instant, fully auditable, and removes an entire class of NLP-classification bugs and runtime cost. Career-history titles use the same table. Where career history shows AI/ML/search work under a *different* current title (the JD's "Tier 5" case), Layer 2's semantic similarity over career-history *descriptions* is what catches it — this is precisely why Layer 2 exists.

---

## 3. Technology Stack & Justification

| Component | Choice | Justification |
|---|---|---|
| Language | Python 3.11 | Required ecosystem (pandas, sentence-transformers, rank_bm25); matches `python_version` field in metadata template |
| Data handling | `pandas`, `numpy`, `pyarrow` (parquet) | Vectorized ops on 100K rows; parquet for fast intermediate artifact I/O within disk budget |
| Schema validation | `jsonschema` | Validates against the provided `candidate_schema.json` directly |
| Lexical retrieval | `rank_bm25` | Pure Python, no network, trivial cost for 100K short docs |
| Dense retrieval | `sentence-transformers` (`all-MiniLM-L6-v2`, ~80 MB, CPU) | Small, CPU-friendly, widely validated; cached locally so ranking step needs no network |
| Config | `PyYAML` | Weight configs (`config/weights.yaml`) and `submission_metadata.yaml` |
| Testing | `pytest` | Unit + integration tests, phase gates |
| Memory/time profiling | `psutil`, `time` | `resource` module is POSIX-only — dev machine is Windows, so `psutil` is used for cross-platform peak-RSS measurement |
| Sandbox | Streamlit, deployed on **Streamlit Community Cloud** | In spec §10.5's accepted platform list; deploys directly from the same GitHub repo (no separate container registry/account), free tier, builds from `requirements.txt`/`runtime.txt` automatically |
| Version control | Git + GitHub | Spec §10.3; commit history must show real iteration (enforced procedurally, see Phase 9) |

---

## 4. Repository Structure

```
redrob-ranker/
├── README.md
├── requirements.txt
├── runtime.txt                     # pins Python version for Streamlit Cloud build
├── submission_metadata.yaml
├── .gitignore
├── .streamlit/
│   └── config.toml                 # e.g. maxUploadSize, theme — Streamlit Cloud app config
├── config/
│   └── weights.yaml
├── data/
│   ├── job_description.md
│   ├── candidate_schema.json
│   ├── redrob_signals_doc.md
│   └── candidates.jsonl            # gitignored — too large for git, documented download step
├── src/
│   └── redrob_ranker/
│       ├── __init__.py
│       ├── config.py
│       ├── schema_validation.py
│       ├── taxonomy.py             # Appendix A/B tables
│       ├── filters.py              # Layer 1
│       ├── features.py             # Layer 3 + Layer 4
│       ├── retrieval.py            # Layer 2 (loads precomputed artifacts)
│       ├── scoring.py              # Composite + ranking
│       ├── reasoning.py             # Layer 6 templates
│       └── rank.py                 # single entrypoint (CLI)
├── scripts/
│   ├── eda.py
│   ├── precompute_embeddings.py
│   └── profile_run.py              # timing + memory profiling wrapper
├── artifacts/
│   ├── candidate_corpus.parquet
│   ├── embeddings.npy
│   ├── jd_embedding.npy
│   └── bm25_index.pkl
├── tests/
│   ├── test_schema.py
│   ├── test_filters.py
│   ├── test_features.py
│   ├── test_retrieval.py
│   ├── test_scoring.py
│   ├── test_reasoning.py
│   ├── test_end_to_end.py
│   └── test_sandbox.py
├── sandbox/
│   ├── app.py                      # Streamlit Cloud entrypoint (Main file path: sandbox/app.py)
│   └── requirements.txt            # lightweight, CPU-only deps for the sandbox build
└── outputs/
    └── team_xxx.csv
```

---

## 5. Constraint Compliance Matrix

| Constraint (`submission_spec.md` §3, §6, §7) | How this PRD satisfies it | Verified in |
|---|---|---|
| Runtime ≤ 5 min (ranking step) | Layers 1/3/4/5 vectorized; Layer 2 uses precomputed artifacts only | Phase 7 |
| RAM ≤ 16 GB | Measured ~1.6 GB data + ~150 MB embeddings; profiled with `psutil` | Phase 7 |
| CPU only, no GPU | No GPU code paths anywhere; MiniLM runs on CPU | Phase 4, 7 |
| No network during ranking | All models/artifacts cached locally before `rank.py` runs; verified by running with network disabled | Phase 4, 7 |
| Disk ≤ 5 GB intermediate state | Artifacts ~200–300 MB total | Phase 4, 7 |
| Exactly 100 data rows, ranks 1–100 unique, candidate_ids unique & valid, score non-increasing, tie-break by candidate_id asc | `validate_submission.py` run in Phase 5 & 7; unit tests in `test_scoring.py` | Phase 5, 7 |
| Honeypot rate ≤ 10% in top 100 | Layer 1 hard-excludes flagged honeypots before ranking; Phase 5 human test explicitly counts flags in final top-100 (target: 0) | Phase 2, 5 |
| Reasoning column quality (6 checks, §3) | Template+slot-filled from real fields only; Phase 6 self-audits 10 random rows against all 6 checks | Phase 6 |
| GitHub repo, README, single reproduce command, `submission_metadata.yaml` | Phase 9 | Phase 9 |
| Sandbox / demo link (§10.5) | Streamlit app deployed on Streamlit Community Cloud, ≤100-candidate sample, ≤5 min | Phase 8 |
| 3-submission cap | Phase 9 procedural checklist — only run portal upload once Phase 0–8 fully signed off | Phase 9 |

---

## 6. Phased Delivery Plan

### Phase 0 — Environment & Repository Bootstrap

**Objective:** Reproducible Windows/PowerShell Python environment, repo skeleton, version control initialized.

**Why:** Everything downstream depends on a pinned, reproducible environment — this is also what Stage 3 reproduces.

**Agent tasks:**
1. Create repo folder structure exactly as in Section 4.
2. Create `requirements.txt` pinning: `pandas`, `numpy`, `pyarrow`, `jsonschema`, `rank_bm25`, `sentence-transformers`, `scikit-learn`, `pyyaml`, `pytest`, `psutil`, `streamlit`.
3. Create `.gitignore` excluding `data/candidates.jsonl`, `artifacts/*.npy`, `artifacts/*.pkl`, `.venv/`, `__pycache__/`, `outputs/*.csv`.
4. Copy provided reference docs (`job_description.md`, `candidate_schema.json`, `redrob_signals_doc.md`, `submission_spec.md`, `validate_submission.py`, `submission_metadata_template.yaml`) into `data/` and repo root as appropriate.
5. Initialize git, first commit.

**Deliverables:** Repo skeleton, `requirements.txt`, `.gitignore`, initial commit.

**Automated tests:**
- `python -c "import pandas, numpy, jsonschema, rank_bm25, sentence_transformers, sklearn, yaml, pytest, psutil"` exits 0.
- `pytest --collect-only` runs without error (0 tests collected is fine at this stage).

**Human-based tests (what they verify):**
| Test | Verifies |
|---|---|
| Activate venv, run `pip list`, eyeball versions | Environment matches `requirements.txt`; reproducible on a clean machine |
| Open repo in file explorer, confirm folder structure matches Section 4 | Repo scaffold correctness before any logic is built |
| `git log` shows exactly one commit | Clean starting point for the "real iteration" history check later |

**PowerShell commands:**
```powershell
# From the directory where you want the project
mkdir redrob-ranker
cd redrob-ranker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install pandas numpy pyarrow jsonschema rank_bm25 sentence-transformers scikit-learn pyyaml pytest psutil streamlit
pip freeze > requirements.txt
git init
git add .
git commit -m "Phase 0: project scaffold and environment setup"
```

**Exit criteria:** Environment installs cleanly from `requirements.txt` on a second machine; folder structure matches Section 4; one clean commit exists.

**Human action items:**
- Provide the actual hackathon bundle files (`candidates.jsonl`, `job_description.md`/`.docx`, `submission_spec`, `candidate_schema.json`, `redrob_signals_doc`, `validate_submission.py`, `submission_metadata_template.yaml`) into `data/`.
- Confirm machine specs (CPU cores, RAM) for `submission_metadata.yaml` later.

---

### Phase 1 — Data Ingestion, Schema Validation & EDA

**Objective:** Confirm the dataset matches the schema, and reproduce/extend the baseline EDA numbers in Section 1.1.

**Why:** Every downstream layer's thresholds (honeypot cutoffs, title taxonomy, behavioral-signal ranges) must be derived from real data, not assumptions. EDA also doubles as a data-quality gate before any modeling effort is spent.

**Agent tasks:**
1. `scripts/eda.py`: stream-parse `data/candidates.jsonl` line-by-line (no full in-memory retention for the streaming pass), validate each record against `candidate_schema.json` with `jsonschema`, and accumulate: title counts, company counts, skill counts, redrob_signals distributions (min/max/mean/percentiles for numeric fields), and the honeypot-heuristic counters from Section 1.1.
2. Write `reports/eda_report.md` summarizing findings, including the full 47-title frequency table and top-30 companies.
3. Write `tests/test_schema.py` validating `sample_candidates.json` (50 rows, already available) and a streaming validation pass over the full file, reporting % schema-valid.

**Deliverables:** `scripts/eda.py`, `reports/eda_report.md`, `tests/test_schema.py`.

**Automated tests:**
- `pytest tests/test_schema.py -v` → 100% of `sample_candidates.json` rows validate against `candidate_schema.json`.
- `scripts/eda.py` runs end-to-end on the full 100K file in under 60 seconds.
- Reproduced counters match Section 1.1 within rounding (100,000 unique ids; 47 unique titles; ~9.0% consulting-only; ~1.2% current-title-ML; 13,449 / 21 / 24 for the three honeypot heuristics — exact numbers, since this is a fixed dataset).

**Human-based tests:**
| Test | Verifies |
|---|---|
| Open `reports/eda_report.md`, compare the 47-title table and top-companies table against Appendix A/B | Taxonomy inputs are correct before Phase 2 hard-codes them |
| Spot-check 5 candidates flagged by each honeypot heuristic (21 "expert+0mo", 24 "career sum > yoe") by opening their raw JSON | Heuristics catch *genuinely* impossible profiles, not noise — calibrates Phase 2 thresholds |
| Confirm schema-validation failure rate is 0% (or review and approve any non-zero failures) | Dataset integrity — a non-zero failure rate would mean the whole pipeline needs defensive parsing added now, not discovered later |

**PowerShell commands:**
```powershell
.\.venv\Scripts\Activate.ps1
python scripts\eda.py --input data\candidates.jsonl --schema data\candidate_schema.json --output reports\eda_report.md
pytest tests\test_schema.py -v
git add .
git commit -m "Phase 1: EDA and schema validation"
```

**Exit criteria:** EDA report generated and matches Section 1.1 baseline; schema validation at 100% (or documented exceptions approved by human); human has reviewed and approved the 47-title list that Phase 2 will hard-code.

**Human action items:**
- Review `reports/eda_report.md` and explicitly approve (in writing / commit message) the title list and consulting-firm list before Phase 2 begins, since both are hand-curated from this report.

---

### Phase 2 — Taxonomy, Hard Filters & Honeypot Detection (Layer 1)

**Objective:** Encode the JD's explicit disqualifiers and the dataset's internal-consistency honeypot signals as deterministic, vectorized rules producing `eligible` and `honeypot_flag` columns.

**Why:** This is the highest-leverage layer for the Stage-3 honeypot gate (>10% in top-100 = disqualification regardless of score) and for the JD's "things we explicitly do NOT want" list. Doing this first, before any scoring, means later layers only ever operate on a pre-cleaned candidate pool.

**Agent tasks:**
1. `src/redrob_ranker/taxonomy.py`: hard-code the 47-title → tier table (Appendix A, human-approved in Phase 1) and the consulting-firm set (Appendix B).
2. `src/redrob_ranker/filters.py`, implementing (all vectorized over the full dataframe):
   - **Consulting-only career** (Tier D unless career-history descriptions show AI/ML/search/ranking work — pass through to Layer 2 for that nuance rather than hard-excluding; see Appendix B for the exact rule).
   - **Pure-research-without-production**: `current_industry`/`career_history[].industry` all "Research"/"Academia" AND no `is_current`/past role with `company_size` indicating a product company.
   - **CV/Speech/Robotics without NLP/IR exposure**: `current_title`/career titles in {Computer Vision Engineer, ...} AND no skill in the NLP/IR/retrieval skill set (Appendix A skill list).
   - **Title-chaser**: ≥3 employers in ≤1.5 years average tenure with escalating seniority words in title.
   - **Honeypot consistency checks** (Appendix C): any `skills[].duration_months > years_of_experience*12 + 6`, OR `proficiency=="expert" and duration_months==0`, OR `sum(career_history duration_months) > years_of_experience*12 + 12`, OR overlapping `is_current=true` entries. **Combine with AND-style severity scoring, not a single OR flag** — Phase 1 showed the naive single-field check (13.5%) is too broad; require ≥2 independent anomalies, or 1 severe anomaly (e.g., `expert`+0 months), to set `honeypot_flag=True`.
3. Output `flags.parquet`: `candidate_id, eligible (bool), honeypot_flag (bool), exclusion_reason (str|null)`.

**Deliverables:** `taxonomy.py`, `filters.py`, `artifacts/flags.parquet`, `tests/test_filters.py`.

**Automated tests:**
- Unit tests with hand-built fixture candidates (one per disqualifier type, plus the real `CAND_0000031`-style fixture with `Pinecone duration_months=88` against `years_of_experience=6.0`) — each must be flagged correctly.
- A "golden" Tier-S fixture (e.g., a Recommendation Systems Engineer at Swiggy with consistent durations, verified signals) must NOT be flagged.
- Regression assertion: `honeypot_flag` rate over the full 100K is between 0.03% and 0.3% (i.e., 30–300 candidates) — consistent with "~80 honeypots" rather than the 13.5% noise rate.
- Runtime on full 100K < 30 seconds.

**Human-based tests:**
| Test | Verifies |
|---|---|
| Pull 20 candidates with `honeypot_flag=True`, read their raw JSON | No false positives — each genuinely has an impossible/contradictory profile, not just noisy data |
| Pull 15 candidates with `eligible=False` and `exclusion_reason` set to each disqualifier type (3 each across 5 types), read raw JSON | Each exclusion matches the JD's stated "things we explicitly do NOT want" — no over-exclusion of legitimate Tier-5 candidates |
| Pull 10 random candidates where `current_title` is a generic non-tech title (e.g., HR Manager) but career_history descriptions mention ML/search work (search manually) — confirm these are **not** excluded by Layer 1 | Layer 1 doesn't accidentally exclude Tier-5 candidates that Layer 2 is meant to catch |

**PowerShell commands:**
```powershell
.\.venv\Scripts\Activate.ps1
pytest tests\test_filters.py -v
python -m src.redrob_ranker.filters --input data\candidates.jsonl --taxonomy src\redrob_ranker\taxonomy.py --output artifacts\flags.parquet
git add .
git commit -m "Phase 2: Layer 1 hard filters and honeypot detection"
```

**Exit criteria:** All unit tests pass; honeypot flag rate in the 0.03–0.3% band; human has reviewed and approved both the flagged-honeypot sample and the excluded-candidate sample; Tier-5-style candidates confirmed not excluded.

**Human action items:**
- Read the 20+15+10 sampled candidates above (raw JSON, ~10 minutes) and sign off in a short note committed to `reports/phase2_human_review.md`.

---

### Phase 3 — Feature Engineering (Layer 3 structured + Layer 4 behavioral)

**Objective:** Compute, for every eligible candidate, a `structured_score` (title-tier, skill-trust, location/notice/relocation, education) and an `availability_multiplier` (behavioral signals).

**Why:** This is where the JD's "skills you absolutely need" weighting and "down-weight unavailable candidates" instruction become numeric, auditable formulas — directly defensible at Stage 5.

**Agent tasks:**
1. `src/redrob_ranker/features.py`, vectorized over the eligible dataframe:
   - **Title-tier score**: lookup from Appendix A tier table (current title weighted highest; best career-history title contributes a smaller secondary term).
   - **Skill-trust score**: for each of the JD's "absolutely need" skill families (embeddings/retrieval, vector DB/hybrid search, Python, eval frameworks — map to skill-name groups, see Appendix D), compute `proficiency_weight × (1 + log1p(endorsements)) × min(duration_months/24, 1) × (skill_assessment_scores.get(skill, 50)/100)`; sum/normalize across matched skill families.
   - **Location/relocation/notice score**: bonus for Pune/Noida/Tier-1 India cities or `willing_to_relocate=true`; penalty scaling with `notice_period_days` above 30 (per JD's stated preference, not a hard cut).
   - **Education tier**: small additive term from `education[].tier` (tier_1 > tier_2 > ... > unknown), capped low weight per JD ("skills are teachable").
   - **Availability multiplier**: combine `open_to_work_flag`, recency-decayed `last_active_date` (e.g., exponential decay with ~90-day half-life), `recruiter_response_rate`, `interview_completion_rate`, `offer_acceptance_rate` (treat `-1` as neutral 0.5, not 0), `search_appearance_30d`/`saved_by_recruiters_30d` (log-scaled), `verified_email`/`verified_phone`/`linkedin_connected` (small trust bonus). Clip final multiplier to `[0.3, 1.0]` so it down-weights without zeroing out a strong otherwise-fit candidate.
2. `config/weights.yaml`: all weights as named, commented constants — no magic numbers in code.
3. Output `features.parquet`: `candidate_id, title_tier_score, skill_trust_score, location_score, education_score, structured_score, availability_multiplier`.

**Deliverables:** `features.py`, `config/weights.yaml`, `artifacts/features.parquet`, `tests/test_features.py`.

**Automated tests:**
- Unit tests for each sub-score function against 5 hand-computed fixtures (including `CAND_0000001` — the Backend Engineer with inflated "advanced" AI skills but low `skill_assessment_scores` — must score *lower* on `skill_trust_score` than its raw skill-list would suggest).
- No NaN/Inf in any output column across the full eligible pool.
- `availability_multiplier` always within `[0.3, 1.0]`.
- Runtime on full 100K < 45 seconds; peak memory (`psutil`) < 4 GB for this step.

**Human-based tests:**
| Test | Verifies |
|---|---|
| Pick 10 candidates spanning the score distribution, manually recompute `structured_score` and `availability_multiplier` from raw JSON using the documented formulas | Formula implementation matches the documented spec exactly |
| Compare `CAND_0000001` and `CAND_0000031` (from earlier analysis): confirm `CAND_0000001`'s `skill_trust_score` is meaningfully discounted relative to its raw skill-list size, and `CAND_0000031` is flagged by Phase 2 (honeypot) so it doesn't reach this layer with an inflated score | The two key trap patterns identified during EDA are handled correctly end-to-end |
| Review `config/weights.yaml` weight values and rationale comments | Weights reflect the JD's stated priorities ("skills are teachable", "production > research", location preferences are soft) — human owns this judgment call, not the agent |

**PowerShell commands:**
```powershell
.\.venv\Scripts\Activate.ps1
pytest tests\test_features.py -v
python -m src.redrob_ranker.features --input artifacts\flags.parquet --candidates data\candidates.jsonl --config config\weights.yaml --output artifacts\features.parquet
git add .
git commit -m "Phase 3: Layer 3 structured features and Layer 4 availability multiplier"
```

**Exit criteria:** All unit tests pass; manual recomputation matches for 10/10 sampled candidates; human has reviewed and signed off on `config/weights.yaml`.

**Human action items:**
- Manually recompute 10 candidates' scores by hand (or spreadsheet) and confirm match — this is the single most important human checkpoint for "can I defend these numbers in the Stage 5 interview".
- Approve/adjust weight values in `config/weights.yaml`.

---

### Phase 4 — Hybrid Retrieval: BM25 + Dense Embeddings (Layer 2, offline precompute)

**Objective:** Build a one-time offline precomputation producing per-candidate BM25 and dense-embedding similarity to the fixed JD, cached to disk so the 5-minute ranking step does zero model inference.

**Why:** This is the layer that catches Tier-5 candidates whose *titles* don't say "AI" but whose *career narrative* does — and it's the layer most constrained by the no-network/no-GPU/5-minute rules, hence "precompute once, load fast at rank time."

**Agent tasks:**
1. `scripts/precompute_embeddings.py` (run once, network allowed for first model download only):
   - Build `candidate_corpus`: for each candidate, concatenate `profile.headline + profile.summary + " ".join(career_history[].title + description)`.
   - Download & cache `all-MiniLM-L6-v2` locally (first run only; set `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE` for all subsequent runs).
   - Encode all 100K candidate texts → `artifacts/embeddings.npy` (shape `(100000, 384)`, float32).
   - Encode the JD text → `artifacts/jd_embedding.npy`.
   - Build a `rank_bm25.BM25Okapi` index over tokenized `candidate_corpus` → `artifacts/bm25_index.pkl`.
2. `src/redrob_ranker/retrieval.py`: at rank time, loads the three artifacts, computes:
   - `dense_score = embeddings @ jd_embedding` (cosine, vectors pre-normalized) — one matrix-vector product.
   - `bm25_score = bm25_index.get_scores(jd_tokens)` — one call.
   - `semantic_score = α·minmax(bm25_score) + (1-α)·minmax(dense_score)` (α configurable in `config/weights.yaml`, default 0.4).

**Deliverables:** `precompute_embeddings.py`, `retrieval.py`, three artifact files, `tests/test_retrieval.py`.

**Automated tests:**
- `embeddings.npy.shape == (100000, 384)`; `jd_embedding.npy.shape == (384,)`.
- `retrieval.py` runs with `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1` and no network adapter (simulate via PowerShell firewall rule, see human test) and still produces scores — i.e., it only ever loads cached artifacts at rank time, never calls the encoder.
- Sanity ranking test: a synthetic "Recommendation Systems Engineer at a product company with FAISS/embeddings/ranking experience" fixture scores in the top 1% of `semantic_score`; a synthetic "HR Manager" fixture scores in the bottom 50%.
- `retrieval.py` step on full 100K completes in < 5 seconds.

**Human-based tests:**
| Test | Verifies |
|---|---|
| Disable network (see PowerShell command below), run `python -m src.redrob_ranker.retrieval ...` | No-network constraint genuinely holds for the ranking step, not just "should work" |
| Sort by `semantic_score` alone (no other layers), read top-20 candidates' headlines/summaries | Hybrid retrieval surfaces plausible AI/ML/search/ranking people without needing skill-list keyword matches — validates the Layer 2 thesis |
| Spot-check 5 candidates with generic current titles (e.g., "Senior Data Engineer") but high `semantic_score` — read their career-history descriptions | Confirms Layer 2 is catching the "Tier 5" pattern the JD describes |

**PowerShell commands:**
```powershell
.\.venv\Scripts\Activate.ps1
# One-time precompute (network allowed)
python scripts\precompute_embeddings.py --input data\candidates.jsonl --jd data\job_description.md --output-dir artifacts\

# Verify offline operation: temporarily block outbound network for this process
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
pytest tests\test_retrieval.py -v
python -m src.redrob_ranker.retrieval --features artifacts\features.parquet --artifacts-dir artifacts\ --output artifacts\retrieval.parquet
Remove-Item Env:\HF_HUB_OFFLINE, Env:\TRANSFORMERS_OFFLINE
git add .
git commit -m "Phase 4: hybrid BM25 + dense embedding retrieval (offline precomputed)"
```

**Exit criteria:** All artifacts generated and committed (via Git LFS or a documented regeneration script if too large for plain git — embeddings.npy at ~150 MB needs LFS); offline run succeeds; human-reviewed top-20-by-semantic-score sanity check passes.

**Human action items:**
- Decide and configure Git LFS (or document the regeneration command in README) for `embeddings.npy` given GitHub's file-size limits.
- Read the top-20 semantic-only list (~5 minutes) and confirm plausibility.

---

### Phase 5 — Composite Scoring & Ranking Engine

**Objective:** Combine Layers 1–4 into the final composite score, produce the validated top-100 CSV.

**Why:** This is the single point where every prior decision becomes the actual submission artifact — and the highest-stakes human review point, since it's what the hidden ground truth will score.

**Agent tasks:**
1. `src/redrob_ranker/scoring.py`:
   - Join `flags.parquet` + `features.parquet` + `retrieval.parquet` on `candidate_id`.
   - Filter to `eligible == True`.
   - `composite = (w2·semantic_score_norm + w3·structured_score_norm) × availability_multiplier`.
   - Sort descending by `composite`; tie-break by `candidate_id` ascending (per spec §3).
   - Take top 100; assign `rank = 1..100`; `score = composite` (rounded to 3 decimals, still strictly non-increasing after rounding — add epsilon-based tie adjustment if rounding creates ties out of order... actually ties are allowed, just keep candidate_id-ascending order for equal scores).
2. `src/redrob_ranker/rank.py`: the single CLI entrypoint — `python -m src.redrob_ranker.rank --candidates data\candidates.jsonl --out outputs\team_xxx.csv` — runs Layers 1–5 end to end (using precomputed Layer 2 artifacts).

**Deliverables:** `scoring.py`, `rank.py`, `outputs/team_xxx.csv` (draft), `tests/test_scoring.py`.

**Automated tests:**
- `tests/test_end_to_end.py`: running `rank.py` on `sample_candidates.json` (50 rows) produces a valid (smaller) ranking with no errors.
- `score` column strictly non-increasing by `rank`; ties broken by `candidate_id` ascending — unit test with constructed equal-score fixtures.
- Zero `honeypot_flag=True` candidates appear in the output (Layer 1 already excluded them, but assert it explicitly here too as a regression guard).
- `python validate_submission.py outputs\team_xxx.csv` (adapted for 100K-derived output) exits 0 with "Submission is valid."

**Human-based tests:**
| Test | Verifies |
|---|---|
| Read all 100 rows' `candidate_id` + current title + headline (join back to raw JSON) | Overall plausibility — does this list look like "10 great matches", per the JD's stated expectation, rather than 100 generic software engineers? |
| For the top 10, read full profiles and compare against the JD's "ideal candidate" bullet list (6–8 yrs, applied ML at product company, shipped ranking/search/rec system, Pune/Noida or relocatable, active on platform) | Top-of-funnel quality — these are the rows Stage 4 reviewers will scrutinize most |
| For ranks 90–100, read profiles and confirm they're plausible "filler" (adjacent skills, some real but lesser fit) rather than nonsensical | Tail quality — avoids "all scores identical" / "no differentiation" rejection pattern (§6) |
| Count `honeypot_flag` among the 100 (should be 0); separately, manually eyeball 5 of the 100 for the honeypot patterns from Appendix C as an independent check | Stage-3 honeypot gate (>10% disqualifies regardless of score) — this is the single highest-stakes check in the whole PRD |

**PowerShell commands:**
```powershell
.\.venv\Scripts\Activate.ps1
pytest tests\test_scoring.py tests\test_end_to_end.py -v
python -m src.redrob_ranker.rank --candidates data\candidates.jsonl --out outputs\team_xxx.csv
python validate_submission.py outputs\team_xxx.csv
git add .
git commit -m "Phase 5: composite scoring, ranking engine, draft top-100"
```

**Exit criteria:** `validate_submission.py` passes; honeypot count = 0 in output; human has read all 100 rows (top-10 in depth, 90–100 in depth, middle skimmed) and signed off in `reports/phase5_human_review.md`.

**Human action items:**
- Full read-through of the 100-row draft submission (~30–45 minutes) — this is the largest single human time investment in the plan and directly determines submission quality.
- If quality issues are found, return to Phase 3 weight tuning (not Phase 5 code) — document the weight change rationale.

---

### Phase 6 — Reasoning Generation

**Objective:** Populate the `reasoning` column for all 100 rows with non-templated, fact-grounded, rank-appropriate justifications.

**Why:** Directly maps to spec §3's 6-point Stage-4 reasoning rubric — the second-highest-stakes check after honeypot rate.

**Agent tasks:**
1. `src/redrob_ranker/reasoning.py`: a small template library (8–12 templates) with slots filled from `features.parquet` + raw profile fields: `years_of_experience`, `current_title`, `current_company`, top 1–2 matched skill families with their `skill_assessment_scores`, the dominant `availability_multiplier` driver (positive: high `recruiter_response_rate`/recently active; negative: stale `last_active_date`/low response rate), and — for ranks below ~30 — an explicit "concern" clause (notice period, location mismatch, adjacent-but-not-exact title, etc.), satisfying the "honest concerns" rubric item.
2. Template selection is **deterministic but feature-dependent** (e.g., hash of `candidate_id` mod template-bucket, further filtered by which features are present) so that the 10-sample audit shows genuine variation, not random luck.
3. Integrate into `rank.py` so `outputs/team_xxx.csv` has reasoning populated end-to-end.

**Deliverables:** `reasoning.py`, updated `rank.py`/output, `tests/test_reasoning.py`.

**Automated tests:**
- No two of the 100 reasoning strings are identical.
- Every named skill/employer/number in each reasoning string is checked (string containment / field lookup) against that candidate's actual profile — zero hallucinated references.
- No empty reasoning strings; length between ~60 and ~280 characters.
- For ranks 1–10, no reasoning contains a "concern" clause keyword (e.g., "however", "gap", "concern") unless the candidate genuinely has one flagged in `features.parquet` (rank-tone consistency, automatable subset of rubric item 6).

**Human-based tests:**
| Test | Verifies |
|---|---|
| Sample 10 random rows (mirroring Stage 4's exact process) and score each against all 6 official rubric items (specific facts / JD connection / honest concerns / no hallucination / variation / rank consistency) | This *is* the Stage-4 check, run by the team before submission — any failure here is a failure at the real Stage 4 |
| Read the rank-1 and rank-100 reasoning side by side | Confirms tone clearly differs (glowing vs. measured/filler) — catches the "templated reasoning generated independently of rank" failure mode explicitly called out in the spec |

**PowerShell commands:**
```powershell
.\.venv\Scripts\Activate.ps1
pytest tests\test_reasoning.py -v
python -m src.redrob_ranker.rank --candidates data\candidates.jsonl --out outputs\team_xxx.csv
git add .
git commit -m "Phase 6: reasoning generation for top-100"
```

**Exit criteria:** Automated hallucination/duplication checks pass; human 10-sample audit passes all 6 rubric items (documented in `reports/phase6_human_review.md`).

**Human action items:**
- Perform the 10-sample Stage-4-style audit (~15 minutes) and record results.
- If templates are too formulaic, add/edit 2–3 more templates and re-run — this is expected iteration (and helps the "real iteration in git history" check at Phase 9).

---

### Phase 7 — Validation, Compute Profiling & Constraint Compliance

**Objective:** Prove, with measurements, that `rank.py` satisfies every limit in `submission_spec.md` §3 on the actual dev machine (which mirrors the Stage-3 reproduction environment).

**Why:** "Cannot reproduce within compute limits" is a hard Stage-3 disqualifier *independent of score*. This phase produces the evidence that goes into `submission_metadata.yaml`'s compute section.

**Agent tasks:**
1. `scripts/profile_run.py`: wraps `rank.py` execution, recording wall-clock time and peak RSS via `psutil.Process().memory_info().rss` sampled on a background thread; writes `reports/compliance_report.md` with: total runtime, peak memory, total disk used by `artifacts/` + `outputs/`, and an explicit checklist against each row of the Constraint Compliance Matrix (Section 5).
2. Re-run the full pipeline from a **completely clean checkout** (fresh venv) to catch any hidden dependency on dev-machine state (e.g., HF cache paths) — this simulates Stage 3.

**Deliverables:** `scripts/profile_run.py`, `reports/compliance_report.md`.

**Automated tests:**
- `pytest`: assert `runtime_seconds < 300` and `peak_rss_gb < 16` and `artifacts_disk_gb + outputs_disk_gb < 5` from the profiling output.
- `validate_submission.py outputs\team_xxx.csv` exits 0 (re-confirmed after Phase 6 changes).
- Manually check the output CSV against all 6 items in spec §6 "Common rejections" (automatable as one combined test).

**Human-based tests:**
| Test | Verifies |
|---|---|
| On a fresh PowerShell session, with network disabled via firewall rule, run the single reproduce command from a clean checkout (delete `.venv`, recreate) and time it with a stopwatch independent of the script's own measurement | True end-to-end reproducibility — the exact scenario Stage 3 will execute |
| Open `outputs/team_xxx.csv` in a spreadsheet, eyeball column types, header row, 100 data rows, score column monotonicity | Final sanity pass on the literal file that gets uploaded |
| Review `reports/compliance_report.md` against Section 5's matrix, row by row | Every constraint has documented evidence — this becomes the basis for the `compute:` section of `submission_metadata.yaml` |

**PowerShell commands:**
```powershell
# Clean-room reproduction
deactivate  # if a venv is active
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Disable network for this PowerShell session (example using a temporary firewall rule)
New-NetFirewallRule -DisplayName "BlockOutboundTemp" -Direction Outbound -Action Block -Program "$($PWD)\.venv\Scripts\python.exe"

Measure-Command { python -m src.redrob_ranker.rank --candidates data\candidates.jsonl --out outputs\team_xxx.csv }
python scripts\profile_run.py --candidates data\candidates.jsonl --out outputs\team_xxx.csv --report reports\compliance_report.md
python validate_submission.py outputs\team_xxx.csv

# Re-enable network
Remove-NetFirewallRule -DisplayName "BlockOutboundTemp"

pytest -v
git add .
git commit -m "Phase 7: compute profiling and constraint compliance report"
```

**Exit criteria:** `compliance_report.md` shows all green against Section 5; clean-room run with network blocked succeeds within 5 minutes; validator passes.

**Human action items:**
- Run the clean-room reproduction personally (not just trust the agent's run) — this is the step most likely to surface "works on my machine" issues.
- Record actual measured runtime/memory/disk numbers — these go verbatim into `submission_metadata.yaml`'s `compute:` block in Phase 9.

---

### Phase 8 — Sandbox / Deployment (Streamlit Community Cloud)

**Objective:** A publicly reachable **Streamlit Community Cloud** app satisfying spec §10.5 — accepts a small (≤100) candidate sample, runs the ranking pipeline end-to-end, returns a ranked CSV, within the compute budget.

**Why Streamlit Community Cloud specifically:** it's in the spec's accepted platform list, deploys directly from the *same* GitHub repo used for the submission (one repo, one story for reviewers), requires no separate container registry/account, and builds automatically from `requirements.txt` + `runtime.txt` — no Dockerfile to write or maintain. The trade-off is its resource ceiling (Community Cloud apps run with **~1 GB RAM, shared CPU**, and sleep after a period of inactivity) — the design below is shaped around that ceiling.

**Design implications of the 1 GB ceiling (time/memory-efficient design principles):**
- The sandbox **must not** load the full-scale `artifacts/embeddings.npy` (100,000 × 384 floats, ~150 MB) or the full `candidates.jsonl` (487 MB) — it only ever operates on the ≤100-row uploaded/sample file, computing BM25 + embeddings **on the fly** for just those rows.
- The sentence-transformer model is loaded **once per app session** via `st.cache_resource` (not once per rerun), and a CPU-only `torch` wheel is pinned in `sandbox/requirements.txt` (via `--extra-index-url https://download.pytorch.org/whl/cpu`) to keep the build small and avoid pulling CUDA dependencies.
- `.streamlit/config.toml` sets `server.maxUploadSize` to a small value (e.g., 5 MB) — defensive engineering so a reviewer accidentally uploading the full 487 MB dataset fails fast with a clear message instead of exhausting the app's memory.
- The sandbox imports and calls the **same** `src/redrob_ranker` package used by `rank.py` (Layers 1, 3, 4, 5, 6 are cheap vectorized/pandas operations even for 100 rows; only Layer 2's embedding step differs — on-the-fly inference instead of precomputed-artifact lookup). No logic is duplicated between the production pipeline and the sandbox.

**Agent tasks:**
1. `sandbox/app.py` (Streamlit):
   - File-uploader for a `.jsonl` of ≤100 candidates (defaults to the bundled `data/sample_candidates.json` if nothing is uploaded).
   - `@st.cache_resource` loader for the MiniLM model and BM25 tokenizer.
   - Calls `src/redrob_ranker` Layers 1→6 on the small input (Layer 2 computes embeddings/BM25 on the fly for these rows only, against the precomputed `jd_embedding.npy` / JD BM25 tokens, which are tiny and fine to ship in the repo).
   - Displays the ranked table in the app and offers a CSV download button.
   - Shows a small "compute footprint" panel (rows processed, elapsed seconds) so reviewers can see the ≤5 min budget is met live.
2. `sandbox/requirements.txt`: minimal, CPU-only — `streamlit`, `pandas`, `numpy`, `rank_bm25`, `scikit-learn`, `pyyaml`, and `sentence-transformers` + `torch` pinned via the CPU wheel index.
3. `runtime.txt` at repo root: pin Python version (e.g., `3.11`) for Streamlit Cloud's build.
4. `.streamlit/config.toml`: `maxUploadSize`, basic theme (optional).

**Deliverables:** `sandbox/app.py`, `sandbox/requirements.txt`, `runtime.txt`, `.streamlit/config.toml`, live Streamlit Community Cloud URL (`https://<app-name>.streamlit.app`).

**Automated tests:**
- `streamlit run sandbox\app.py` starts locally without error and serves on `http://localhost:8501`.
- In a **fresh venv** (not the dev `.venv`), `pip install -r sandbox\requirements.txt` completes successfully and under a reasonable size budget — this is the closest local proxy to Streamlit Cloud's build step.
- A scripted run of `data/sample_candidates.json` (50 rows, within the ≤100 limit) through `sandbox/app.py`'s pipeline functions (called directly, headless) completes in well under 60 seconds, confirming the on-the-fly embedding path is cheap at this scale.
- `tests/test_sandbox.py`: asserts the sandbox's Layer-1–6 invocation produces a CSV with the same schema as `validate_submission.py` expects (minus the fixed 100-row count, since input may be smaller).

**Human-based tests:**
| Test | Verifies |
|---|---|
| Sign in to **share.streamlit.io** with GitHub, deploy a new app pointing at this repo with **Main file path = `sandbox/app.py`**, and watch the build log | The build succeeds on Streamlit Cloud's actual environment (different from local) — catches missing/incompatible dependencies in `sandbox/requirements.txt` |
| From a different network/device (e.g., phone hotspot), open `https://<app-name>.streamlit.app`, upload `sample_candidates.json` (or use the bundled default), run, and download the resulting CSV | Public reachability and end-to-end function exactly as organizers will test, per §10.5 |
| Time the run in the deployed app with a stopwatch, including any "app waking up" cold-start delay | Confirms the ≤5 min budget holds even with Streamlit Cloud's cold-start, satisfying §10.5 item 3 |
| Open "Manage app" → logs/resource usage on Streamlit Cloud after a run | Confirms memory stays within the ~1 GB Community Cloud ceiling — if it doesn't, return to the on-the-fly design above before proceeding |
| Try uploading a deliberately oversized file (e.g., a >5 MB JSONL) | Confirms `maxUploadSize` rejects it gracefully instead of crashing the app — production-readiness check |

**PowerShell commands:**
```powershell
.\.venv\Scripts\Activate.ps1

# Local smoke test
streamlit run sandbox\app.py
# Open http://localhost:8501 in a browser to verify before deploying

# Build-isolation check: mirrors Streamlit Cloud's own build step
python -m venv .venv-sandboxcheck
.\.venv-sandboxcheck\Scripts\Activate.ps1
pip install -r sandbox\requirements.txt
streamlit run sandbox\app.py
deactivate
Remove-Item -Recurse -Force .venv-sandboxcheck
.\.venv\Scripts\Activate.ps1

# Ensure Streamlit Cloud build files are present and committed
"3.11" | Out-File -Encoding ascii runtime.txt -NoNewline
git add sandbox\app.py sandbox\requirements.txt runtime.txt .streamlit\config.toml
git commit -m "Phase 8: Streamlit Community Cloud sandbox app"
git push origin main

# Deployment itself is a one-time manual step at https://share.streamlit.io:
#   1. Sign in with GitHub
#   2. "New app" -> select this repo + branch
#   3. Main file path: sandbox/app.py
#   4. Deploy, then watch the build log
```

**Exit criteria:** App live on Streamlit Community Cloud and reachable from an external network; end-to-end run on `sample_candidates.json` succeeds, stays within the ~1 GB memory ceiling, and completes well within 5 minutes; oversized-upload handling verified.

**Human action items:**
- Sign in to Streamlit Community Cloud (share.streamlit.io) with the GitHub account that owns/has access to the submission repo.
- Deploy the app via the web UI (`sandbox/app.py` as the main file) — this step cannot be scripted.
- If the repo is private, grant Streamlit Cloud's GitHub App the necessary repo access.
- Perform the external-network test personally, record the live `https://<app-name>.streamlit.app` URL for `submission_metadata.yaml`'s `sandbox_link`.
- Note in `README.md` that the app may need ~30–60s to "wake" if it has been asleep, so reviewers aren't surprised by a cold-start delay — and consider visiting the URL shortly before the evaluation window to pre-warm it.

---

### Phase 9 — Submission Packaging & Final Repository

**Objective:** `submission_metadata.yaml` filled, `README.md` with the single reproduce command, final `team_xxx.csv`, git history reviewed for "real iteration", portal upload.

**Why:** This is the last gate before consuming one of the 3 allowed submissions — and the repo/README/metadata are what Stage 3 and Stage 4 reviewers see first.

**Agent tasks:**
1. Fill `submission_metadata.yaml` from `submission_metadata_template.yaml`: team identity, `github_repo`, `sandbox_link` (from Phase 8), `reproduce_command` (the exact Phase 5 CLI), `compute:` block (from Phase 7's measured numbers), `ai_tools_used` + `ai_usage_summary` (honest — list every AI-assisted phase), `methodology_summary` (≤200 words, summarizing the four-layer architecture and the two concrete trap examples found in EDA), and `declarations:` (all true only if genuinely true — e.g., `honeypot_check_done: true` given Phase 2/5's explicit checks).
2. `README.md`: setup (Phase 0 commands), the single reproduce command, repo structure summary, link to `reports/` for EDA/compliance/human-review docs.
3. Review `git log --oneline`: confirm it shows the Phase 0–8 commit sequence (real iteration) — do **not** squash into one commit.

**Deliverables:** `submission_metadata.yaml`, `README.md`, final `outputs/team_xxx.csv`, clean `git log`.

**Automated tests:**
- `submission_metadata.yaml` parses with `PyYAML` and contains every field from the template (no leftover placeholder values like `"YOUR_USERNAME"`).
- `validate_submission.py outputs\team_xxx.csv` passes (final re-check).
- README's documented reproduce command, run verbatim, produces `outputs/team_xxx.csv` byte-for-byte identical to the committed one (determinism check — set random seeds anywhere randomness is used, e.g., template selection in Phase 6).

**Human-based tests:**
| Test | Verifies |
|---|---|
| Read `submission_metadata.yaml` end to end, especially `ai_usage_summary` and `declarations` | Honesty of the AI-tools declaration — per spec, contradictions with the interview are a stronger negative than AI use itself |
| Read `methodology_summary` aloud and ask: "could I explain and defend every sentence of this in a 30-minute interview?" | Direct Stage-5 readiness check |
| `git log --oneline --graph` review | Confirms real, multi-commit iteration history (not a single dump), per Stage-4's git-history check |
| Final manual review of `outputs/team_xxx.csv` (re-open the Phase 5 review one more time after all later changes) | Last chance to catch regressions introduced in Phases 6–8 |
| **Portal upload** (manual, cannot be automated): upload CSV + fill portal form with the same values as `submission_metadata.yaml` | Submission #1 of 3 consumed — confirm receipt/confirmation email |

**PowerShell commands:**
```powershell
.\.venv\Scripts\Activate.ps1
# Determinism check
python -m src.redrob_ranker.rank --candidates data\candidates.jsonl --out outputs\team_xxx_check.csv
Compare-Object (Get-Content outputs\team_xxx.csv) (Get-Content outputs\team_xxx_check.csv)
Remove-Item outputs\team_xxx_check.csv

python validate_submission.py outputs\team_xxx.csv
git log --oneline --graph
git add .
git commit -m "Phase 9: final submission packaging, metadata, README"
git push origin main
```

**Exit criteria:** All automated tests pass; human has completed the portal upload and has a confirmation; repo is public/accessible (or Stage-3 access plan documented for private repos).

**Human action items:**
- Final honest fill of `ai_usage_summary` and `declarations`.
- Perform the portal upload personally — this is the one irreversible, non-agent step in the whole plan.
- Decide repo visibility (public vs. private+grant-access-at-Stage-3) and act accordingly.

---

## 7. Master Human Action Checklist (all phases, consolidated)

| # | Action | Phase |
|---|---|---|
| 1 | Supply hackathon bundle files into `data/` | 0 |
| 2 | Confirm machine specs (CPU/RAM/OS/Python version) for metadata | 0 |
| 3 | Approve 47-title taxonomy and consulting-firm list from EDA report | 1 |
| 4 | Review 20 honeypot-flagged + 15 excluded + 10 Tier-5-candidate samples | 2 |
| 5 | Manually recompute 10 candidates' Layer 3/4 scores; approve `weights.yaml` | 3 |
| 6 | Configure Git LFS / artifact regeneration strategy; review top-20 semantic list | 4 |
| 7 | Full read-through of draft top-100 (top-10 deep, 90–100 deep, middle skim) | 5 |
| 8 | 10-sample Stage-4-style reasoning audit | 6 |
| 9 | Personally run clean-room, network-disabled reproduction; record measurements | 7 |
| 10 | Sign in to Streamlit Community Cloud (GitHub login), deploy `sandbox/app.py`, grant repo access if private, perform external-network end-to-end test, record live URL | 8 |
| 11 | Honest AI-usage declaration; portal upload; repo visibility decision | 9 |

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Honeypot heuristics (Phase 2) miss novel honeypot patterns not seen in the 50-row sample | Medium | High (Stage-3 disqualification) | Phase 2's combined-anomaly approach + Phase 5's explicit re-check + human eyeball of 5 final-top-100 candidates against Appendix C patterns |
| Embedding precompute artifact (`embeddings.npy`, ~150 MB) too large for plain git push | Medium | Medium (Stage-3 "missing repo content") | Git LFS, or document `scripts/precompute_embeddings.py` as a one-command regeneration step in README |
| Weight tuning (Phase 3) produces a top-100 that's plausible but not "10 great matches" per JD framing | Medium | High (scoring) | Phase 5's mandatory full 100-row human read-through, with explicit return-to-Phase-3 loop |
| Reasoning templates feel formulaic under Stage-4's 10-sample audit | Medium | Medium (Stage-4) | Phase 6 human audit mirrors Stage 4 exactly, with iteration expected and welcomed (also strengthens git history) |
| Clean-room reproduction fails due to hidden dev-machine state (cached HF model paths, absolute paths) | Medium | High (Stage-3 hard disqualifier) | Phase 7 mandatory clean-`.venv` re-run + network-disabled run |
| Streamlit Community Cloud's ~1 GB RAM ceiling and sleep-after-inactivity behavior cause apparent failure during an organizer check | Medium | Medium | Phase 8's on-the-fly (not precomputed-artifact) sandbox design keeps memory low; human pre-warms the app before the evaluation window and verifies resource usage via "Manage app" |
| `sandbox/requirements.txt`'s `torch`/`sentence-transformers` install fails or times out on Streamlit Cloud's build (large dependency) | Low | Medium | Pin CPU-only `torch` wheel via the PyTorch CPU index URL; verify with the Phase 8 build-isolation check (`pip install -r sandbox\requirements.txt` in a fresh venv) before pushing |

---

## Appendix A — Title Taxonomy (47 titles → tiers)

*Hand-curated from the full 100K EDA; "Tier S/A" titles are direct JD matches, "Tier B" are the JD's explicit "Tier-5" candidates (caught primarily by Layer 2), "Tier C/D" are generally irrelevant unless career history overrides.*

| Tier | Titles (count in dataset) |
|---|---|
| **S** — Core match | Recommendation Systems Engineer (26), Search Engineer (23), Senior AI Engineer (4), Lead AI Engineer (3), Staff Machine Learning Engineer (6), Senior Machine Learning Engineer (6), Senior NLP Engineer (6), NLP Engineer (14), Machine Learning Engineer (24), Applied ML Engineer (23), ML Engineer (167), Senior Applied Scientist (4), Senior Data Scientist (19) |
| **A** — Adjacent AI/ML (needs Layer-1 nuance) | AI Engineer (21), Data Scientist (145), Senior Software Engineer (ML) (142), Computer Vision Engineer (132) — *NLP/IR-exposure check applies*, AI Research Engineer (153) — *production-deployment check applies*, AI Specialist (130), Junior ML Engineer (131) |
| **B** — "Tier-5" adjacent (Layer 2 is the primary signal here) | Senior Data Engineer (687), Data Engineer (744), Analytics Engineer (764), Backend Engineer (704), Senior Software Engineer (653), Software Engineer (3450), Data Analyst (728), Full Stack Developer (2873), Cloud Engineer (2836), DevOps Engineer (2787) |
| **C** — Generic tech, low prior | Java Developer (2809), .NET Developer (2788), Mobile Developer (2757), Frontend Engineer (2738), QA Engineer (2682) |
| **D** — Non-tech (excluded unless career history strongly overrides) | Business Analyst (5833), HR Manager (5830), Mechanical Engineer (5791), Accountant (5764), Project Manager (5754), Customer Support (5750), Operations Manager (5744), Content Writer (5727), Sales Executive (5713), Civil Engineer (5702), Graphic Designer (5689), Marketing Manager (5524) |

**NLP/IR skill set** (for the Tier-A "CV without NLP" check): NLP, Information Retrieval, Embeddings, Sentence Transformers, Hugging Face Transformers, RAG, LLM-related skill names found in the skill taxonomy.

---

## Appendix B — Consulting-Firm Rule

Consulting-only firm set: `{TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, Tech Mahindra, Mindtree, HCL}` (matches JD's named list + 2 dataset-observed additions).

**Rule:** if `{candidate's current_company} ∪ {career_history[].company}` ⊆ consulting-only set → mark `consulting_only = True`. Per JD ("if you're currently at one of these but have prior product-company experience, that's fine"), this is **not** an automatic exclusion — it sets a flag that Layer 3's title-tier score and Layer 2's semantic score naturally down-weight (a consulting-only career with no AI/ML/search content in any title or description will simply score low on both). Only combine with hard exclusion if `title_tier ∈ {C, D}` AND `consulting_only = True` AND `semantic_score` below the 50th percentile.

---

## Appendix C — Honeypot / Internal-Consistency Heuristics

All self-contained per candidate record (no external company-founding-date database required):

1. **Skill-duration overflow**: `skills[].duration_months > years_of_experience × 12 + 6` (small buffer for rounding).
2. **Unverified expert with zero tenure**: `proficiency == "expert"` and `duration_months == 0`.
3. **Career-history overflow**: `sum(career_history[].duration_months) > years_of_experience × 12 + 12`.
4. **Overlapping current roles**: more than one `career_history[]` entry with `is_current == true`, or overlapping date ranges between full-time roles.
5. **Technology-era impossibility** (optional, Phase 2 stretch goal): cross-reference skill names with a small hand-built "earliest plausible year" table (e.g., Pinecone ≈ 2019, Sentence Transformers ≈ 2019, LoRA ≈ 2021) against `signup_date`/`career_history` dates minus `duration_months`.

**Severity rule** (from Section 1.1 EDA, where heuristic 1 alone fires on 13.5% of the pool — too broad): `honeypot_flag = True` only if **(heuristic 2 or 3 or 4 fire)** OR **(heuristic 1 fires AND the overflow exceeds 12 months AND at least one other heuristic also fires)**. Calibrate the exact thresholds during Phase 2's human review against the target ~80/100,000 (~0.08%) honeypot rate.

---

## Appendix D — JD "Absolutely Need" Skill Families (for Layer 3 skill-trust scoring)

| Family | Example skill names to match |
|---|---|
| Embeddings-based retrieval | Embeddings, Sentence Transformers, Hugging Face Transformers, sentence-transformers, BGE, E5 |
| Vector DB / hybrid search | FAISS, Pinecone, Milvus, Weaviate, Qdrant, OpenSearch, Elasticsearch |
| Python / engineering quality | Python, scikit-learn, MLOps, MLflow, BentoML |
| Ranking / eval frameworks | Learning to Rank, XGBoost, LightGBM, Feature Engineering, NDCG/MRR/MAP (if present in skill text) |
| LLM fine-tuning ("nice to have") | LoRA, QLoRA, PEFT, Fine-tuning LLMs |

---

*End of PRD. Each phase's "Exit criteria" is the literal gate — the agent should treat an unmet exit criterion as a blocking issue, not a note for later.*
