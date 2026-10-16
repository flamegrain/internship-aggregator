import requests
import logging
from datetime import datetime

try:
    from data_quality import classify_job_type, classify_role_category, is_dedicated_job_detail_url
except ImportError:
    from backend.data_quality import classify_job_type, classify_role_category, is_dedicated_job_detail_url


def crawl_morgan_stanley(source_config):
    """
    Crawls Morgan Stanley Careers using their official JSON API.
    """
    logging.info(f"[{datetime.now()}] Starting Morgan Stanley crawl...")
    internships = []

    search_api_url = "https://www.morganstanley.com/web/career_services/webapp/service/careerservice/resultset.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    params = {
        "opportunity": "sg",
        "lang": "EN",
        "businessArea": "Technology",
    }

    try:
        logging.info("Fetching jobs from Morgan Stanley API...")
        response = requests.get(search_api_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "resultSet" not in data:
            logging.error(f"Unexpected response structure from Morgan Stanley API: {list(data.keys())}")
            return []

        jobs = data["resultSet"]
        logging.info(f"Found {len(jobs)} jobs in Morgan Stanley API response.")

        for job in jobs:
            title = (job.get("jobTitle") or "").strip()
            job_url = (job.get("url") or "").strip()
            if not job_url:
                job_id = job.get("jobNumber")
                if job_id:
                    job_url = f"https://morganstanley.tal.net/vx/candidate/apply/{job_id}"

            # Requirement 1: Never fall back to generic search page URL
            valid_url, _ = is_dedicated_job_detail_url(job_url)
            if not title or not valid_url:
                continue

            job_type = classify_job_type(title)
            if job_type == "non_student":
                continue

            role_category, category_evidence = classify_role_category(title)

            city = job.get("allCity", "")
            country = job.get("allCountries", "")
            location = f"{city}, {country}".strip(", ") or "United States"

            # Requirement 2: Morgan Stanley resultset JSON does not include a real posted timestamp -> keep posted_at = None
            internships.append(
                {
                    "company": "Morgan Stanley",
                    "role": title,
                    "location": location,
                    "industry": "Finance",
                    "job_type": job_type,
                    "role_category": role_category,
                    "category_evidence": category_evidence,
                    "ai_label": role_category == "ai_ml",
                    "url": job_url,
                    "posted_at": None,
                    "source": "morgan_stanley_official",
                    "source_type": "official_api",
                    "logo_url": "https://upload.wikimedia.org/wikipedia/commons/3/34/Morgan_Stanley_Logo_1.svg",
                }
            )

    except Exception as e:
        logging.error(f"Error fetching Morgan Stanley jobs: {e}")

    logging.info(f"Morgan Stanley crawl complete. Found {len(internships)} verified student jobs.")
    return internships
