import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
try:
    from sqlmodel import Session, select
    try:
        from models import Internship
    except ImportError:
        from backend.models import Internship
except ImportError:
    Session = Any
    select = None
    Internship = Any


# Strictly prohibited placeholder salaries and fictional requirements
BLOCKED_PLACEHOLDER_SALARIES: Set[str] = {
    "$30 - $60 / hr",
    "$30-$60/hr",
    "$40 - $70 / hr",
    "$50 - $90 / hr",
    "competitive",
    "competitive pay",
    "tbd",
    "n/a",
    "unknown",
    "placeholder",
}

BLOCKED_PLACEHOLDER_REQUIREMENTS: Set[str] = {
    "python, react, sql",
    "currently enrolled in bachelor's or master's degree. 3.0+ gpa preferred.",
    "tbd",
    "n/a",
    "placeholder",
    "none",
}

BLOCKED_SOURCE_TYPES: Set[str] = {
    "simulated",
    "simulated_company_listing",
    "mock",
    "fake",
}

# Source tier priority for duplicate merging (higher = more authoritative)
SOURCE_TIER_PRIORITY: Dict[str, int] = {
    "official_api": 100,
    "public_ats": 90,
    "official_portal": 80,
    "community_verified": 60,
}
SOURCE_PRIORITY = SOURCE_TIER_PRIORITY

# Known company domain mapping for accurate favicon/logo resolution
COMPANY_DOMAIN_MAP: Dict[str, str] = {
    "google": "google.com",
    "alphabet": "abc.xyz",
    "waymo": "waymo.com",
    "meta": "meta.com",
    "apple": "apple.com",
    "amazon": "amazon.com",
    "microsoft": "microsoft.com",
    "goldman sachs": "goldmansachs.com",
    "jpmorgan chase": "jpmorganchase.com",
    "jpmorgan": "jpmorganchase.com",
    "morgan stanley": "morganstanley.com",
    "nasa": "nasa.gov",
    "stripe": "stripe.com",
    "databricks": "databricks.com",
    "cloudflare": "cloudflare.com",
    "scale ai": "scale.com",
    "robinhood": "robinhood.com",
    "figma": "figma.com",
    "coinbase": "coinbase.com",
    "anthropic": "anthropic.com",
    "openai": "openai.com",
    "spacex": "spacex.com",
    "jane street": "janestreet.com",
    "citadel": "citadel.com",
    "optiver": "optiver.com",
    "american express": "americanexpress.com",
    "oracle": "oracle.com",
    "amd": "amd.com",
    "nvidia": "nvidia.com",
    "tiktok": "tiktok.com",
    "bytedance": "bytedance.com",
    "t-mobile": "t-mobile.com",
    "electronic arts": "ea.com",
    "expedia group": "expediagroup.com",
    "servicenow": "servicenow.com",
    "lseg": "lseg.com",
    "cadence design systems": "cadence.com",
    "general dynamics": "gd.com",
    "general dynamics mission systems": "gdmissionsystems.com",
    "general dynamics information technology": "gdit.com",
    "rtx": "rtx.com",
    "boeing": "boeing.com",
    "lockheed martin": "lockheedmartin.com",
}

TRACKING_QUERY_PARAMS: Set[str] = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "gh_src",
    "source",
    "src",
}


def is_placeholder_salary(salary: Optional[str]) -> bool:
    if not salary:
        return True
    cleaned = salary.strip().lower()
    if not cleaned or cleaned in BLOCKED_PLACEHOLDER_SALARIES:
        return True
    return False


def is_placeholder_requirements(req: Optional[str]) -> bool:
    if not req:
        return True
    cleaned = req.strip().lower()
    if not cleaned or cleaned in BLOCKED_PLACEHOLDER_REQUIREMENTS:
        return True
    return False


def sanitize_salary(salary: Optional[str]) -> Optional[str]:
    if is_placeholder_salary(salary):
        return None
    return salary.strip()


def sanitize_requirements(req: Optional[str]) -> Optional[str]:
    if is_placeholder_requirements(req):
        return None
    return req.strip()


def canonicalize_url(url: str) -> str:
    """
    Strips marketing/tracking query parameters (like utm_source=Simplify&ref=Simplify)
    while preserving essential ATS job identifier parameters.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
        filtered_pairs = [
            (k, v) for k, v in query_pairs
            if k.lower() not in TRACKING_QUERY_PARAMS
        ]
        clean_path = parsed.path.rstrip("/") if parsed.path != "/" else parsed.path
        return urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            clean_path,
            parsed.params,
            urlencode(filtered_pairs, doseq=True),
            ""  # strip fragment
        ))
    except Exception:
        return url.strip()


def normalize_text_token(text: str) -> str:
    if not text:
        return ""
    # Strip emojis and special symbols, collapse whitespace
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def compute_canonical_key(company: str, role: str, location: str) -> str:
    """
    Computes a deterministic deduplication key across sources for the same job posting.
    """
    norm_company = normalize_text_token(company)
    # Normalize common role suffixes
    norm_role = normalize_text_token(role)
    norm_loc = normalize_text_token(location or "united states")
    return f"{norm_company}::{norm_role}::{norm_loc}"


def resolve_logo_url(company: str, current_logo_url: Optional[str] = None) -> str:
    """
    Fixes broken logo URLs (e.g. domain=.com) and resolves clean company favicons/logos.
    """
    if current_logo_url and "domain=.com" not in current_logo_url and current_logo_url.startswith("http"):
        return current_logo_url

    comp_lower = (company or "").strip().lower()
    if comp_lower in COMPANY_DOMAIN_MAP:
        domain = COMPANY_DOMAIN_MAP[comp_lower]
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

    for key, domain in COMPANY_DOMAIN_MAP.items():
        if key in comp_lower:
            return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

    alpha_only = re.sub(r"[^a-z0-9]", "", comp_lower)
    if alpha_only:
        return f"https://www.google.com/s2/favicons?domain={alpha_only}.com&sz=128"

    return f"https://ui-avatars.com/api/?name={company or 'Intern'}&background=2563eb&color=fff"


def extract_verified_salary_from_text(text: str) -> Optional[str]:
    """
    Extracts real disclosed pay ranges from official ATS job descriptions
    (e.g., '$45 - $65/hr', '$52.00/hr', '$110,000 - $145,000').
    Never fabricates or guesses salaries.
    """
    if not text:
        return None

    # Pattern 1: Hourly range e.g. $45 - $65 / hr, $45.00 - $60.00 per hour
    hourly_range = re.search(
        r"\$(\d{2,3}(?:\.\d{2})?)\s*(?:-|to|–)\s*\$?(\d{2,3}(?:\.\d{2})?)\s*(?:/\s*hr|/\s*hour|per\s+hour|hourly|an\s+hour)",
        text,
        re.IGNORECASE,
    )
    if hourly_range:
        low = hourly_range.group(1).split(".")[0]
        high = hourly_range.group(2).split(".")[0]
        return f"${low} - ${high} / hr"

    # Pattern 2: Single hourly rate e.g. $55/hr, $58.50 per hour
    hourly_single = re.search(
        r"\$(\d{2,3}(?:\.\d{2})?)\s*(?:/\s*hr|/\s*hour|per\s+hour|hourly)",
        text,
        re.IGNORECASE,
    )
    if hourly_single:
        rate = hourly_single.group(1).split(".")[0]
        return f"${rate} / hr"

    # Pattern 3: Monthly rate e.g. $8,500 / month
    monthly = re.search(
        r"\$(\d{1,2},\d{3})\s*(?:/\s*mo|/\s*month|per\s+month|monthly)",
        text,
        re.IGNORECASE,
    )
    if monthly:
        return f"${monthly.group(1)} / mo"

    return None


def extract_verified_requirements_from_text(text: str) -> Optional[str]:
    """
    Extracts real technical skills mentioned in an official job description.
    Returns None if no specific skills are found in the text.
    """
    if not text or len(text) < 40:
        return None

    skill_patterns = [
        ("Python", r"\bpython\b"),
        ("C++", r"\bc\+\+\b"),
        ("Java", r"\bjava\b"),
        ("Go", r"\bgolang\b|\bgo\b"),
        ("Rust", r"\brust\b"),
        ("TypeScript", r"\btypescript\b"),
        ("React", r"\breact\b"),
        ("PyTorch", r"\bpytorch\b"),
        ("TensorFlow", r"\btensorflow\b"),
        ("SQL", r"\bsql\b"),
        ("Kubernetes", r"\bkubernetes\b|\bk8s\b"),
        ("AWS", r"\baws\b"),
        ("Linux", r"\blinux\b"),
        ("Distributed Systems", r"\bdistributed systems\b"),
        ("Machine Learning", r"\bmachine learning\b"),
    ]
    found = []
    for label, pat in skill_patterns:
        if re.search(pat, text, re.IGNORECASE):
            found.append(label)
        if len(found) >= 5:
            break

    return ", ".join(found) if found else None


def parse_sources_list(sources_str: Optional[str], fallback_source: str) -> List[str]:
    if not sources_str:
        return [fallback_source] if fallback_source else []
    try:
        parsed = json.loads(sources_str)
        if isinstance(parsed, list):
            return [str(s) for s in parsed if s]
    except Exception:
        pass
    return [s.strip() for s in sources_str.split(",") if s.strip()]


def upsert_or_merge_internship(
    session: Session,
    item_data: Dict[str, Any],
    source_id: Optional[str] = None,
    source_type: Optional[str] = None,
) -> Tuple[Optional[Internship], str]:
    """
    Validates, sanitizes, and inserts or merges an internship posting.
    Returns (Internship, action) where action is 'inserted', 'merged', or 'rejected'.
    """
    payload = item_data
    source_type = source_type or payload.get("source_type", "community_verified")
    source_id = source_id or payload.get("source") or "unknown"

    # 1. Block simulated / mock jobs from entering production
    if source_type in BLOCKED_SOURCE_TYPES or "simulated" in source_id.lower() or payload.get("is_simulated"):
        logging.warning(f"Rejected simulated job from entering production: {payload.get('company')} - {payload.get('role')}")
        return None, "rejected"

    company = (payload.get("company") or "").strip()
    role = (payload.get("role") or "").strip()
    raw_url = (payload.get("url") or "").strip()

    if not company or not role or not raw_url or not raw_url.startswith("http"):
        return None, "rejected"

    location = (payload.get("location") or "United States").strip()
    clean_url = canonicalize_url(raw_url)
    c_key = compute_canonical_key(company, role, location)

    # 2. Strip any placeholder salaries or fictional requirements
    clean_salary = sanitize_salary(payload.get("salary"))
    clean_reqs = sanitize_requirements(payload.get("requirements"))
    clean_logo = resolve_logo_url(company, payload.get("logo_url"))
    now = datetime.utcnow()
    incoming_status = payload.get("status", "active")

    # 3. Check for existing record by canonical URL or canonical (company, role, location) key
    existing = session.exec(
        select(Internship).where(
            (Internship.url == clean_url) |
            (Internship.url == raw_url) |
            (Internship.canonical_key == c_key)
        )
    ).first()

    if existing:
        # Merge duplicate record
        existing_sources = parse_sources_list(existing.sources_list, existing.source)
        if source_id not in existing_sources:
            existing_sources.append(source_id)
        existing.sources_list = json.dumps(existing_sources)

        # Promote primary source & URL if incoming source is higher priority
        old_priority = SOURCE_TIER_PRIORITY.get(existing.source_type or "community_verified", 0)
        new_priority = SOURCE_TIER_PRIORITY.get(source_type, 0)
        if new_priority >= old_priority:
            existing.source = source_id
            existing.source_type = source_type
            existing.url = clean_url

        # Update verified timestamp & status
        existing.last_verified_at = now
        if incoming_status == "closed":
            # Only close if no higher-priority official source keeps it active, or if same source closed it
            if new_priority >= old_priority:
                existing.status = "closed"
        else:
            existing.status = "active"

        # Preserve earliest first_seen_at
        if payload.get("first_seen_at") and existing.first_seen_at and payload["first_seen_at"] < existing.first_seen_at:
            existing.first_seen_at = payload["first_seen_at"]

        # Enrich non-null verified fields
        if clean_salary and not sanitize_salary(existing.salary):
            existing.salary = clean_salary
        elif is_placeholder_salary(existing.salary):
            existing.salary = clean_salary

        if clean_reqs and not sanitize_requirements(existing.requirements):
            existing.requirements = clean_reqs
        elif is_placeholder_requirements(existing.requirements):
            existing.requirements = clean_reqs

        if payload.get("summary") and not existing.summary:
            existing.summary = payload["summary"]

        existing.logo_url = resolve_logo_url(company, existing.logo_url or clean_logo)
        existing.canonical_key = c_key

        session.add(existing)
        return existing, "merged"

    # 4. Insert brand new verified record
    posted_date = payload.get("posted_date") or now
    first_seen = payload.get("first_seen_at") or min(posted_date, now)

    new_job = Internship(
        company=company,
        role=role,
        location=location,
        industry=payload.get("industry", "Technology"),
        ai_label=bool(payload.get("ai_label", False)),
        summary=payload.get("summary"),
        requirements=clean_reqs,
        salary=clean_salary,
        deadline=payload.get("deadline"),
        international_score=payload.get("international_score", 5),
        logo_url=clean_logo,
        url=clean_url,
        source=source_id,
        source_type=source_type,
        sources_list=json.dumps([source_id]),
        canonical_key=c_key,
        posted_date=posted_date,
        first_seen_at=first_seen,
        last_verified_at=now,
        status=incoming_status,
    )
    session.add(new_job)
    return new_job, "inserted"


def reconcile_source_snapshot(
    session: Session,
    source_id: str,
    seen_canonical_keys: Set[str],
    min_expected_count: int = 5,
) -> int:
    """
    When a full-snapshot source completes a healthy crawl, marks previously active jobs
    exclusive to that source as 'expired' if they are no longer present in the live feed.
    """
    if not seen_canonical_keys or len(seen_canonical_keys) < min_expected_count:
        return 0

    active_from_source = session.exec(
        select(Internship).where(
            Internship.source == source_id,
            Internship.status == "active",
        )
    ).all()

    expired_count = 0
    for job in active_from_source:
        if job.canonical_key and job.canonical_key not in seen_canonical_keys:
            sources = parse_sources_list(job.sources_list, job.source)
            # If only backed by this source, mark expired
            if len(sources) <= 1:
                job.status = "expired"
                session.add(job)
                expired_count += 1

    return expired_count


def detect_expired_and_stale_jobs(
    session: Session,
    stale_days: int = 14,
    expired_days: int = 30,
) -> Dict[str, int]:
    """
    Scans active jobs and transitions jobs past their deadline or verification TTL
    to 'stale' or 'expired'.
    """
    now = datetime.utcnow()
    stale_cutoff = now - timedelta(days=stale_days)
    expired_cutoff = now - timedelta(days=expired_days)

    active_jobs = session.exec(
        select(Internship).where(Internship.status == "active")
    ).all()

    marked_expired = 0
    marked_stale = 0

    for job in active_jobs:
        if job.deadline and job.deadline < now:
            job.status = "expired"
            session.add(job)
            marked_expired += 1
            continue

        last_ver = job.last_verified_at or job.posted_date
        if last_ver and last_ver < expired_cutoff:
            job.status = "expired"
            session.add(job)
            marked_expired += 1
        elif last_ver and last_ver < stale_cutoff:
            job.status = "stale"
            session.add(job)
            marked_stale += 1

    return {
        "marked_expired": marked_expired,
        "marked_stale": marked_stale,
    }
