import os
import re
import sys
import argparse
import json
import pickle
import subprocess
import hashlib
import numpy as np
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

def extract_bm25_text(candidate):
    """
    Concatenate profile headline, summary, and career history titles/descriptions.
    Retains full text for maximum detail in BM25 lexical matching.
    """
    profile = candidate.get("profile", {})
    headline = profile.get("headline") or ""
    summary = profile.get("summary") or ""
    
    parts = []
    if headline:
        parts.append(headline)
    if summary:
        parts.append(summary)
        
    for job in candidate.get("career_history", []):
        title = job.get("title") or ""
        desc = job.get("description") or ""
        part = f"{title} {desc}".strip()
        if part:
            parts.append(part)
            
    return " ".join(parts).strip()

def extract_dense_text(candidate):
    """
    Concatenate profile headline, summary, and career history titles/descriptions.
    Truncates job descriptions to 150 characters to keep overall text length short
    for faster sentence-transformer encoding, while still representing the entire career history.
    """
    profile = candidate.get("profile", {})
    headline = profile.get("headline") or ""
    summary = profile.get("summary") or ""
    
    parts = []
    if headline:
        parts.append(headline)
    if summary:
        parts.append(summary)
        
    for job in candidate.get("career_history", []):
        title = job.get("title") or ""
        desc = job.get("description") or ""
        if len(desc) > 150:
            desc = desc[:150]
        part = f"{title} {desc}".strip()
        if part:
            parts.append(part)
            
    return " ".join(parts).strip()

def tokenize(text):
    """
    Alphanumeric lower-case tokenization for BM25.
    """
    if not text:
        return []
    return [w for w in re.findall(r'[a-zA-Z0-9]+', text.lower()) if w]

def run_shard(args):
    """
    Child process execution to encode a single shard of candidates.
    Runs completely independently to avoid IPC/queue deadlocks on Windows.
    """
    import torch
    # Cap PyTorch CPU threads per shard process to avoid thread thrashing/contention
    torch.set_num_threads(2)

    # 1. Determine shard boundary
    print(f"[Shard {args.shard_id}] Counting total candidates...")
    with open(args.input, "r", encoding="utf-8") as f:
        total_candidates = sum(1 for line in f if line.strip())

    shard_size = int(np.ceil(total_candidates / args.num_shards))
    start_idx = args.shard_id * shard_size
    end_idx = min(start_idx + shard_size, total_candidates)

    print(f"[Shard {args.shard_id}] Reading candidate lines {start_idx} to {end_idx}...")
    dense_corpus = []
    
    with open(args.input, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            if idx < start_idx:
                continue
            if idx >= end_idx:
                break
            c = json.loads(line)
            dense_corpus.append(extract_dense_text(c))

    print(f"[Shard {args.shard_id}] Loaded {len(dense_corpus)} candidates. Loading model...")
    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

    print(f"[Shard {args.shard_id}] Encoding embeddings...")
    embeddings = model.encode(
        dense_corpus,
        batch_size=128,
        show_progress_bar=False,
        normalize_embeddings=True
    )

    shard_path = os.path.join(args.output_dir, f"embeddings_shard_{args.shard_id}.npy")
    print(f"[Shard {args.shard_id}] Saving shard embeddings of shape {embeddings.shape} to {shard_path}...")
    np.save(shard_path, embeddings.astype(np.float32))
    print(f"[Shard {args.shard_id}] Completed successfully!")

def run_parent(args):
    """
    Parent process execution to build BM25, spawn shards, and merge results.
    """
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Reading candidates from {args.input}...")
    bm25_corpus = []
    candidate_ids = []
    
    with open(args.input, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            c = json.loads(line)
            candidate_ids.append(c["candidate_id"])
            bm25_corpus.append(extract_bm25_text(c))
            
            if (idx + 1) % 20000 == 0:
                print(f"Processed {idx + 1} candidates...")

    print(f"Loaded {len(candidate_ids)} candidates.")

    # 1. Build and save BM25 Index
    print("Tokenizing corpus for BM25...")
    tokenized_corpus = [tokenize(text) for text in bm25_corpus]
    
    print("Building BM25 Okapi index...")
    bm25 = BM25Okapi(tokenized_corpus)
    
    bm25_path = os.path.join(args.output_dir, "bm25_index.pkl")
    print(f"Saving BM25 index to {bm25_path}...")
    with open(bm25_path, "wb") as f:
        pickle.dump(bm25, f, protocol=pickle.HIGHEST_PROTOCOL)

    # Save candidate IDs list
    ids_path = os.path.join(args.output_dir, "candidate_ids.pkl")
    print(f"Saving candidate IDs list to {ids_path}...")
    with open(ids_path, "wb") as f:
        pickle.dump(candidate_ids, f, protocol=pickle.HIGHEST_PROTOCOL)

    # 2. Spawning Shard Subprocesses
    num_shards = 4
    print(f"Spawning {num_shards} parallel shard encoding processes...")
    processes = []
    for s_id in range(num_shards):
        cmd = [
            sys.executable,
            __file__,
            "--input", args.input,
            "--jd", args.jd,
            "--output-dir", args.output_dir,
            "--shard-id", str(s_id),
            "--num-shards", str(num_shards)
        ]
        print(f"Starting shard subprocess: {' '.join(cmd)}")
        p = subprocess.Popen(cmd)
        processes.append(p)

    print("Waiting for all shard processes to complete...")
    for idx, p in enumerate(processes):
        exit_code = p.wait()
        if exit_code != 0:
            print(f"Error: Shard process {idx} failed with exit code {exit_code}")
            sys.exit(exit_code)
        print(f"Shard process {idx} finished successfully.")

    # 3. Merge Shard Embeddings
    print("Merging shard embeddings...")
    embeddings_list = []
    for s_id in range(num_shards):
        shard_path = os.path.join(args.output_dir, f"embeddings_shard_{s_id}.npy")
        embeddings_list.append(np.load(shard_path))
        # Remove temporary shard file
        os.remove(shard_path)
        
    embeddings = np.concatenate(embeddings_list, axis=0)
    
    embeddings_path = os.path.join(args.output_dir, "embeddings.npy")
    print(f"Saving final merged candidate embeddings of shape {embeddings.shape} to {embeddings_path}...")
    np.save(embeddings_path, embeddings.astype(np.float32))

    # 4. Encode Job Description
    print("Loading SentenceTransformer model to encode Job Description...")
    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    
    print(f"Reading Job Description from {args.jd}...")
    with open(args.jd, "r", encoding="utf-8") as f:
        jd_text = f.read()
        
    print("Encoding job description...")
    jd_embedding = model.encode(jd_text, normalize_embeddings=True)
    
    jd_path = os.path.join(args.output_dir, "jd_embedding.npy")
    print(f"Saving JD embedding of shape {jd_embedding.shape} to {jd_path}...")
    np.save(jd_path, jd_embedding.astype(np.float32))
    
    # 5. Precompute BM25 scores and JD hash
    print("Precomputing BM25 scores for the Job Description...")
    jd_tokens = tokenize(jd_text)
    bm25_scores = np.array(bm25.get_scores(jd_tokens), dtype=np.float32)
    bm25_scores_path = os.path.join(args.output_dir, "bm25_scores.npy")
    print(f"Saving precomputed BM25 scores to {bm25_scores_path}...")
    np.save(bm25_scores_path, bm25_scores)
    
    jd_hash = hashlib.md5(jd_text.encode('utf-8')).hexdigest()
    hash_path = os.path.join(args.output_dir, "jd_text_hash.txt")
    print(f"Saving Job Description MD5 hash to {hash_path}...")
    with open(hash_path, "w", encoding="utf-8") as f:
        f.write(jd_hash)
        
    print("Precomputation finished successfully!")

def main():
    parser = argparse.ArgumentParser(description="Precompute candidate embeddings and BM25 index offline.")
    parser.add_argument("--input", type=str, default="data/candidates.jsonl", help="Path to candidates.jsonl")
    parser.add_argument("--jd", type=str, default="data/job_description.md", help="Path to job_description.md")
    parser.add_argument("--output-dir", type=str, default="artifacts", help="Directory to save precomputed artifacts")
    
    # Internal arguments for parallel shards
    parser.add_argument("--shard-id", type=int, default=-1, help="Shard ID (internal use)")
    parser.add_argument("--num-shards", type=int, default=-1, help="Total number of shards (internal use)")
    
    args = parser.parse_args()

    if args.shard_id >= 0:
        run_shard(args)
    else:
        run_parent(args)

if __name__ == "__main__":
    main()
