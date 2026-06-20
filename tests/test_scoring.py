import os
import pytest
import pandas as pd
import numpy as np
import yaml
from src.redrob_ranker.scoring import score_and_rank

@pytest.fixture
def mock_parquet_data(tmp_path):
    # Create mock flags
    flags_data = pd.DataFrame({
        "candidate_id": [f"CAND_000000{i}" for i in range(1, 6)],
        "eligible": [True, True, True, True, True],
        "honeypot_flag": [False, False, False, False, False],
        "exclusion_reason": [None] * 5,
        "consulting_only": [False, False, True, False, False],
        "title_tier": ["S", "A", "C", "B", "D"]
    })
    
    # Create mock features
    features_data = pd.DataFrame({
        "candidate_id": [f"CAND_000000{i}" for i in range(1, 6)],
        "structured_score": [80.0, 70.0, 50.0, 60.0, 30.0],
        "availability_multiplier": [1.0, 0.9, 0.8, 0.7, 0.6]
    })
    
    # Create mock retrieval
    retrieval_data = pd.DataFrame({
        "candidate_id": [f"CAND_000000{i}" for i in range(1, 6)],
        "semantic_score": [0.9, 0.8, 0.1, 0.7, 0.5]
    })
    
    flags_path = tmp_path / "flags.parquet"
    features_path = tmp_path / "features.parquet"
    retrieval_path = tmp_path / "retrieval.parquet"
    
    flags_data.to_parquet(flags_path, index=False)
    features_data.to_parquet(features_path, index=False)
    retrieval_data.to_parquet(retrieval_path, index=False)
    
    return str(flags_path), str(features_path), str(retrieval_path)

@pytest.fixture
def mock_config(tmp_path):
    config_content = {
        "composite_weights": {
            "weight_semantic": 0.60,
            "weight_structured": 0.40
        }
    }
    cfg_path = tmp_path / "weights.yaml"
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config_content, f)
    return str(cfg_path)

def test_consulting_only_exclusion(mock_parquet_data, mock_config, tmp_path):
    flags, features, retrieval = mock_parquet_data
    
    # run scoring
    top_df = score_and_rank(flags, features, retrieval, mock_config, output_dir=str(tmp_path))
    
    # Candidate CAND_0000003 is consulting_only=True and title_tier=C.
    # Its semantic score is 0.1, which is below the median (which is 0.7 since candidates have scores [0.9, 0.8, 0.7, 0.5, 0.1]).
    # So Candidate 3 should be excluded!
    assert "CAND_0000003" not in top_df["candidate_id"].values
    
    # The output dataframe should have only eligible candidates (max 100, here 4)
    assert len(top_df) == 4

def test_normalization_and_scoring(mock_parquet_data, mock_config, tmp_path):
    flags, features, retrieval = mock_parquet_data
    top_df = score_and_rank(flags, features, retrieval, mock_config, output_dir=str(tmp_path))
    
    # Check that Min-Max normalization is performed correctly.
    # Candidate CAND_0000001 (S tier) has highest semantic (0.9) and structured (80.0) score, and multiplier 1.0.
    # So CAND_0000001 norm values should be 1.0, and composite score should be (0.6 * 1.0 + 0.4 * 1.0) * 1.0 = 1.0.
    # Let's verify
    cand1 = top_df[top_df["candidate_id"] == "CAND_0000001"].iloc[0]
    assert np.isclose(cand1["composite_score"], 1.0)
    assert cand1["rank"] == 1
    assert np.isclose(cand1["score"], 1.0)

def test_tie_breaking(tmp_path, mock_config):
    # Create mock data where CAND_0000002 and CAND_0000001 have equal composite scores
    flags_data = pd.DataFrame({
        "candidate_id": ["CAND_0000002", "CAND_0000001"],
        "eligible": [True, True],
        "honeypot_flag": [False, False],
        "exclusion_reason": [None, None],
        "consulting_only": [False, False],
        "title_tier": ["S", "S"]
    })
    features_data = pd.DataFrame({
        "candidate_id": ["CAND_0000002", "CAND_0000001"],
        "structured_score": [80.0, 80.0],
        "availability_multiplier": [1.0, 1.0]
    })
    retrieval_data = pd.DataFrame({
        "candidate_id": ["CAND_0000002", "CAND_0000001"],
        "semantic_score": [0.9, 0.9]
    })
    
    flags_path = tmp_path / "flags_tie.parquet"
    features_path = tmp_path / "features_tie.parquet"
    retrieval_path = tmp_path / "retrieval_tie.parquet"
    
    flags_data.to_parquet(flags_path, index=False)
    features_data.to_parquet(features_path, index=False)
    retrieval_data.to_parquet(retrieval_path, index=False)
    
    # Run scoring
    top_df = score_and_rank(str(flags_path), str(features_path), str(retrieval_path), mock_config, output_dir=str(tmp_path))
    
    # Ranks should be 1 and 2
    # CAND_0000001 should be Rank 1 because it's sorted alphabetically first
    # CAND_0000002 should be Rank 2
    assert top_df.iloc[0]["candidate_id"] == "CAND_0000001"
    assert top_df.iloc[1]["candidate_id"] == "CAND_0000002"
    assert top_df.iloc[0]["rank"] == 1
    assert top_df.iloc[1]["rank"] == 2
