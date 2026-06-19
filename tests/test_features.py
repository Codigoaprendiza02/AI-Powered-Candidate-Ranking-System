import os
import yaml
import pytest
import numpy as np
from datetime import datetime
from src.redrob_ranker.features import compute_candidate_features

CONFIG_PATH = "config/weights.yaml"

@pytest.fixture
def weights_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@pytest.fixture
def ref_date():
    return datetime(2026, 5, 20)

@pytest.fixture
def mock_candidate():
    return {
        "candidate_id": "CAND_0000001",
        "profile": {
            "years_of_experience": 5.0,
            "current_title": "Search Engineer",
            "current_company": "Pied Piper",
            "current_industry": "Software",
            "location": "Noida",
            "country": "India"
        },
        "career_history": [
            {
                "company": "Pied Piper",
                "title": "Search Engineer",
                "start_date": "2024-01-01",
                "end_date": None,
                "duration_months": 24,
                "is_current": True,
                "industry": "Software",
                "company_size": "11-50",
                "description": "Building search engines"
            }
        ],
        "education": [
            {"institution": "IIT Delhi", "degree": "B.Tech", "field_of_study": "CS", "start_year": 2017, "end_year": 2021, "tier": "tier_1"}
        ],
        "skills": [
            {"name": "Python", "proficiency": "advanced", "endorsements": 10, "duration_months": 36},
            {"name": "Embeddings", "proficiency": "expert", "endorsements": 25, "duration_months": 24}
        ],
        "redrob_signals": {
            "last_active_date": "2026-05-20",
            "open_to_work_flag": True,
            "recruiter_response_rate": 0.8,
            "interview_completion_rate": 0.9,
            "offer_acceptance_rate": 0.5,
            "search_appearance_30d": 150,
            "saved_by_recruiters_30d": 15,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
            "notice_period_days": 15,
            "willing_to_relocate": False,
            "skill_assessment_scores": {
                "Embeddings": 40.0,  # low assessment score! Should discount the expert proficiency.
                "Python": 90.0
            }
        }
    }

def test_mock_candidate_scoring(mock_candidate, weights_config, ref_date):
    scores = compute_candidate_features(mock_candidate, weights_config, ref_date)
    
    # 1. Title Tier (Search Engineer is S tier -> 100 points)
    assert scores["title_tier_score"] == 100.0
    
    # 2. Location Noida (in_city -> 100 points, notice period 15 days <= 30 days -> no penalty)
    assert scores["location_score"] == 100.0
    
    # 3. Education IIT Delhi (tier_1 -> 10 points)
    assert scores["education_score"] == 10.0
    
    # 4. Availability Multiplier is clipped to [0.3, 1.0]
    assert 0.3 <= scores["availability_multiplier"] <= 1.0
    
def test_skill_discount(mock_candidate, weights_config, ref_date):
    # Calculate scores with low assessment score (40)
    scores_low = compute_candidate_features(mock_candidate, weights_config, ref_date)
    
    # Now set assessment score to 100 and check that the score increases
    mock_candidate["redrob_signals"]["skill_assessment_scores"]["Embeddings"] = 100.0
    scores_high = compute_candidate_features(mock_candidate, weights_config, ref_date)
    
    # The skill trust score and structured score should be higher with 100.0 assessment score
    assert scores_high["skill_trust_score"] > scores_low["skill_trust_score"]

def test_notice_period_penalty(mock_candidate, weights_config, ref_date):
    # Base notice is 15 days (<= 30 days) -> no penalty -> score is 100
    scores_base = compute_candidate_features(mock_candidate, weights_config, ref_date)
    
    # Set notice to 90 days (> 30 days) -> should penalize
    mock_candidate["redrob_signals"]["notice_period_days"] = 90
    scores_penalized = compute_candidate_features(mock_candidate, weights_config, ref_date)
    
    assert scores_penalized["location_score"] < scores_base["location_score"]

def test_neutral_offer_acceptance(mock_candidate, weights_config, ref_date):
    # When offer acceptance rate is -1, it should be treated as 0.5 (neutral)
    mock_candidate["redrob_signals"]["offer_acceptance_rate"] = -1
    scores_neg_1 = compute_candidate_features(mock_candidate, weights_config, ref_date)
    
    # When offer acceptance is exactly 0.5
    mock_candidate["redrob_signals"]["offer_acceptance_rate"] = 0.5
    scores_neutral = compute_candidate_features(mock_candidate, weights_config, ref_date)
    
    # They should yield identical availability multipliers
    assert scores_neg_1["availability_multiplier"] == pytest.approx(scores_neutral["availability_multiplier"], rel=1e-5)
