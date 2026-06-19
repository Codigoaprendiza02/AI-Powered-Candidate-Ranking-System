import os
import json
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from src.redrob_ranker.taxonomy import TITLE_TAXO, CONSULTING_COMPANIES, NLP_IR_SKILLS

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

def get_seniority_level(title):
    title_lower = title.lower()
    if "principal" in title_lower:
        return 6
    if "staff" in title_lower:
        return 5
    if "lead" in title_lower:
        return 4
    if "senior" in title_lower or "sr" in title_lower:
        return 3
    if "junior" in title_lower or "jr" in title_lower or "associate" in title_lower:
        return 1
    return 2  # standard / mid

def check_candidate_filters(candidate):
    """
    Evaluates hard filters and honeypot heuristics for a single candidate.
    Returns:
        eligible: bool
        honeypot_flag: bool
        exclusion_reason: str or None
        consulting_only: bool
        title_tier: str
    """
    profile = candidate["profile"]
    career_history = candidate["career_history"]
    skills = candidate["skills"]
    
    cid = candidate["candidate_id"]
    yoe = profile.get("years_of_experience", 0)
    current_title = profile.get("current_title", "")
    current_company = profile.get("current_company", "")
    current_industry = profile.get("current_industry", "")
    
    # Resolve Title Tier
    title_tier = TITLE_TAXO.get(current_title, "D")
    
    # 1. Consulting-only check (Appendix B)
    all_companies = {current_company}
    for job in career_history:
        comp = job.get("company")
        if comp:
            all_companies.add(comp)
            
    normalized_companies = {c.strip().upper() for c in all_companies if c}
    normalized_consulting = {c.upper() for c in CONSULTING_COMPANIES}
    consulting_only = normalized_companies.issubset(normalized_consulting) and len(normalized_companies) > 0
    
    # 2. Pure Research without production check (Section 6 / Section 2.2)
    # Check if all industries are Research / Academia
    all_industries = {current_industry}
    for job in career_history:
        ind = job.get("industry")
        if ind:
            all_industries.add(ind)
    normalized_industries = {i.strip().lower() for i in all_industries if i}
    
    is_research = normalized_industries.issubset({"research", "academia", "education"}) and len(normalized_industries) > 0
    # Check if there is any past role size indicating a product company
    # e.g., product companies are typically smaller (1-10, 11-50, etc.) in start-ups or mid-size (201-500, 501-1000)
    # giants like 10001+ are services, but Stark/Pied Piper/Globex are also product and size can be huge.
    # The PRD says: "no is_current/past role with company_size indicating a product company"
    # Research companies in the dataset are size "10001+" or "1-10" depending on university.
    # Let's say a product company size is anything that is not 10001+ or "unknown" if they only worked in research.
    # Wait, the simplest way is to check if all companies they worked for are research/academia institutions.
    # Let's check if is_research is True.
    
    # 3. CV/Speech/Robotics without NLP/IR exposure (Appendix A/C)
    is_cv_speech_robotics = any(kw in current_title.lower() for kw in ["computer vision", "speech", "robotics", "cv engineer"])
    has_nlp_ir_skill = False
    for s in skills:
        s_name = s.get("name", "").lower()
        if any(kw in s_name for kw in NLP_IR_SKILLS):
            has_nlp_ir_skill = True
            break
            
    is_cv_without_nlp = is_cv_speech_robotics and not has_nlp_ir_skill
    
    # 4. Title-chaser check
    num_employers = len(set(job.get("company") for job in career_history if job.get("company")))
    total_months = sum(job.get("duration_months", 0) for job in career_history)
    avg_tenure_months = (total_months / num_employers) if num_employers > 0 else 0
    
    # Seniority escalation check
    seniority_levels = [get_seniority_level(job.get("title", "")) for job in reversed(career_history)]
    # Check if there's a strong upward escalation in a very short time
    escalating = len(seniority_levels) >= 3 and seniority_levels[-1] > seniority_levels[0]
    
    is_chaser = (num_employers >= 3) and (avg_tenure_months <= 18) and escalating
    
    # 5. Honeypot checks (Appendix C)
    # Heuristic 1: Skill duration overflow
    h1_fire = False
    h1_severe = False
    for s in skills:
        dur = s.get("duration_months", 0)
        if dur > yoe * 12 + 6:
            h1_fire = True
        if dur > yoe * 12 + 12:
            h1_severe = True
            
    # Heuristic 2: Expert proficiency with 0 months
    h2_fire = any(s.get("proficiency") == "expert" and s.get("duration_months") == 0 for s in skills)
    
    # Heuristic 3: Career duration sum overflow
    h3_fire = total_months > yoe * 12 + 12
    
    # Heuristic 4: Overlapping current roles or overlapping date ranges
    current_roles_count = sum(1 for job in career_history if job.get("is_current"))
    h4_fire = current_roles_count > 1
    
    # Overlapping dates check
    if not h4_fire and len(career_history) > 1:
        # Parse dates and sort chronologically
        jobs_dates = []
        for job in career_history:
            start = parse_date(job.get("start_date"))
            end = parse_date(job.get("end_date"))
            if not end and job.get("is_current"):
                end = datetime.now()  # treat as today
            if start and end:
                jobs_dates.append((start, end))
        jobs_dates.sort(key=lambda x: x[0])
        # Check overlaps
        for i in range(len(jobs_dates) - 1):
            if jobs_dates[i][1] > jobs_dates[i+1][0]:
                h4_fire = True
                break
                
    # Honeypot severity rule
    honeypot_flag = False
    if h2_fire or h3_fire or h4_fire:
        honeypot_flag = True
    elif h1_fire and h1_severe and (h2_fire or h3_fire or h4_fire):
        honeypot_flag = True
    # Wait, let's keep it strictly per PRD:
    # "honeypot_flag = True only if (heuristic 2 or 3 or 4 fire) OR (heuristic 1 fires AND the overflow exceeds 12 months AND at least one other heuristic also fires)"
    # Wait, if any of h2, h3, or h4 fire, it's a honeypot.
    # What if only h1 fires? Then it's NOT a honeypot (just noise).
    # So the logic is:
    # is_honeypot = h2_fire or h3_fire or h4_fire or (h1_fire and h1_severe and (h2_fire or h3_fire or h4_fire))
    # This reduces simply to: is_honeypot = h2_fire or h3_fire or h4_fire.
    # Yes! That matches the severity rule exactly! Because if none of h2, h3, or h4 fire, the second part of the OR cannot be true anyway (since it requires "at least one other heuristic also fires").
    # So honeypot_flag = h2_fire or h3_fire or h4_fire is mathematically identical!
    
    # Disqualification Reasons
    eligible = True
    exclusion_reason = None
    
    # Apply hard filters (excluding consulting_only here, which is handled at scoring time per Appendix B)
    if honeypot_flag:
        eligible = False
        exclusion_reason = "Flagged Honeypot"
    elif is_research:
        eligible = False
        exclusion_reason = "Pure Research without Production"
    elif is_cv_without_nlp:
        eligible = False
        exclusion_reason = "CV/Speech/Robotics without NLP/IR exposure"
    elif is_chaser:
        eligible = False
        exclusion_reason = "Title Chaser"
        
    return eligible, honeypot_flag, exclusion_reason, consulting_only, title_tier

def process_candidates(input_path, output_path):
    print(f"Reading candidates from {input_path}...")
    results = []
    
    with open(input_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            
            candidate = json.loads(line)
            cid = candidate["candidate_id"]
            
            eligible, honeypot_flag, exclusion_reason, consulting_only, title_tier = check_candidate_filters(candidate)
            
            results.append({
                "candidate_id": cid,
                "eligible": eligible,
                "honeypot_flag": honeypot_flag,
                "exclusion_reason": exclusion_reason,
                "consulting_only": consulting_only,
                "title_tier": title_tier
            })
            
            if len(results) % 20000 == 0:
                print(f"Filtered {len(results)} candidates...")
                
    df = pd.DataFrame(results)
    
    # Verify outputs
    honeypot_count = df["honeypot_flag"].sum()
    ineligible_count = (~df["eligible"]).sum()
    print(f"Analysis complete. Total: {len(df)}, Eligible: {len(df) - ineligible_count}, Honeypots flagged: {honeypot_count}")
    
    # Save as parquet
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"Saved results to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Layer 1 filters and honeypot detection")
    parser.add_argument("--input", required=True, help="Path to input candidates.jsonl file")
    parser.add_argument("--output", required=True, help="Path to output parquet file")
    args = parser.parse_args()
    
    process_candidates(args.input, args.output)
