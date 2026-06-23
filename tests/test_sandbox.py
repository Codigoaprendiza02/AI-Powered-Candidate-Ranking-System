import os
import json
import yaml
import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from src.redrob_ranker.filters import check_candidate_filters
from src.redrob_ranker.features import compute_candidate_features
from src.redrob_ranker.retrieval import tokenize, min_max_normalize
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SAMPLE_PATH = os.path.join(PROJECT_ROOT, "data", "sample_candidates.json")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "weights.yaml")
JD_PATH = os.path.join(PROJECT_ROOT, "data", "job_description.md")

def test_sandbox_pipeline_flow():
    """
    Test headless flow representing the sandbox app execution on sample candidates.
    """
    # 1. Load data
    assert os.path.exists(SAMPLE_PATH)
    with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
        candidates = json.load(f)
        
    assert os.path.exists(CONFIG_PATH)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config_weights = yaml.safe_load(f)
        
    assert os.path.exists(JD_PATH)
    with open(JD_PATH, "r", encoding="utf-8") as f:
        jd_text = f.read()

    # 2. Layer 1 filter and honeypot detection
    filter_results = []
    eligible_candidates = []
    
    for c in candidates:
        eligible, honeypot_flag, exclusion_reason, consulting_only, title_tier = check_candidate_filters(c)
        if eligible:
            eligible_candidates.append(c)
            filter_results.append({
                "candidate_id": c["candidate_id"],
                "eligible": True,
                "honeypot_flag": honeypot_flag,
                "exclusion_reason": None,
                "consulting_only": consulting_only,
                "title_tier": title_tier
            })
        else:
            filter_results.append({
                "candidate_id": c["candidate_id"],
                "eligible": False,
                "honeypot_flag": honeypot_flag,
                "exclusion_reason": exclusion_reason,
                "consulting_only": consulting_only,
                "title_tier": title_tier
            })
            
    filter_df = pd.DataFrame(filter_results)
    assert len(eligible_candidates) > 0
    
    # 3. Layer 3 & 4 structured features & availability multiplier
    max_active_date = datetime.strptime("2026-05-27", "%Y-%m-%d") # Use fixed date
    feature_results = []
    for c in eligible_candidates:
        scores = compute_candidate_features(c, config_weights, max_active_date)
        scores["candidate_id"] = c["candidate_id"]
        feature_results.append(scores)
        
    features_df = pd.DataFrame(feature_results)
    
    # 4. Layer 2 Hybrid Retrieval on-the-fly
    jd_tokens = tokenize(jd_text)
    
    # BM25
    def extract_bm25_text(cand):
        profile = cand.get("profile", {})
        headline = profile.get("headline") or ""
        summary = profile.get("summary") or ""
        parts = [headline, summary]
        for job in cand.get("career_history", []):
            parts.append(job.get("title") or "")
            parts.append(job.get("description") or "")
        return " ".join(parts).strip()

    def extract_dense_text(cand):
        profile = cand.get("profile", {})
        headline = profile.get("headline") or ""
        summary = profile.get("summary") or ""
        parts = [headline, summary]
        for job in cand.get("career_history", []):
            title = job.get("title") or ""
            desc = job.get("description") or ""
            if len(desc) > 150:
                desc = desc[:150]
            parts.append(f"{title} {desc}".strip())
        return " ".join(parts).strip()

    tokenized_corpus = [tokenize(extract_bm25_text(c)) for c in eligible_candidates]
    bm25_index = BM25Okapi(tokenized_corpus)
    bm25_scores = np.array(bm25_index.get_scores(jd_tokens))
    
    # Dense embeddings
    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    candidate_dense_texts = [extract_dense_text(c) for c in eligible_candidates]
    candidate_embeddings = model.encode(candidate_dense_texts, normalize_embeddings=True)
    
    jd_embedding = model.encode(jd_text, normalize_embeddings=True)
    dense_scores = candidate_embeddings @ jd_embedding
    
    # Normalize & Combine
    dense_norm = min_max_normalize(dense_scores)
    bm25_norm = min_max_normalize(bm25_scores)
    
    retrieval_alpha = 0.4
    semantic_scores = retrieval_alpha * bm25_norm + (1.0 - retrieval_alpha) * dense_norm
    
    retrieval_df = pd.DataFrame({
        "candidate_id": [c["candidate_id"] for c in eligible_candidates],
        "semantic_score": semantic_scores
    })

    # 5. Composite Scoring
    df = filter_df.merge(features_df, on="candidate_id").merge(retrieval_df, on="candidate_id")
    
    # Consulting exclusion rule
    semantic_median = df["semantic_score"].median()
    is_consulting_exclude = (df["title_tier"].isin(["C", "D"])) & (df["consulting_only"]) & (df["semantic_score"] < semantic_median)
    df.loc[is_consulting_exclude, "eligible"] = False
    
    eligible_df = df[df["eligible"] == True].copy()
    assert len(eligible_df) > 0
    
    # Normalizations
    sem_min = eligible_df["semantic_score"].min()
    sem_max = eligible_df["semantic_score"].max()
    sem_denom = sem_max - sem_min
    eligible_df["semantic_score_norm"] = (eligible_df["semantic_score"] - sem_min) / (sem_denom if sem_denom > 1e-8 else 1.0)
    
    struct_min = eligible_df["structured_score"].min()
    struct_max = eligible_df["structured_score"].max()
    struct_denom = struct_max - struct_min
    eligible_df["structured_score_norm"] = (eligible_df["structured_score"] - struct_min) / (struct_denom if struct_denom > 1e-8 else 1.0)
    
    # Composite Score Formula
    weight_semantic = 0.60
    weight_structured = 0.40
    eligible_df["composite_score"] = (
        weight_semantic * eligible_df["semantic_score_norm"] +
        weight_structured * eligible_df["structured_score_norm"]
    ) * eligible_df["availability_multiplier"]
    
    # Sort
    sorted_df = eligible_df.sort_values(by=["composite_score", "candidate_id"], ascending=[False, True]).copy()
    sorted_df["rank"] = range(1, len(sorted_df) + 1)
    
    # Adjusted score sequence checks
    rounded_scores = []
    prev_score = None
    for _, row in sorted_df.iterrows():
        s_rounded = round(row["composite_score"], 3)
        if prev_score is not None:
            if s_rounded >= prev_score:
                s_rounded = round(prev_score - 0.001, 3)
        rounded_scores.append(s_rounded)
        prev_score = s_rounded
        
    sorted_df["score"] = rounded_scores
    
    # Assertion Checks
    assert "rank" in sorted_df.columns
    assert "score" in sorted_df.columns
    assert "candidate_id" in sorted_df.columns
    
    # Ensure scores are strictly non-increasing
    scores = sorted_df["score"].tolist()
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i+1], f"Score at index {i} ({scores[i]}) is less than score at index {i+1} ({scores[i+1]})"
