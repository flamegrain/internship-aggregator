import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_SITE = os.path.join(ROOT_DIR, "venv", "lib", "python3.11", "site-packages")
for p in (BACKEND_DIR, ROOT_DIR, VENV_SITE):
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

import json
import logging
import re
import sqlite3
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

import data_quality as dq
from crawlers.ats import crawl_greenhouse, crawl_lever, crawl_workday, crawl_smartrecruiters
from crawlers.microsoft import crawl_microsoft
from crawlers.morgan_stanley import crawl_morgan_stanley

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DB_PATH = os.path.join(BACKEND_DIR, "database.db")
SOURCES_PATH = os.path.join(BACKEND_DIR, "data_sources.json")
STATUS_PATH = os.path.join(BACKEND_DIR, "crawler_status.json")


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


def ensure_schema(cur):
    cols = {r[1] for r in cur.execute("PRAGMA table_info(internship)").fetchall()}
    new_cols = [
        ("job_type", "TEXT DEFAULT 'internship'"),
        ("role_category", "TEXT DEFAULT 'unclassified'"),
        ("category_evidence", "TEXT"),
        ("salary_min", "REAL"),
        ("salary_max", "REAL"),
        ("salary_period", "TEXT"),
        ("currency", "TEXT"),
        ("required_skills", "TEXT"),
        ("preferred_skills", "TEXT"),
        ("extraction_evidence", "TEXT"),
        ("visa_status", "TEXT DEFAULT 'not_specified'"),
        ("visa_evidence", "TEXT"),
        ("visa_source_url", "TEXT"),
        ("visa_verified_at", "TIMESTAMP"),
        ("source_type", "TEXT DEFAULT 'community_verified'"),
        ("sources_list", "TEXT"),
        ("canonical_key", "TEXT"),
        ("posted_at", "TIMESTAMP"),
        ("first_seen_at", "TIMESTAMP"),
        ("last_verified_at", "TIMESTAMP"),
        ("status", "TEXT DEFAULT 'active'"),
        ("status_authority", "TEXT DEFAULT 'community_verified'"),
    ]
    for col_name, col_def in new_cols:
        if col_name not in cols:
            logging.info(f"Adding column {col_name} to internship...")
            cur.execute(f"ALTER TABLE internship ADD COLUMN {col_name} {col_def}")

    cur.execute("CREATE INDEX IF NOT EXISTS ix_internship_job_type ON internship (job_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_internship_role_category ON internship (role_category)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_internship_visa_status ON internship (visa_status)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_internship_posted_at ON internship (posted_at)")


def audit_and_migrate_existing_rows(cur):
    """
    Re-audits every existing row in database.db so that:
    - Non-dedicated URLs are marked 'pending_review'
    - job_type is strictly classified ('internship', 'co-op', 'fellowship', 'new_grad_full_time', 'other_student_program', 'non_student')
    - role_category and category_evidence are classified using full phrases
    - posted_at is cleared to NULL on rows where posted_date was just crawl discovery time
    - international_score is cleared to NULL and visa_status is set with 100% evidence backing
    """
    rows = cur.execute("SELECT * FROM internship").fetchall()
    now_iso = datetime.utcnow().isoformat()
    non_student_count = 0
    pending_url_count = 0

    for r in rows:
        row_id = r["id"]
        company = (r["company"] or "").strip()
        role = re.sub(r"[🛂🇺🇸🔒🎓🔥]", "", r["role"] or "").strip()
        role = re.sub(r"\s+", " ", role)
        location = (r["location"] or "United States").strip()
        clean_url = dq.canonicalize_url(r["url"] or "")
        c_key = dq.compute_canonical_key(company, role, location)

        is_valid_url, _ = dq.is_dedicated_job_detail_url(clean_url)
        status = r["status"] or "active"
        if not is_valid_url and status == "active":
            status = "pending_review"
            pending_url_count += 1

        job_type = dq.classify_job_type(role)
        if job_type == "non_student":
            non_student_count += 1
            if status == "active":
                status = "closed"

        role_category, category_evidence = dq.classify_role_category(role)
        ai_label = 1 if role_category == "ai_ml" else 0

        # Clear unbacked international_score; preserve visa_status only if backed by evidence
        visa_status = r["visa_status"] if "visa_status" in r.keys() and r["visa_status"] else "not_specified"
        visa_evidence = r["visa_evidence"] if "visa_evidence" in r.keys() else None
        visa_source_url = r["visa_source_url"] if "visa_source_url" in r.keys() else None
        visa_verified_at = r["visa_verified_at"] if "visa_verified_at" in r.keys() else None

        if visa_status != "not_specified" and not visa_evidence:
            visa_status = "not_specified"
            visa_evidence = None
        if not visa_source_url:
            visa_source_url = clean_url
        if not visa_verified_at:
            visa_verified_at = r["last_verified_at"] or now_iso

        # Separate posted_at: only keep posted_at if from public_ats where upstream timestamp was parsed
        src_type = r["source_type"] or "community_verified"
        posted_at = r["posted_at"] if "posted_at" in r.keys() else None
        if src_type in ("community_verified", "official_portal"):
            posted_at = None

        status_authority = r["status_authority"] if "status_authority" in r.keys() and r["status_authority"] else src_type

        cur.execute(
            """
            UPDATE internship
            SET role = ?, url = ?, canonical_key = ?, status = ?, status_authority = ?,
                job_type = ?, role_category = ?, category_evidence = ?, ai_label = ?,
                visa_status = ?, visa_evidence = ?, visa_source_url = ?, visa_verified_at = ?,
                international_score = NULL, posted_at = ?
            WHERE id = ?
            """,
            (
                role, clean_url, c_key, status, status_authority,
                job_type, role_category, category_evidence, ai_label,
                visa_status, visa_evidence, visa_source_url, visa_verified_at,
                posted_at, row_id,
            ),
        )
    logging.info(f"Migrated existing rows: {non_student_count} non-student roles isolated, {pending_url_count} generic URLs marked pending_review.")


def upsert_sqlite_row(cur, item: dict, source_id: str, source_type: str) -> str:
    company = (item.get("company") or "").strip()
    role = (item.get("role") or "").strip()
    raw_url = (item.get("url") or "").strip()
    if not company or not role or not raw_url or not raw_url.startswith("http"):
        return "rejected"

    clean_url = dq.canonicalize_url(raw_url)
    is_valid_url, _ = dq.is_dedicated_job_detail_url(clean_url)
    incoming_status = item.get("status", "active")
    if not is_valid_url:
        incoming_status = "pending_review"

    location = (item.get("location") or "United States").strip()
    c_key = dq.compute_canonical_key(company, role, location)

    job_type = item.get("job_type") or dq.classify_job_type(role)
    if job_type == "non_student":
        return "rejected"

    role_category = item.get("role_category")
    category_evidence = item.get("category_evidence")
    if not role_category or role_category == "unclassified":
        role_category, category_evidence = dq.classify_role_category(role)
    ai_label = 1 if role_category == "ai_ml" else 0

    clean_sal = dq.sanitize_salary(item.get("salary"))
    salary_min = item.get("salary_min")
    salary_max = item.get("salary_max")
    salary_period = item.get("salary_period")
    currency = item.get("currency")
    req_skills = dq.sanitize_requirements(item.get("required_skills") or item.get("requirements"))
    pref_skills = dq.sanitize_requirements(item.get("preferred_skills"))
    extraction_evidence = item.get("extraction_evidence")

    now_iso = datetime.utcnow().isoformat()
    posted_at_val = item.get("posted_at")
    posted_at_iso = posted_at_val.isoformat() if isinstance(posted_at_val, datetime) else (str(posted_at_val) if posted_at_val else None)

    first_seen_val = item.get("first_seen_at")
    first_seen_iso = first_seen_val.isoformat() if isinstance(first_seen_val, datetime) else (str(first_seen_val) if first_seen_val else now_iso)

    visa_status = item.get("visa_status") or "not_specified"
    visa_evidence = item.get("visa_evidence")
    if visa_status != "not_specified" and not visa_evidence:
        visa_status = "not_specified"
    visa_source_url = item.get("visa_source_url") or clean_url
    visa_verified_val = item.get("visa_verified_at")
    visa_verified_iso = visa_verified_val.isoformat() if isinstance(visa_verified_val, datetime) else now_iso

    clean_logo = dq.resolve_logo_url(company, item.get("logo_url"))
    industry = item.get("industry") or infer_industry(company, role)

    ex = cur.execute(
        """
        SELECT id, source, source_type, sources_list, url, salary, salary_min, salary_max,
               salary_period, currency, required_skills, preferred_skills, extraction_evidence,
               visa_status, visa_evidence, visa_source_url, visa_verified_at,
               posted_at, first_seen_at, status, status_authority, role_category, category_evidence
        FROM internship
        WHERE canonical_key = ? OR url = ? OR url = ?
        LIMIT 1
        """,
        (c_key, clean_url, raw_url),
    ).fetchone()

    if ex:
        ex_id = ex["id"]
        try:
            ex_sources = json.loads(ex["sources_list"]) if ex["sources_list"] else [ex["source"]]
        except Exception:
            ex_sources = [ex["source"]] if ex["source"] else []
        if source_id not in ex_sources:
            ex_sources.append(source_id)

        old_prio = dq.SOURCE_PRIORITY.get(ex["source_type"] or "community_verified", 0)
        new_prio = dq.SOURCE_PRIORITY.get(source_type, 0)
        auth_prio = dq.SOURCE_PRIORITY.get(ex["status_authority"] or ex["source_type"] or "community_verified", 0)

        new_src = source_id if (new_prio >= old_prio and is_valid_url) else ex["source"]
        new_src_type = source_type if (new_prio >= old_prio and is_valid_url) else ex["source_type"]
        new_url = clean_url if (new_prio >= old_prio and is_valid_url) else ex["url"]

        # Requirement 7: Source-level authority protection on status transitions
        new_status = ex["status"]
        new_authority = ex["status_authority"] or ex["source_type"]
        if incoming_status in ("closed", "expired"):
            if new_prio >= auth_prio or source_id == ex["source"]:
                new_status = incoming_status
                new_authority = source_type
        elif incoming_status == "active" and is_valid_url:
            if ex["status"] in ("closed", "expired"):
                if new_prio > auth_prio or (
                    new_prio == auth_prio and source_type in ("official_api", "public_ats", "official_portal")
                ):
                    new_status = "active"
                    new_authority = source_type
            elif ex["status"] == "pending_review":
                new_status = "active"
                new_authority = source_type
            else:
                if new_prio >= auth_prio:
                    new_authority = source_type

        # Update compensation & skills when incoming has verified values
        final_sal = clean_sal if clean_sal else ex["salary"]
        final_smin = salary_min if salary_min is not None else ex["salary_min"]
        final_smax = salary_max if salary_max is not None else ex["salary_max"]
        final_sper = salary_period if salary_period else ex["salary_period"]
        final_curr = currency if currency else ex["currency"]
        final_req = req_skills if req_skills else ex["required_skills"]
        final_pref = pref_skills if pref_skills else ex["preferred_skills"]
        final_ev = extraction_evidence if extraction_evidence else ex["extraction_evidence"]

        # Update visa status when incoming has explicit evidence
        final_vstatus = visa_status if visa_status != "not_specified" else ex["visa_status"]
        final_vev = visa_evidence if visa_status != "not_specified" else ex["visa_evidence"]
        final_vurl = visa_source_url if visa_status != "not_specified" else ex["visa_source_url"]
        final_vver = visa_verified_iso if visa_status != "not_specified" else ex["visa_verified_at"]

        final_posted = posted_at_iso if posted_at_iso else ex["posted_at"]
        final_cat = role_category if role_category != "unclassified" else ex["role_category"]
        final_cat_ev = category_evidence if role_category != "unclassified" else ex["category_evidence"]

        cur.execute(
            """
            UPDATE internship
            SET source = ?, source_type = ?, sources_list = ?, url = ?, canonical_key = ?,
                job_type = ?, role_category = ?, category_evidence = ?, ai_label = ?,
                salary = ?, salary_min = ?, salary_max = ?, salary_period = ?, currency = ?,
                requirements = ?, required_skills = ?, preferred_skills = ?, extraction_evidence = ?,
                visa_status = ?, visa_evidence = ?, visa_source_url = ?, visa_verified_at = ?,
                international_score = NULL,
                logo_url = ?, posted_at = ?, posted_date = COALESCE(?, posted_date),
                last_verified_at = ?, status = ?, status_authority = ?
            WHERE id = ?
            """,
            (
                new_src, new_src_type, json.dumps(ex_sources), new_url, c_key,
                job_type, final_cat, final_cat_ev, 1 if final_cat == "ai_ml" else 0,
                final_sal, final_smin, final_smax, final_sper, final_curr,
                final_req, final_req, final_pref, final_ev,
                final_vstatus, final_vev, final_vurl, final_vver,
                clean_logo, final_posted, final_posted,
                now_iso, new_status, new_authority,
                ex_id,
            ),
        )
        return "merged"

    cur.execute(
        """
        INSERT INTO internship (
            company, role, location, industry, job_type, role_category, category_evidence, ai_label,
            salary, salary_min, salary_max, salary_period, currency,
            requirements, required_skills, preferred_skills, extraction_evidence,
            visa_status, visa_evidence, visa_source_url, visa_verified_at, international_score,
            logo_url, url, source, source_type, sources_list, canonical_key,
            posted_at, posted_date, first_seen_at, last_verified_at, status, status_authority
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            company, role, location, industry, job_type, role_category, category_evidence, ai_label,
            clean_sal, salary_min, salary_max, salary_period, currency,
            req_skills, req_skills, pref_skills, extraction_evidence,
            visa_status, visa_evidence, visa_source_url, visa_verified_iso,
            clean_logo, clean_url, source_id, source_type, json.dumps([source_id]), c_key,
            posted_at_iso, posted_at_iso or first_seen_iso, first_seen_iso, now_iso, incoming_status, source_type,
        ),
    )
    return "inserted"


def crawl_simplify_readme(source: dict, cur):
    resp = requests.get(source["url"], timeout=25)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table")
    fetched = 0
    inserted = 0
    merged = 0
    closed = 0
    last_company = ""

    for table in tables:
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if not cols or len(cols) < 4:
                continue
            company_col, role_col, location_col, app_col = cols[0], cols[1], cols[2], cols[3]
            raw_company = company_col.get_text(strip=True)
            cleaned_company = re.sub(r"[^\w\s&.,'-]", "", raw_company).strip()
            if not cleaned_company and last_company:
                company_name = last_company
            elif cleaned_company:
                company_name = cleaned_company
                last_company = company_name
            else:
                continue

            raw_role = role_col.get_text(" ", strip=True)
            has_no_sponsor = "🛂" in raw_role or "🛂" in raw_company
            has_us_citizen = "🇺🇸" in raw_role or "🇺🇸" in raw_company
            is_closed = "🔒" in app_col.get_text(strip=True) or "🔒" in raw_role

            role_clean = re.sub(r"[🛂🇺🇸🔒🎓🔥]", "", raw_role).strip()
            role_clean = re.sub(r"\s+", " ", role_clean)
            if not role_clean:
                continue

            if location_col.find("details"):
                loc_clean = location_col.get_text(", ", strip=True)
                loc_clean = re.sub(r"^\d+\s*locations?\s*,?\s*", "", loc_clean, flags=re.IGNORECASE)
            else:
                loc_clean = location_col.get_text(", ", strip=True)
            if not loc_clean:
                loc_clean = "United States"

            c_key = dq.compute_canonical_key(company_name, role_clean, loc_clean)
            if is_closed:
                # Only close if current status_authority is community_verified
                cur.execute(
                    """
                    UPDATE internship
                    SET status = 'closed', last_verified_at = ?
                    WHERE canonical_key = ? AND status = 'active'
                      AND COALESCE(status_authority, 'community_verified') = 'community_verified'
                    """,
                    (datetime.utcnow().isoformat(), c_key),
                )
                if cur.rowcount > 0:
                    closed += cur.rowcount
                continue

            # Requirement 1: Must have a direct application link in app_col (never fall back to company homepage)
            link_tag = app_col.find("a")
            if not link_tag or not link_tag.get("href"):
                continue
            job_url = dq.canonicalize_url(link_tag.get("href"))
            valid_url, _ = dq.is_dedicated_job_detail_url(job_url)
            if not valid_url:
                continue

            # Requirement 2: Community age is an estimate of discovery, NOT an employer posted_at
            first_seen_dt = datetime.utcnow()
            if len(cols) >= 5:
                age_text = cols[4].get_text(strip=True).lower()
                digits = re.sub(r"[^0-9]", "", age_text)
                if digits:
                    val = int(digits)
                    if "h" in age_text:
                        first_seen_dt = datetime.utcnow() - timedelta(hours=val)
                    elif "d" in age_text:
                        first_seen_dt = datetime.utcnow() - timedelta(days=val)
                    elif "mo" in age_text:
                        first_seen_dt = datetime.utcnow() - timedelta(days=val * 30)

            visa_info = dq.classify_visa_status(
                jd_text=None,
                source_url=job_url,
                explicit_flags={
                    "has_no_sponsor_flag": has_no_sponsor,
                    "has_us_citizen_flag": has_us_citizen,
                },
            )
            role_category, category_evidence = dq.classify_role_category(role_clean)
            job_type = dq.classify_job_type(role_clean)

            item = {
                "company": company_name,
                "role": role_clean,
                "location": loc_clean,
                "url": job_url,
                "industry": infer_industry(company_name, role_clean),
                "job_type": job_type,
                "role_category": role_category,
                "category_evidence": category_evidence,
                "posted_at": None,  # No employer publication date in README table
                "first_seen_at": first_seen_dt,
                "visa_status": visa_info["visa_status"],
                "visa_evidence": visa_info["visa_evidence"],
                "visa_source_url": visa_info["visa_source_url"],
                "visa_verified_at": visa_info["visa_verified_at"],
                "logo_url": dq.resolve_logo_url(company_name),
                "status": "active",
            }
            action = upsert_sqlite_row(cur, item, source["id"], "community_verified")
            if action != "rejected":
                fetched += 1
            if action == "inserted":
                inserted += 1
            elif action == "merged":
                merged += 1

    return fetched, inserted, merged, closed


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    ensure_schema(cur)
    audit_and_migrate_existing_rows(cur)
    conn.commit()

    if "--offline-only" in sys.argv:
        conn.close()
        return

    simplify_only = "--simplify-only" in sys.argv

    with open(SOURCES_PATH, "r") as f:
        sources = json.load(f)
    sources.sort(key=lambda s: dq.SOURCE_PRIORITY.get(s.get("source_type", "official_portal"), 50), reverse=True)

    for src in sources:
        if not src.get("enabled", True):
            continue
        src_id = src["id"]
        src_name = src["name"]
        src_type = src.get("type")
        src_tier = src.get("source_type", "official_portal")

        if simplify_only and src_type != "github_readme":
            continue
        if src_type not in ("greenhouse_ats", "lever_ats", "workday_ats", "smartrecruiters_ats", "microsoft_official", "morgan_stanley_official", "github_readme"):
            continue

        logging.info(f"Syncing [{src_tier}] {src_name} ({src_id})...")
        try:
            if src_type == "github_readme":
                crawl_simplify_readme(src, cur)
            elif src_type == "greenhouse_ats":
                for item in crawl_greenhouse(src):
                    upsert_sqlite_row(cur, item, src_id, src_tier)
            elif src_type == "lever_ats":
                for item in crawl_lever(src):
                    upsert_sqlite_row(cur, item, src_id, src_tier)
            elif src_type == "workday_ats":
                for item in crawl_workday(src):
                    upsert_sqlite_row(cur, item, src_id, src_tier)
            elif src_type == "smartrecruiters_ats":
                for item in crawl_smartrecruiters(src):
                    upsert_sqlite_row(cur, item, src_id, src_tier)
            elif src_type == "microsoft_official":
                for item in crawl_microsoft(src):
                    upsert_sqlite_row(cur, item, src_id, src_tier)
            elif src_type == "morgan_stanley_official":
                for item in crawl_morgan_stanley(src):
                    upsert_sqlite_row(cur, item, src_id, src_tier)
            conn.commit()
        except Exception as e:
            logging.error(f"Error syncing {src_name}: {e}")

    conn.close()


if __name__ == "__main__":
    main()
