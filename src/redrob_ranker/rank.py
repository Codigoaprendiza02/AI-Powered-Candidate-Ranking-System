import os
import time
import argparse
import pandas as pd
from src.redrob_ranker.filters import process_candidates
from src.redrob_ranker.features import process_features
from src.redrob_ranker.retrieval import compute_retrieval_scores
from src.redrob_ranker.scoring import score_and_rank
from src.redrob_ranker.reasoning import populate_reasoning

def run_pipeline(candidates_path, out_path, config_path, artifacts_dir, jd_path):
    overall_start = time.time()
    
    # Define intermediate paths
    flags_path = os.path.join(artifacts_dir, "flags.parquet")
    features_path = os.path.join(artifacts_dir, "features.parquet")
    retrieval_path = os.path.join(artifacts_dir, "retrieval.parquet")
    
    # 1. Run Layer 1: Filters & Honeypots
    print("\n--- PHASE 2: RUNNING HARD FILTERS & HONEYPOT DETECTION ---")
    start = time.time()
    process_candidates(candidates_path, flags_path)
    print(f"Phase 2 completed in {time.time() - start:.2f} seconds.")
    
    # 2. Run Layer 3/4: Feature Engineering
    print("\n--- PHASE 3: RUNNING FEATURE ENGINEERING ---")
    start = time.time()
    process_features(flags_path, candidates_path, config_path, features_path)
    print(f"Phase 3 completed in {time.time() - start:.2f} seconds.")
    
    # 3. Run Layer 2: Hybrid Retrieval
    print("\n--- PHASE 4: RUNNING HYBRID RETRIEVAL ---")
    start = time.time()
    retrieval_df = compute_retrieval_scores(
        artifacts_dir=artifacts_dir,
        jd_path=jd_path,
        config_path=config_path,
        features_path=features_path
    )
    retrieval_df.to_parquet(retrieval_path, index=False)
    print(f"Phase 4 completed in {time.time() - start:.2f} seconds.")
    
    # 4. Run Layer 5: Composite Scoring & Ranking
    print("\n--- PHASE 5: RUNNING COMPOSITE SCORING & RANKING ---")
    start = time.time()
    top_100_df = score_and_rank(
        flags_path=flags_path,
        features_path=features_path,
        retrieval_path=retrieval_path,
        config_path=config_path,
        output_dir=artifacts_dir
    )
    print(f"Phase 5 completed in {time.time() - start:.2f} seconds.")
    
    # 5. Run Layer 6: Reasoning Generation
    print("\n--- PHASE 6: RUNNING REASONING GENERATION ---")
    start = time.time()
    final_df = populate_reasoning(top_100_df, candidates_path)
    print(f"Phase 6 completed in {time.time() - start:.2f} seconds.")
    
    # 6. Save final output CSV
    print("\nSaving final CSV submission file...")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Keep only the requested columns in correct order
    submission_df = final_df[["candidate_id", "rank", "score", "reasoning"]].copy()
    submission_df.to_csv(out_path, index=False, encoding="utf-8")
    
    overall_elapsed = time.time() - overall_start
    print(f"\nPipeline successfully completed! Total elapsed time: {overall_elapsed:.2f} seconds.")
    print(f"Submission saved to: {out_path}")

def main():
    parser = argparse.ArgumentParser(description="AI-Powered Candidate Ranking unified ranking runner")
    parser.add_argument("--candidates", default="data/candidates.jsonl", help="Path to input candidates.jsonl")
    parser.add_argument("--out", default="outputs/team_xxx.csv", help="Path to output team_xxx.csv submission file")
    parser.add_argument("--config", default="config/weights.yaml", help="Path to configuration weights.yaml")
    parser.add_argument("--artifacts-dir", default="artifacts", help="Directory containing/storing intermediate artifacts")
    parser.add_argument("--jd", default="data/job_description.md", help="Path to job_description.md")
    
    args = parser.parse_args()
    
    run_pipeline(
        candidates_path=args.candidates,
        out_path=args.out,
        config_path=args.config,
        artifacts_dir=args.artifacts_dir,
        jd_path=args.jd
    )

if __name__ == "__main__":
    main()
