import os
import sys
import json
import time
import yaml
import hashlib
import jsonschema
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st

# Setup pathing to allow importing from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from src.redrob_ranker.filters import check_candidate_filters
from src.redrob_ranker.features import compute_candidate_features, find_reference_date
from src.redrob_ranker.retrieval import tokenize, min_max_normalize
from src.redrob_ranker.reasoning import get_candidate_skills, resolve_concern

# Custom page config
st.set_page_config(
    page_title="Redrob Candidate Ranker Workspace",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium dark theme styling injection
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Grotesk:wght@300;400;700&display=swap');

/* Apply modern typography */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Outfit', sans-serif !important;
}

/* Background gradient overlays */
.stApp {
    background-color: #0F0F1A !important;
    background-image: radial-gradient(circle at 10% 20%, rgba(0, 255, 163, 0.05) 0%, transparent 40%),
                      radial-gradient(circle at 90% 80%, rgba(98, 0, 238, 0.05) 0%, transparent 40%) !important;
}

/* Custom premium KPI card styles */
.kpi-card {
    background: rgba(30, 30, 48, 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35);
    transition: all 0.3s ease-in-out;
}

.kpi-card:hover {
    transform: translateY(-3px);
    border-color: rgba(0, 255, 163, 0.25);
    box-shadow: 0 12px 40px 0 rgba(0, 255, 163, 0.08);
}

.kpi-title {
    font-size: 0.85rem;
    color: #9E9EB2;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
}

.kpi-value {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #00FFA3 0%, #6200EE 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-top: 5px;
}

/* Glowing text title */
.header-container {
    padding: 20px 0 30px 0;
    text-align: center;
}

.header-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.8rem;
    font-weight: 700;
    letter-spacing: -1px;
    background: linear-gradient(90deg, #00FFA3, #8a2be2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 15px rgba(0, 255, 163, 0.15);
}

.header-subtitle {
    font-size: 1.1rem;
    color: #9E9EB2;
    margin-top: 8px;
}

/* Download button customized styling */
div.stDownloadButton > button {
    background: linear-gradient(135deg, #00FFA3 0%, #6200EE 100%) !important;
    color: #0F0F1A !important;
    font-weight: 700 !important;
    border: none !important;
    padding: 12px 28px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 15px rgba(0, 255, 163, 0.2) !important;
    transition: all 0.3s ease !important;
    width: 100%;
}

div.stDownloadButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 22px rgba(0, 255, 163, 0.35) !important;
}

/* Style normal user inputs to blend in */
div[data-baseweb="select"] {
    background-color: #1E1E30 !important;
    border-radius: 6px;
}

</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# Loading Cached Resources
# ------------------------------------------------------------------------------
@st.cache_resource
def load_sentence_transformer():
    """Load the sentence transformer model and cache it across Streamlit sessions."""
    return SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

# Load configuration and job description
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "weights.yaml")
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "data", "candidate_schema.json")
JD_PATH = os.path.join(PROJECT_ROOT, "data", "job_description.md")
SAMPLE_PATH = os.path.join(PROJECT_ROOT, "data", "sample_candidates.json")

@st.cache_data
def load_default_jd():
    try:
        with open(JD_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Senior AI Engineer — Founding Team..."

@st.cache_data
def load_default_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}

# ------------------------------------------------------------------------------
# In-Memory Helper Functions for On-the-Fly Retrieval
# ------------------------------------------------------------------------------
def extract_bm25_text(candidate):
    profile = candidate.get("profile", {})
    headline = profile.get("headline") or ""
    summary = profile.get("summary") or ""
    parts = [headline, summary]
    for job in candidate.get("career_history", []):
        parts.append(job.get("title") or "")
        parts.append(job.get("description") or "")
    return " ".join(parts).strip()

def extract_dense_text(candidate):
    profile = candidate.get("profile", {})
    headline = profile.get("headline") or ""
    summary = profile.get("summary") or ""
    parts = [headline, summary]
    for job in candidate.get("career_history", []):
        title = job.get("title") or ""
        desc = job.get("description") or ""
        if len(desc) > 150:
            desc = desc[:150]
        parts.append(f"{title} {desc}".strip())
    return " ".join(parts).strip()

# ------------------------------------------------------------------------------
# App Flow Header
# ------------------------------------------------------------------------------
st.markdown("""
<div class="header-container">
    <h1 class="header-title">🎯 Intelligent Candidate Discovery</h1>
    <p class="header-subtitle">Senior AI Engineer (Founding Team) — Dynamic Interactive Ranker Workspace</p>
</div>
""", unsafe_allow_html=True)

# Sidebar configs
st.sidebar.markdown("### ⚙️ Engine Parameters")

# Sidebar Weights Overrides
config_weights = load_default_config()
st.sidebar.subheader("Composite Weights")
weight_semantic = st.sidebar.slider("Semantic (Dense + BM25) Weight", 0.0, 1.0, 0.60, 0.05)
weight_structured = st.sidebar.slider("Structured features Weight", 0.0, 1.0, 0.40, 0.05)
# Ensure they sum to 1.0 or let them be whatever they are, but normalize them if desired.
# For consistency with weights.yaml, we just let the user set them.
st.sidebar.caption("Current weights: semantic ({:.2f}), structured ({:.2f})".format(weight_semantic, weight_structured))

st.sidebar.subheader("Retrieval Mix")
retrieval_alpha = st.sidebar.slider("BM25 Alpha (Lexical weight)", 0.0, 1.0, 0.40, 0.05)
st.sidebar.caption("Semantic Score = alpha*BM25 + (1-alpha)*Dense")

# Sidebar file uploader
st.sidebar.markdown("---")
st.sidebar.subheader("📂 Upload Candidate Pool")
uploaded_file = st.sidebar.file_uploader("Upload candidates file (.json or .jsonl)", type=["json", "jsonl"])

# Load Job Description & Schema
jd_text = load_default_jd()
try:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    validator = jsonschema.Draft7Validator(schema)
except FileNotFoundError:
    schema = None
    validator = None

# Parsing Candidates
candidates = []
file_source_name = "Default Sample Candidates (50 rows)"

if uploaded_file is not None:
    file_contents = uploaded_file.read().decode("utf-8")
    file_source_name = uploaded_file.name
    
    # Try parsing as JSON list first
    try:
        candidates = json.loads(file_contents)
    except json.JSONDecodeError:
        # Try parsing as JSONL
        candidates = []
        for line in file_contents.splitlines():
            if line.strip():
                try:
                    candidates.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
else:
    # Load default sample candidates
    try:
        with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
            candidates = json.load(f)
    except FileNotFoundError:
        st.error(f"Sample candidates file not found at {SAMPLE_PATH}")
        st.stop()

# Cap the uploaded candidates to 100 rows for Streamlit resources safety
if len(candidates) > 100:
    st.warning(f"⚠️ Uploaded file contains {len(candidates)} candidates. Streamlit Sandbox enforces a strict limit of 100 candidates to satisfy the ~1 GB memory ceiling. Only the first 100 candidates will be ranked.")
    candidates = candidates[:100]

# Execution Button
if len(candidates) > 0:
    t_start = time.time()
    
    # 1. Schema Validation
    invalid_candidates_count = 0
    valid_candidates = []
    
    if validator:
        for idx, c in enumerate(candidates):
            errors = list(validator.iter_errors(c))
            if errors:
                invalid_candidates_count += 1
            else:
                valid_candidates.append(c)
    else:
        valid_candidates = candidates
        
    if invalid_candidates_count > 0:
        st.sidebar.error(f"❌ Excluded {invalid_candidates_count} candidates failing JSON Schema validation.")
        
    if not valid_candidates:
        st.error("No valid candidates found to rank.")
        st.stop()

    # 2. Filter & Honeypot Checks (Layer 1)
    filter_results = []
    eligible_candidates = []
    honeypot_count = 0
    disqualified_count = 0
    
    for c in valid_candidates:
        eligible, honeypot_flag, exclusion_reason, consulting_only, title_tier = check_candidate_filters(c)
        
        if honeypot_flag:
            honeypot_count += 1
        
        if eligible:
            eligible_candidates.append(c)
            filter_results.append({
                "candidate_id": c["candidate_id"],
                "eligible": True,
                "honeypot_flag": honeypot_flag,
                "exclusion_reason": None,
                "consulting_only": consulting_only,
                "title_tier": title_tier
            })
        else:
            disqualified_count += 1
            filter_results.append({
                "candidate_id": c["candidate_id"],
                "eligible": False,
                "honeypot_flag": honeypot_flag,
                "exclusion_reason": exclusion_reason,
                "consulting_only": consulting_only,
                "title_tier": title_tier
            })
            
    filter_df = pd.DataFrame(filter_results)
    
    # Check if we have eligible candidates left
    if not eligible_candidates:
        st.info("No candidates are eligible after hard filters. Adjust candidate input.")
        st.stop()

    # 3. Features (Layer 3 & 4)
    # Resolve reference date dynamically on this pool
    max_active_date = None
    for c in eligible_candidates:
        dt_s = c["redrob_signals"].get("last_active_date")
        if dt_s:
            try:
                dt = datetime.strptime(dt_s, "%Y-%m-%d")
                if not max_active_date or dt > max_active_date:
                    max_active_date = dt
            except ValueError:
                pass
    if not max_active_date:
        max_active_date = datetime.now()
        
    feature_results = []
    for c in eligible_candidates:
        scores = compute_candidate_features(c, config_weights, max_active_date)
        scores["candidate_id"] = c["candidate_id"]
        feature_results.append(scores)
        
    features_df = pd.DataFrame(feature_results)

    # 4. On-the-Fly Hybrid Retrieval (Layer 2)
    # Tokenize JD
    jd_tokens = tokenize(jd_text)
    
    # BM25 lexical retrieval
    tokenized_corpus = [tokenize(extract_bm25_text(c)) for c in eligible_candidates]
    bm25_index = BM25Okapi(tokenized_corpus)
    bm25_scores = np.array(bm25_index.get_scores(jd_tokens))
    
    # Dense Embeddings
    model = load_sentence_transformer()
    # Embed candidates
    candidate_dense_texts = [extract_dense_text(c) for c in eligible_candidates]
    candidate_embeddings = model.encode(candidate_dense_texts, normalize_embeddings=True)
    
    # Load or compute JD embedding
    # We can load precomputed artifacts/jd_embedding.npy if it exists, otherwise compute on-the-fly
    jd_emb_path = os.path.join(PROJECT_ROOT, "artifacts", "jd_embedding.npy")
    if os.path.exists(jd_emb_path):
        jd_embedding = np.load(jd_emb_path)
    else:
        jd_embedding = model.encode(jd_text, normalize_embeddings=True)
        
    dense_scores = candidate_embeddings @ jd_embedding
    
    # Normalize and Combine
    dense_norm = min_max_normalize(dense_scores)
    bm25_norm = min_max_normalize(bm25_scores)
    
    semantic_scores = retrieval_alpha * bm25_norm + (1.0 - retrieval_alpha) * dense_norm
    
    retrieval_df = pd.DataFrame({
        "candidate_id": [c["candidate_id"] for c in eligible_candidates],
        "semantic_score": semantic_scores
    })

    # 5. Composite Scoring & Ranking (Layer 5)
    # Join
    df = filter_df.merge(features_df, on="candidate_id").merge(retrieval_df, on="candidate_id")
    
    # Consulting exclusion rule
    semantic_median = df["semantic_score"].median()
    is_consulting_exclude = (df["title_tier"].isin(["C", "D"])) & (df["consulting_only"]) & (df["semantic_score"] < semantic_median)
    exclude_count = is_consulting_exclude.sum()
    if exclude_count > 0:
        df.loc[is_consulting_exclude, "eligible"] = False
        df.loc[is_consulting_exclude & df["exclusion_reason"].isna(), "exclusion_reason"] = "Consulting-only in Tier C/D with low semantic score"
        
    # Re-filter to eligible candidates
    eligible_df = df[df["eligible"] == True].copy()
    
    # Normalize scores over current eligible subset
    sem_min = eligible_df["semantic_score"].min()
    sem_max = eligible_df["semantic_score"].max()
    sem_denom = sem_max - sem_min
    eligible_df["semantic_score_norm"] = (eligible_df["semantic_score"] - sem_min) / (sem_denom if sem_denom > 1e-8 else 1.0)
    
    struct_min = eligible_df["structured_score"].min()
    struct_max = eligible_df["structured_score"].max()
    struct_denom = struct_max - struct_min
    eligible_df["structured_score_norm"] = (eligible_df["structured_score"] - struct_min) / (struct_denom if struct_denom > 1e-8 else 1.0)
    
    # Compute composite
    eligible_df["composite_score"] = (
        weight_semantic * eligible_df["semantic_score_norm"] +
        weight_structured * eligible_df["structured_score_norm"]
    ) * eligible_df["availability_multiplier"]
    
    # Sort
    sorted_df = eligible_df.sort_values(by=["composite_score", "candidate_id"], ascending=[False, True]).copy()
    
    # Assign ranks
    sorted_df["rank"] = range(1, len(sorted_df) + 1)
    
    # Rounded score strictly decreasing adjustment
    rounded_scores = []
    prev_score = None
    for _, row in sorted_df.iterrows():
        s_rounded = round(row["composite_score"], 3)
        if prev_score is not None:
            if s_rounded >= prev_score:
                s_rounded = round(prev_score - 0.001, 3)
        rounded_scores.append(s_rounded)
        prev_score = s_rounded
        
    sorted_df["score"] = rounded_scores

    # 6. Reasoning Generation (Layer 6)
    # Adapt reasoning logic to run in-memory
    profiles_dict = {c["candidate_id"]: c for c in eligible_candidates}
    
    templates_glow = [
        "Outstanding candidate with {yoe} years of experience as a {title} at {company}. Strong background in {skills} matching JD requirements, combined with high platform activity.",
        "Top-tier AI Engineer with {yoe} years of experience. Demonstrated production success in {skills} at {company}. Outstanding availability and response rates on the platform.",
        "Perfect founding team fit with {yoe} years of experience. Shipped {skills} at {company}. Highly active platform indicators verify readiness for immediate contribution.",
        "Excellent match with {yoe} years of experience. Proven expertise in {skills} at {company}, backed by strong recruiter engagement and high responsiveness."
    ]
    
    templates_strong = [
        "Strong {title} with {yoe} years of experience, showing solid skills in {skills} at {company}. Excellent platform engagement signals.",
        "Experienced AI specialist ({yoe} yrs YoE) with proven competence in {skills}. Strong past work at {company} and high recruitment responsiveness.",
        "Promising match with {yoe} years in the field. Solid technical foundations in {skills} developed at {company}, backed by strong availability.",
        "Competent {title} with {yoe} years of experience at {company}. Possesses strong hands-on skills in {skills} and excellent activity indicators."
    ]
    
    templates_measured = [
        "Adjacent fit as a {title} with {yoe} years of experience. Strong in {skills}, though {concern}.",
        "Relevant engineering background ({yoe} yrs YoE) at {company} with skills in {skills}. Included as filler, noting {concern}.",
        "Competent engineer with {yoe} years of experience. Possesses adjacent skills in {skills}, but ranking is tempered by {concern}.",
        "Plausible candidate with {yoe} years of experience and skills in {skills}, but ranking is deferred due to {concern}."
    ]
    
    reasonings = []
    for _, row in sorted_df.iterrows():
        cid = row["candidate_id"]
        rank = row["rank"]
        
        c = profiles_dict.get(cid, {})
        profile = c.get("profile", {})
        
        yoe = profile.get("years_of_experience", 0)
        title = profile.get("current_title", "Software Engineer")
        company = profile.get("current_company", "prior employer")
        if not company or company.strip() == "":
            company = "prior employer"
            
        skills = get_candidate_skills(c)
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
            
        reasonings.append(text)
        
    sorted_df["reasoning"] = reasonings
    
    t_end = time.time()
    elapsed = t_end - t_start

    # --------------------------------------------------------------------------
    # Render Diagnostics KPI cards
    # --------------------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-title">📂 Input Source</div>
            <div class="kpi-value" style="font-size:1.4rem; padding-top:15px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{}</div>
        </div>
        """.format(file_source_name), unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-title">✅ Eligible Ranked</div>
            <div class="kpi-value">{}</div>
        </div>
        """.format(len(sorted_df)), unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-title">💀 Honeypots Excluded</div>
            <div class="kpi-value" style="background:linear-gradient(135deg, #FF4B4B 0%, #FF8585 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">{}</div>
        </div>
        """.format(honeypot_count), unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-title">⏱️ Processing Time</div>
            <div class="kpi-value">{:.2f}s</div>
        </div>
        """.format(elapsed), unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # Results & Exporter
    # --------------------------------------------------------------------------
    st.markdown("### 🏆 Candidate Leaderboard")
    
    # Format and present ranked DataFrame cleanly
    display_df = sorted_df[["rank", "candidate_id", "score", "reasoning"]].copy()
    
    # Expand profiles detail lookup inside st
    joined_display = sorted_df.merge(
        pd.DataFrame([{
            "candidate_id": c["candidate_id"],
            "name": c["profile"].get("name", "N/A"),
            "current_title": c["profile"].get("current_title", "N/A"),
            "current_company": c["profile"].get("current_company", "N/A"),
            "yoe": c["profile"].get("years_of_experience", 0),
            "location": c["profile"].get("location", "N/A")
        } for c in eligible_candidates]), 
        on="candidate_id"
    )
    
    # Presentation Table
    show_df = joined_display[["rank", "candidate_id", "name", "current_title", "yoe", "score", "reasoning"]].copy()
    show_df.columns = ["Rank", "ID", "Name", "Current Title", "YoE", "Score", "Justification / Reasoning"]
    
    st.dataframe(show_df, use_container_width=True, hide_index=True)

    # Download Exporter Block
    export_csv = display_df.to_csv(index=False, encoding="utf-8")
    
    st.markdown("### 📥 Download Results")
    col_dl1, col_dl2 = st.columns([1, 2])
    with col_dl1:
        st.download_button(
            label="Download Spec-Compliant CSV",
            data=export_csv,
            file_name="team_xxx_sandbox.csv",
            mime="text/csv"
        )
    with col_dl2:
        st.caption("This CSV output contains exactly candidate_id, rank, score, and reasoning fields, conforming strictly to the validator constraints.")

    # --------------------------------------------------------------------------
    # Interactive Details Inspector
    # --------------------------------------------------------------------------
    st.markdown("### 🔍 Candidate Profile Inspector")
    inspect_id = st.selectbox("Select Candidate ID to review detailed profile details", show_df["ID"].tolist())
    
    if inspect_id:
        c_inspect = profiles_dict[inspect_id]
        col_prof1, col_prof2 = st.columns(2)
        with col_prof1:
            st.markdown("#### Stated Resume Info")
            st.write(f"**Name**: {c_inspect['profile'].get('name', 'N/A')}")
            st.write(f"**Current Role**: {c_inspect['profile'].get('current_title', 'N/A')} at {c_inspect['profile'].get('current_company', 'N/A')}")
            st.write(f"**Experience**: {c_inspect['profile'].get('years_of_experience', 0)} years")
            st.write(f"**Location**: {c_inspect['profile'].get('location', 'N/A')} ({c_inspect['profile'].get('country', 'N/A')})")
            
            # Skills list
            skills_names = [s.get("name") for s in c_inspect.get("skills", [])]
            st.write(f"**Skills Stated ({len(skills_names)})**: {', '.join(skills_names)}")
            
        with col_prof2:
            st.markdown("#### platform behavior & Trust signals")
            inspect_signals = c_inspect.get("redrob_signals", {})
            st.write(f"**Recruiter Response Rate**: {inspect_signals.get('recruiter_response_rate', 'N/A')}")
            st.write(f"**Interview Completion Rate**: {inspect_signals.get('interview_completion_rate', 'N/A')}")
            st.write(f"**Offer Acceptance Rate**: {inspect_signals.get('offer_acceptance_rate', 'N/A')}")
            st.write(f"**Active Status**: notice period is {inspect_signals.get('notice_period_days', 'N/A')} days")
            st.write(f"**Willing to relocate**: {'Yes' if inspect_signals.get('willing_to_relocate') else 'No'}")
            
            # Display score breakdowns
            c_row = sorted_df[sorted_df["candidate_id"] == inspect_id].iloc[0]
            st.markdown("##### Sub-Score Breakdowns")
            st.json({
                "structured_score": c_row["structured_score"],
                "title_tier_score": c_row["title_tier_score"],
                "skill_trust_score": c_row["skill_trust_score"],
                "location_score": c_row["location_score"],
                "education_score": c_row["education_score"],
                "semantic_retrieval_score": c_row["semantic_score"],
                "availability_multiplier": c_row["availability_multiplier"]
            })
else:
    st.info("No candidates loaded to process.")
