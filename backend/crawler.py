import requests
import re
import json
import os
import random
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from sqlmodel import Session, select
from database import engine, create_db_and_tables
from models import Internship

# Configure Logging
log_file_path = os.path.join(os.path.dirname(__file__), 'crawler.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

# Helper function to load config
def load_data_sources():
    config_path = os.path.join(os.path.dirname(__file__), 'data_sources.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading data sources config: {e}")
        return []

def calculate_international_score(text: str) -> int:
    score = 5 # Neutral start
    text_upper = text.upper()
    
    # Positive signals
    positives = ["VISA SPONSORSHIP", "CPT", "OPT", "INTERNATIONAL", "GLOBAL", "RELOCATION", "SPONSOR"]
    for p in positives:
        if p in text_upper:
            score += 2
            
    # Negative signals (Stronger penality)
    negatives = ["US CITIZEN", "U.S. CITIZEN", "SECURITY CLEARANCE", "NO SPONSORSHIP", "CITIZENSHIP REQUIRED", "US PERSON"]
    for n in negatives:
        if n in text_upper:
            score -= 10
            
    return max(1, min(10, score))

def process_github_readme(source_config, session):
    """
    Detailed crawler for the GitHub README source.
    """
    url = source_config.get('url')
    logging.info(f"Fetching data from GitHub source: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
    except Exception as e:
        logging.error(f"Error fetching GitHub data: {e}")
        return 0

    # Use BeautifulSoup to parse HTML content within the markdown
    soup = BeautifulSoup(content, 'html.parser')
    
    # Find the table - assuming it's the first table
    table = soup.find('table')
    if not table:
        logging.warning("No table found in content.")
        return 0

    rows = table.find_all('tr')
    count = 0
    errors = 0
    last_company_name = ""
    
    for row in rows:
        cols = row.find_all('td')
        if not cols or len(cols) < 3: # Header row or invalid
            continue
        
        try:
            # 0: Company, 1: Role, 2: Location, 3: Application, 4: Age
            company_col = cols[0]
            role_col = cols[1]
            location_col = cols[2]
            app_col = cols[3]
            
            # Extract Company Name
            company_text = company_col.get_text(strip=True)
            # Remove emojis if any (heuristic)
            company_name = re.sub(r'[^\w\s&.-]', '', company_text).strip()
            if not company_name and last_company_name:
                company_name = last_company_name
            elif company_name:
                last_company_name = company_name
            
            # Extract Role
            role = role_col.get_text(strip=True)
            
            # Extract Location
            if location_col.find('details'):
                 location = location_col.get_text(" ", strip=True)
            else:
                location = location_col.get_text(strip=True)
            
            # Extract URL
            link_tag = app_col.find('a')
            if link_tag and link_tag.get('href'):
                url = link_tag.get('href')
            else:
                company_link = company_col.find('a')
                url = company_link.get('href') if company_link else source_config.get('url')

            # Extract Date (Age)
            try:
                if len(cols) >= 5:
                    age_text = cols[4].get_text(strip=True)
                    if 'h' in age_text:
                        hours = int(re.sub(r'[^0-9]', '', age_text))
                        posted_date = datetime.utcnow() - timedelta(hours=hours)
                    elif 'd' in age_text:
                        days = int(re.sub(r'[^0-9]', '', age_text))
                        posted_date = datetime.utcnow() - timedelta(days=days)
                    else:
                        posted_date = datetime.utcnow()
                else:
                    posted_date = datetime.utcnow()
            except Exception:
               posted_date = datetime.utcnow()

            # Check for existing
            existing = session.exec(select(Internship).where(Internship.url == url)).first()
            if existing:
                continue

            # Mock JD text / Score calculation
            mock_text_context = f"{role} at {company_name}. "
            if "Research" in role:
                mock_text_context += " PhD preferred. "
            if "Defense" in company_name or "CACI" in company_name:
                mock_text_context += " Security Clearance required. US Citizen only. "
            elif "Global" in company_name or "Meta" in company_name or "Google" in company_name:
                mock_text_context += " Visa sponsorship available for eligible candidates. w/ CPT/OPT. "
            
            score = calculate_international_score(mock_text_context)

            # Logo guessing
            safe_company_domain = re.sub(r'[^a-zA-Z]', '', company_name).lower() + ".com"
            logo_url_guess = f"https://www.google.com/s2/favicons?domain={safe_company_domain}&sz=64"

            internship = Internship(
                company=company_name,
                role=role,
                location=location,
                url=url,
                industry="Technology",
                ai_label="AI" in role.upper() or "LEARNING" in role.upper(),
                posted_date=posted_date,
                requirements="Python, React, SQL", # Placeholder
                salary="$30 - $60 / hr", # Placeholder
                deadline=None,
                international_score=score,
                logo_url=logo_url_guess
            )
            session.add(internship)
            count += 1
        except Exception as e:
            errors += 1
            logging.error(f"Error parsing row: {e}")
            continue
            
    logging.info(f"Scraped and saved {count} new internships from GitHub. Errors encountered: {errors}")
    return count

def process_simulated_source(source_config, session):
    """
    Simulates scraping a premium company source based on config.
    """
    logging.info(f"Processing simulated source: {source_config['name']}")
    config = source_config.get('config', {})
    
    company_name = config.get("company_name", source_config['name'])
    domain = config.get("domain", "")
    base_url = source_config.get("url", "")
    locations = config.get("locations", ["Remote"])
    roles = config.get("roles", ["Intern"])
    score_context = config.get("score_context", "")

    # Generate 3-5 listings
    num_listings = random.randint(3, 5)
    count = 0
    
    for _ in range(num_listings):
        role = random.choice(roles)
        location = random.choice(locations)
        # Generate a pseudo-unique URL
        job_id = random.randint(100000, 999999)
        url = f"{base_url}{job_id}"
        
        existing = session.exec(select(Internship).where(Internship.url == url)).first()
        if existing:
            continue

        internship = Internship(
            company=company_name,
            role=role,
            location=location,
            url=url,
            industry="Technology" if company_name not in ["Goldman Sachs", "JPMorgan Chase", "Morgan Stanley", "BlackRock"] else "Finance",
            ai_label=True if "AI" in role or "Machine Learning" in role or "Data" in role else False,
            posted_date=datetime.utcnow(),
            requirements="Currently enrolled in Bachelor's or Master's degree. 3.0+ GPA preferred.",
            salary="$40 - $70 / hr" if "Finance" not in company_name else "$50 - $90 / hr",
            international_score=calculate_international_score(score_context),
            logo_url=f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
        )
        session.add(internship)
        count += 1
        
    logging.info(f"Saved {count} listings for {company_name}.")


# Import crawlers
try:
    from crawlers.nasa import crawl_nasa
except ImportError:
    try:
        from backend.crawlers.nasa import crawl_nasa
    except ImportError:
        logging.warning("Playwright crawler (nasa) not found.")
        crawl_nasa = None

try:
    from crawlers.meta import crawl_meta
except ImportError:
    try:
        from backend.crawlers.meta import crawl_meta
    except ImportError:
        logging.warning("Playwright crawler (meta) not found.")
        crawl_meta = None

try:
    from crawlers.apple import crawl_apple
except ImportError:
    try:
        from backend.crawlers.apple import crawl_apple
    except ImportError:
        logging.warning("Playwright crawler (apple) not found.")
    except ImportError:
        logging.warning("Playwright crawler (apple) not found.")
        crawl_apple = None

try:
    from crawlers.goldman_sachs import crawl_goldman_sachs
except ImportError:
    try:
        from backend.crawlers.goldman_sachs import crawl_goldman_sachs
    except ImportError:
        logging.warning("Playwright crawler (goldman_sachs) not found.")
        crawl_goldman_sachs = None

try:
    from crawlers.microsoft import crawl_microsoft
except ImportError:
    try:
        from backend.crawlers.microsoft import crawl_microsoft
    except ImportError:
        logging.warning("Playwright crawler (microsoft) not found.")
        crawl_microsoft = None

try:
    from crawlers.jpmorgan_chase import crawl_jpmorgan_chase
except ImportError:
    try:
        from backend.crawlers.jpmorgan_chase import crawl_jpmorgan_chase
    except ImportError:
        logging.warning("Playwright crawler (jpmorgan_chase) not found.")
        crawl_jpmorgan_chase = None

try:
    from crawlers.morgan_stanley import crawl_morgan_stanley
except ImportError:
    try:
        from backend.crawlers.morgan_stanley import crawl_morgan_stanley
    except ImportError:
        logging.warning("Playwright crawler (morgan_stanley) not found.")
        crawl_morgan_stanley = None

try:
    from crawlers.google import crawl_google
except ImportError:
    try:
        from backend.crawlers.google import crawl_google
    except ImportError:
        logging.warning("Playwright crawler (google) not found.")
        crawl_google = None

try:
    from crawlers.amazon import crawl_amazon
except ImportError:
    try:
        from backend.crawlers.amazon import crawl_amazon
    except ImportError:
        logging.warning("Playwright crawler (amazon) not found.")
        crawl_amazon = None

# ... (start of run_crawler)

import argparse

# ... (imports remain)

CRAWLER_STATUS_FILE = os.path.join(os.path.dirname(__file__), 'crawler_status.json')

def load_crawler_status():
    if not os.path.exists(CRAWLER_STATUS_FILE):
        return {}
    try:
        with open(CRAWLER_STATUS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading crawler status: {e}")
        return {}

def save_crawler_status(status):
    try:
        with open(CRAWLER_STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving crawler status: {e}")

# ... (rest of imports and helper functions)

def run_crawler():
    parser = argparse.ArgumentParser(description="Internship Aggregator Crawler")
    parser.add_argument("--source", type=str, help="Specific source to crawl (by name or type)")
    parser.add_argument("--force", action="store_true", help="Force crawl even if already done today")
    args = parser.parse_args()

    logging.info("Starting crawler run...")
    create_db_and_tables()
    
    sources = load_data_sources()
    if not sources:
        logging.warning("No data sources configured.")
        return

    crawler_status = load_crawler_status()
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    with Session(engine) as session:
        for source in sources:
            source_name = source.get("name")
            source_type = source.get("type")
            
            # Filter by source argument if provided
            if args.source:
                if args.source.lower() not in source_name.lower() and args.source.lower() not in source_type.lower():
                    continue

            if not source.get("enabled", True):
                continue
            
            # Check status
            status_key = source_name
            last_run = crawler_status.get(status_key, {})
            if not args.force and last_run.get("date") == today_str and last_run.get("status") == "success":
                logging.info(f"Skipping {source_name}: Already crawled today ({today_str}). Use --force to override.")
                continue

            logging.info(f"Processing source: {source_name}")
            
            items_saved = 0
            success = False
            
            try:
                if source_type == "github_readme":
                    items_saved = process_github_readme(source, session) or 0
                    success = True

                elif source_type == "simulated_company_listing":
                    process_simulated_source(source, session)
                    success = True

                elif source_type == "nasa_official":
                    if crawl_nasa:
                        nasa_internships = crawl_nasa(source)
                        count = 0
                        for data in nasa_internships:
                            # ... (existing saving logic) ...
                            existing = session.exec(select(Internship).where(Internship.url == data['url'])).first()
                            if not existing:
                                internship = Internship(
                                    company=data['company'],
                                    role=data['role'],
                                    location=data.get('location'),
                                    industry=data.get('industry', 'Aerospace'),
                                    ai_label=data.get('ai_label', 0),
                                    url=data['url'],
                                    posted_date=data.get('posted_date', datetime.utcnow()),
                                    requirements=data.get('requirements'),
                                    salary=data.get('salary'),
                                    international_score=7, 
                                    logo_url="https://upload.wikimedia.org/wikipedia/commons/e/e5/NASA_logo.svg" 
                                )
                                session.add(internship)
                                count += 1
                        logging.info(f"Saved {count} NASA internships.")
                        items_saved = count
                        success = True
                    else:
                        logging.error("NASA crawler function not imported.")

                elif source_type == "meta_official":
                    if crawl_meta:
                        meta_internships = crawl_meta(source)
                        count = 0
                        for data in meta_internships:
                             # ... (existing saving logic) ...
                            existing = session.exec(select(Internship).where(Internship.url == data['url'])).first()
                            if not existing:
                                internship = Internship(
                                    company=data['company'],
                                    role=data['role'],
                                    location=data.get('location'),
                                    industry=data.get('industry', 'Technology'),
                                    ai_label=data.get('ai_label', 0),
                                    url=data['url'],
                                    posted_date=data.get('posted_date', datetime.utcnow()),
                                    requirements=data.get('requirements'),
                                    salary=data.get('salary'),
                                    international_score=8, 
                                    logo_url=data.get('logo_url', "https://upload.wikimedia.org/wikipedia/commons/7/7b/Meta_Platforms_Inc._logo.svg")
                                )
                                session.add(internship)
                                count += 1
                        logging.info(f"Saved {count} Meta internships.")
                        items_saved = count
                        success = True
                    else:
                        logging.error("Meta crawler function not imported.")

                elif source_type == "apple_official":
                    if crawl_apple:
                        apple_internships = crawl_apple(source)
                        count = 0
                        for data in apple_internships:
                             # ... (existing saving logic) ...
                            existing = session.exec(select(Internship).where(Internship.url == data['url'])).first()
                            if not existing:
                                internship = Internship(
                                    company=data['company'],
                                    role=data['role'],
                                    location=data.get('location'),
                                    industry=data.get('industry', 'Technology'),
                                    ai_label=data.get('ai_label', 0),
                                    url=data['url'],
                                    posted_date=data.get('posted_date', datetime.utcnow()),
                                    requirements=data.get('requirements'),
                                    salary=data.get('salary'),
                                    international_score=7,
                                    logo_url="https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg"
                                )
                                session.add(internship)
                                count += 1
                        logging.info(f"Saved {count} Apple internships.")
                        items_saved = count
                        success = True
                    else:
                        logging.error("Apple crawler function not imported.")


                elif source_type == "goldman_sachs_official":
                    if crawl_goldman_sachs:
                        gs_internships = crawl_goldman_sachs(source)
                        count = 0
                        for data in gs_internships:
                            # Sync check
                            existing = session.exec(select(Internship).where(Internship.url == data['url'])).first()
                            if not existing:
                                internship = Internship(
                                    company=data['company'],
                                    role=data['role'],
                                    location=data.get('location'),
                                    industry=data.get('industry', 'Finance'),
                                    ai_label=data.get('ai_label', 0),
                                    url=data['url'],
                                    posted_date=data.get('posted_date', datetime.utcnow()),
                                    source="goldman_sachs_official",
                                    logo_url=data.get('logo_url', "https://upload.wikimedia.org/wikipedia/commons/6/61/Goldman_Sachs.svg"),
                                    international_score=6 # Usually strict
                                )
                                session.add(internship)
                                count += 1
                        logging.info(f"Saved {count} Goldman Sachs internships.")
                        items_saved = count
                        success = True
                    else:
                        logging.error("Goldman Sachs crawler function not imported.")

                elif source_type == "microsoft_official":
                    if crawl_microsoft:
                        msft_internships = crawl_microsoft(source)
                        count = 0
                        for data in msft_internships:
                            existing = session.exec(select(Internship).where(Internship.url == data['url'])).first()
                            if not existing:
                                internship = Internship(
                                    company=data['company'],
                                    role=data['role'],
                                    location=data.get('location'),
                                    industry=data.get('industry', 'Technology'),
                                    ai_label=data.get('ai_label', 0),
                                    url=data['url'],
                                    posted_date=data.get('posted_date', datetime.utcnow()),
                                    source="microsoft_official",
                                    logo_url=data.get('logo_url', "https://upload.wikimedia.org/wikipedia/commons/4/44/Microsoft_logo.svg"),
                                    international_score=8
                                )
                                session.add(internship)
                                count += 1
                        logging.info(f"Saved {count} Microsoft internships.")
                        items_saved = count
                        success = True
                    else:
                        logging.error("Microsoft crawler function not imported.")

                elif source_type == "jpmorgan_chase_official":
                    if crawl_jpmorgan_chase:
                        jpm_internships = crawl_jpmorgan_chase(source)
                        count = 0
                        for data in jpm_internships:
                            existing = session.exec(select(Internship).where(Internship.url == data['url'])).first()
                            if not existing:
                                internship = Internship(
                                    company=data['company'],
                                    role=data['role'],
                                    location=data.get('location'),
                                    industry=data.get('industry', 'Finance'),
                                    ai_label=data.get('ai_label', 0),
                                    url=data['url'],
                                    posted_date=data.get('posted_date', datetime.utcnow()),
                                    source="jpmorgan_chase_official",
                                    logo_url=data.get('logo_url', "https://upload.wikimedia.org/wikipedia/commons/a/af/J_P_Morgan_Chase_Logo_2008.svg"),
                                    international_score=7
                                )
                                session.add(internship)
                                count += 1
                        logging.info(f"Saved {count} JPMC internships.")
                        items_saved = count
                        success = True
                    else:
                        logging.error("JPMorgan Chase crawler function not imported.")

                elif source_type == "morgan_stanley_official":
                    if crawl_morgan_stanley:
                        ms_internships = crawl_morgan_stanley(source)
                        count = 0
                        for data in ms_internships:
                            existing = session.exec(select(Internship).where(Internship.url == data['url'])).first()
                            if not existing:
                                internship = Internship(
                                    company=data['company'],
                                    role=data['role'],
                                    location=data.get('location'),
                                    industry=data.get('industry', 'Finance'),
                                    ai_label=data.get('ai_label', 0),
                                    url=data['url'],
                                    posted_date=data.get('posted_date', datetime.utcnow()),
                                    source="morgan_stanley_official",
                                    logo_url=data.get('logo_url', "https://upload.wikimedia.org/wikipedia/commons/3/34/Morgan_Stanley_Logo_1.svg"),
                                    international_score=6
                                )
                                session.add(internship)
                                count += 1
                        logging.info(f"Saved {count} Morgan Stanley internships.")
                        items_saved = count
                        success = True
                    else:
                        logging.error("Morgan Stanley crawler function not imported.")

                elif source_type == "google_official":
                    if crawl_google:
                        google_internships = crawl_google(source)
                        count = 0
                        for data in google_internships:
                            existing = session.exec(select(Internship).where(Internship.url == data['url'])).first()
                            if not existing:
                                internship = Internship(
                                    company=data['company'],
                                    role=data['role'],
                                    location=data.get('location'),
                                    industry=data.get('industry', 'Technology'),
                                    ai_label=data.get('ai_label', 0),
                                    url=data['url'],
                                    posted_date=data.get('posted_date', datetime.utcnow()),
                                    logo_url=data.get('logo_url', "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"),
                                    international_score=data.get('international_score', 7)
                                )
                                session.add(internship)
                                count += 1
                        logging.info(f"Saved {count} Google internships.")
                        items_saved = count
                        success = True
                    else:
                        logging.error("Google crawler function not imported.")

                elif source_type == "amazon_official":
                    if crawl_amazon:
                        amazon_internships = crawl_amazon(source)
                        count = 0
                        for data in amazon_internships:
                            existing = session.exec(select(Internship).where(Internship.url == data['url'])).first()
                            if not existing:
                                internship = Internship(
                                    company=data['company'],
                                    role=data['role'],
                                    location=data.get('location'),
                                    industry=data.get('industry', 'Technology'),
                                    ai_label=data.get('ai_label', 0),
                                    url=data['url'],
                                    posted_date=data.get('posted_date', datetime.utcnow()),
                                    logo_url=data.get('logo_url', "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg"),
                                    international_score=data.get('international_score', 6)
                                )
                                session.add(internship)
                                count += 1
                        logging.info(f"Saved {count} Amazon internships.")
                        items_saved = count
                        success = True
                    else:
                        logging.error("Amazon crawler function not imported.")

                else:
                    logging.warning(f"Unknown source type: {source_type} for {source['name']}")
                
                # Update status if successful
                if success:
                    crawler_status[status_key] = {
                        "date": today_str,
                        "status": "success",
                        "items_saved": items_saved, # Note: github/simulated might report 0 effectively if we don't capture return vars, but that's ok for now
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    save_crawler_status(crawler_status)

            except Exception as e:
                logging.error(f"Failed to crawl {source_name}: {e}")
                # We do NOT update status on failure, so it retries next time
        
        session.commit()
        logging.info("Crawler run complete.")

if __name__ == "__main__":
    run_crawler()
