import html
import json
import logging
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Any

try:
    from data_quality import (
        is_dedicated_job_detail_url,
        classify_job_type,
        classify_role_category,
        classify_visa_status,
        extract_structured_compensation,
        extract_structured_skills,
        resolve_logo_url,
    )
except ImportError:
    from backend.data_quality import (
        is_dedicated_job_detail_url,
        classify_job_type,
        classify_role_category,
        classify_visa_status,
        extract_structured_compensation,
        extract_structured_skills,
        resolve_logo_url,
    )


def _strip_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    unescaped = html.unescape(raw_html)
    soup = BeautifulSoup(unescaped, "html.parser")
    return soup.get_text(" ", strip=True)


def crawl_greenhouse(source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fetch verified internship postings directly from a company's public Greenhouse ATS API:
    https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
    """
    board_token = source_config.get("board_token")
    company_name = source_config.get("company") or source_config.get("name", "").replace(" (Greenhouse ATS)", "")
    industry = source_config.get("industry", "Technology")
    logo_url = resolve_logo_url(company_name, source_config.get("logo_url"))

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
        if not title:
            continue

        raw_content = job.get("content") or ""
        plain_text = _strip_html(raw_content)
        metadata_list = job.get("metadata") or []
        for meta in metadata_list:
            if isinstance(meta, dict) and meta.get("value"):
                plain_text += f" {meta.get('name', '')}: {meta.get('value')}"

        job_type = classify_job_type(title, plain_text)
        if job_type == "non_student":
            continue

        location_obj = job.get("location") or {}
        location_name = (location_obj.get("name") or "United States").strip()

        loc_lower = location_name.lower()
        non_us_markers = [
            "uk", "london", "dublin", "ireland", "germany", "berlin", "munich",
            "france", "paris", "india", "bangalore", "bengaluru", "hyderabad",
            "singapore", "tokyo", "japan", "australia", "sydney", "brazil",
            "são paulo", "sao paulo", "poland", "warsaw", "krakow", "spain",
            "madrid", "barcelona", "netherlands", "amsterdam", "israel", "tel aviv",
            "korea", "seoul", "china", "beijing", "shanghai", "taiwan", "taipei",
            "mexico", "romania", "bucharest", "serbia", "belgrade", "zurich", "switzerland",
        ]
        if any(marker in loc_lower for marker in non_us_markers) and not any(
            us_m in loc_lower for us_m in ["us", "united states", "ny", "ca", "wa", "tx", "il", "ma", "san francisco", "new york", "seattle"]
        ):
            continue

        job_url = (job.get("absolute_url") or "").strip()
        is_valid_url, _ = is_dedicated_job_detail_url(job_url)
        if not is_valid_url:
            continue

        comp = extract_structured_compensation(plain_text)
        skills = extract_structured_skills(plain_text)
        role_category, category_evidence = classify_role_category(title, plain_text)
        visa_info = classify_visa_status(plain_text, job_url)

        evidence_dict = {}
        if comp["salary_quote"]:
            evidence_dict["salary_quote"] = comp["salary_quote"]
        if skills["required_skills_quote"]:
            evidence_dict["required_skills_quote"] = skills["required_skills_quote"]
        if skills["preferred_skills_quote"]:
            evidence_dict["preferred_skills_quote"] = skills["preferred_skills_quote"]

        # Requirement 2: Authentic employer posted_at from Greenhouse API (first_published or updated_at)
        published_str = job.get("first_published") or job.get("updated_at")
        posted_at = None
        if published_str:
            try:
                posted_at = datetime.fromisoformat(published_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                posted_at = None

        internships.append(
            {
                "company": company_name,
                "role": title,
                "location": location_name,
                "url": job_url,
                "industry": industry,
                "job_type": job_type,
                "role_category": role_category,
                "category_evidence": category_evidence,
                "ai_label": role_category == "ai_ml",
                "posted_at": posted_at,
                "salary": comp["salary"],
                "salary_min": comp["salary_min"],
                "salary_max": comp["salary_max"],
                "salary_period": comp["salary_period"],
                "currency": comp["currency"],
                "requirements": skills["required_skills"],
                "required_skills": skills["required_skills"],
                "preferred_skills": skills["preferred_skills"],
                "extraction_evidence": json.dumps(evidence_dict) if evidence_dict else None,
                "visa_status": visa_info["visa_status"],
                "visa_evidence": visa_info["visa_evidence"],
                "visa_source_url": visa_info["visa_source_url"],
                "visa_verified_at": visa_info["visa_verified_at"],
                "logo_url": logo_url,
                "source": source_config.get("id", f"greenhouse_{board_token}"),
                "source_type": "public_ats",
                "status": "active",
            }
        )

    logging.info(f"[Greenhouse ATS] Found {len(internships)} verified student roles for {company_name}")
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
        if not title:
            continue

        desc_plain = job.get("descriptionPlain") or _strip_html(job.get("description") or "")
        lists_text = " ".join(
            f"{lst.get('text', '')}: {_strip_html(lst.get('content') or '')}"
            for lst in (job.get("lists") or [])
            if isinstance(lst, dict)
        )
        additional_plain = job.get("additionalPlain") or _strip_html(job.get("additional") or "")
        full_text = f"{desc_plain} {lists_text} {additional_plain}".strip()

        job_type = classify_job_type(title, full_text)
        if job_type == "non_student":
            continue

        categories = job.get("categories") or {}
        location_name = (categories.get("location") or job.get("country") or "United States").strip()
        job_url = (job.get("hostedUrl") or job.get("applyUrl") or "").strip()
        is_valid_url, _ = is_dedicated_job_detail_url(job_url)
        if not is_valid_url:
            continue

        comp = extract_structured_compensation(full_text, job.get("salaryRange"))
        skills = extract_structured_skills(full_text)
        role_category, category_evidence = classify_role_category(title, full_text)
        visa_info = classify_visa_status(full_text, job_url)

        evidence_dict = {}
        if comp["salary_quote"]:
            evidence_dict["salary_quote"] = comp["salary_quote"]
        if skills["required_skills_quote"]:
            evidence_dict["required_skills_quote"] = skills["required_skills_quote"]
        if skills["preferred_skills_quote"]:
            evidence_dict["preferred_skills_quote"] = skills["preferred_skills_quote"]

        created_at_ms = job.get("createdAt")
        posted_at = None
        if isinstance(created_at_ms, (int, float)) and created_at_ms > 0:
            try:
                posted_at = datetime.utcfromtimestamp(created_at_ms / 1000.0)
            except Exception:
                posted_at = None

        internships.append(
            {
                "company": company_name,
                "role": title,
                "location": location_name,
                "url": job_url,
                "industry": industry,
                "job_type": job_type,
                "role_category": role_category,
                "category_evidence": category_evidence,
                "ai_label": role_category == "ai_ml",
                "posted_at": posted_at,
                "salary": comp["salary"],
                "salary_min": comp["salary_min"],
                "salary_max": comp["salary_max"],
                "salary_period": comp["salary_period"],
                "currency": comp["currency"],
                "requirements": skills["required_skills"],
                "required_skills": skills["required_skills"],
                "preferred_skills": skills["preferred_skills"],
                "extraction_evidence": json.dumps(evidence_dict) if evidence_dict else None,
                "visa_status": visa_info["visa_status"],
                "visa_evidence": visa_info["visa_evidence"],
                "visa_source_url": visa_info["visa_source_url"],
                "visa_verified_at": visa_info["visa_verified_at"],
                "logo_url": logo_url,
                "source": source_config.get("id", f"lever_{site_token}"),
                "source_type": "public_ats",
                "status": "active",
            }
        )

    logging.info(f"[Lever ATS] Found {len(internships)} verified student roles for {company_name}")
    return internships
