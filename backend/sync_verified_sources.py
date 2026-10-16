import os
import sys

# Ensure venv pure-python packages (requests, bs4) and backend modules are importable
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
from crawlers.ats import crawl_greenhouse, crawl_lever
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


def upsert_sqlite_row(cur, item: dict, source_id: str, source_type: str) -> str:
    company = (item.get("company") or "").strip()
    role = (item.get("role") or "").strip()
    raw_url = (item.get("url") or "").strip()
    if not company or not role or not raw_url or not raw_url.startswith("http"):
        return "rejected"

    location = (item.get("location") or "United States").strip()
    clean_url = dq.canonicalize_url(raw_url)
    c_key = dq.compute_canonical_key(company, role, location)
    clean_sal = dq.sanitize_salary(item.get("salary"))
    clean_req = dq.sanitize_requirements(item.get("requirements"))
    clean_logo = dq.resolve_logo_url(company, item.get("logo_url"))
    now_iso = datetime.utcnow().isoformat()
    posted_dt = item.get("posted_date")
    if isinstance(posted_dt, datetime):
        posted_iso = posted_dt.isoformat()
    else:
        posted_iso = str(posted_dt) if posted_dt else now_iso

    industry = item.get("industry") or infer_industry(company, role)
    ai_label = 1 if item.get("ai_label") else 0
    intl_score = int(item.get("international_score", 7))
    incoming_status = item.get("status", "active")

    ex = cur.execute(
        "SELECT id, source, source_type, sources_list, url, salary, requirements, status FROM internship WHERE canonical_key = ? OR url = ? OR url = ? LIMIT 1",
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
        new_src = source_id if new_prio >= old_prio else ex["source"]
        new_src_type = source_type if new_prio >= old_prio else ex["source_type"]
        new_url = clean_url if new_prio >= old_prio else ex["url"]
        new_status = incoming_status if new_prio >= old_prio else ex["status"]

        cur.execute(
            """
            UPDATE internship
            SET source = ?, source_type = ?, sources_list = ?, url = ?, canonical_key = ?,
                salary = COALESCE(?, salary),
                requirements = COALESCE(?, requirements),
                logo_url = ?,
                last_verified_at = ?,
                status = ?
            WHERE id = ?
            """,
            (
                new_src,
                new_src_type,
                json.dumps(ex_sources),
                new_url,
                c_key,
                clean_sal,
                clean_req,
                clean_logo,
                now_iso,
                new_status,
                ex_id,
            ),
        )
        return "merged"

    cur.execute(
        """
        INSERT INTO internship (
            company, role, location, industry, ai_label, requirements, salary,
            international_score, logo_url, url, source, source_type, sources_list,
            canonical_key, posted_date, first_seen_at, last_verified_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            company,
            role,
            location,
            industry,
            ai_label,
            clean_req,
            clean_sal,
            intl_score,
            clean_logo,
            clean_url,
            source_id,
            source_type,
            json.dumps([source_id]),
            c_key,
            posted_iso,
            posted_iso,
            now_iso,
            incoming_status,
        ),
    )
    return "inserted"


def record_alert_sqlite(cur, source_id: str, source_name: str, alert_type: str, severity: str, message: str, details: dict):
    now_iso = datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT INTO crawleralert (source_id, source_name, alert_type, severity, message, details, created_at, resolved)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (source_id, source_name, alert_type, severity, message, json.dumps(details), now_iso),
    )


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
            no_sponsor = "🛂" in raw_role or "🛂" in raw_company or "🇺🇸" in raw_role or "🇺🇸" in raw_company
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
                cur.execute(
                    "UPDATE internship SET status = 'closed', last_verified_at = ? WHERE canonical_key = ? AND status = 'active'",
                    (datetime.utcnow().isoformat(), c_key),
                )
                if cur.rowcount > 0:
                    closed += cur.rowcount
                continue

            link_tag = app_col.find("a")
            if not link_tag or not link_tag.get("href"):
                continue
            job_url = dq.canonicalize_url(link_tag.get("href"))

            posted_date = datetime.utcnow()
            if len(cols) >= 5:
                age_text = cols[4].get_text(strip=True).lower()
                digits = re.sub(r"[^0-9]", "", age_text)
                if digits:
                    val = int(digits)
                    if "h" in age_text:
                        posted_date = datetime.utcnow() - timedelta(hours=val)
                    elif "d" in age_text:
                        posted_date = datetime.utcnow() - timedelta(days=val)
                    elif "mo" in age_text:
                        posted_date = datetime.utcnow() - timedelta(days=val * 30)

            intl_score = 1 if no_sponsor else 7
            item = {
                "company": company_name,
                "role": role_clean,
                "location": loc_clean,
                "url": job_url,
                "industry": infer_industry(company_name, role_clean),
                "ai_label": bool(re.search(r"\b(ai|ml|machine learning|data science|deep learning|llm|nlp|computer vision)\b", role_clean, re.IGNORECASE)),
                "posted_date": posted_date,
                "salary": None,
                "requirements": None,
                "international_score": intl_score,
                "logo_url": dq.resolve_logo_url(company_name),
                "status": "active",
            }
            action = upsert_sqlite_row(cur, item, source["id"], "community_verified")
            fetched += 1
            if action == "inserted":
                inserted += 1
            elif action == "merged":
                merged += 1

    return fetched, inserted, merged, closed


def main():
    with open(SOURCES_PATH, "r") as f:
        sources = json.load(f)
    sources.sort(key=lambda s: dq.SOURCE_PRIORITY.get(s.get("source_type", "official_portal"), 50), reverse=True)

    status_map = {}
    if os.path.exists(STATUS_PATH):
        try:
            with open(STATUS_PATH, "r") as f:
                status_map = json.load(f)
        except Exception:
            status_map = {}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    for src in sources:
        if not src.get("enabled", True):
            continue
        src_id = src["id"]
        src_name = src["name"]
        src_type = src.get("type")
        src_tier = src.get("source_type", "official_portal")

        # Skip Playwright browser-only portals in lightweight sync, but evaluate any existing 0-item portals for alerts
        if src_type in ("nasa_official", "goldman_sachs_official", "jpmorgan_chase_official"):
            prev = status_map.get(src_name, {})
            if prev.get("items_saved", 0) == 0:
                msg = f"{src_name} returned 0 listings during last browser crawl (possible anti-bot wall or closed recruiting window)."
                # Avoid duplicate unresolved alerts
                existing_alert = cur.execute(
                    "SELECT id FROM crawleralert WHERE source_id = ? AND resolved = 0 LIMIT 1",
                    (src_id,),
                ).fetchone()
                if not existing_alert:
                    record_alert_sqlite(cur, src_id, src_name, "zero_results", "warning", msg, {"items_fetched": 0})
                status_map[src_name] = {
                    "source_id": src_id,
                    "source_name": src_name,
                    "source_type": src_tier,
                    "date": prev.get("date", today_str),
                    "timestamp": prev.get("timestamp", datetime.utcnow().isoformat()),
                    "items_fetched": 0,
                    "items_saved": 0,
                    "items_merged": 0,
                    "items_closed": 0,
                    "status": "warning",
                    "alert": msg,
                }
            continue

        if src_type in ("meta_official", "apple_official", "google_official", "amazon_official"):
            # Keep existing portal status metadata enriched with source_id and source_type
            prev = status_map.get(src_name, {})
            if prev:
                prev["source_id"] = src_id
                prev["source_name"] = src_name
                prev["source_type"] = src_tier
                prev.setdefault("items_fetched", prev.get("items_saved", 0))
                prev.setdefault("items_merged", 0)
                prev.setdefault("items_closed", 0)
                status_map[src_name] = prev
            continue

        logging.info(f"Syncing [{src_tier}] {src_name} ({src_id})...")
        fetched = 0
        inserted = 0
        merged = 0
        closed = 0
        err_str = None

        try:
            if src_type == "github_readme":
                fetched, inserted, merged, closed = crawl_simplify_readme(src, cur)
            elif src_type == "greenhouse_ats":
                items = crawl_greenhouse(src)
                fetched = len(items)
                for item in items:
                    act = upsert_sqlite_row(cur, item, src_id, src_tier)
                    if act == "inserted":
                        inserted += 1
                    elif act == "merged":
                        merged += 1
            elif src_type == "lever_ats":
                items = crawl_lever(src)
                fetched = len(items)
                for item in items:
                    act = upsert_sqlite_row(cur, item, src_id, src_tier)
                    if act == "inserted":
                        inserted += 1
                    elif act == "merged":
                        merged += 1
            elif src_type == "microsoft_official":
                items = crawl_microsoft(src)
                fetched = len(items)
                for item in items:
                    act = upsert_sqlite_row(cur, item, src_id, src_tier)
                    if act == "inserted":
                        inserted += 1
                    elif act == "merged":
                        merged += 1
            elif src_type == "morgan_stanley_official":
                items = crawl_morgan_stanley(src)
                fetched = len(items)
                for item in items:
                    act = upsert_sqlite_row(cur, item, src_id, src_tier)
                    if act == "inserted":
                        inserted += 1
                    elif act == "merged":
                        merged += 1
        except Exception as e:
            err_str = str(e)
            logging.error(f"Error syncing {src_name}: {e}")

        now_iso = datetime.utcnow().isoformat()
        if err_str:
            msg = f"Failed to collect from {src_name}: {err_str}"
            record_alert_sqlite(cur, src_id, src_name, "exception", "critical", msg, {"error": err_str})
            status_map[src_name] = {
                "source_id": src_id,
                "source_name": src_name,
                "source_type": src_tier,
                "date": today_str,
                "timestamp": now_iso,
                "items_fetched": 0,
                "items_saved": 0,
                "items_merged": 0,
                "items_closed": 0,
                "status": "failed",
                "alert": msg,
            }
        elif fetched == 0:
            msg = f"{src_name} returned 0 active internship listings."
            record_alert_sqlite(cur, src_id, src_name, "zero_results", "warning", msg, {"items_fetched": 0})
            status_map[src_name] = {
                "source_id": src_id,
                "source_name": src_name,
                "source_type": src_tier,
                "date": today_str,
                "timestamp": now_iso,
                "items_fetched": 0,
                "items_saved": 0,
                "items_merged": 0,
                "items_closed": 0,
                "status": "warning",
                "alert": msg,
            }
        else:
            cur.execute("UPDATE crawleralert SET resolved = 1, resolved_at = ? WHERE source_id = ? AND resolved = 0", (now_iso, src_id))
            status_map[src_name] = {
                "source_id": src_id,
                "source_name": src_name,
                "source_type": src_tier,
                "date": today_str,
                "timestamp": now_iso,
                "items_fetched": fetched,
                "items_saved": inserted,
                "items_merged": merged,
                "items_closed": closed,
                "status": "success",
                "alert": None,
            }
        conn.commit()

    with open(STATUS_PATH, "w") as f:
        json.dump(status_map, f, indent=2)

    # Print summary stats
    stats = cur.execute(
        "SELECT status, COUNT(*) as c FROM internship GROUP BY status"
    ).fetchall()
    tiers = cur.execute(
        "SELECT source_type, COUNT(*) as c FROM internship WHERE status = 'active' GROUP BY source_type"
    ).fetchall()
    real_salaries = cur.execute(
        "SELECT COUNT(*) FROM internship WHERE salary IS NOT NULL AND status = 'active'"
    ).fetchone()[0]
    real_reqs = cur.execute(
        "SELECT COUNT(*) FROM internship WHERE requirements IS NOT NULL AND status = 'active'"
    ).fetchone()[0]
    multi_source = cur.execute(
        "SELECT COUNT(*) FROM internship WHERE sources_list LIKE '%,%'"
    ).fetchone()[0]
    alerts_count = cur.execute(
        "SELECT COUNT(*) FROM crawleralert WHERE resolved = 0"
    ).fetchone()[0]

    logging.info(f"By status: {[(r['status'], r['c']) for r in stats]}")
    logging.info(f"Active by source_type: {[(r['source_type'], r['c']) for r in tiers]}")
    logging.info(f"Verified salaries: {real_salaries}, Verified requirements: {real_reqs}, Cross-source merged: {multi_source}, Active alerts: {alerts_count}")
    conn.close()


if __name__ == "__main__":
    main()
