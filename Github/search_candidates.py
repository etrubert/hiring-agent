"""
GitHub candidate sourcing tool.

Finds AI/ML engineers in France matching 4 target roles by searching the
GitHub Search API, enriching with profile/repo data, then scoring via LLM.

Outputs a ranked CSV: top 5 candidates per role = 20 total.
"""

import os
import re
import sys
import csv
import json
import time
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from github import _fetch_github_api
from llm_utils import initialize_llm_provider, extract_json_from_response
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("search_candidates")


ROLES = {
    "agent_builder": {
        "label": "Agent Builder",
        "experience_years": (3, 5),
    },
    "ai_engineering_manager": {
        "label": "AI Engineering Manager",
        "experience_years": (7, 20),
    },
    "senior_ai_engineer": {
        "label": "Senior AI Engineer",
        "experience_years": (5, 15),
    },
    "data_scientist_senior": {
        "label": "Senior Data Scientist",
        "experience_years": (6, 12),
    },
}

# Keywords used for lightweight filtering BEFORE the LLM stage
AI_SIGNAL_KEYWORDS = [
    "llm", "gpt", "openai", "anthropic", "langchain", "langgraph", "langflow",
    "rag", "retrieval", "embedding", "vector", "agent", "mcp",
    "machine learning", "deep learning", "neural", "nlp", "transformer",
    "pytorch", "tensorflow", "huggingface", "fine-tun",
    "data scientist", "ml engineer", "ai engineer", "mlops",
    "n8n", "dust", "automation",
]

# Role-specific search queries. Each query is run through GitHub user search;
# the role key is kept as a "source_role" hint to preserve diversity later.
SEARCH_QUERIES_PER_ROLE = {
    "agent_builder": [
        "location:France langchain",
        "location:France langgraph",
        "location:France \"ai agent\"",
        "location:France llm rag",
        "location:Paris langchain",
    ],
    "ai_engineering_manager": [
        "location:France \"engineering manager\" ai",
        "location:France \"head of ai\"",
        "location:France \"ml lead\"",
        "location:France \"tech lead\" machine-learning",
        "location:France \"vp engineering\" ai",
        "location:Paris \"engineering manager\" ml",
    ],
    "senior_ai_engineer": [
        "location:France \"machine learning engineer\"",
        "location:France \"ai engineer\"",
        "location:France mlops",
        "location:France pytorch tensorflow",
        "location:Paris \"ml engineer\"",
    ],
    "data_scientist_senior": [
        "location:France \"data scientist\"",
        "location:France \"senior data scientist\"",
        "location:France kaggle",
        "location:Paris \"data scientist\"",
        "location:France \"lead data scientist\"",
    ],
}

# Keyword hints used to pre-classify a candidate before the LLM stage.
# Helps the LLM avoid defaulting everyone to senior_ai_engineer.
ROLE_HINT_KEYWORDS = {
    "ai_engineering_manager": [
        "engineering manager", "em ai", "em ml", "head of ai", "head of ml",
        "head of data", "vp engineering", "vp ai", "director of", "ai lead",
        "ml lead", "tech lead", "team lead", "principal engineer",
        "engineering director", "staff engineer", "cto", "chief ai",
    ],
    "agent_builder": [
        "langchain", "langgraph", "langflow", "ai agent", "agent builder",
        "autonomous agent", "mcp", "llamaindex", "rag pipeline", "dust.tt",
        "n8n", "llm agent",
    ],
    "data_scientist_senior": [
        "data scientist", "kaggle", "data science", "statistical",
        "analytics", "econometric", "feature engineering",
    ],
    "senior_ai_engineer": [
        "machine learning engineer", "ml engineer", "ai engineer",
        "mlops", "deep learning engineer", "senior software",
        "production ml", "model deployment",
    ],
}

FRANCE_LOCATION_MARKERS = [
    "france", "paris", "lyon", "marseille", "toulouse", "bordeaux", "nantes",
    "lille", "strasbourg", "montpellier", "rennes", "nice", "grenoble",
    "île-de-france", "ile-de-france", "fr,", "(fr)",
]


# ---------- GitHub API helpers ----------

def search_users(query: str, page: int = 1, per_page: int = 100) -> list[dict]:
    """GitHub user search. Returns list of {login, id, avatar_url, ...}."""
    url = "https://api.github.com/search/users"
    params = {"q": query, "per_page": per_page, "page": page,
              "sort": "followers", "order": "desc"}
    status, data = _fetch_github_api(url, params=params)
    if status != 200:
        logger.warning(f"search_users failed for '{query}' page {page}: {status}")
        return []
    return data.get("items", [])


def fetch_user_profile(username: str) -> dict | None:
    """Full profile for a user."""
    url = f"https://api.github.com/users/{username}"
    status, data = _fetch_github_api(url)
    return data if status == 200 else None


def fetch_user_repos(username: str, per_page: int = 30) -> list[dict]:
    """Top repos for a user, sorted by updated_at."""
    url = f"https://api.github.com/users/{username}/repos"
    params = {"sort": "updated", "per_page": per_page, "type": "owner"}
    status, data = _fetch_github_api(url, params=params)
    return data if status == 200 and isinstance(data, list) else []


def fetch_user_readme(username: str) -> str:
    """Fetch the README of the user's 'profile' repo (username/username)."""
    url = f"https://api.github.com/repos/{username}/{username}/readme"
    status, data = _fetch_github_api(url)
    if status != 200 or not isinstance(data, dict):
        return ""
    import base64
    content_b64 = data.get("content", "")
    try:
        return base64.b64decode(content_b64).decode("utf-8", errors="ignore")[:3000]
    except Exception:
        return ""


# ---------- Filtering ----------

def is_france_location(loc: str | None) -> bool:
    if not loc:
        return False
    loc_lower = loc.lower()
    return any(m in loc_lower for m in FRANCE_LOCATION_MARKERS)


def has_ai_signal(bio: str, repos: list[dict]) -> bool:
    """Quick keyword check across bio + repo descriptions + repo names."""
    blob_parts = [bio or ""]
    for r in repos:
        blob_parts.append(r.get("name", "") or "")
        blob_parts.append(r.get("description", "") or "")
        blob_parts.extend(r.get("topics", []) or [])
    blob = " ".join(blob_parts).lower()
    return any(kw in blob for kw in AI_SIGNAL_KEYWORDS)


def account_age_years(created_at: str | None) -> float:
    if not created_at:
        return 0.0
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - created
        return round(delta.days / 365.25, 1)
    except Exception:
        return 0.0


# ---------- Enrichment per candidate ----------

def enrich_candidate(username: str) -> dict | None:
    """Fetch profile + repos + personal README. Returns None if not France
    or no AI signal."""
    profile = fetch_user_profile(username)
    if not profile:
        return None
    if not is_france_location(profile.get("location")):
        return None

    repos = fetch_user_repos(username, per_page=30)
    if not repos:
        return None
    if not has_ai_signal(profile.get("bio", "") or "", repos):
        return None

    readme = fetch_user_readme(username)

    # Keep only meaningful repo fields
    trimmed_repos = []
    for r in repos:
        if r.get("fork") and r.get("stargazers_count", 0) < 3:
            continue
        trimmed_repos.append({
            "name": r.get("name"),
            "description": r.get("description"),
            "language": r.get("language"),
            "stars": r.get("stargazers_count", 0),
            "topics": r.get("topics", []),
            "updated_at": r.get("updated_at"),
            "fork": r.get("fork", False),
        })
    # Sort by stars desc, take top 15 to keep LLM prompt small
    trimmed_repos.sort(key=lambda x: x["stars"], reverse=True)
    trimmed_repos = trimmed_repos[:15]

    return {
        "username": username,
        "name": profile.get("name"),
        "bio": profile.get("bio"),
        "location": profile.get("location"),
        "company": profile.get("company"),
        "blog": profile.get("blog"),
        "email": profile.get("email"),
        "followers": profile.get("followers", 0),
        "public_repos": profile.get("public_repos", 0),
        "account_age_years": account_age_years(profile.get("created_at")),
        "html_url": profile.get("html_url"),
        "readme_excerpt": readme,
        "top_repos": trimmed_repos,
    }


# ---------- LLM scoring ----------

SCORING_SYSTEM = (
    "You are an expert technical recruiter evaluating a GitHub profile for AI/ML "
    "engineering roles. You output STRICT JSON only — no prose, no markdown."
)

SCORING_PROMPT_TEMPLATE = """Evaluate this GitHub candidate for 4 possible roles.

CANDIDATE DATA:
- Username: {username}
- Name: {name}
- Bio: {bio}
- Location: {location}
- Company: {company}
- Account age: {account_age_years} years
- Followers: {followers}
- Public repos: {public_repos}
- Preliminary hint_roles (keyword-based, may be wrong): {hint_roles}
- Found via searches for: {source_roles}

PERSONAL README EXCERPT:
{readme_excerpt}

TOP REPOSITORIES:
{repos_json}

TARGET ROLES — read carefully, pick the BEST fit:

1. agent_builder (3-5 yrs exp)
   REQUIRED: evidence of LLM / agent / RAG work (LangChain, LangGraph, MCP,
   autonomous agents, LlamaIndex, Dust, n8n). Typical bio: "building AI agents",
   "LLM engineer", "RAG systems". Account age usually 3-7 years.

2. ai_engineering_manager (7+ yrs + leadership)
   REQUIRED: explicit leadership evidence in bio OR company title OR README —
   words like "Engineering Manager", "Head of AI", "ML Lead", "Tech Lead",
   "Director", "VP", "Principal", "Staff Engineer leading...", "managing a team".
   Often account age 8+ years, fewer recent personal commits, company-focused repos.

3. senior_ai_engineer (5+ yrs, strong SWE + ML/DL)
   Strong software eng + production ML. Bio often says "ML Engineer",
   "AI Engineer", "MLOps". Account 5+ years, many polished production repos.

4. data_scientist_senior (6-8 yrs)
   Data science focus: Kaggle, notebooks, statistical modeling, feature
   engineering, business analytics. Bio usually says "Data Scientist",
   "Senior Data Scientist", "Lead Data Scientist". Often more Jupyter / pandas
   / scikit-learn than production API code.

CRITICAL CLASSIFICATION RULES:
- Do NOT default to "senior_ai_engineer". It should only win when evidence
  points there specifically, not as a safe fallback.
- For "ai_engineering_manager": require explicit management/leadership wording,
  not just seniority. If no such wording, DO NOT pick this role.
- For "agent_builder": require at least one agent/LLM/RAG library or keyword.
- If no role fits well, return "none" — don't force a match.
- Use the hint_roles as a signal, not a command. Override it if evidence is stronger.

KEY SKILLS TO DETECT: LLMs, RAG, MCP, LangChain, LangGraph, LangFlow, NLP,
Deep Learning, TensorFlow, PyTorch, Python, SQL, Databricks, Spark, Delta Lake,
Airflow, Production Deployment, n8n, Dust, APIs/Webhooks, Leadership,
Management, Stakeholder Management.

OUTPUT STRICT JSON with this exact schema:
{{
  "best_role_match": "agent_builder|ai_engineering_manager|senior_ai_engineer|data_scientist_senior|none",
  "role_match_confidence": 0-100,
  "alternative_role": "second-best role or null",
  "experience_years_estimate": number,
  "experience_fits_role": true|false,
  "leadership_evidence": "quote from bio/readme or null",
  "skills_detected": ["skill1", "skill2", ...],
  "wow_signals": ["specific thing that stands out", ...],
  "red_flags": ["concerns", ...],
  "overall_score": 0-100,
  "summary": "one sentence why this candidate is relevant"
}}

Return JSON only."""


def score_candidate(provider, candidate: dict) -> dict | None:
    """Run the LLM on one candidate. Returns parsed JSON or None."""
    repos_json = json.dumps(candidate["top_repos"], ensure_ascii=False, indent=2)
    prompt = SCORING_PROMPT_TEMPLATE.format(
        username=candidate["username"],
        name=candidate.get("name") or "N/A",
        bio=(candidate.get("bio") or "N/A")[:500],
        location=candidate.get("location") or "N/A",
        company=candidate.get("company") or "N/A",
        account_age_years=candidate.get("account_age_years"),
        followers=candidate.get("followers"),
        public_repos=candidate.get("public_repos"),
        hint_roles=", ".join(candidate.get("hint_roles", [])) or "(none)",
        source_roles=", ".join(candidate.get("source_roles", [])) or "(none)",
        readme_excerpt=(candidate.get("readme_excerpt") or "(none)")[:1500],
        repos_json=repos_json[:4000],
    )
    try:
        response = provider.chat(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SCORING_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            options=MODEL_PARAMETERS.get(DEFAULT_MODEL, {"temperature": 0.1}),
        )
        text = response["message"]["content"].strip()
        text = extract_json_from_response(text)
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed for {candidate['username']}: {e}")
        return None
    except Exception as e:
        logger.warning(f"LLM call failed for {candidate['username']}: {e}")
        return None


# ---------- Main orchestration ----------

def phase_search() -> dict[str, set[str]]:
    """Run all search queries. Returns {role_key: set of usernames}
    so we preserve which role's search surfaced each candidate."""
    logger.info("=== Phase 1: GitHub search (per role) ===")
    per_role: dict[str, set[str]] = {role: set() for role in ROLES}
    for role_key, queries in SEARCH_QUERIES_PER_ROLE.items():
        for q in queries:
            logger.info(f"[{role_key}] searching: {q}")
            for page in (1, 2):
                users = search_users(q, page=page, per_page=100)
                for u in users:
                    per_role[role_key].add(u["login"])
                if len(users) < 100:
                    break
    total_unique = len(set().union(*per_role.values()))
    for role_key, users in per_role.items():
        logger.info(f"  {role_key}: {len(users)} candidates from search")
    logger.info(f"Total unique candidates across all roles: {total_unique}")
    return per_role


def classify_role_hints(candidate: dict) -> list[str]:
    """Return role keys whose keywords appear in the candidate's bio,
    company, or README. A candidate can match multiple roles."""
    blob = " ".join([
        candidate.get("bio") or "",
        candidate.get("company") or "",
        candidate.get("readme_excerpt") or "",
        # Also look at repo names/descs for skill keywords
        " ".join((r.get("name") or "") + " " + (r.get("description") or "")
                 for r in candidate.get("top_repos", [])),
    ]).lower()
    matched = []
    for role_key, kws in ROLE_HINT_KEYWORDS.items():
        if any(kw in blob for kw in kws):
            matched.append(role_key)
    return matched


def phase_enrich(per_role_users: dict[str, set[str]],
                 max_workers: int = 8) -> list[dict]:
    """Parallel enrichment + filter. Tags each candidate with 'source_roles'
    listing which role searches surfaced them, plus 'hint_roles' from keyword
    matching on the enriched data."""
    logger.info("=== Phase 2: Enrich + filter (France + AI signal) ===")

    # Reverse-index: username -> set of source role keys
    source_map: dict[str, set[str]] = {}
    for role_key, users in per_role_users.items():
        for u in users:
            source_map.setdefault(u, set()).add(role_key)

    usernames = list(source_map.keys())
    logger.info(f"Enriching {len(usernames)} candidates with {max_workers} workers")
    enriched = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(enrich_candidate, u): u for u in usernames}
        for i, fut in enumerate(as_completed(futures), 1):
            username = futures[fut]
            result = fut.result()
            if result:
                result["source_roles"] = sorted(source_map.get(username, set()))
                result["hint_roles"] = classify_role_hints(result)
                enriched.append(result)
            if i % 25 == 0:
                logger.info(f"  enriched {i}/{len(usernames)} — kept {len(enriched)}")
    logger.info(f"Kept {len(enriched)} candidates after France + AI signal filter")
    return enriched


def balance_pool_per_role(candidates: list[dict],
                          per_role_cap: int = 20) -> list[dict]:
    """Select up to `per_role_cap` candidates per role bucket for LLM scoring,
    so we don't starve low-supply roles (like managers)."""
    buckets: dict[str, list[dict]] = {role: [] for role in ROLES}

    # Prefer candidates with matching hint_roles, fall back to source_roles.
    # A candidate can land in multiple buckets, which is fine — the LLM picks
    # the final single role later.
    for c in candidates:
        matched = set(c.get("hint_roles", [])) | set(c.get("source_roles", []))
        if not matched:
            # Fallback: let them compete as senior_ai_engineer
            matched = {"senior_ai_engineer"}
        for role_key in matched:
            if role_key in buckets:
                buckets[role_key].append(c)

    # Within each bucket, pre-rank by followers (visibility proxy)
    selected_usernames: set[str] = set()
    selected: list[dict] = []
    for role_key, bucket in buckets.items():
        bucket.sort(key=lambda c: c.get("followers", 0), reverse=True)
        kept = 0
        for c in bucket:
            if c["username"] in selected_usernames:
                continue
            if kept >= per_role_cap:
                break
            selected.append(c)
            selected_usernames.add(c["username"])
            kept += 1
        logger.info(f"  pool[{role_key}]: kept {kept} for LLM scoring")
    return selected


def phase_score(candidates: list[dict]) -> list[dict]:
    """Score each candidate via LLM. Returns list of merged (candidate + score)."""
    logger.info(f"=== Phase 3: LLM scoring ({len(candidates)} candidates) ===")
    provider = initialize_llm_provider(DEFAULT_MODEL)
    results = []
    for i, cand in enumerate(candidates, 1):
        logger.info(f"  [{i}/{len(candidates)}] scoring {cand['username']}...")
        t0 = time.time()
        scored = score_candidate(provider, cand)
        dt = time.time() - t0
        if scored is None:
            continue
        merged = {**cand, "llm": scored}
        results.append(merged)
        logger.info(
            f"    {cand['username']} → {scored.get('best_role_match')} "
            f"(score {scored.get('overall_score')}) [{dt:.1f}s]"
        )
    return results


def phase_rank(scored: list[dict], per_role: int = 5) -> list[dict]:
    """Keep top `per_role` per role, across the 4 defined roles."""
    logger.info("=== Phase 4: Rank + select top 5 per role ===")
    out = []
    for role_key in ROLES:
        bucket = [s for s in scored if s["llm"].get("best_role_match") == role_key]
        # Must also have experience_fits_role == True
        bucket = [s for s in bucket if s["llm"].get("experience_fits_role")]
        bucket.sort(key=lambda s: s["llm"].get("overall_score", 0), reverse=True)
        kept = bucket[:per_role]
        logger.info(
            f"  {role_key}: {len(bucket)} candidates matched → "
            f"kept top {len(kept)}"
        )
        for c in kept:
            c["_role_bucket"] = role_key
        out.extend(kept)
    return out


def write_csv(candidates: list[dict], path: str = "candidates.csv"):
    fields = [
        "role", "username", "name", "github_url", "location", "company",
        "experience_years_est", "account_age_years", "followers", "public_repos",
        "role_match_confidence", "overall_score",
        "skills_detected", "wow_signals", "red_flags", "summary",
        "bio", "blog", "email",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in candidates:
            llm = c.get("llm", {})
            w.writerow({
                "role": ROLES.get(c.get("_role_bucket"), {}).get("label", "?"),
                "username": c["username"],
                "name": c.get("name") or "",
                "github_url": c.get("html_url") or "",
                "location": c.get("location") or "",
                "company": c.get("company") or "",
                "experience_years_est": llm.get("experience_years_estimate", ""),
                "account_age_years": c.get("account_age_years", ""),
                "followers": c.get("followers", 0),
                "public_repos": c.get("public_repos", 0),
                "role_match_confidence": llm.get("role_match_confidence", ""),
                "overall_score": llm.get("overall_score", ""),
                "skills_detected": "; ".join(llm.get("skills_detected", [])),
                "wow_signals": "; ".join(llm.get("wow_signals", [])),
                "red_flags": "; ".join(llm.get("red_flags", [])),
                "summary": llm.get("summary", ""),
                "bio": (c.get("bio") or "").replace("\n", " "),
                "blog": c.get("blog") or "",
                "email": c.get("email") or "",
            })
    logger.info(f"Wrote {len(candidates)} candidates to {path}")


def print_console_report(candidates: list[dict]):
    print("\n" + "=" * 80)
    print("TOP CANDIDATES PAR RÔLE")
    print("=" * 80)
    for role_key, role_info in ROLES.items():
        bucket = [c for c in candidates if c.get("_role_bucket") == role_key]
        print(f"\n### {role_info['label']} ({len(bucket)} candidats)\n")
        for c in bucket:
            llm = c.get("llm", {})
            print(f"  • {c['username']} ({c.get('name') or '—'}) — "
                  f"score {llm.get('overall_score')}/100, "
                  f"~{llm.get('experience_years_estimate')} ans")
            print(f"    {c.get('html_url')}")
            print(f"    {llm.get('summary', '')[:200]}")


def main():
    if not os.environ.get("GITHUB_TOKEN"):
        logger.error(
            "GITHUB_TOKEN not set. Add it to .env or export it in your shell. "
            "Without a token, search API is limited to 10 req/min."
        )
        return

    t_start = time.time()

    per_role_users = phase_search()
    total_found = len(set().union(*per_role_users.values()))
    if not total_found:
        logger.error("No candidates found in search. Aborting.")
        return

    # Cap enrichment per role (each enrich = ~3 API calls).
    # 60/role × 4 = up to 240 enrich jobs before dedup across roles.
    ENRICH_CAP_PER_ROLE = 60
    for role_key, users in per_role_users.items():
        if len(users) > ENRICH_CAP_PER_ROLE:
            # Convert to list, trim. order from search is already follower-sorted.
            per_role_users[role_key] = set(list(users)[:ENRICH_CAP_PER_ROLE])
            logger.info(f"  capped enrich pool for {role_key} to {ENRICH_CAP_PER_ROLE}")

    enriched = phase_enrich(per_role_users)
    if not enriched:
        logger.error("No candidates passed the France + AI filter. Aborting.")
        return

    # Balance pool across 4 roles BEFORE LLM scoring so managers/agent-builders
    # (lower supply) don't get crowded out by senior_ai_engineers.
    logger.info("=== Phase 2b: Balance pool per role ===")
    to_score = balance_pool_per_role(enriched, per_role_cap=15)
    logger.info(f"Sending {len(to_score)} candidates to LLM scoring")

    scored = phase_score(to_score)
    top = phase_rank(scored, per_role=5)

    output_path = sys.argv[1] if len(sys.argv) > 1 else "candidates-1.csv"
    if not output_path.endswith(".csv"):
        output_path += ".csv"
    write_csv(top, output_path)
    print_console_report(top)

    dt = time.time() - t_start
    logger.info(f"\n✅ Done in {dt/60:.1f} min. Output: {output_path}")


if __name__ == "__main__":
    main()
