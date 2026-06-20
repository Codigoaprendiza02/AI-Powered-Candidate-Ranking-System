import os
import pytest
import json
import pandas as pd
from src.redrob_ranker.reasoning import populate_reasoning

@pytest.fixture
def sample_top_100_data():
    # Create a small sample dataframe representing rank outputs
    data = pd.DataFrame({
        "candidate_id": ["CAND_0000001", "CAND_0000002", "CAND_0000031"],
        "rank": [1, 25, 50],
        "composite_score": [0.95, 0.78, 0.52],
        "score": [0.95, 0.78, 0.52],
        "title_tier": ["S", "A", "B"],
        "availability_multiplier": [1.0, 0.9, 0.5],
        "consulting_only": [False, False, False]
    })
    return data

def test_reasoning_length_and_uniqueness(sample_top_100_data):
    # Run reasoning generator over sample data using the sample_candidates.json
    candidates_path = "data/sample_candidates.json"
    
    # We must mock candidate_id in sample_top_100_data to match those in sample_candidates.json
    with open(candidates_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)
        
    ids = [c["candidate_id"] for c in candidates[:3]]
    df = sample_top_100_data.copy()
    df["candidate_id"] = ids
    
    res_df = populate_reasoning(df, candidates_path)
    
    assert "reasoning" in res_df.columns
    reasonings = res_df["reasoning"].tolist()
    
    # Check length and uniqueness
    for r in reasonings:
        assert len(r) >= 60
        assert len(r) <= 280
        
    assert len(set(reasonings)) == len(reasonings)  # all unique

def test_reasoning_factual_accuracy():
    candidates_path = "data/sample_candidates.json"
    with open(candidates_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)
        
    ids = [c["candidate_id"] for c in candidates[:10]]
    df = pd.DataFrame({
        "candidate_id": ids,
        "rank": list(range(1, 11)),
        "composite_score": [0.9] * 10,
        "score": [0.9] * 10,
        "title_tier": ["S"] * 10,
        "availability_multiplier": [1.0] * 10,
        "consulting_only": [False] * 10
    })
    
    res_df = populate_reasoning(df, candidates_path)
    
    # Check that each reasoning contains correct YoE and Title from raw profile
    profiles_dict = {c["candidate_id"]: c for c in candidates}
    for _, row in res_df.iterrows():
        cid = row["candidate_id"]
        text = row["reasoning"]
        raw_c = profiles_dict[cid]
        yoe = raw_c["profile"]["years_of_experience"]
        title = raw_c["profile"]["current_title"]
        
        # Verify YoE is in text
        assert f"{yoe} years" in text or f"{yoe} yrs" in text
        # Verify title is in text (some templates use title)
        # Note: If title is present in text, check it matches
        if "as a" in text:
            # e.g., "as a Search Engineer at"
            assert title in text

def test_reasoning_rank_consistency():
    candidates_path = "data/sample_candidates.json"
    with open(candidates_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)
        
    ids = [c["candidate_id"] for c in candidates[:3]]
    df = pd.DataFrame({
        "candidate_id": ids,
        "rank": [1, 20, 90], # representing glow, strong, and measured
        "composite_score": [0.9, 0.7, 0.4],
        "score": [0.9, 0.7, 0.4],
        "title_tier": ["S", "A", "B"],
        "availability_multiplier": [1.0, 0.9, 0.4],
        "consulting_only": [False, False, False]
    })
    
    res_df = populate_reasoning(df, candidates_path)
    
    text_glow = res_df.iloc[0]["reasoning"]
    text_strong = res_df.iloc[1]["reasoning"]
    text_measured = res_df.iloc[2]["reasoning"]
    
    # Ranks 1-10 should have glowing adjectives
    assert any(kw in text_glow.lower() for kw in ["outstanding", "top-tier", "perfect", "excellent"])
    
    # Ranks 11-30 should be positive but measured
    assert any(kw in text_strong.lower() for kw in ["strong", "experienced", "promising", "competent"])
    
    # Ranks 31-100 should contain a concern clause (e.g. notice, relocation, adjacent, engagement, experience)
    assert any(kw in text_measured.lower() for kw in ["though", "noting", "concern", "tempered", "deferred"])
