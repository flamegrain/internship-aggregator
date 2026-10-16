import html
import logging
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Any

try:
    from data_quality import (
        extract_verified_salary_from_text,
        extract_verified_requirements_from_text,
        resolve_logo_url,
    )
except ImportError:
    from backend.data_quality import (
        extract_verified_salary_from_text,
        extract_verified_requirements_from_text,
        resolve_logo_url,
    )

INTERN_KEYWORDS = re.compile(
    r"\b(intern|internship|co-op|coop|fellowship|summer\s+analyst|campus|university\s+grad)\b",
    re.IGNORECASE,
)

AI_KEYWORDS = re.compile(
    r"\b(ai|artificial intelligence|machine learning|ml|deep learning|llm|nlp|computer vision|data science|research)\b",
    re.IGNORECASE,
)


def _strip_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    unescaped = html.unescape(raw_html)
    soup = BeautifulSoup(unescaped, "html.parser")
    return soup.get_text(" ", strip=True)


def _score_international_from_jd(jd_text: str, default_score: int = 7) -> int:
    if not jd_text:
        return default_score
    upper = jd_text.upper()
    negatives = [
        "US CITIZEN",
        "U.S. CITIZEN",
        "SECURITY CLEARANCE",
        "DO NOT SPONSOR",
        "UNABLE TO SPONSOR",
        "WILL NOT SPONSOR",
        "NO VISA SPONSORSHIP",
        "CITIZENSHIP REQUIRED",
    ]
    for neg in negatives:
        if neg in upper:
            return 1

    score = default_score
    positives = [
        "VISA SPONSORSHIP",
        "SPONSOR VISAS",
        "F-1",
        "CPT",
        "OPT",
        "STEM OPT",
        "H-1B",
        "INTERNATIONAL STUDENTS",
    ]
    for pos in positives:
        if pos in upper:
            score += 1
    return max(1, min(10, score))


def crawl_greenhouse(source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fetch verified internship postings directly from a company's public Greenhouse ATS API:
    https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
    """
    board_token = source_config.get("board_token")
    company_name = source_config.get("company") or source_config.get("name", "").replace(" (Greenhouse ATS)", "")
    industry = source_config.get("industry", "Technology")
    logo_url = resolve_logo_url(company_name, source_config.get("logo_url"))
    default_intl = source_config.get("default_international_score", 7)

    api_url = source_config.get("url") or f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    if "content=true" not in api_url:
        sep = "&" if "?" in api_url else "?"
        api_url = f"{api_url}{sep}content=true"

    logging.info(f"[Greenhouse ATS] Fetching {company_name} from {api_url}")
    resp = requests.get(api_url, timeout=20, headers={"Accept": "application/json"})
    resp.raise_for_status()
    payload = resp.json()
    jobs = payload.get("jobs", [])

    internships: List[Dict[str, Any]] = []
    for job in jobs:
        title = (job.get("title") or "").strip()
        if not title or not INTERN_KEYWORDS.search(title):
            continue

        location_obj = job.get("location") or {}
        location_name = (location_obj.get("name") or "United States").strip()

        # Filter out clearly non-US / non-North America roles unless Remote
        loc_lower = location_name.lower()
        non_us_markers = [
            "uk", "london", "dublin", "ireland", "germany", "berlin", "munich",
            "france", "paris", "india", "bangalore", "bengaluru", "hyderabad",
            "singapore", "tokyo", "japan", "australia", "sydney", "brazil",
            "são paulo", "sao paulo", "poland", "warsaw", "krakow", "spain",
            "madrid", "barcelona", "netherlands", "amsterdam", "israel", "tel aviv",
            "korea", "seoul", "china", "beijing", "shanghai", "taiwan", "taipei",
            "mexico", "romania", "bucharest", "serbia", "belgrade",
        ]
        if any(marker in loc_lower for marker in non_us_markers) and not any(
            us_m in loc_lower for us_m in ["us", "united states", "ny", "ca", "wa", "tx", "il", "ma", "san francisco", "new york", "seattle"]
        ):
            continue

        job_url = job.get("absolute_url")
        if not job_url:
            continue

        raw_content = job.get("content") or ""
        plain_text = _strip_html(raw_content)

        # Also inspect metadata if present
        metadata_list = job.get("metadata") or []
        for meta in metadata_list:
            if isinstance(meta, dict) and meta.get("value"):
                plain_text += f" {meta.get('name', '')}: {meta.get('value')}"

        verified_salary = extract_verified_salary_from_text(plain_text)
        verified_reqs = extract_verified_requirements_from_text(plain_text)
        intl_score = _score_international_from_jd(plain_text, default_score=default_intl)

        updated_at_str = job.get("updated_at") or job.get("first_published")
        posted_date = datetime.utcnow()
        if updated_at_str:
            try:
                posted_date = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                posted_date = datetime.utcnow()

        internships.append(
            {
                "company": company_name,
                "role": title,
                "location": location_name,
                "url": job_url,
                "industry": industry,
                "ai_label": bool(AI_KEYWORDS.search(title)),
                "posted_date": posted_date,
                "salary": verified_salary,
                "requirements": verified_reqs,
                "international_score": intl_score,
                "logo_url": logo_url,
                "source": source_config.get("id", f"greenhouse_{board_token}"),
                "source_type": "public_ats",
                "status": "active",
            }
        )

    logging.info(f"[Greenhouse ATS] Found {len(internships)} verified internships for {company_name}")
    return internships


def crawl_lever(source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fetch verified internship postings directly from a company's public Lever ATS API:
    https://api.lever.co/v0/postings/{site}?mode=json
    """
    site_token = source_config.get("site_token")
    company_name = source_config.get("company") or source_config.get("name", "").replace(" (Lever ATS)", "")
    industry = source_config.get("industry", "Technology")
    logo_url = resolve_logo_url(company_name, source_config.get("logo_url"))
    default_intl = source_config.get("default_international_score", 7)

    api_url = source_config.get("url") or f"https://api.lever.co/v0/postings/{site_token}?mode=json"
    logging.info(f"[Lever ATS] Fetching {company_name} from {api_url}")
    resp = requests.get(api_url, timeout=20, headers={"Accept": "application/json"})
    resp.raise_for_status()
    jobs = resp.json()
    if not isinstance(jobs, list):
        return []

    internships: List[Dict[str, Any]] = []
    for job in jobs:
        title = (job.get("text") or "").strip()
        categories = job.get("categories") or {}
        commitment = (categories.get("commitment") or "").strip()
        if not title:
            continue
        if not INTERN_KEYWORDS.search(title) and "intern" not in commitment.lower():
            continue

        location_name = (categories.get("location") or job.get("country") or "United States").strip()
        job_url = job.get("hostedUrl") or job.get("applyUrl")
        if not job_url:
            continue

        desc_plain = job.get("descriptionPlain") or _strip_html(job.get("description") or "")
        lists_text = " ".join(
            _strip_html(lst.get("content") or "")
            for lst in (job.get("lists") or [])
            if isinstance(lst, dict)
        )
        additional_plain = job.get("additionalPlain") or _strip_html(job.get("additional") or "")
        full_text = f"{desc_plain} {lists_text} {additional_plain}".strip()

        # Check structured salaryRange on Lever if available
        verified_salary = None
        salary_range = job.get("salaryRange")
        if isinstance(salary_range, dict) and salary_range.get("min") and salary_range.get("max"):
            s_min = salary_range.get("min")
            s_max = salary_range.get("max")
            interval = (salary_range.get("interval") or "").lower()
            if "hour" in interval:
                verified_salary = f"${int(s_min)} - ${int(s_max)} / hr"
            elif "month" in interval:
                verified_salary = f"${int(s_min):,} - ${int(s_max):,} / mo"
            elif "year" in interval or "annual" in interval:
                verified_salary = f"${int(s_min):,} - ${int(s_max):,} / yr"

        if not verified_salary:
            verified_salary = extract_verified_salary_from_text(full_text)

        verified_reqs = extract_verified_requirements_from_text(full_text)
        intl_score = _score_international_from_jd(full_text, default_score=default_intl)

        created_at_ms = job.get("createdAt")
        posted_date = datetime.utcnow()
        if isinstance(created_at_ms, (int, float)) and created_at_ms > 0:
            try:
                posted_date = datetime.utcfromtimestamp(created_at_ms / 1000.0)
            except Exception:
                posted_date = datetime.utcnow()

        internships.append(
            {
                "company": company_name,
                "role": title,
                "location": location_name,
                "url": job_url,
                "industry": industry,
                "ai_label": bool(AI_KEYWORDS.search(title)),
                "posted_date": posted_date,
                "salary": verified_salary,
                "requirements": verified_reqs,
                "international_score": intl_score,
                "logo_url": logo_url,
                "source": source_config.get("id", f"lever_{site_token}"),
                "source_type": "public_ats",
                "status": "active",
            }
        )

    logging.info(f"[Lever ATS] Found {len(internships)} verified internships for {company_name}")
    return internships
