import argparse
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Set
import requests
from bs4 import BeautifulSoup
from sqlmodel import Session, select
from sqlalchemy import text

from database import engine, create_db_and_tables
from models import Internship, CrawlerAlert
from data_quality import (
    BLOCKED_PLACEHOLDER_SALARIES,
    BLOCKED_PLACEHOLDER_REQUIREMENTS,
    BLOCKED_SOURCE_TYPES,
    SOURCE_PRIORITY,
    sanitize_salary,
    sanitize_requirements,
    canonicalize_url,
    compute_canonical_key,
    resolve_logo_url,
    is_dedicated_job_detail_url,
    classify_job_type,
    classify_visa_status,
    classify_role_category,
    upsert_or_merge_internship,
    reconcile_source_snapshot,
    detect_expired_and_stale_jobs,
)
from alert_service import evaluate_crawl_run_health, record_crawler_alert

# Configure Logging
log_file_path = os.path.join(os.path.dirname(__file__), "crawler.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file_path), logging.StreamHandler()],
)

CRAWLER_STATUS_FILE = os.path.join(os.path.dirname(__file__), "crawler_status.json")

# Import specialized crawlers
try:
    from crawlers.ats import crawl_greenhouse, crawl_lever
except ImportError:
    from backend.crawlers.ats import crawl_greenhouse, crawl_lever

try:
    from crawlers.nasa import crawl_nasa
except ImportError:
    try:
        from backend.crawlers.nasa import crawl_nasa
    except ImportError:
        crawl_nasa = None

try:
    from crawlers.meta import crawl_meta
except ImportError:
    try:
        from backend.crawlers.meta import crawl_meta
    except ImportError:
        crawl_meta = None

try:
    from crawlers.apple import crawl_apple
except ImportError:
    try:
        from backend.crawlers.apple import crawl_apple
    except ImportError:
        crawl_apple = None

try:
    from crawlers.goldman_sachs import crawl_goldman_sachs
except ImportError:
    try:
        from backend.crawlers.goldman_sachs import crawl_goldman_sachs
    except ImportError:
        crawl_goldman_sachs = None

try:
    from crawlers.microsoft import crawl_microsoft
except ImportError:
    try:
        from backend.crawlers.microsoft import crawl_microsoft
    except ImportError:
        crawl_microsoft = None

try:
    from crawlers.jpmorgan_chase import crawl_jpmorgan_chase
except ImportError:
    try:
        from backend.crawlers.jpmorgan_chase import crawl_jpmorgan_chase
    except ImportError:
        crawl_jpmorgan_chase = None

try:
    from crawlers.morgan_stanley import crawl_morgan_stanley
except ImportError:
    try:
        from backend.crawlers.morgan_stanley import crawl_morgan_stanley
    except ImportError:
        crawl_morgan_stanley = None

try:
    from crawlers.google import crawl_google
except ImportError:
    try:
        from backend.crawlers.google import crawl_google
    except ImportError:
        crawl_google = None

try:
    from crawlers.amazon import crawl_amazon
except ImportError:
    try:
        from backend.crawlers.amazon import crawl_amazon
    except ImportError:
        crawl_amazon = None


def load_data_sources() -> List[Dict[str, Any]]:
    config_path = os.path.join(os.path.dirname(__file__), "data_sources.json")
    try:
        with open(config_path, "r") as f:
            sources = json.load(f)
        # Sort sources by priority tier so Official APIs & Public ATS run first
        sources.sort(
            key=lambda s: SOURCE_PRIORITY.get(s.get("source_type", "official_portal"), 50),
            reverse=True,
        )
        return sources
    except Exception as e:
        logging.error(f"Error loading data sources config: {e}")
        return []


def load_crawler_status() -> Dict[str, Any]:
    if not os.path.exists(CRAWLER_STATUS_FILE):
        return {}
    try:
        with open(CRAWLER_STATUS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading crawler status: {e}")
        return {}


def save_crawler_status(status: Dict[str, Any]) -> None:
    try:
        with open(CRAWLER_STATUS_FILE, "w") as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving crawler status: {e}")


def calculate_international_score(text_str: str) -> int:
    score = 7  # Default F-1/CPT friendly baseline for major US tech/finance employers
    text_upper = (text_str or "").upper()

    positives = ["VISA SPONSORSHIP", "CPT", "OPT", "INTERNATIONAL", "GLOBAL", "RELOCATION", "SPONSOR"]
    for p in positives:
        if p in text_upper:
            score += 1

    negatives = [
        "US CITIZEN",
        "U.S. CITIZEN",
        "SECURITY CLEARANCE",
        "NO SPONSORSHIP",
        "DOES NOT OFFER SPONSORSHIP",
        "CITIZENSHIP REQUIRED",
        "US PERSON",
        "🛂",
        "🇺🇸",
    ]
    for n in negatives:
        if n in text_upper:
            return 1

    return max(1, min(10, score))


def infer_industry(company_name: str, role_title: str) -> str:
    comp_upper = (company_name or "").upper()
    role_upper = (role_title or "").upper()
    finance_keywords = [
        "GOLDMAN", "MORGAN", "JPMORGAN", "CHASE", "CITADEL", "JANE STREET",
        "TWO SIGMA", "DE SHAW", "BLACKROCK", "CAPITAL ONE", "FIDELITY",
        "SCHWAB", "VISA", "MASTERCARD", "AMERICAN EXPRESS", "STRIPE",
        "ROBINHOOD", "COINBASE", "POINT72", "SIG", "SUSQUEHANNA", "AKUNA",
        "IMC", "OPTIVER", "HUDSON RIVER", "BANK", "FINANCIAL", "CAPITAL",
    ]
    aerospace_keywords = ["NASA", "SPACEX", "BOEING", "LOCKHEED", "NORTHROP", "RAYTHEON", "ANDURIL", "BLUE ORIGIN"]
    if any(k in comp_upper for k in finance_keywords) or "QUANT" in role_upper:
        return "Finance"
    if any(k in comp_upper for k in aerospace_keywords):
        return "Aerospace"
    return "Technology"


def process_github_readme(
    source_config: Dict[str, Any], session: Session
) -> Tuple[int, int, int, int, Set[str]]:
    """
    Collect verified community listings from SimplifyJobs GitHub repository.
    Strictly prohibits placeholder salaries or fabricated skill requirements.
    Detects closed roles (🔒) and sponsorship restrictions (🛂 / 🇺🇸).
    """
    source_id = source_config.get("id", "simplify_jobs_github")
    source_tier = source_config.get("source_type", "community_verified")
    feed_url = source_config.get("url")
    logging.info(f"Fetching community verified listings from: {feed_url}")

    response = requests.get(feed_url, timeout=25)
    response.raise_for_status()
    content = response.text

    soup = BeautifulSoup(content, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        logging.warning("No tables found in SimplifyJobs README content.")
        return 0, 0, 0, 0, set()

    fetched_count = 0
    inserted_count = 0
    merged_count = 0
    closed_count = 0
    seen_keys: Set[str] = set()
    last_company_name = ""

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if not cols or len(cols) < 4:
                continue

            try:
                company_col = cols[0]
                role_col = cols[1]
                location_col = cols[2]
                app_col = cols[3]

                raw_company_text = company_col.get_text(strip=True)
                cleaned_company = re.sub(r"[^\w\s&.,'-]", "", raw_company_text).strip()
                if not cleaned_company and last_company_name:
                    company_name = last_company_name
                elif cleaned_company:
                    company_name = cleaned_company
                    last_company_name = company_name
                else:
                    continue

                raw_role_text = role_col.get_text(" ", strip=True)
                # Preserve flags before stripping emojis from role title
                has_no_sponsor_flag = "🛂" in raw_role_text or "🛂" in raw_company_text
                has_us_citizen_flag = "🇺🇸" in raw_role_text or "🇺🇸" in raw_company_text
                is_closed = "🔒" in app_col.get_text(strip=True) or "🔒" in raw_role_text

                role_clean = re.sub(r"[🛂🇺🇸🔒🎓🔥]", "", raw_role_text).strip()
                role_clean = re.sub(r"\s+", " ", role_clean)
                if not role_clean:
                    continue

                if location_col.find("details"):
                    location_clean = location_col.get_text(", ", strip=True)
                    location_clean = re.sub(r"^\d+\s*locations?\s*,?\s*", "", location_clean, flags=re.IGNORECASE)
                else:
                    location_clean = location_col.get_text(", ", strip=True)
                if not location_clean:
                    location_clean = "United States"

                # Extract primary application link (prefer direct job link over simplify link)
                link_tag = app_col.find("a")
                job_url = None
                if link_tag and link_tag.get("href"):
                    job_url = canonicalize_url(link_tag.get("href"))

                canonical_key = compute_canonical_key(company_name, role_clean, location_clean)

                # If role is marked closed (🔒), only close if community_verified has >= authority than existing record's status_authority
                if is_closed:
                    existing_item = session.exec(
                        select(Internship).where(Internship.canonical_key == canonical_key)
                    ).first()
                    if existing_item and existing_item.status == "active":
                        existing_auth = SOURCE_PRIORITY.get(existing_item.status_authority or existing_item.source_type or "community_verified", 50)
                        incoming_auth = SOURCE_PRIORITY.get(source_tier, 50)
                        if incoming_auth >= existing_auth:
                            existing_item.status = "closed"
                            existing_item.status_authority = source_tier
                            existing_item.last_verified_at = datetime.utcnow()
                            session.add(existing_item)
                            closed_count += 1
                    continue

                if not job_url:
                    continue

                valid_url, _ = is_dedicated_job_detail_url(job_url)
                if not valid_url:
                    continue

                # Parse age column into first_seen_at; keep posted_at = None since community age is not an employer publication timestamp
                first_seen_at = datetime.utcnow()
                if len(cols) >= 5:
                    age_text = cols[4].get_text(strip=True).lower()
                    digits = re.sub(r"[^0-9]", "", age_text)
                    if digits:
                        val = int(digits)
                        if "h" in age_text:
                            first_seen_at = datetime.utcnow() - timedelta(hours=val)
                        elif "d" in age_text:
                            first_seen_at = datetime.utcnow() - timedelta(days=val)
                        elif "mo" in age_text:
                            first_seen_at = datetime.utcnow() - timedelta(days=val * 30)

                visa_info = classify_visa_status(
                    jd_text=None,
                    source_url=job_url,
                    explicit_flags={
                        "has_no_sponsor_flag": has_no_sponsor_flag,
                        "has_us_citizen_flag": has_us_citizen_flag,
                    },
                )
                cat_info = classify_role_category(role_clean, None)
                job_type = classify_job_type(role_clean, None)

                logo_url = resolve_logo_url(company_name)
                industry = infer_industry(company_name, role_clean)

                item_data = {
                    "company": company_name,
                    "role": role_clean,
                    "location": location_clean,
                    "url": job_url,
                    "industry": industry,
                    "job_type": job_type,
                    "role_category": cat_info["role_category"],
                    "category_evidence": cat_info["category_evidence"],
                    "ai_label": cat_info["ai_label"],
                    "posted_at": None,
                    "posted_date": first_seen_at,
                    "first_seen_at": first_seen_at,
                    "requirements": None,
                    "required_skills": None,
                    "preferred_skills": None,
                    "salary": None,
                    "salary_min": None,
                    "salary_max": None,
                    "salary_period": None,
                    "currency": None,
                    "extraction_evidence": None,
                    "deadline": None,
                    "visa_status": visa_info["visa_status"],
                    "visa_evidence": visa_info["visa_evidence"],
                    "visa_source_url": visa_info["visa_source_url"],
                    "visa_verified_at": visa_info["visa_verified_at"],
                    "international_score": None,
                    "logo_url": logo_url,
                    "status": "active",
                    "status_authority": source_tier,
                }

                _, action = upsert_or_merge_internship(
                    session=session,
                    item_data=item_data,
                    source_id=source_id,
                    source_type=source_tier,
                )
                fetched_count += 1
                seen_keys.add(canonical_key)
                if action == "inserted":
                    inserted_count += 1
                elif action == "merged":
                    merged_count += 1

            except Exception as e:
                logging.error(f"Error parsing SimplifyJobs row: {e}")
                continue

    logging.info(
        f"[SimplifyJobs] Fetched {fetched_count} active listings: "
        f"{inserted_count} new, {merged_count} merged/verified, {closed_count} marked closed."
    )
    return fetched_count, inserted_count, merged_count, closed_count, seen_keys


def ensure_schema_and_clean_production_data(session: Session) -> Dict[str, int]:
    """
    Idempotent schema migration & production data sanitization:
    1. Adds provenance, timestamp, canonical_key, job_type, role_category, visa_status, structured salary/skills, and status_authority columns if missing.
    2. Strips all banned placeholder salaries ('$30 - $60 / hr', etc.) and fake requirements ('Python, React, SQL').
    3. Deletes or isolates any simulated listings.
    4. Fixes broken '.com' logo URLs and backfills source, source_type, first_seen_at, last_verified_at, status.
    5. Deduplicates existing rows sharing the same canonical_key or canonical URL, merging their sources_list.
    """
    # 1. Ensure SQLite columns exist on internship table
    existing_cols_rows = session.exec(text("PRAGMA table_info(internship)")).all()
    existing_cols = {row[1] for row in existing_cols_rows}

    alter_statements = [
        ("source_type", "ALTER TABLE internship ADD COLUMN source_type TEXT DEFAULT 'community_verified'"),
        ("sources_list", "ALTER TABLE internship ADD COLUMN sources_list TEXT"),
        ("canonical_key", "ALTER TABLE internship ADD COLUMN canonical_key TEXT"),
        ("first_seen_at", "ALTER TABLE internship ADD COLUMN first_seen_at TIMESTAMP"),
        ("last_verified_at", "ALTER TABLE internship ADD COLUMN last_verified_at TIMESTAMP"),
        ("status", "ALTER TABLE internship ADD COLUMN status TEXT DEFAULT 'active'"),
        ("job_type", "ALTER TABLE internship ADD COLUMN job_type TEXT DEFAULT 'internship'"),
        ("role_category", "ALTER TABLE internship ADD COLUMN role_category TEXT DEFAULT 'unclassified'"),
        ("category_evidence", "ALTER TABLE internship ADD COLUMN category_evidence TEXT"),
        ("salary_min", "ALTER TABLE internship ADD COLUMN salary_min REAL"),
        ("salary_max", "ALTER TABLE internship ADD COLUMN salary_max REAL"),
        ("salary_period", "ALTER TABLE internship ADD COLUMN salary_period TEXT"),
        ("currency", "ALTER TABLE internship ADD COLUMN currency TEXT"),
        ("required_skills", "ALTER TABLE internship ADD COLUMN required_skills TEXT"),
        ("preferred_skills", "ALTER TABLE internship ADD COLUMN preferred_skills TEXT"),
        ("extraction_evidence", "ALTER TABLE internship ADD COLUMN extraction_evidence TEXT"),
        ("visa_status", "ALTER TABLE internship ADD COLUMN visa_status TEXT DEFAULT 'not_specified'"),
        ("visa_evidence", "ALTER TABLE internship ADD COLUMN visa_evidence TEXT"),
        ("visa_source_url", "ALTER TABLE internship ADD COLUMN visa_source_url TEXT"),
        ("visa_verified_at", "ALTER TABLE internship ADD COLUMN visa_verified_at TIMESTAMP"),
        ("posted_at", "ALTER TABLE internship ADD COLUMN posted_at TIMESTAMP"),
        ("status_authority", "ALTER TABLE internship ADD COLUMN status_authority TEXT DEFAULT 'community_verified'"),
    ]
    for col_name, stmt in alter_statements:
        if col_name not in existing_cols:
            logging.info(f"Adding missing column '{col_name}' to internship table...")
            session.exec(text(stmt))
    session.commit()

    # Create indexes if not present
    session.exec(text("CREATE INDEX IF NOT EXISTS ix_internship_canonical_key ON internship (canonical_key)"))
    session.exec(text("CREATE INDEX IF NOT EXISTS ix_internship_status ON internship (status)"))
    session.exec(text("CREATE INDEX IF NOT EXISTS ix_internship_source_type ON internship (source_type)"))
    session.exec(text("CREATE INDEX IF NOT EXISTS ix_internship_job_type ON internship (job_type)"))
    session.exec(text("CREATE INDEX IF NOT EXISTS ix_internship_role_category ON internship (role_category)"))
    session.exec(text("CREATE INDEX IF NOT EXISTS ix_internship_visa_status ON internship (visa_status)"))
    session.commit()

    all_jobs = session.exec(select(Internship)).all()
    placeholders_stripped = 0
    simulated_removed = 0
    logos_fixed = 0
    duplicates_merged = 0

    canonical_map: Dict[str, Internship] = {}
    url_map: Dict[str, Internship] = {}

    for job in all_jobs:
        # Remove simulated rows if any exist
        if job.source in BLOCKED_SOURCE_TYPES or job.source_type in BLOCKED_SOURCE_TYPES:
            session.delete(job)
            simulated_removed += 1
            continue

        # Strip banned placeholder salaries & requirements
        clean_sal = sanitize_salary(job.salary)
        clean_req = sanitize_requirements(job.requirements)
        if clean_sal != job.salary or clean_req != job.requirements:
            placeholders_stripped += 1
            job.salary = clean_sal
            job.requirements = clean_req

        # Backfill source & source_type
        if not job.source or job.source == "simplify_github":
            if "microsoft.com" in (job.url or ""):
                job.source = "microsoft_official"
            elif "morganstanley" in (job.url or ""):
                job.source = "morgan_stanley_official"
            elif "metacareers.com" in (job.url or ""):
                job.source = "meta_official"
            elif "jobs.apple.com" in (job.url or ""):
                job.source = "apple_official"
            elif "amazon.jobs" in (job.url or ""):
                job.source = "amazon_official"
            elif "google.com/about/careers" in (job.url or ""):
                job.source = "google_official"
            else:
                job.source = "simplify_jobs_github"

        if job.source in ("microsoft_official", "morgan_stanley_official"):
            job.source_type = "official_api"
        elif "greenhouse_ats" in job.source or "lever_ats" in job.source:
            job.source_type = "public_ats"
        elif job.source.endswith("_official"):
            job.source_type = "official_portal"
        else:
            job.source_type = "community_verified"

        # Ensure sources_list is populated JSON
        try:
            src_list = json.loads(job.sources_list) if job.sources_list else []
        except Exception:
            src_list = []
        if job.source not in src_list:
            src_list.append(job.source)
        job.sources_list = json.dumps(src_list)

        # Normalize URL & canonical_key
        job.url = canonicalize_url(job.url)
        job.canonical_key = compute_canonical_key(job.company, job.role, job.location)

        # Backfill timestamps & status
        if not job.first_seen_at:
            job.first_seen_at = job.posted_date or datetime.utcnow()
        if not job.last_verified_at:
            job.last_verified_at = job.posted_date or datetime.utcnow()
        if not job.status:
            job.status = "active"

        # Fix broken logo_url (e.g. domain=.com)
        fixed_logo = resolve_logo_url(job.company, job.logo_url)
        if fixed_logo != job.logo_url:
            job.logo_url = fixed_logo
            logos_fixed += 1

        # Fix industry classification
        job.industry = infer_industry(job.company, job.role)

        # Check for duplicate by canonical_key or url
        existing = canonical_map.get(job.canonical_key) or url_map.get(job.url)
        if existing and existing.id != job.id:
            # Merge into `existing`
            try:
                existing_sources = json.loads(existing.sources_list) if existing.sources_list else [existing.source]
            except Exception:
                existing_sources = [existing.source]
            for s in src_list:
                if s and s not in existing_sources:
                    existing_sources.append(s)
            existing.sources_list = json.dumps(existing_sources)

            # Keep earliest first_seen_at and latest last_verified_at
            if job.first_seen_at and (not existing.first_seen_at or job.first_seen_at < existing.first_seen_at):
                existing.first_seen_at = job.first_seen_at
            if job.last_verified_at and (not existing.last_verified_at or job.last_verified_at > existing.last_verified_at):
                existing.last_verified_at = job.last_verified_at

            # Upgrade source priority if duplicate has higher authority
            if SOURCE_PRIORITY.get(job.source_type, 0) > SOURCE_PRIORITY.get(existing.source_type, 0):
                existing.source = job.source
                existing.source_type = job.source_type
                existing.url = job.url

            if not existing.salary and job.salary:
                existing.salary = job.salary
            if not existing.requirements and job.requirements:
                existing.requirements = job.requirements

            session.delete(job)
            duplicates_merged += 1
        else:
            canonical_map[job.canonical_key] = job
            url_map[job.url] = job
            session.add(job)

    session.commit()
    summary = {
        "placeholders_stripped": placeholders_stripped,
        "simulated_removed": simulated_removed,
        "logos_fixed": logos_fixed,
        "duplicates_merged": duplicates_merged,
    }
    logging.info(f"Database migration & data quality audit complete: {summary}")
    return summary


def _run_collector_for_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    source_type = source.get("type")
    if source_type == "greenhouse_ats":
        return crawl_greenhouse(source)
    if source_type == "lever_ats":
        return crawl_lever(source)
    if source_type == "microsoft_official" and crawl_microsoft:
        return crawl_microsoft(source)
    if source_type == "morgan_stanley_official" and crawl_morgan_stanley:
        return crawl_morgan_stanley(source)
    if source_type == "nasa_official" and crawl_nasa:
        return crawl_nasa(source)
    if source_type == "meta_official" and crawl_meta:
        return crawl_meta(source)
    if source_type == "apple_official" and crawl_apple:
        return crawl_apple(source)
    if source_type == "goldman_sachs_official" and crawl_goldman_sachs:
        return crawl_goldman_sachs(source)
    if source_type == "jpmorgan_chase_official" and crawl_jpmorgan_chase:
        return crawl_jpmorgan_chase(source)
    if source_type == "google_official" and crawl_google:
        return crawl_google(source)
    if source_type == "amazon_official" and crawl_amazon:
        return crawl_amazon(source)
    raise ValueError(f"Unsupported or unavailable crawler type: {source_type}")


def run_crawler():
    parser = argparse.ArgumentParser(description="Internship Aggregator Verified Crawler")
    parser.add_argument("--source", type=str, help="Specific source to crawl (by id, name, or type)")
    parser.add_argument("--force", action="store_true", help="Force crawl even if already done today")
    parser.add_argument("--clean-only", action="store_true", help="Run schema migration, sanitization, and deduplication only")
    args = parser.parse_args()

    logging.info("Starting verified crawler pipeline...")
    create_db_and_tables()

    with Session(engine) as session:
        ensure_schema_and_clean_production_data(session)
        if args.clean_only:
            expired_summary = detect_expired_and_stale_jobs(session)
            session.commit()
            logging.info(f"Clean-only run complete. Expiration summary: {expired_summary}")
            return

        sources = load_data_sources()
        if not sources:
            logging.warning("No data sources configured.")
            return

        crawler_status = load_crawler_status()
        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        for source in sources:
            source_id = source.get("id", source.get("name"))
            source_name = source.get("name", source_id)
            crawler_type = source.get("type", "")
            source_tier = source.get("source_type", "official_portal")

            # Block simulated sources from ever running in production
            if crawler_type in BLOCKED_SOURCE_TYPES or source_tier in BLOCKED_SOURCE_TYPES:
                record_crawler_alert(
                    session=session,
                    source_id=source_id,
                    source_name=source_name,
                    alert_type="blocked_simulated_source",
                    severity="warning",
                    message=f"Blocked simulated source '{source_name}' from entering production.",
                )
                continue

            if args.source:
                q = args.source.lower()
                if (
                    q not in source_id.lower()
                    and q not in source_name.lower()
                    and q not in crawler_type.lower()
                    and q not in source_tier.lower()
                ):
                    continue

            if not source.get("enabled", True):
                continue

            status_key = source_name
            last_run = crawler_status.get(status_key, {})
            if (
                not args.force
                and last_run.get("date") == today_str
                and last_run.get("status") == "success"
                and last_run.get("items_fetched", 0) > 0
            ):
                logging.info(f"Skipping {source_name}: Already crawled successfully today ({today_str}).")
                continue

            logging.info(f"Processing [{source_tier}] source: {source_name} ({source_id})")
            items_fetched = 0
            items_inserted = 0
            items_merged = 0
            items_closed = 0
            seen_keys: Set[str] = set()
            error_msg = None

            try:
                if crawler_type == "github_readme":
                    (
                        items_fetched,
                        items_inserted,
                        items_merged,
                        items_closed,
                        seen_keys,
                    ) = process_github_readme(source, session)
                else:
                    raw_listings = _run_collector_for_source(source)
                    items_fetched = len(raw_listings)
                    for item in raw_listings:
                        item.setdefault("logo_url", source.get("logo_url"))
                        item.setdefault("industry", source.get("industry") or infer_industry(item.get("company", ""), item.get("role", "")))
                        item.setdefault("international_score", source.get("default_international_score", 7))
                        rec, action = upsert_or_merge_internship(
                            session=session,
                            item_data=item,
                            source_id=source_id,
                            source_type=source_tier,
                        )
                        if rec:
                            seen_keys.add(rec.canonical_key)
                        if action == "inserted":
                            items_inserted += 1
                        elif action == "merged":
                            items_merged += 1

                # Reconcile snapshot for authoritative API / ATS feeds
                if seen_keys and source_tier in ("official_api", "public_ats") and items_fetched >= 5:
                    closed_from_snapshot = reconcile_source_snapshot(
                        session=session,
                        source_id=source_id,
                        seen_canonical_keys=seen_keys,
                        min_expected_count=5,
                    )
                    items_closed += closed_from_snapshot

                session.commit()

            except Exception as e:
                session.rollback()
                error_msg = str(e)
                logging.error(f"Exception while crawling {source_name}: {e}")

            status_entry = evaluate_crawl_run_health(
                session=session,
                source_config=source,
                items_fetched=items_fetched,
                items_inserted=items_inserted,
                items_merged=items_merged,
                items_closed=items_closed,
                error=error_msg,
                previous_status=last_run,
            )
            crawler_status[status_key] = status_entry
            save_crawler_status(crawler_status)
            session.commit()

        # Run expiration & staleness detector across all internships
        exp_summary = detect_expired_and_stale_jobs(session, stale_days=45)
        session.commit()
        logging.info(f"Crawler run complete. Expiration/Staleness summary: {exp_summary}")


if __name__ == "__main__":
    run_crawler()
