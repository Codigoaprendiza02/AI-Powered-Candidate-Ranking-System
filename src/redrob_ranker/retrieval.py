import os
import re
import argparse
import pickle
import yaml
import hashlib
import numpy as np
import pandas as pd

def tokenize(text):
    """
    Alphanumeric lower-case tokenization for BM25.
    Must match the tokenization used during indexing.
    """
    if not text:
        return []
    return [w for w in re.findall(r'[a-zA-Z0-9]+', text.lower()) if w]

def min_max_normalize(scores):
    """
    Min-max normalize a numpy array of scores to [0.0, 1.0].
    Handles zero division gracefully.
    """
    min_val = np.min(scores)
    max_val = np.max(scores)
    denom = max_val - min_val
    if denom < 1e-8:
        return np.zeros_like(scores)
    return (scores - min_val) / denom

def compute_retrieval_scores(artifacts_dir, jd_path, config_path, features_path):
    """
    Computes lexical and dense retrieval scores, normalizes, and combines them.
    Filters output to only candidates in features_path.
    """
    # 1. Load precomputed artifacts
    ids_path = os.path.join(artifacts_dir, "candidate_ids.pkl")
    embeddings_path = os.path.join(artifacts_dir, "embeddings.npy")
    jd_embedding_path = os.path.join(artifacts_dir, "jd_embedding.npy")
    bm25_path = os.path.join(artifacts_dir, "bm25_index.pkl")

    print("Loading precomputed artifacts...")
    with open(ids_path, "rb") as f:
        candidate_ids = pickle.load(f)
    
    embeddings = np.load(embeddings_path, mmap_mode="r")
    jd_embedding = np.load(jd_embedding_path)

    # 2. Load Config retrieval weights
    print(f"Loading retrieval configuration from {config_path}...")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Get alpha parameter
    retrieval_cfg = config.get("retrieval", {})
    alpha = retrieval_cfg.get("alpha", 0.4)
    print(f"Retrieval alpha resolved: {alpha} (BM25 weight: {alpha}, Dense weight: {1.0 - alpha})")

    # 3. Dense Embeddings Cosine Similarity
    print("Computing dense vector cosine similarity (matrix-vector dot product)...")
    # Vectors are pre-normalized, so dot product is exactly cosine similarity
    dense_scores = embeddings @ jd_embedding

    # 4. BM25 Lexical Score
    print(f"Loading and tokenizing job description from {jd_path}...")
    with open(jd_path, "r", encoding="utf-8") as f:
        jd_text = f.read()
    
    # Check if we can use precomputed BM25 scores
    current_hash = hashlib.md5(jd_text.encode('utf-8')).hexdigest()
    hash_path = os.path.join(artifacts_dir, "jd_text_hash.txt")
    bm25_scores_path = os.path.join(artifacts_dir, "bm25_scores.npy")
    
    use_precomputed = False
    if os.path.exists(hash_path) and os.path.exists(bm25_scores_path):
        with open(hash_path, "r", encoding="utf-8") as f:
            saved_hash = f.read().strip()
        if current_hash == saved_hash:
            use_precomputed = True
            
    if use_precomputed:
        print("Loading precomputed BM25 scores (fast path)...")
        bm25_scores = np.load(bm25_scores_path)
    else:
        print("Job Description changed or precomputed scores missing. Computing BM25 scores dynamically...")
        with open(bm25_path, "rb") as f:
            bm25_index = pickle.load(f)
        jd_tokens = tokenize(jd_text)
        bm25_scores = np.array(bm25_index.get_scores(jd_tokens))

    # 5. Normalize and combine
    print("Applying Min-Max normalization...")
    dense_norm = min_max_normalize(dense_scores)
    bm25_norm = min_max_normalize(bm25_scores)
    
    print("Combining retrieval scores...")
    semantic_scores = alpha * bm25_norm + (1.0 - alpha) * dense_norm

    # 6. Build retrieval dataframe and filter to eligible candidates
    all_df = pd.DataFrame({
        "candidate_id": candidate_ids,
        "semantic_score": semantic_scores
    })

    print(f"Loading eligible candidates list from {features_path}...")
    features_df = pd.read_parquet(features_path, columns=["candidate_id"])
    
    print(f"Filtering to {len(features_df)} eligible candidates using merge...")
    retrieval_df = pd.merge(all_df, features_df, on="candidate_id", how="inner")
    
    return retrieval_df

def main():
    parser = argparse.ArgumentParser(description="Layer 2 candidate retrieval and similarity scoring")
    parser.add_argument("--features", required=True, help="Path to features.parquet file (defines eligible pool)")
    parser.add_argument("--artifacts-dir", required=True, help="Directory containing precomputed embeddings and indices")
    parser.add_argument("--jd", default="data/job_description.md", help="Path to job_description.md file")
    parser.add_argument("--config", default="config/weights.yaml", help="Path to weights.yaml configuration file")
    parser.add_argument("--output", required=True, help="Path to output parquet file")
    args = parser.parse_args()

    df = compute_retrieval_scores(
        artifacts_dir=args.artifacts_dir,
        jd_path=args.jd,
        config_path=args.config,
        features_path=args.features
    )

    print("\nRetrieval Scoring Summary Statistics:")
    print(df["semantic_score"].describe())

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    df.to_parquet(args.output, index=False)
    print(f"Saved retrieval scores to {args.output}")

if __name__ == "__main__":
    main()
