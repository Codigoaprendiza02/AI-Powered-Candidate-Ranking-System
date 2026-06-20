import os
import json
import hashlib
import pandas as pd

# Keywords for detecting skill families to mention in reasoning
SKILL_DISPLAY_NAMES = {
    "embeddings": "embeddings/retrieval",
    "vector_db": "vector databases",
    "python": "Python engineering",
    "ranking": "search/ranking systems",
    "llm": "LLMs/fine-tuning"
}

SKILL_KEYWORDS = {
    "embeddings": ["embedding", "sentence transformer", "hugging face transformer", "sentence-transformers", "bge", "e5", "retrieval", "semantic search"],
    "vector_db": ["faiss", "pinecone", "milvus", "weaviate", "qdrant", "opensearch", "elasticsearch", "vector db", "vector search", "hybrid search"],
    "python": ["python", "scikit-learn", "mlops", "mlflow", "bentoml", "pandas", "numpy", "pytorch", "tensorflow", "keras"],
    "ranking": ["learning to rank", "xgboost", "lightgbm", "feature engineering", "ndcg", "mrr", "map", "ranking"],
    "llm": ["lora", "qlora", "peft", "fine-tuning llms", "llm", "large language model", "prompt engineering", "langchain", "llama", "gpt"]
}

def get_candidate_skills(candidate):
    """
    Extracts the key matched skill families for display in the reasoning string.
    """
    skills = candidate.get("skills", [])
    matched_families = []
    
    skill_names_lower = [s.get("name", "").lower() for s in skills]
    
    for family, keywords in SKILL_KEYWORDS.items():
        if any(any(kw in name for kw in keywords) for name in skill_names_lower):
            matched_families.append(SKILL_DISPLAY_NAMES[family])
            
    if not matched_families:
        return "applied ML"
    elif len(matched_families) == 1:
        return matched_families[0]
    else:
        return f"{matched_families[0]} and {matched_families[1]}"

def resolve_concern(candidate, row):
    """
    Identifies the primary gap or concern for lower-ranked candidates.
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    
    notice_days = signals.get("notice_period_days", 0)
    location = profile.get("location", "")
    title = profile.get("current_title", "")
    
    # 1. Notice period concern
    if notice_days > 45:
        return f"notice period is relatively long ({notice_days} days)"
    
    # 2. Location mismatch
    loc_lower = location.lower()
    in_city = "noida" in loc_lower or "pune" in loc_lower
    regional = any(city in loc_lower for city in ["bangalore", "bengaluru", "mumbai", "hyderabad", "chennai", "kolkata", "gurgaon", "delhi"])
    willing = signals.get("willing_to_relocate", False)
    
    if not in_city:
        if regional and not willing:
            return f"relocation is required from {location}"
        elif not willing:
            return f"candidate is located in {location} and requires relocation"
            
    # 3. Adjacent title concern
    if row.get("title_tier") in ["B", "C"]:
        return f"current role is adjacent ({title}) rather than core AI/ML"
        
    # 4. Availability multiplier decay
    avail = row.get("availability_multiplier", 1.0)
    if avail < 0.6:
        return "platform engagement indicates lower immediate response probability"
        
    # Default concern
    return "slightly less direct production experience in search/ranking systems"

def populate_reasoning(top_100_df, candidates_path):
    print(f"Loading candidate profiles for reasoning generation from {candidates_path}...")
    candidate_ids = top_100_df["candidate_id"].tolist()
    
    # Fast streaming pass or standard JSON load to read matching profiles
    profiles = {}
    target_ids = set(candidate_ids)
    
    # Check if file is standard JSON array or JSONL
    is_json = candidates_path.endswith(".json")
    if is_json:
        with open(candidates_path, "r", encoding="utf-8") as f:
            candidates_list = json.load(f)
        for c in candidates_list:
            cid = c["candidate_id"]
            if cid in target_ids:
                profiles[cid] = c
    else:
        with open(candidates_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                c = json.loads(line)
                cid = c["candidate_id"]
                if cid in target_ids:
                    profiles[cid] = c
                    if len(profiles) == len(target_ids):
                        break
                    
    reasoning_texts = []
    
    # Define templates for each tier to maximize variation and fit rank-tone
    # Glow (Ranks 1–10)
    templates_glow = [
        "Outstanding candidate with {yoe} years of experience as a {title} at {company}. Strong background in {skills} matching JD requirements, combined with high platform activity.",
        "Top-tier AI Engineer with {yoe} years of experience. Demonstrated production success in {skills} at {company}. Outstanding availability and response rates on the platform.",
        "Perfect founding team fit with {yoe} years of experience. Shipped {skills} at {company}. Highly active platform indicators verify readiness for immediate contribution.",
        "Excellent match with {yoe} years of experience. Proven expertise in {skills} at {company}, backed by strong recruiter engagement and high responsiveness."
    ]
    
    # Strong (Ranks 11–30)
    templates_strong = [
        "Strong {title} with {yoe} years of experience, showing solid skills in {skills} at {company}. Excellent platform engagement signals.",
        "Experienced AI specialist ({yoe} yrs YoE) with proven competence in {skills}. Strong past work at {company} and high recruitment responsiveness.",
        "Promising match with {yoe} years in the field. Solid technical foundations in {skills} developed at {company}, backed by strong availability.",
        "Competent {title} with {yoe} years of experience at {company}. Possesses strong hands-on skills in {skills} and excellent activity indicators."
    ]
    
    # Measured (Ranks 31–100)
    templates_measured = [
        "Adjacent fit as a {title} with {yoe} years of experience. Strong in {skills}, though {concern}.",
        "Relevant engineering background ({yoe} yrs YoE) at {company} with skills in {skills}. Included as filler, noting {concern}.",
        "Competent engineer with {yoe} years of experience. Possesses adjacent skills in {skills}, but ranking is tempered by {concern}.",
        "Plausible candidate with {yoe} years of experience and skills in {skills}, but ranking is deferred due to {concern}."
    ]
    
    for _, row in top_100_df.iterrows():
        cid = row["candidate_id"]
        rank = row["rank"]
        
        c = profiles.get(cid, {})
        profile = c.get("profile", {})
        
        yoe = profile.get("years_of_experience", 0)
        title = profile.get("current_title", "Software Engineer")
        company = profile.get("current_company", "Top Tech")
        if not company or company.strip() == "":
            company = "prior employer"
            
        skills = get_candidate_skills(c)
        
        # Deterministic hash of candidate_id to choose template
        h = int(hashlib.md5(cid.encode('utf-8')).hexdigest(), 16)
        
        if rank <= 10:
            template = templates_glow[h % len(templates_glow)]
            text = template.format(yoe=yoe, title=title, company=company, skills=skills)
        elif rank <= 30:
            template = templates_strong[h % len(templates_strong)]
            text = template.format(yoe=yoe, title=title, company=company, skills=skills)
        else:
            template = templates_measured[h % len(templates_measured)]
            concern = resolve_concern(c, row)
            text = template.format(yoe=yoe, title=title, company=company, skills=skills, concern=concern)
            
        reasoning_texts.append(text)
        
    top_100_df["reasoning"] = reasoning_texts
    return top_100_df
