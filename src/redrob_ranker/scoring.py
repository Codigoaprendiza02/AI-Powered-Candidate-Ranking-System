import os
import argparse
import yaml
import numpy as np
import pandas as pd

def score_and_rank(flags_path, features_path, retrieval_path, config_path, output_dir=None):
    # 1. Load Parquet files
    print(f"Loading flags from {flags_path}...")
    flags_df = pd.read_parquet(flags_path)
    
    print(f"Loading features from {features_path}...")
    features_df = pd.read_parquet(features_path)
    
    print(f"Loading retrieval scores from {retrieval_path}...")
    retrieval_df = pd.read_parquet(retrieval_path)
    
    # 2. Join dataframes on candidate_id
    df = flags_df.merge(features_df, on="candidate_id").merge(retrieval_df, on="candidate_id")
    
    # 3. Load config and get weights
    print(f"Loading weights from {config_path}...")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    comp_cfg = config.get("composite_weights", {})
    weight_semantic = comp_cfg.get("weight_semantic", 0.60)
    weight_structured = comp_cfg.get("weight_structured", 0.40)
    print(f"Composite weights: weight_semantic={weight_semantic}, weight_structured={weight_structured}")
    
    # 4. Apply consulting hard exclusion per Appendix B
    # "Only combine with hard exclusion if title_tier in {C, D} AND consulting_only == True AND semantic_score below the 50th percentile."
    semantic_median = df["semantic_score"].median()
    is_consulting_exclude = (df["title_tier"].isin(["C", "D"])) & (df["consulting_only"]) & (df["semantic_score"] < semantic_median)
    
    exclude_count = is_consulting_exclude.sum()
    if exclude_count > 0:
        print(f"Excluding {exclude_count} candidates under the Consulting-Only Tier C/D and low semantic score rule...")
        df.loc[is_consulting_exclude, "eligible"] = False
        # Update exclusion reason where updated
        df.loc[is_consulting_exclude & df["exclusion_reason"].isna(), "exclusion_reason"] = "Consulting-only in Tier C/D with low semantic score"
        
    # 5. Filter to eligible candidates
    eligible_df = df[df["eligible"] == True].copy()
    print(f"Total candidates: {len(df)}, Eligible candidates: {len(eligible_df)}")
    
    # 6. Normalize scores to [0.0, 1.0] over eligible pool
    sem_min = eligible_df["semantic_score"].min()
    sem_max = eligible_df["semantic_score"].max()
    sem_denom = sem_max - sem_min
    eligible_df["semantic_score_norm"] = (eligible_df["semantic_score"] - sem_min) / (sem_denom if sem_denom > 1e-8 else 1.0)
    
    struct_min = eligible_df["structured_score"].min()
    struct_max = eligible_df["structured_score"].max()
    struct_denom = struct_max - struct_min
    eligible_df["structured_score_norm"] = (eligible_df["structured_score"] - struct_min) / (struct_denom if struct_denom > 1e-8 else 1.0)
    
    # 7. Compute final composite score
    eligible_df["composite_score"] = (
        weight_semantic * eligible_df["semantic_score_norm"] +
        weight_structured * eligible_df["structured_score_norm"]
    ) * eligible_df["availability_multiplier"]
    
    # 8. Sort descending by score and tie-break by candidate_id ascending
    sorted_df = eligible_df.sort_values(by=["composite_score", "candidate_id"], ascending=[False, True]).copy()
    
    # 9. Extract top 100 and assign ranks
    top_100 = sorted_df.head(100).copy()
    top_100["rank"] = range(1, len(top_100) + 1)
    
    # 10. Round score to 3 decimals with epsilon adjustments to prevent equal score tie-breaker errors
    rounded_scores = []
    prev_score = None
    for _, row in top_100.iterrows():
        s_rounded = round(row["composite_score"], 3)
        if prev_score is not None:
            if s_rounded >= prev_score:
                s_rounded = round(prev_score - 0.001, 3)
        rounded_scores.append(s_rounded)
        prev_score = s_rounded
        
    top_100["score"] = rounded_scores
    
    # Check for honeypots in top 100
    honeypot_count = top_100["honeypot_flag"].sum()
    if honeypot_count > 0:
        print(f"WARNING: {honeypot_count} honeypots found in the top 100 candidates!")
    else:
        print("Honeypot check passed: 0 honeypots in top 100.")
        
    if output_dir:
        # Save intermediate scored df
        os.makedirs(output_dir, exist_ok=True)
        top_100.to_parquet(os.path.join(output_dir, "top_100_scores.parquet"), index=False)
        print(f"Saved top 100 scored candidates to parquet.")
        
    return top_100

def main():
    parser = argparse.ArgumentParser(description="Layer 5 final scoring and ranking engine")
    parser.add_argument("--flags", required=True, help="Path to flags.parquet")
    parser.add_argument("--features", required=True, help="Path to features.parquet")
    parser.add_argument("--retrieval", required=True, help="Path to retrieval.parquet")
    parser.add_argument("--config", default="config/weights.yaml", help="Path to weights.yaml")
    parser.add_argument("--output-dir", default="artifacts", help="Directory to save output parquet")
    args = parser.parse_args()
    
    score_and_rank(
        flags_path=args.flags,
        features_path=args.features,
        retrieval_path=args.retrieval,
        config_path=args.config,
        output_dir=args.output_dir
    )

if __name__ == "__main__":
    main()
