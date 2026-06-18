import os
import sys
import json
import time
import argparse
import jsonschema
import numpy as np

# Pinned lists per PRD Appendix A/B
CONSULTING_COMPANIES = {
    "TCS", "Infosys", "Wipro", "Accenture", "Cognizant", 
    "Capgemini", "Tech Mahindra", "Mindtree", "HCL"
}

ML_AI_TITLES = {
    "Recommendation Systems Engineer", "Search Engineer", "Senior AI Engineer", 
    "Lead AI Engineer", "Staff Machine Learning Engineer", "Senior Machine Learning Engineer", 
    "Senior NLP Engineer", "NLP Engineer", "Machine Learning Engineer", 
    "Applied ML Engineer", "ML Engineer", "Senior Applied Scientist", 
    "Senior Data Scientist", "AI Engineer", "Data Scientist", 
    "Senior Software Engineer (ML)", "Computer Vision Engineer", 
    "AI Research Engineer", "AI Specialist", "Junior ML Engineer"
}

def analyze_dataset(input_path, schema_path, output_path):
    print(f"Loading schema from {schema_path}...")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    # Pre-compile schema validator for speed
    validator = jsonschema.Draft7Validator(schema)
    
    print(f"Analyzing {input_path} in streaming mode...")
    start_time = time.time()
    
    total_candidates = 0
    candidate_ids = set()
    duplicate_ids_count = 0
    
    title_counts = {}
    company_counts = {}
    industry_counts = {}
    
    total_skills = 0
    
    consulting_only_count = 0
    ml_ai_title_count = 0
    
    # Heuristic counters
    heuristic_skill_overflow = 0
    heuristic_expert_zero_months = 0
    heuristic_career_overflow = 0
    
    # Store some signals for percentile calculation
    signals_data = {
        "profile_completeness_score": [],
        "recruiter_response_rate": [],
        "avg_response_time_hours": [],
        "connection_count": [],
        "endorsements_received": [],
        "notice_period_days": [],
        "github_activity_score": [],
        "search_appearance_30d": [],
        "saved_by_recruiters_30d": [],
        "interview_completion_rate": [],
        "offer_acceptance_rate": []
    }
    
    validation_failures = []
    
    with open(input_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError as e:
                validation_failures.append((idx + 1, None, f"JSON Decode Error: {e}"))
                continue
            
            total_candidates += 1
            
            # 1. Candidate ID and duplicates
            cid = candidate.get("candidate_id")
            if cid in candidate_ids:
                duplicate_ids_count += 1
            else:
                candidate_ids.add(cid)
            
            # 2. Schema validation
            errors = list(validator.iter_errors(candidate))
            if errors:
                err_msg = "; ".join([e.message for e in errors])
                validation_failures.append((idx + 1, cid, err_msg))
                continue
            
            profile = candidate["profile"]
            career_history = candidate["career_history"]
            skills = candidate["skills"]
            signals = candidate["redrob_signals"]
            
            # Current title, company, industry
            title = profile.get("current_title")
            company = profile.get("current_company")
            industry = profile.get("current_industry")
            
            title_counts[title] = title_counts.get(title, 0) + 1
            company_counts[company] = company_counts.get(company, 0) + 1
            industry_counts[industry] = industry_counts.get(industry, 0) + 1
            
            # Skills count
            total_skills += len(skills)
            
            # Consulting-only career check
            all_companies = {company}
            for job in career_history:
                all_companies.add(job.get("company"))
            
            # Strip whitespace and normalize case-insensitive check
            normalized_companies = {c.strip().upper() for c in all_companies if c}
            normalized_consulting = {c.upper() for c in CONSULTING_COMPANIES}
            
            if normalized_companies.issubset(normalized_consulting):
                consulting_only_count += 1
                
            # ML/AI title check
            if title in ML_AI_TITLES:
                ml_ai_title_count += 1
                
            # Heuristic checks
            yoe = profile.get("years_of_experience", 0)
            
            # Heuristic 1: skills[].duration_months > years_of_experience * 12 + 6 (6-month buffer)
            has_skill_overflow = False
            for s in skills:
                if s.get("duration_months", 0) > yoe * 12 + 6:
                    has_skill_overflow = True
                    break
            if has_skill_overflow:
                heuristic_skill_overflow += 1
                
            # Heuristic 2: expert-proficiency and duration_months == 0
            has_expert_zero = False
            for s in skills:
                if s.get("proficiency") == "expert" and s.get("duration_months") == 0:
                    has_expert_zero = True
                    break
            if has_expert_zero:
                heuristic_expert_zero_months += 1
                
            # Heuristic 3: sum(career_history[].duration_months) > years_of_experience * 12 + 12
            total_career_months = sum(job.get("duration_months", 0) for job in career_history)
            if total_career_months > yoe * 12 + 12:
                heuristic_career_overflow += 1
                
            # Save signal values for stats
            for sig_name in signals_data.keys():
                val = signals.get(sig_name)
                if val is not None:
                    # handle -1 values if appropriate, but keep them for raw statistics
                    signals_data[sig_name].append(val)
                    
            if total_candidates % 20000 == 0:
                print(f"Processed {total_candidates} candidates...")
                
    elapsed_time = time.time() - start_time
    print(f"Processed {total_candidates} candidates in {elapsed_time:.2f} seconds.")
    
    # Compute signals distributions
    signals_stats = {}
    for sig_name, vals in signals_data.items():
        if vals:
            arr = np.array(vals)
            signals_stats[sig_name] = {
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "mean": float(np.mean(arr)),
                "p25": float(np.percentile(arr, 25)),
                "p50": float(np.percentile(arr, 50)),
                "p75": float(np.percentile(arr, 75))
            }
            
    # Sort dictionaries by frequency descending
    sorted_titles = sorted(title_counts.items(), key=lambda x: x[1], reverse=True)
    sorted_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)
    sorted_industries = sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Write reports/eda_report.md
    print(f"Writing EDA report to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as rf:
        rf.write("# Exploratory Data Analysis & Schema Validation Report\n\n")
        rf.write(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        rf.write(f"Dataset processed: `{input_path}`\n")
        rf.write(f"Elapsed time: {elapsed_time:.2f} seconds\n\n")
        
        rf.write("## 1. Summary of Dataset Integrity\n\n")
        rf.write("| Metric | Value |\n")
        rf.write("|---|---|\n")
        rf.write(f"| Total candidates processed | {total_candidates:,} |\n")
        rf.write(f"| Unique candidate IDs | {len(candidate_ids):,} |\n")
        rf.write(f"| Duplicate candidate IDs | {duplicate_ids_count} |\n")
        rf.write(f"| Schema validation failures | {len(validation_failures)} |\n")
        rf.write(f"| Unique current titles | {len(title_counts)} |\n")
        rf.write(f"| Average skills per candidate | {total_skills / total_candidates:.2f} |\n")
        rf.write(f"| Candidates with consulting-only careers | {consulting_only_count:,} ({consulting_only_count / total_candidates * 100:.2f}%) |\n")
        rf.write(f"| Candidates in target ML/AI/Search/Ranking titles | {ml_ai_title_count:,} ({ml_ai_title_count / total_candidates * 100:.2f}%) |\n\n")
        
        if validation_failures:
            rf.write("### Schema Validation Failures (showing first 10)\n\n")
            rf.write("| Line | Candidate ID | Error Description |\n")
            rf.write("|---|---|---|\n")
            for line_no, cid, err in validation_failures[:10]:
                rf.write(f"| {line_no} | {cid or 'N/A'} | {err} |\n")
            rf.write("\n")
            
        rf.write("## 2. Honeypot & Internal Consistency Heuristics\n\n")
        rf.write("These heuristics match Section 1.1 of the PRD and identify potentially anomalous/adversarial candidate profiles:\n\n")
        rf.write("| Heuristic | Description | Count | Percentage |\n")
        rf.write("|---|---|---|---|\n")
        rf.write(f"| **1. Skill-duration overflow** | `skills[].duration_months > years_of_experience × 12` | {heuristic_skill_overflow:,} | {heuristic_skill_overflow / total_candidates * 100:.2f}% |\n")
        rf.write(f"| **2. Unverified expert** | `proficiency == \"expert\"` and `duration_months == 0` | {heuristic_expert_zero_months} | {heuristic_expert_zero_months / total_candidates * 100:.4f}% |\n")
        rf.write(f"| **3. Career-history overflow** | `sum(career_history.duration_months) > years_of_experience × 12 + 12` | {heuristic_career_overflow} | {heuristic_career_overflow / total_candidates * 100:.4f}% |\n\n")
        
        rf.write("## 3. Platform Signals Distribution (Redrob Signals)\n\n")
        rf.write("Descriptive statistics for numeric engagement metrics across the dataset:\n\n")
        rf.write("| Signal | Min | Max | Mean | 25% | Median (50%) | 75% |\n")
        rf.write("|---|---|---|---|---|---|---|\n")
        for sig_name, stats in sorted(signals_stats.items()):
            rf.write(f"| {sig_name} | {stats['min']:.2f} | {stats['max']:.2f} | {stats['mean']:.2f} | {stats['p25']:.2f} | {stats['p50']:.2f} | {stats['p75']:.2f} |\n")
        rf.write("\n")
        
        rf.write("## 4. Current Title Taxonomy\n\n")
        rf.write(f"Full taxonomy of all {len(title_counts)} unique `current_title` values:\n\n")
        rf.write("| Title | Count | Percentage |\n")
        rf.write("|---|---|---|\n")
        for title, count in sorted_titles:
            rf.write(f"| {title} | {count:,} | {count / total_candidates * 100:.3f}% |\n")
        rf.write("\n")
        
        rf.write("## 5. Top 30 Companies\n\n")
        rf.write("| Company | Count | Percentage |\n")
        rf.write("|---|---|---|\n")
        for comp, count in sorted_companies[:30]:
            rf.write(f"| {comp} | {count:,} | {count / total_candidates * 100:.2f}% |\n")
        rf.write("\n")
        
        rf.write("## 6. Top 30 Industries\n\n")
        rf.write("| Industry | Count | Percentage |\n")
        rf.write("|---|---|---|\n")
        for ind, count in sorted_industries[:30]:
            rf.write(f"| {ind} | {count:,} | {count / total_candidates * 100:.2f}% |\n")
        rf.write("\n")
        
    print("EDA analysis completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Streaming EDA and Schema Validation script")
    parser.add_argument("--input", required=True, help="Path to input candidates.jsonl file")
    parser.add_argument("--schema", required=True, help="Path to candidate_schema.json")
    parser.add_argument("--output", required=True, help="Path to output markdown report file")
    
    args = parser.parse_args()
    analyze_dataset(args.input, args.schema, args.output)
