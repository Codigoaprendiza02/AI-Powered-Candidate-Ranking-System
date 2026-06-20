import json
import pandas as pd

RETRIEVAL_PATH = "artifacts/retrieval.parquet"
CANDIDATES_PATH = "data/candidates.jsonl"

def main():
    print("Loading retrieval scores...")
    ret_df = pd.read_parquet(RETRIEVAL_PATH)
    
    # Sort descending
    top_20 = ret_df.sort_values(by="semantic_score", ascending=False).head(20)
    top_20_ids = set(top_20["candidate_id"])
    top_20_scores = dict(zip(top_20["candidate_id"], top_20["semantic_score"]))

    print("\nMatching top 20 candidates with candidate profiles...")
    profiles = {}
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            c = json.loads(line)
            cid = c["candidate_id"]
            if cid in top_20_ids:
                profiles[cid] = c

    print("\n=================================================================================")
    print("TOP 20 SEMANTIC MATCHES")
    print("=================================================================================")
    
    # Order top_20 by score descending
    top_20_sorted = top_20.sort_values(by="semantic_score", ascending=False)
    for idx, row in top_20_sorted.iterrows():
        cid = row["candidate_id"]
        score = row["semantic_score"]
        c = profiles.get(cid, {})
        prof = c.get("profile", {})
        
        print(f"Rank {idx+1} | ID: {cid} | Score: {score:.4f}")
        print(f"  Title:    {prof.get('current_title')}")
        print(f"  Headline: {prof.get('headline')}")
        print(f"  Summary:  {prof.get('summary')}")
        print("-" * 80)

    # 3. Check for Tier-5 matches (Generic titles like "Senior Software Engineer" but high semantic scores)
    print("\n=================================================================================")
    print("TIER 5 SANITY CHECK: Generic titles with high semantic scores")
    print("=================================================================================")
    
    generic_titles = ["Senior Software Engineer", "Backend Engineer", "Software Engineer", "Senior Developer"]
    tier5_candidates = []
    
    # Sort all by semantic score descending
    all_sorted = ret_df.sort_values(by="semantic_score", ascending=False)
    
    # Find candidates with generic titles in top 500
    top_500_ids = set(all_sorted.head(500)["candidate_id"])
    
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            c = json.loads(line)
            cid = c["candidate_id"]
            if cid in top_500_ids:
                title = c.get("profile", {}).get("current_title")
                if title in generic_titles:
                    score = float(all_sorted[all_sorted["candidate_id"] == cid]["semantic_score"].iloc[0])
                    tier5_candidates.append((cid, title, c.get("profile", {}).get("headline"), score, c))
                    if len(tier5_candidates) >= 5:
                        break

    for cid, title, headline, score, c in tier5_candidates:
        print(f"ID: {cid} | Title: {title} | Score: {score:.4f}")
        print(f"  Headline: {headline}")
        # print first job history description
        history = c.get("career_history", [])
        if history:
            print(f"  Latest Job Desc: {history[0].get('description', '')[:120]}...")
        print("-" * 80)

if __name__ == "__main__":
    main()
