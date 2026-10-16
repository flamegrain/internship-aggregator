import requests
import logging
from datetime import datetime

try:
    from data_quality import classify_job_type, classify_role_category, is_dedicated_job_detail_url
except ImportError:
    from backend.data_quality import classify_job_type, classify_role_category, is_dedicated_job_detail_url


def crawl_microsoft(source_config):
    """
    Crawls Microsoft Careers using their official PCSX search API.
    """
    logging.info(f"[{datetime.now()}] Starting Microsoft crawl...")
    internships = []

    search_api_url = "https://apply.careers.microsoft.com/api/pcsx/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    start = 0
    page_size = 20
    max_items = 200

    while start < max_items:
        params = {
            "domain": "microsoft.com",
            "query": "internship",
            "location": "",
            "start": start,
            "sort_by": "relevance",
        }

        try:
            logging.info(f"Fetching Microsoft jobs starting from {start}...")
            response = requests.get(search_api_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "data" not in data or "positions" not in data["data"]:
                logging.error(f"Unexpected response structure from Microsoft API: {list(data.keys())}")
                break

            positions = data["data"]["positions"]
            if not positions:
                break

            for pos in positions:
                job_id = pos.get("id")
                title = (pos.get("name") or "").strip()
                if not job_id or not title:
                    # Requirement 1: Never fall back to generic search URL when job_id is missing
                    continue

                job_url = f"https://apply.careers.microsoft.com/careers/job/{job_id}"
                valid_url, _ = is_dedicated_job_detail_url(job_url)
                if not valid_url:
                    continue

                job_type = classify_job_type(title)
                if job_type == "non_student":
                    continue

                role_category, category_evidence = classify_role_category(title)

                # Requirement 2: Only set posted_at when Microsoft API returns authentic postedTs
                posted_ts = pos.get("postedTs")
                posted_at = None
                if isinstance(posted_ts, (int, float)) and posted_ts > 0:
                    try:
                        posted_at = datetime.utcfromtimestamp(posted_ts)
                    except Exception:
                        posted_at = None

                locations = pos.get("locations", [])
                location_str = ", ".join(locations) if locations else "United States"

                internships.append(
                    {
                        "company": "Microsoft",
                        "role": title,
                        "location": location_str,
                        "industry": "Technology",
                        "job_type": job_type,
                        "role_category": role_category,
                        "category_evidence": category_evidence,
                        "ai_label": role_category == "ai_ml",
                        "url": job_url,
                        "posted_at": posted_at,
                        "source": "microsoft_official",
                        "source_type": "official_api",
                        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/4/44/Microsoft_logo.svg",
                    }
                )

            start += page_size
            if len(positions) < page_size:
                break

        except Exception as e:
            logging.error(f"Error fetching Microsoft jobs (start={start}): {e}")
            break

    logging.info(f"Microsoft crawl complete. Found {len(internships)} verified student jobs.")
    return internships
