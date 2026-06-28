"""
INDIA RUNS — Data & AI Challenge
Candidate Ranker Script
Author: Sowmya Jadala

Usage:
    python rank.py

Output:
    submission.csv  (top 100 ranked candidates)
"""

import json
import pandas as pd
from datetime import date, datetime

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
CANDIDATES_FILE = "candidates.jsonl"
OUTPUT_FILE = "submission.csv"
REFERENCE_DATE = date(2026, 6, 28)

# ─────────────────────────────────────────────
# STEP 1: Load candidates
# ─────────────────────────────────────────────
print("Loading candidates... (this may take 1-2 minutes)")

candidates = []
with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            candidates.append(json.loads(line))

print(f"Loaded {len(candidates)} candidates.")

# ─────────────────────────────────────────────
# STEP 2: Scoring helpers
# ─────────────────────────────────────────────

STRONG_TITLES = {
    "machine learning engineer", "ml engineer", "ai engineer",
    "senior machine learning engineer", "senior ml engineer", "senior ai engineer",
    "data scientist", "senior data scientist", "applied ml engineer",
    "nlp engineer", "research engineer", "applied scientist",
    "software engineer", "backend engineer", "senior software engineer",
    "deep learning engineer", "computer vision engineer",
    "data engineer", "principal engineer", "staff engineer",
}

WEAK_TITLES = {
    "junior ml engineer", "junior data scientist", "associate data scientist",
    "analyst", "data analyst", "business analyst",
}

IRRELEVANT_TITLES = {
    "hr manager", "accountant", "content writer", "graphic designer",
    "marketing manager", "sales executive", "operations manager",
    "project manager", "customer support", "civil engineer",
    "mechanical engineer", "teacher", "recruiter",
}

CORE_SKILLS = {
    "python", "embeddings", "vector search", "semantic search",
    "information retrieval", "ranking", "elasticsearch", "faiss",
    "pinecone", "weaviate", "qdrant", "milvus", "opensearch",
    "sentence transformers", "hugging face", "transformers",
    "llm", "fine-tuning", "rag", "retrieval augmented generation",
    "pytorch", "tensorflow", "scikit-learn", "nlp",
    "natural language processing", "bert", "gpt", "recommendation systems",
    "a/b testing", "machine learning", "deep learning", "xgboost",
    "sql", "docker", "kubernetes", "mlops", "model deployment",
    "pandas", "numpy", "spark", "distributed systems",
}

SOFT_SKILLS = {
    "communication", "leadership", "teamwork", "problem solving",
    "excel", "powerpoint", "ms office",
}


def score_title(title):
    t = title.lower().strip()
    if any(irr in t for irr in IRRELEVANT_TITLES):
        return 0.0
    if any(strong in t for strong in STRONG_TITLES):
        return 1.0
    if any(weak in t for weak in WEAK_TITLES):
        return 0.4
    return 0.2


def score_career(career_history):
    if not career_history:
        return 0.0
    consulting_firms = {
        "tcs", "infosys", "wipro", "accenture", "cognizant",
        "capgemini", "hcl", "tech mahindra", "mphasis",
    }
    total_months = 0
    relevant_months = 0
    consulting_only = True
    for job in career_history:
        company = job.get("company", "").lower()
        title = job.get("title", "").lower()
        months = job.get("duration_months", 0)
        total_months += months
        is_consulting = any(cf in company for cf in consulting_firms)
        if not is_consulting:
            consulting_only = False
        is_relevant_role = any(s in title for s in [
            "ml", "machine learning", "ai", "data scientist",
            "nlp", "engineer", "developer", "researcher",
        ])
        if is_relevant_role and not is_consulting:
            relevant_months += months
    if total_months == 0:
        return 0.0
    relevance_ratio = relevant_months / total_months
    career_score = relevance_ratio
    if consulting_only:
        career_score *= 0.4
    return min(career_score, 1.0)


def score_experience(years):
    if years < 2:
        return 0.1
    elif years < 4:
        return 0.4
    elif years < 5:
        return 0.7
    elif years <= 9:
        return 1.0
    elif years <= 12:
        return 0.8
    else:
        return 0.6


def score_skills(skills):
    if not skills:
        return 0.0
    proficiency_weights = {
        "expert": 1.0, "advanced": 0.8,
        "intermediate": 0.5, "beginner": 0.2,
    }
    total_score = 0.0
    matched_core = 0
    for skill in skills:
        name = skill.get("name", "").lower().strip()
        proficiency = skill.get("proficiency", "beginner")
        duration = skill.get("duration_months", 0)
        endorsements = skill.get("endorsements", 0)
        if any(soft in name for soft in SOFT_SKILLS):
            continue
        is_core = any(cs in name or name in cs for cs in CORE_SKILLS)
        if not is_core:
            continue
        matched_core += 1
        pw = proficiency_weights.get(proficiency, 0.2)
        duration_bonus = min(duration / 36, 1.0)
        endorse_bonus = min(endorsements / 10, 1.0)
        trust = 0.6 + 0.2 * duration_bonus + 0.2 * endorse_bonus
        total_score += pw * trust
    normalized = min(total_score / 8.0, 1.0)
    if matched_core > 15 and all(
        s.get("proficiency") == "expert" for s in skills
    ):
        normalized *= 0.6
    return normalized


def days_since(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (REFERENCE_DATE - d).days
    except Exception:
        return 999


def score_behavioral(signals):
    score = 0.0
    days_inactive = days_since(signals.get("last_active_date", "2020-01-01"))
    if days_inactive <= 7:
        score += 0.25
    elif days_inactive <= 30:
        score += 0.20
    elif days_inactive <= 90:
        score += 0.10
    elif days_inactive <= 180:
        score += 0.05
    if signals.get("open_to_work_flag", False):
        score += 0.20
    response_rate = signals.get("recruiter_response_rate", 0)
    score += 0.20 * response_rate
    notice = signals.get("notice_period_days", 90)
    if notice <= 30:
        score += 0.10
    elif notice <= 60:
        score += 0.06
    elif notice <= 90:
        score += 0.03
    github = signals.get("github_activity_score", -1)
    if github > 0:
        score += 0.10 * (github / 100)
    icr = signals.get("interview_completion_rate", 0)
    score += 0.05 * icr
    completeness = signals.get("profile_completeness_score", 0)
    score += 0.05 * (completeness / 100)
    if signals.get("verified_email", False):
        score += 0.025
    if signals.get("verified_phone", False):
        score += 0.025
    return min(score, 1.0)


def score_location(location, willing_to_relocate):
    preferred = ["pune", "noida", "delhi", "ncr", "hyderabad",
                 "mumbai", "bangalore", "bengaluru", "chennai", "gurugram"]
    loc = location.lower()
    if any(p in loc for p in preferred):
        return 1.0
    elif willing_to_relocate:
        return 0.7
    else:
        return 0.3


# ─────────────────────────────────────────────
# STEP 3: Score all candidates
# ─────────────────────────────────────────────
print("Scoring candidates...")

rows = []
for c in candidates:
    cid = c["candidate_id"]
    profile = c.get("profile", {})
    signals = c.get("redrob_signals", {})
    career = c.get("career_history", [])
    skills = c.get("skills", [])

    current_title = profile.get("current_title", "")
    years_exp = profile.get("years_of_experience", 0)
    location = profile.get("location", "")
    willing_to_relocate = signals.get("willing_to_relocate", False)

    s_title = score_title(current_title)
    s_career = score_career(career)
    s_exp = score_experience(years_exp)
    s_skills = score_skills(skills)
    s_behavioral = score_behavioral(signals)
    s_location = score_location(location, willing_to_relocate)

    final_score = (
        0.30 * s_title +
        0.20 * s_career +
        0.15 * s_exp +
        0.20 * s_skills +
        0.10 * s_behavioral +
        0.05 * s_location
    )

    if s_title == 0.0:
        final_score = min(final_score, 0.15)

    rows.append({
        "candidate_id": cid,
        "score": round(final_score, 4),
        "title": current_title,
        "years_exp": years_exp,
        "location": location,
        "s_title": s_title,
        "s_career": s_career,
        "s_exp": s_exp,
        "s_skills": s_skills,
        "s_behavioral": s_behavioral,
        "last_active": signals.get("last_active_date", ""),
        "response_rate": signals.get("recruiter_response_rate", 0),
        "notice_days": signals.get("notice_period_days", 0),
        "open_to_work": signals.get("open_to_work_flag", False),
    })

df = pd.DataFrame(rows)
df["candidate_num"] = df["candidate_id"].str.extract(r"(\d+)").astype(int)
df = df.sort_values(["score", "candidate_num"], ascending=[False, True]).reset_index(drop=True)

print(f"\nTop 10 candidates preview:")
print(df[["candidate_id", "title", "years_exp", "score"]].head(10).to_string())

# ─────────────────────────────────────────────
# STEP 4: Build top 100 with reasoning
# ─────────────────────────────────────────────
print("\nBuilding submission CSV...")

top100 = df.head(100).copy()
top100["rank"] = range(1, 101)

def build_reasoning(row):
    parts = []
    parts.append(f"{row['title']} with {row['years_exp']:.1f} yrs experience")
    if row["s_skills"] >= 0.7:
        parts.append("strong AI/ML skill match")
    elif row["s_skills"] >= 0.4:
        parts.append("moderate AI/ML skill match")
    else:
        parts.append("limited core skill overlap")
    if row["open_to_work"]:
        parts.append("actively open to work")
    if row["response_rate"] >= 0.6:
        parts.append(f"high recruiter response rate ({row['response_rate']:.0%})")
    elif row["response_rate"] > 0:
        parts.append(f"response rate {row['response_rate']:.0%}")
    if row["notice_days"] <= 30:
        parts.append(f"notice period {int(row['notice_days'])}d")
    if row["location"]:
        parts.append(f"based in {row['location']}")
    reasoning = "; ".join(parts) + "."
    if len(reasoning) > 200:
        reasoning = reasoning[:197] + "..."
    return reasoning

top100["reasoning"] = top100.apply(build_reasoning, axis=1)

# ─────────────────────────────────────────────
# STEP 5: Write submission CSV
# ─────────────────────────────────────────────
submission = top100[["candidate_id", "rank", "score", "reasoning"]]
submission.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print(f"\n✅ Done! Submission saved to: {OUTPUT_FILE}")
print(f"   Rows: {len(submission)}")
print(f"   Score range: {submission['score'].max():.4f} → {submission['score'].min():.4f}")
print(f"\nNext step — run the validator:")
print(f"   python validate_submission.py submission.csv")
