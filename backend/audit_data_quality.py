import json
import logging
import os
import random
import re
import sqlite3
import sys
from datetime import datetime
from typing import Dict, Any, List, Tuple

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_SITE = os.path.join(ROOT_DIR, "venv", "lib", "python3.11", "site-packages")
for p in (BACKEND_DIR, ROOT_DIR, VENV_SITE):
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

import requests
import data_quality as dq

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DB_PATH = os.path.join(BACKEND_DIR, "database.db")
AUDIT_REPORT_PATH = os.path.join(BACKEND_DIR, "data_quality_audit.json")


def verify_salary_matches_evidence(row: sqlite3.Row) -> Tuple[bool, str]:
    sal = row["salary"]
    s_min = row["salary_min"]
    s_max = row["salary_max"]
    s_period = row["salary_period"]
    curr = row["currency"]
    ev_raw = row["extraction_evidence"]

    if dq.is_placeholder_salary(sal):
        return False, f"Placeholder or invalid salary string: {sal}"
    if s_min is None or s_max is None or s_min > s_max:
        return False, f"Missing or inverted structured salary bounds: min={s_min}, max={s_max}"
    if s_period not in ("hour", "month", "year") or not curr:
        return False, f"Missing salary_period ({s_period}) or currency ({curr})"
    if not ev_raw:
        return False, "Missing extraction_evidence JSON"

    try:
        ev = json.loads(ev_raw)
    except Exception:
        return False, "Malformed extraction_evidence JSON"

    quote = ev.get("salary_quote") or ""
    if not quote:
        return False, "Missing salary_quote in extraction_evidence"

    # Verify that the numeric bound appears in the verbatim quote
    min_int_str = str(int(round(s_min)))
    min_comma_str = f"{int(round(s_min)):,}"
    if min_int_str not in quote and min_comma_str not in quote:
        return False, f"salary_min ({s_min}) not found in verbatim quote: '{quote}'"

    return True, f"Verified against quote: '{quote[:80]}'"


def run_stratified_audit(sample_size: int = 120, check_live_http: bool = False) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Default internship pool: status == 'active' and job_type in ('internship', 'co-op', 'fellowship')
    active_pool = cur.execute(
        """
        SELECT * FROM internship
        WHERE status = 'active'
          AND job_type IN ('internship', 'co-op', 'fellowship')
        ORDER BY id ASC
        """
    ).fetchall()

    total_all_rows = cur.execute("SELECT COUNT(*) FROM internship").fetchone()[0]
    closed_or_expired_rows = cur.execute(
        "SELECT COUNT(*) FROM internship WHERE status IN ('closed', 'expired', 'stale')"
    ).fetchone()[0]

    # Group by source_type for stratified sampling
    by_tier: Dict[str, List[sqlite3.Row]] = {
        "official_api": [],
        "public_ats": [],
        "official_portal": [],
        "community_verified": [],
    }
    for r in active_pool:
        tier = r["source_type"] or "community_verified"
        by_tier.setdefault(tier, []).append(r)

    random.seed(20261016)
    sampled_rows: List[sqlite3.Row] = []
    sampled_ids = set()

    # Stratified allocation across all tiers:
    # - All available official_api (up to 15)
    # - Up to 45 from public_ats (includes rows with structured salaries & posted_at)
    # - Up to 20 from official_portal
    # - Remaining from community_verified to reach sample_size (120 >= 100)
    tier_quotas = [
        ("official_api", 15),
        ("public_ats", 45),
        ("official_portal", 20),
        ("community_verified", sample_size),
    ]

    for tier, quota in tier_quotas:
        candidates = by_tier.get(tier, [])
        if not candidates:
            continue
        # Prioritize candidates with rich fields (salary, posted_at, visa_status) in sample so denominators are well-tested
        rich = [
            c for c in candidates
            if c["salary"] is not None or c["posted_at"] is not None or c["visa_status"] != "not_specified"
        ]
        rest = [c for c in candidates if c not in rich]
        random.shuffle(rich)
        random.shuffle(rest)
        ordered = rich + rest
        take = min(len(ordered), quota, sample_size - len(sampled_rows))
        for item in ordered[:take]:
            if item["id"] not in sampled_ids:
                sampled_rows.append(item)
                sampled_ids.add(item["id"])

    actual_sample_size = len(sampled_rows)

    # Precompute canonical_key and URL counts across active pool to detect any duplicates
    key_counts: Dict[str, int] = {}
    url_counts: Dict[str, int] = {}
    for r in active_pool:
        ck = r["canonical_key"] or ""
        u = r["url"] or ""
        key_counts[ck] = key_counts.get(ck, 0) + 1
        url_counts[u] = url_counts.get(u, 0) + 1

    valid_url_count = 0
    valid_internship_type_count = 0
    duplicate_in_sample_count = 0

    posted_at_total = 0
    posted_at_valid = 0

    salary_total = 0
    salary_valid = 0

    visa_judged_total = 0
    visa_judged_with_evidence = 0

    sample_audit_log: List[Dict[str, Any]] = []

    # Optional HTTP reachability verification on a subset if check_live_http is enabled
    http_checked = 0
    for idx, row in enumerate(sampled_rows):
        url = row["url"] or ""
        is_dedicated, url_reason = dq.is_dedicated_job_detail_url(url)

        http_ok = True
        if check_live_http and is_dedicated and http_checked < 25:
            http_checked += 1
            try:
                resp = requests.head(url, timeout=6, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 404 or resp.status_code == 410:
                    http_ok = False
                    url_reason = f"HTTP {resp.status_code}"
            except Exception:
                # Network timeout does not invalidate URL format if dedicated job ID is present
                pass

        url_valid = is_dedicated and http_ok
        if url_valid:
            valid_url_count += 1

        # 2. Internship job_type accuracy
        reclassified_type = dq.classify_job_type(row["role"])
        is_target_internship = (
            row["job_type"] in dq.DEFAULT_INTERNSHIP_JOB_TYPES
            and reclassified_type in dq.DEFAULT_INTERNSHIP_JOB_TYPES
        )
        if is_target_internship:
            valid_internship_type_count += 1

        # 3. Duplicate check
        is_dup = key_counts.get(row["canonical_key"] or "", 0) > 1 or url_counts.get(url, 0) > 1
        if is_dup:
            duplicate_in_sample_count += 1

        # 4. Posted date accuracy
        posted_at = row["posted_at"]
        posted_ok = None
        if posted_at is not None:
            posted_at_total += 1
            # Must come from an authoritative ATS/API source that provides real timestamps and be valid ISO date
            try:
                dt = datetime.fromisoformat(str(posted_at).replace("Z", "+00:00")).replace(tzinfo=None)
                posted_ok = row["source_type"] in ("public_ats", "official_api") and dt <= datetime.utcnow()
            except Exception:
                posted_ok = False
            if posted_ok:
                posted_at_valid += 1

        # 5. Salary accuracy
        sal_ok = None
        sal_reason = None
        if row["salary"] is not None or row["salary_min"] is not None:
            salary_total += 1
            sal_ok, sal_reason = verify_salary_matches_evidence(row)
            if sal_ok:
                salary_valid += 1

        # 6. Visa status evidence coverage
        v_status = row["visa_status"] or "not_specified"
        visa_ev_ok = None
        if v_status in ("explicitly_restricted", "sponsorship_explicitly_supported", "needs_review"):
            visa_judged_total += 1
            visa_ev_ok = bool(
                row["visa_evidence"]
                and len(str(row["visa_evidence"]).strip()) >= 5
                and row["visa_source_url"]
                and row["visa_verified_at"]
                and row["international_score"] is None
            )
            if visa_ev_ok:
                visa_judged_with_evidence += 1

        if len(sample_audit_log) < 25:
            sample_audit_log.append(
                {
                    "id": row["id"],
                    "company": row["company"],
                    "role": row["role"],
                    "source": row["source"],
                    "source_type": row["source_type"],
                    "job_type": row["job_type"],
                    "role_category": row["role_category"],
                    "url_valid": url_valid,
                    "is_target_internship": is_target_internship,
                    "is_duplicate": is_dup,
                    "posted_at": row["posted_at"],
                    "posted_at_valid": posted_ok,
                    "salary": row["salary"],
                    "salary_valid": sal_ok,
                    "visa_status": v_status,
                    "visa_evidence_valid": visa_ev_ok,
                }
            )

    # Compute rates and compare against targets
    url_validity_rate = round((valid_url_count / actual_sample_size) * 100, 2) if actual_sample_size else 0.0
    internship_accuracy_rate = round((valid_internship_type_count / actual_sample_size) * 100, 2) if actual_sample_size else 0.0
    duplicate_rate = round((duplicate_in_sample_count / actual_sample_size) * 100, 2) if actual_sample_size else 0.0
    posted_date_accuracy_rate = round((posted_at_valid / posted_at_total) * 100, 2) if posted_at_total else 100.0
    salary_accuracy_rate = round((salary_valid / salary_total) * 100, 2) if salary_total else 100.0
    visa_evidence_coverage_rate = round((visa_judged_with_evidence / visa_judged_total) * 100, 2) if visa_judged_total else 100.0
    expired_filtered_rate = round((closed_or_expired_rows / total_all_rows) * 100, 2) if total_all_rows else 0.0

    metrics = {
        "valid_unique_url_rate": {
            "value_pct": url_validity_rate,
            "numerator": valid_url_count,
            "denominator": actual_sample_size,
            "target_pct": ">= 98.0%",
            "passed": url_validity_rate >= 98.0,
        },
        "internship_type_accuracy": {
            "value_pct": internship_accuracy_rate,
            "numerator": valid_internship_type_count,
            "denominator": actual_sample_size,
            "target_pct": ">= 95.0%",
            "passed": internship_accuracy_rate >= 95.0,
        },
        "duplicate_record_rate": {
            "value_pct": duplicate_rate,
            "numerator": duplicate_in_sample_count,
            "denominator": actual_sample_size,
            "target_pct": "<= 2.0%",
            "passed": duplicate_rate <= 2.0,
        },
        "posted_date_accuracy": {
            "value_pct": posted_date_accuracy_rate,
            "numerator": posted_at_valid,
            "denominator": posted_at_total,
            "target_pct": ">= 95.0%",
            "passed": posted_date_accuracy_rate >= 95.0,
        },
        "salary_accuracy": {
            "value_pct": salary_accuracy_rate,
            "numerator": salary_valid,
            "denominator": salary_total,
            "target_pct": ">= 98.0%",
            "passed": salary_accuracy_rate >= 98.0,
        },
        "visa_evidence_coverage": {
            "value_pct": visa_evidence_coverage_rate,
            "numerator": visa_judged_with_evidence,
            "denominator": visa_judged_total,
            "target_pct": "100.0%",
            "passed": visa_evidence_coverage_rate == 100.0,
        },
    }

    passed_all = all(m["passed"] for m in metrics.values()) and actual_sample_size >= 100

    report = {
        "audited_at": datetime.utcnow().isoformat(),
        "sample_size": actual_sample_size,
        "stratified_sample_breakdown": {
            tier: sum(1 for r in sampled_rows if (r["source_type"] or "community_verified") == tier)
            for tier in ("official_api", "public_ats", "official_portal", "community_verified")
        },
        "population_summary": {
            "total_records_in_db": total_all_rows,
            "verified_active_internships": len(active_pool),
            "closed_or_expired_filtered": closed_or_expired_rows,
            "expired_or_closed_rate_pct": expired_filtered_rate,
        },
        "passed_all_targets": passed_all,
        "metrics": metrics,
        "sample_preview": sample_audit_log,
    }

    with open(AUDIT_REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    conn.close()
    logging.info(f"Data Quality Audit Complete (n={actual_sample_size}): passed_all_targets={passed_all}")
    for k, v in metrics.items():
        logging.info(f"  - {k}: {v['value_pct']}% ({v['numerator']}/{v['denominator']}) [Target {v['target_pct']}] -> PASS={v['passed']}")
    return report


if __name__ == "__main__":
    live_flag = "--live-http" in sys.argv
    run_stratified_audit(sample_size=120, check_live_http=live_flag)
