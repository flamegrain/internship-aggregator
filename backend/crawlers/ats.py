import html
import json
import logging
import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

try:
    from data_quality import (
        is_dedicated_job_detail_url,
        classify_job_type,
        classify_role_category,
        classify_visa_status,
        extract_structured_compensation,
        extract_structured_skills,
        resolve_logo_url,
        canonicalize_url,
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
        canonicalize_url,
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


def crawl_workday(source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fetch verified internship postings directly from a company's public Workday CXS API:
    POST {host}/wday/cxs/{tenant}/{client_id}/jobs
    GET {host}/wday/cxs/{tenant}/{client_id}{externalPath}
    Supports Workday wd1, wd3, wd5, wd12 portals (e.g., NVIDIA, Adobe, Salesforce, Boeing, Intel, Capital One).
    """
    company_name = source_config.get("company") or source_config.get("name", "").replace(" (Workday ATS)", "")
    industry = source_config.get("industry", "Technology")
    logo_url = resolve_logo_url(company_name, source_config.get("logo_url"))

    host = (source_config.get("host") or "").rstrip("/")
    tenant = source_config.get("tenant") or ""
    client_id = source_config.get("client_id") or ""
    raw_url = source_config.get("url") or ""

    if not host or not tenant or not client_id:
        m = re.match(r"(https?://[^/]+)/wday/cxs/([^/]+)/([^/]+)", raw_url)
        if m:
            host, tenant, client_id = m.group(1), m.group(2), m.group(3)
        else:
            m2 = re.match(r"(https?://([^.]+)\.[^/]+)/?(?:[a-zA-Z-]+/)?([^/]+)?", raw_url)
            if m2:
                host = m2.group(1)
                tenant = tenant or m2.group(2)
                client_id = client_id or m2.group(3) or "External"

    if not host or not tenant or not client_id:
        logging.error(f"[Workday ATS] Invalid Workday configuration for {company_name}: host={host}, tenant={tenant}, client_id={client_id}")
        return []

    cxs_base = f"{host}/wday/cxs/{tenant}/{client_id}"
    api_jobs_url = f"{cxs_base}/jobs"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    }

    search_terms = source_config.get("search_terms") or ["intern", "internship", "co-op", "summer"]
    logging.info(f"[Workday ATS] Fetching {company_name} from {api_jobs_url} with terms {search_terms}")

    seen_paths = set()
    raw_postings = []

    for term in search_terms:
        payload = {"limit": 20, "offset": 0, "searchText": term}
        try:
            resp = requests.post(api_jobs_url, json=payload, headers=headers, timeout=20)
            if resp.status_code != 200:
                continue
            data = resp.json()
            postings = data.get("jobPostings", [])
            for p in postings:
                ext_path = p.get("externalPath")
                if ext_path and ext_path not in seen_paths:
                    seen_paths.add(ext_path)
                    raw_postings.append(p)
        except Exception as e:
            logging.warning(f"[Workday ATS] Search error for {company_name} (term={term}): {e}")

    internships: List[Dict[str, Any]] = []
    non_us_markers = [
        "uk", "london", "dublin", "ireland", "germany", "berlin", "munich",
        "france", "paris", "india", "bangalore", "bengaluru", "hyderabad",
        "singapore", "tokyo", "japan", "australia", "sydney", "brazil",
        "são paulo", "sao paulo", "poland", "warsaw", "krakow", "spain",
        "madrid", "barcelona", "netherlands", "amsterdam", "israel", "tel aviv",
        "korea", "seoul", "china", "beijing", "shanghai", "taiwan", "taipei",
        "mexico", "romania", "bucharest", "serbia", "belgrade", "zurich", "switzerland",
        "philippines", "costa rica", "malaysia",
    ]

    for p in raw_postings:
        title = (p.get("title") or "").strip()
        if not title:
            continue

        ext_path = p.get("externalPath")
        if not ext_path:
            continue

        loc_text = (p.get("locationsText") or "United States").strip()
        loc_lower = loc_text.lower()
        if any(marker in loc_lower for marker in non_us_markers) and not any(
            us_m in loc_lower for us_m in ["us", "united states", "ny", "ca", "wa", "tx", "il", "ma", "san francisco", "new york", "seattle"]
        ):
            continue

        detail_api_url = f"{cxs_base}{ext_path}"
        try:
            d_resp = requests.get(detail_api_url, headers=headers, timeout=15)
            if d_resp.status_code != 200:
                continue
            info = d_resp.json().get("jobPostingInfo", {})
        except Exception as e:
            logging.warning(f"[Workday ATS] Error fetching detail for {title}: {e}")
            continue

        desc_html = info.get("jobDescription") or ""
        plain_text = _strip_html(desc_html)

        job_type = classify_job_type(title, plain_text)
        if job_type == "non_student":
            continue

        job_location = (info.get("location") or loc_text).strip()
        raw_job_url = info.get("externalUrl") or f"{host}/en-US/{client_id}{ext_path}"
        job_url = canonicalize_url(raw_job_url)

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

        posted_at = None
        start_date = info.get("startDate")
        if start_date:
            try:
                posted_at = datetime.fromisoformat(start_date.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                posted_at = None

        if not posted_at and info.get("postedOn"):
            posted_str = info.get("postedOn", "").strip()
            now = datetime.utcnow()
            if "today" in posted_str.lower():
                posted_at = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif "yesterday" in posted_str.lower():
                posted_at = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                m_days = re.search(r"(\d+)\s+days?\s+ago", posted_str, re.IGNORECASE)
                if m_days:
                    posted_at = (now - timedelta(days=int(m_days.group(1)))).replace(hour=0, minute=0, second=0, microsecond=0)

        internships.append(
            {
                "company": company_name,
                "role": title,
                "location": job_location,
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
                "source": source_config.get("id", f"workday_{tenant}"),
                "source_type": "public_ats",
                "status": "active",
            }
        )

    logging.info(f"[Workday ATS] Found {len(internships)} verified student roles for {company_name}")
    return internships


def crawl_smartrecruiters(source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fetch verified internship postings directly from a company's public SmartRecruiters API:
    https://api.smartrecruiters.com/v1/companies/{company_identifier}/postings
    https://api.smartrecruiters.com/v1/companies/{company_identifier}/postings/{posting_id}
    """
    company_name = source_config.get("company") or source_config.get("name", "").replace(" (SmartRecruiters ATS)", "")
    industry = source_config.get("industry", "Technology")
    logo_url = resolve_logo_url(company_name, source_config.get("logo_url"))

    company_id = source_config.get("company_identifier") or source_config.get("company_id")
    if not company_id and source_config.get("url"):
        m = re.search(r"/companies/([^/?#]+)", source_config["url"])
        if m:
            company_id = m.group(1)

    if not company_id:
        logging.error(f"[SmartRecruiters ATS] Missing company_identifier for {company_name}")
        return []

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    }

    base_api = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
    logging.info(f"[SmartRecruiters ATS] Fetching {company_name} from {base_api}")

    raw_jobs = []
    seen_ids = set()

    for query_param in ["?limit=100&q=intern", "?limit=100&q=co-op", "?limit=100"]:
        try:
            resp = requests.get(f"{base_api}{query_param}", headers=headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                for j in data.get("content", []):
                    j_id = j.get("id")
                    if j_id and j_id not in seen_ids:
                        seen_ids.add(j_id)
                        raw_jobs.append(j)
        except Exception as e:
            logging.warning(f"[SmartRecruiters ATS] Error fetching list for {company_name}: {e}")

    internships: List[Dict[str, Any]] = []
    non_us_markers = [
        "uk", "london", "dublin", "ireland", "germany", "berlin", "munich",
        "france", "paris", "india", "bangalore", "bengaluru", "hyderabad",
        "singapore", "tokyo", "japan", "australia", "sydney", "brazil",
        "são paulo", "sao paulo", "poland", "warsaw", "krakow", "spain",
        "madrid", "barcelona", "netherlands", "amsterdam", "israel", "tel aviv",
        "korea", "seoul", "china", "beijing", "shanghai", "taiwan", "taipei",
        "mexico", "romania", "bucharest", "serbia", "belgrade", "zurich", "switzerland",
        "philippines", "costa rica", "malaysia",
    ]

    for job in raw_jobs:
        title = (job.get("name") or "").strip()
        if not title:
            continue

        job_id = job.get("id")
        loc_obj = job.get("location") or {}
        country_code = (loc_obj.get("country") or "").lower()
        full_loc = loc_obj.get("fullLocation") or f"{loc_obj.get('city', '')}, {loc_obj.get('region', '')}, {country_code}".strip(", ")
        loc_lower = full_loc.lower()

        if country_code not in ("us", "usa", "") and not any(
            us_m in loc_lower for us_m in ["us", "united states", "ny", "ca", "wa", "tx", "il", "ma", "san francisco", "new york", "seattle"]
        ):
            continue

        detail_url = f"{base_api}/{job_id}"
        try:
            d_resp = requests.get(detail_url, headers=headers, timeout=15)
            if d_resp.status_code != 200:
                continue
            det = d_resp.json()
        except Exception as e:
            logging.warning(f"[SmartRecruiters ATS] Error fetching detail for {title}: {e}")
            continue

        job_ad = det.get("jobAd") or {}
        sections = job_ad.get("sections") or {}
        plain_sections = []
        qualifications_plain = ""
        for sec_name, sec_val in sections.items():
            if isinstance(sec_val, dict) and sec_val.get("text"):
                stripped = _strip_html(sec_val.get("text"))
                plain_sections.append(stripped)
                if sec_name.lower() == "qualifications":
                    qualifications_plain = stripped

        full_plain = " ".join(plain_sections).strip()

        job_type = classify_job_type(title, full_plain)
        if job_type == "non_student":
            continue

        job_url = canonicalize_url(f"https://jobs.smartrecruiters.com/{company_id}/{job_id}")
        is_valid_url, _ = is_dedicated_job_detail_url(job_url)
        if not is_valid_url:
            continue

        comp = extract_structured_compensation(full_plain)
        skills = extract_structured_skills(qualifications_plain or full_plain)
        role_category, category_evidence = classify_role_category(title, full_plain)
        visa_info = classify_visa_status(full_plain, job_url)

        evidence_dict = {}
        if comp["salary_quote"]:
            evidence_dict["salary_quote"] = comp["salary_quote"]
        if skills["required_skills_quote"]:
            evidence_dict["required_skills_quote"] = skills["required_skills_quote"]
        if skills["preferred_skills_quote"]:
            evidence_dict["preferred_skills_quote"] = skills["preferred_skills_quote"]

        posted_at = None
        released_str = det.get("releasedDate")
        if released_str:
            try:
                posted_at = datetime.fromisoformat(released_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                posted_at = None

        internships.append(
            {
                "company": company_name,
                "role": title,
                "location": full_loc or "United States",
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
                "source": source_config.get("id", f"smartrecruiters_{company_id}"),
                "source_type": "public_ats",
                "status": "active",
            }
        )

    logging.info(f"[SmartRecruiters ATS] Found {len(internships)} verified student roles for {company_name}")
    return internships
