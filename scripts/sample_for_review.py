import os
import json
import pandas as pd

CANDIDATES_PATH = "data/candidates.jsonl"
FLAGS_PATH = "artifacts/flags.parquet"
OUTPUT_PATH = "reports/phase2_human_review.md"

def load_candidates():
    candidates = {}
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            c = json.loads(line)
            candidates[c["candidate_id"]] = c
    return candidates

def generate_review_report():
    print("Loading flags and candidate details for review...")
    df = pd.read_parquet(FLAGS_PATH)
    candidates = load_candidates()
    
    # 1. Sample 20 flagged honeypots
    honeypots = df[df["honeypot_flag"] == True].head(20)
    
    # 2. Sample 3 candidates for each exclusion reason
    # Reasons: Flagged Honeypot, Pure Research without Production, CV/Speech/Robotics without NLP/IR exposure, Title Chaser
    reasons = df[df["eligible"] == False]["exclusion_reason"].unique()
    excluded_samples = {}
    for reason in reasons:
        if reason:
            excluded_samples[reason] = df[df["exclusion_reason"] == reason].head(3)
            
    # 3. Pull 10 random candidates with generic non-tech titles (tier D) but descriptions mention ML/search
    ml_keywords = ["machine learning", "ml", "nlp", "search", "ranking", "embedding", "vector search", "recommendation"]
    generic_ml_candidates = []
    
    # Search candidates matching conditions
    for cid, c in candidates.items():
        title = c["profile"].get("current_title", "")
        # Check if in Tier D
        from src.redrob_ranker.taxonomy import TITLE_TAXO
        tier = TITLE_TAXO.get(title, "D")
        if tier == "D":
            # Check if career history mentions ML/search keywords
            career_desc = " ".join(job.get("description", "").lower() for job in c["career_history"])
            if any(kw in career_desc for kw in ml_keywords):
                # Check eligibility
                flag_row = df[df["candidate_id"] == cid]
                if not flag_row.empty and flag_row.iloc[0]["eligible"]:
                    generic_ml_candidates.append(c)
                    if len(generic_ml_candidates) >= 10:
                        break
                        
    # Write report
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("# Phase 2 Human Review: Hard Filters & Honeypot Audit\n\n")
        f.write("This document summarizes the sampled candidates for manual audit, verifying the correctness of Layer 1 hard filters and honeypot detection rules.\n\n")
        
        f.write("## Section 1: Flagged Honeypot Audit (20 Samples)\n\n")
        f.write("These candidates are flagged as honeypots based on impossible profile properties:\n\n")
        for i, row in enumerate(honeypots.itertuples()):
            c = candidates[row.candidate_id]
            f.write(f"### {i+1}. Candidate: `{row.candidate_id}`\n")
            f.write(f"- **Name**: {c['profile']['anonymized_name']}\n")
            f.write(f"- **Current Title**: {c['profile']['current_title']}\n")
            f.write(f"- **Years of Experience**: {c['profile']['years_of_experience']}\n")
            f.write(f"- **Total Career Duration (Months)**: {sum(job.get('duration_months', 0) for job in c['career_history'])}\n")
            
            # Print matching anomalies
            f.write("- **Anomalous Heuristics**:\n")
            skills_overflow = [s for s in c["skills"] if s.get("duration_months", 0) > c["profile"]["years_of_experience"] * 12 + 6]
            if skills_overflow:
                f.write(f"  - Skill overflow: {len(skills_overflow)} skill(s) exceed YoE (e.g., {skills_overflow[0]['name']}: {skills_overflow[0]['duration_months']} months against {c['profile']['years_of_experience']} YoE)\n")
            expert_zero = [s for s in c["skills"] if s.get("proficiency") == "expert" and s.get("duration_months") == 0]
            if expert_zero:
                f.write(f"  - Expert with 0 months: {', '.join(s['name'] for s in expert_zero)}\n")
            career_overflow = sum(job.get("duration_months", 0) for job in c["career_history"]) > c["profile"]["years_of_experience"] * 12 + 12
            if career_overflow:
                f.write(f"  - Career duration overflow: sum of jobs = {sum(job.get('duration_months', 0) for job in c['career_history'])} months against {c['profile']['years_of_experience']} YoE\n")
            current_roles = sum(1 for job in c["career_history"] if job.get("is_current"))
            if current_roles > 1:
                f.write(f"  - Overlapping current roles: {current_roles} current roles found\n")
            f.write("\n")
            
        f.write("---\n\n")
        f.write("## Section 2: Excluded Candidates Audit\n\n")
        f.write("Samples for each hard filter exclusion type to confirm that valid matches are not over-excluded:\n\n")
        
        for reason, samples in excluded_samples.items():
            f.write(f"### Exclusion Type: `{reason}`\n\n")
            for i, row in enumerate(samples.itertuples()):
                c = candidates[row.candidate_id]
                f.write(f"#### {i+1}. `{row.candidate_id}` — {c['profile']['current_title']}\n")
                f.write(f"- **Industry**: {c['profile']['current_industry']} | **Company**: {c['profile']['current_company']} | **YoE**: {c['profile']['years_of_experience']}\n")
                f.write("- **Skills**: " + ", ".join(s.get("name", "") for s in c["skills"][:10]) + "\n")
                f.write(f"- **Snippet**: {c['profile']['summary'][:200]}...\n\n")
            f.write("---\n\n")
            
        f.write("## Section 3: Generic Non-Tech with ML/Search Exposure (10 Samples)\n\n")
        f.write("These candidates hold generic non-tech titles (Tier D, e.g. HR Manager) but mention AI/ML keywords in their career descriptions. We confirm that Layer 1 **retains** them (`eligible == True`) so that the Layer 2 hybrid search can evaluate them:\n\n")
        
        for i, c in enumerate(generic_ml_candidates):
            f.write(f"### {i+1}. Candidate: `{c['candidate_id']}`\n")
            f.write(f"- **Current Title**: {c['profile']['current_title']} | **Company**: {c['profile']['current_company']}\n")
            # Extract ML sentence
            career_desc = ""
            for job in c["career_history"]:
                desc = job.get("description", "")
                for kw in ml_keywords:
                    if kw in desc.lower():
                        sentences = desc.split(".")
                        for s in sentences:
                            if kw in s.lower():
                                career_desc += f"  - *{job.get('company')}*: ...{s.strip()}...\n"
                                break
            f.write(f"- **Mentions of ML**:\n{career_desc}\n")
            f.write("\n")
            
    print(f"Generated review report: {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_review_report()
