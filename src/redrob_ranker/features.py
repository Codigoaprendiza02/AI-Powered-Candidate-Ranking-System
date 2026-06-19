import os
import json
import yaml
import argparse
import numpy as np
import pandas as pd
from datetime import datetime
from src.redrob_ranker.taxonomy import TITLE_TAXO

# Normalization keywords for skill matching
SKILL_FAMILIES_KEYWORDS = {
    "embeddings": ["embedding", "sentence transformer", "hugging face transformer", "sentence-transformers", "bge", "e5", "retrieval", "semantic search"],
    "vector_db": ["faiss", "pinecone", "milvus", "weaviate", "qdrant", "opensearch", "elasticsearch", "vector db", "vector search", "hybrid search"],
    "python": ["python", "scikit-learn", "mlops", "mlflow", "bentoml", "pandas", "numpy", "pytorch", "tensorflow", "keras"],
    "ranking": ["learning to rank", "xgboost", "lightgbm", "feature engineering", "ndcg", "mrr", "map", "ranking"],
    "llm": ["lora", "qlora", "peft", "fine-tuning llms", "llm", "large language model", "prompt engineering", "langchain", "llama", "gpt"]
}

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

def compute_candidate_features(candidate, config, reference_date):
    """
    Computes structured subscores and availability multiplier for a single candidate.
    """
    profile = candidate["profile"]
    career_history = candidate["career_history"]
    skills = candidate["skills"]
    signals = candidate["redrob_signals"]
    
    yoe = profile.get("years_of_experience", 0)
    current_title = profile.get("current_title", "")
    current_company = profile.get("current_company", "")
    
    # --------------------------------------------------------------------------
    # 1. Title Tier Score
    # --------------------------------------------------------------------------
    title_scores_cfg = config["title_scores"]
    current_tier = TITLE_TAXO.get(current_title, "D")
    current_title_score = title_scores_cfg.get(current_tier, 0.0)
    
    historical_scores = []
    for job in career_history:
        h_title = job.get("title", "")
        h_tier = TITLE_TAXO.get(h_title, "D")
        historical_scores.append(title_scores_cfg.get(h_tier, 0.0))
        
    best_historical_score = max(historical_scores) if historical_scores else 0.0
    
    comb_cfg = config["title_combination_weights"]
    title_tier_score = (
        current_title_score * comb_cfg["current_title_weight"] +
        best_historical_score * comb_cfg["best_historical_title_weight"]
    )
    
    # --------------------------------------------------------------------------
    # 2. Skill Trust Score
    # --------------------------------------------------------------------------
    family_weights = config["skill_family_weights"]
    prof_weights = config["skill_proficiency_weights"]
    assessment_scores = signals.get("skill_assessment_scores", {})
    
    family_max_scores = {fam: 0.0 for fam in family_weights.keys()}
    
    for s in skills:
        s_name = s.get("name", "")
        s_name_lower = s_name.lower()
        
        # Determine proficiency weight
        proficiency = s.get("proficiency", "beginner").lower()
        prof_weight = prof_weights.get(proficiency, 0.25)
        
        # Endorsements and duration
        endorsements = s.get("endorsements", 0)
        dur = s.get("duration_months", 0)
        
        # Skill assessment score defaults to 50.0 if not assessed
        assess_score = assessment_scores.get(s_name, 50.0)
        
        # Skill-trust formula
        # prof_weight * (1 + log1p(endorsements)) * min(duration_months/24, 1) * (assess_score/100)
        skill_trust = (
            prof_weight * 
            (1.0 + np.log1p(endorsements)) * 
            min(dur / 24.0, 1.0) * 
            (assess_score / 100.0)
        )
        
        # Match to family
        for family, keywords in SKILL_FAMILIES_KEYWORDS.items():
            if any(kw in s_name_lower for kw in keywords):
                if skill_trust > family_max_scores[family]:
                    family_max_scores[family] = skill_trust
                    
    # Weighted sum of skill family scores
    skill_trust_score = sum(score * family_weights[fam] for fam, score in family_max_scores.items())
    
    # --------------------------------------------------------------------------
    # 3. Location / Notice / Relocation Score
    # --------------------------------------------------------------------------
    loc_scores_cfg = config["location_scores"]
    loc_lower = profile.get("location", "").lower()
    country_lower = profile.get("country", "").lower()
    
    # In-city Noida / Pune check
    if "noida" in loc_lower or "pune" in loc_lower:
        base_loc_score = loc_scores_cfg["in_city"]
    # Tier-1 Indian Cities
    elif any(city in loc_lower for city in ["bangalore", "bengaluru", "mumbai", "hyderabad", "chennai", "kolkata", "gurgaon", "delhi"]):
        base_loc_score = loc_scores_cfg["regional"]
    elif signals.get("willing_to_relocate", False):
        base_loc_score = loc_scores_cfg["relocatable"]
    else:
        base_loc_score = loc_scores_cfg["other"]
        
    # Notice Period Penalty
    notice_cfg = config["notice_period"]
    notice_days = signals.get("notice_period_days", 0)
    penalty = 0.0
    if notice_days > notice_cfg["base_days"]:
        penalty = min(
            notice_cfg["max_penalty"],
            ((notice_days - notice_cfg["base_days"]) / notice_cfg["penalty_scale"]) * notice_cfg["max_penalty"]
        )
    location_score = max(0.0, base_loc_score - penalty)
    
    # --------------------------------------------------------------------------
    # 4. Education Score
    # --------------------------------------------------------------------------
    edu_scores_cfg = config["education_scores"]
    education = candidate.get("education", [])
    edu_tiers = [edu.get("tier", "unknown") for edu in education]
    
    edu_score_vals = [edu_scores_cfg.get(t, 0.0) for t in edu_tiers]
    education_score = max(edu_score_vals) if edu_score_vals else 0.0
    
    # --------------------------------------------------------------------------
    # Structured Combined Score
    # --------------------------------------------------------------------------
    struct_weights = config["structured_weights"]
    structured_score = (
        struct_weights["weight_title"] * title_tier_score +
        struct_weights["weight_skill"] * skill_trust_score +
        struct_weights["weight_location"] * location_score +
        struct_weights["weight_education"] * education_score
    )
    
    # --------------------------------------------------------------------------
    # 5. Availability Multiplier (Layer 4)
    # --------------------------------------------------------------------------
    avail_weights = config["availability_weights"]
    
    # last_active_date Recency decay
    active_date = parse_date(signals.get("last_active_date"))
    if active_date and reference_date:
        days_inactive = max(0, (reference_date - active_date).days)
    else:
        days_inactive = 365  # default to stale if missing
        
    decay_cfg = config["availability_decay"]
    decay = np.exp(-days_inactive / (decay_cfg["half_life_days"] / np.log(2.0)))
    
    # open_to_work_flag
    otw_flag = 1.0 if signals.get("open_to_work_flag", False) else 0.0
    
    # Recruiter response rate
    response_rate = signals.get("recruiter_response_rate", 0.5)
    
    # Interview completion rate
    interview_rate = signals.get("interview_completion_rate", 0.5)
    
    # Offer acceptance rate: treat -1 as neutral 0.5
    offer_rate = signals.get("offer_acceptance_rate", 0.5)
    if offer_rate == -1:
        offer_rate = 0.5
        
    # Log-scaled search appearances and saves
    engage_cfg = config["availability_engagement"]
    search_apps = np.log1p(signals.get("search_appearance_30d", 0))
    saves = np.log1p(signals.get("saved_by_recruiters_30d", 0))
    
    # Verification trust bonuses
    bonus_cfg = config["availability_verification_bonuses"]
    email_bonus = bonus_cfg["email_bonus"] if signals.get("verified_email", False) else 0.0
    phone_bonus = bonus_cfg["phone_bonus"] if signals.get("verified_phone", False) else 0.0
    linkedin_bonus = bonus_cfg["linkedin_bonus"] if signals.get("linkedin_connected", False) else 0.0
    
    # Combine signals
    availability_raw = (
        avail_weights["weight_decay"] * decay +
        avail_weights["weight_otw"] * otw_flag +
        avail_weights["weight_response"] * response_rate +
        avail_weights["weight_interview"] * interview_rate +
        avail_weights["weight_offer"] * offer_rate +
        engage_cfg["search_appearances_weight"] * search_apps +
        engage_cfg["saved_by_recruiters_weight"] * saves +
        email_bonus + phone_bonus + linkedin_bonus
    )
    
    # Clip final availability multiplier to [0.3, 1.0]
    availability_multiplier = float(np.clip(availability_raw, 0.3, 1.0))
    
    return {
        "title_tier_score": float(title_tier_score),
        "skill_trust_score": float(skill_trust_score),
        "location_score": float(location_score),
        "education_score": float(education_score),
        "structured_score": float(structured_score),
        "availability_multiplier": float(availability_multiplier)
    }

def find_reference_date(input_path):
    print("Finding reference active date (dataset max)...")
    max_date = None
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            c = json.loads(line)
            active_s = c["redrob_signals"].get("last_active_date")
            if active_s:
                dt = parse_date(active_s)
                if dt and (not max_date or dt > max_date):
                    max_date = dt
    if not max_date:
        max_date = datetime.now()
    print(f"Reference date resolved: {max_date.strftime('%Y-%m-%d')}")
    return max_date

def process_features(flags_path, candidates_path, config_path, output_path):
    print(f"Loading flags from {flags_path}...")
    flags_df = pd.read_parquet(flags_path)
    
    print(f"Loading config from {config_path}...")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    # Get reference date for decay calculation
    reference_date = find_reference_date(candidates_path)
    
    # Filter to eligible candidates
    eligible_cids = set(flags_df[flags_df["eligible"] == True]["candidate_id"])
    print(f"Total eligible candidates: {len(eligible_cids)}")
    
    print(f"Processing candidate features from {candidates_path}...")
    feature_results = []
    
    with open(candidates_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            c = json.loads(line)
            cid = c["candidate_id"]
            
            # Skip ineligible candidates to save time/memory
            if cid not in eligible_cids:
                continue
                
            scores = compute_candidate_features(c, config, reference_date)
            scores["candidate_id"] = cid
            feature_results.append(scores)
            
            if len(feature_results) % 20000 == 0:
                print(f"Processed {len(feature_results)} candidates...")
                
    df = pd.DataFrame(feature_results)
    
    # Output statistics checks
    print("\nFeature Engineering Summary Statistics:")
    print(df[["structured_score", "availability_multiplier"]].describe())
    
    # Save as parquet
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"Saved feature results to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Structured features and availability multiplier scoring")
    parser.add_argument("--input", required=True, help="Path to flags.parquet file")
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl file")
    parser.add_argument("--config", required=True, help="Path to config weights.yaml file")
    parser.add_argument("--output", required=True, help="Path to output parquet file")
    args = parser.parse_args()
    
    process_features(args.input, args.candidates, args.config, args.output)
