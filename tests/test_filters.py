import os
import json
import pytest
from src.redrob_ranker.filters import check_candidate_filters

@pytest.fixture
def base_candidate():
    return {
        "candidate_id": "CAND_0000000",
        "profile": {
            "years_of_experience": 5.0,
            "current_title": "Search Engineer",
            "current_company": "Pied Piper",
            "current_industry": "Software",
            "current_company_size": "11-50"
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
                "description": "Building search algorithms"
            }
        ],
        "skills": [
            {"name": "Python", "proficiency": "advanced", "endorsements": 10, "duration_months": 36},
            {"name": "NLP", "proficiency": "advanced", "endorsements": 5, "duration_months": 24}
        ]
    }

def test_eligible_candidate(base_candidate):
    eligible, honeypot, reason, consulting, tier = check_candidate_filters(base_candidate)
    assert eligible is True
    assert honeypot is False
    assert reason is None
    assert consulting is False
    assert tier == "S"

def test_honeypot_expert_zero_months(base_candidate):
    # Add expert skill with 0 months duration
    base_candidate["skills"].append(
        {"name": "Pinecone", "proficiency": "expert", "endorsements": 20, "duration_months": 0}
    )
    eligible, honeypot, reason, consulting, tier = check_candidate_filters(base_candidate)
    assert eligible is False
    assert honeypot is True
    assert reason == "Flagged Honeypot"

def test_pure_research(base_candidate):
    base_candidate["profile"]["current_industry"] = "Research"
    base_candidate["career_history"][0]["industry"] = "Academia"
    eligible, honeypot, reason, consulting, tier = check_candidate_filters(base_candidate)
    assert eligible is False
    assert reason == "Pure Research without Production"

def test_cv_without_nlp(base_candidate):
    base_candidate["profile"]["current_title"] = "Computer Vision Engineer"
    # Remove NLP skill
    base_candidate["skills"] = [
        {"name": "Python", "proficiency": "advanced", "endorsements": 10, "duration_months": 36}
    ]
    eligible, honeypot, reason, consulting, tier = check_candidate_filters(base_candidate)
    assert eligible is False
    assert reason == "CV/Speech/Robotics without NLP/IR exposure"

def test_title_chaser(base_candidate):
    base_candidate["career_history"] = [
        {
            "company": "Company A",
            "title": "Lead Engineer",
            "start_date": "2025-06-01",
            "end_date": None,
            "duration_months": 6,
            "is_current": True,
            "industry": "Software",
            "company_size": "11-50",
            "description": "chasing lead title"
        },
        {
            "company": "Company B",
            "title": "Senior Engineer",
            "start_date": "2024-06-01",
            "end_date": "2025-05-31",
            "duration_months": 12,
            "is_current": False,
            "industry": "Software",
            "company_size": "11-50",
            "description": "chasing senior title"
        },
        {
            "company": "Company C",
            "title": "Junior Engineer",
            "start_date": "2023-06-01",
            "end_date": "2024-05-31",
            "duration_months": 12,
            "is_current": False,
            "industry": "Software",
            "company_size": "11-50",
            "description": "chasing junior title"
        }
    ]
    eligible, honeypot, reason, consulting, tier = check_candidate_filters(base_candidate)
    assert eligible is False
    assert reason == "Title Chaser"

def test_full_dataset_regression():
    full_path = "data/candidates.jsonl"
    if not os.path.exists(full_path):
        pytest.skip("Full candidates.jsonl file is missing")
        
    honeypot_count = 0
    total_count = 0
    
    with open(full_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            c = json.loads(line)
            _, honeypot, _, _, _ = check_candidate_filters(c)
            if honeypot:
                honeypot_count += 1
            total_count += 1
            
    rate = honeypot_count / total_count
    print(f"Regression Test: Flagged {honeypot_count} honeypots out of {total_count} ({rate * 100:.4f}%)")
    # Verify rate is in 0.03% - 0.3% band
    assert 0.0003 <= rate <= 0.003, f"Honeypot rate {rate:.4f} is outside the allowed 0.03% to 0.3% range"
