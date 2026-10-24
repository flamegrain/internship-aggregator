# 🎓 Internship Aggregator

[![React](https://img.shields.io/badge/Frontend-React-61DAFB?logo=react&logoColor=white)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind--CSS-38B2AC?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Data Quality Audit](https://img.shields.io/badge/Stratified%20Audit%20(n%3D120)-100%25%20PASS-10B981)](./backend/data_quality_audit.json)
[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?logo=vercel&logoColor=white)](https://internship-aggregator-nu.vercel.app/)

[English] | [简体中文](./README.zh-CN.md) | 🌐 **Live Demo**: [internship-aggregator-nu.vercel.app](https://internship-aggregator-nu.vercel.app/)

An **auditable, evidence-backed full-stack internship aggregation platform** built for college students seeking Tech, AI/ML, Quant, and Research internships. Tracks **2,396 verified active internships** across **650+ companies** through Official Career APIs, Public ATS feeds (Greenhouse & Lever), Official Career Portals, and cross-verified community repositories—with **zero simulated listings, zero placeholder compensation, and 100% verbatim evidence traceability**.

![Dashboard Preview](assets/homepage_preview_v2.png)

---

## 🛡️ Data Authenticity & Zero-Fabrication Architecture

Unlike scrapers that inject placeholder salaries, guessed skill tags, or arbitrary `"8/10"` sponsorship scores, **Internship Aggregator** enforces a strict **Zero-Fabrication & Verbatim-Evidence Policy** in [`backend/data_quality.py`](backend/data_quality.py):

1. **Zero Simulated Jobs or Placeholder Fields**
   - Simulated/mock collectors are permanently banned (`BLOCKED_SOURCE_TYPES`).
   - Placeholder compensation strings (e.g., `"$30 - $60 / hr"`, `"Competitive"`) and generic skill lists (`"Python, React, SQL"`) are blocked at ingestion. Fields remain `null` unless backed by a verbatim quote from the employer's job description (`extraction_evidence`).
2. **Dedicated Job Detail URL Gatekeeper**
   - Every record must resolve to a **unique job detail URL or dedicated requisition ID** (`is_dedicated_job_detail_url()`). Generic career homepages or `/search` listing pages are never accepted as direct application links; unverified links are quarantined as `pending_review` or rejected.
3. **Strict Separation of Lifecycle Timestamps**
   - `posted_at`: The authentic publication date provided by the employer or ATS API (`updated_at` / `createdAt` / `postedDate`). Kept strictly `null` when an upstream source only provides relative discovery age.
   - `first_seen_at`: The exact UTC timestamp when our system first discovered the posting.
   - `last_verified_at`: The most recent UTC timestamp when our system confirmed the posting remains active.
4. **Explicit `job_type` Validation**
   - Every posting is classified into `internship`, `co-op`, `fellowship`, `new_grad_full_time`, `other_student_program`, or `non_student` (`classify_job_type()`).
   - Senior/full-time non-student roles and full-time new-grad roles are automatically isolated so **only verified target internships (`internship`, `co-op`, `fellowship`) enter the default listing**.
5. **Auditable Work Authorization (`visa_status`) with Verbatim Evidence**
   - Probabilistic `"Visa Friendliness 8/10"` scores are abolished (`international_score = null`). Every posting is classified into one of four auditable states with a stored `visa_evidence` quote, `visa_source_url`, and `visa_verified_at` timestamp:
     | `visa_status` | Meaning |
     | :--- | :--- |
     | `sponsorship_explicitly_supported` | Current posting explicitly states visa sponsorship is available or welcomes F-1 / CPT / OPT |
     | `explicitly_restricted` | Current posting explicitly requires U.S. Citizenship / Security Clearance / ITAR or states no sponsorship |
     | `not_specified` | Current posting does not explicitly state work authorization or sponsorship terms |
     | `needs_review` | Posting contains conditional or conflicting work authorization statements |
6. **Structured Compensation & Skills with Verbatim Quotes (`extraction_evidence`)**
   - Compensation is parsed into structured numeric fields (`salary_min`, `salary_max`, `salary_period` in `hour`/`month`/`year`, and `currency`), paired with the exact employer sentence in `extraction_evidence.salary_quote`.
   - Skills are separated into `required_skills` and `preferred_skills` according to JD section headers, paired with `required_skills_quote` and `preferred_skills_quote`.
7. **Evidence-Backed Role Taxonomy (`role_category` + `category_evidence`)**
   - Postings are classified into `ai_ml`, `software_engineering`, `data_analytics`, `research`, `other`, or `unclassified` using complete phrase matching and recorded `category_evidence` rather than forced binary tagging.
8. **Source-Level Lifecycle Authority Protection (`status_authority`)**
   - Sources follow a strict authority hierarchy: `official_api (100)` > `public_ats (90)` > `official_portal (80)` > `community_verified (60)`.
   - In `upsert_or_merge_internship()`, each status transition records `status_authority`. A lower-priority community source **can never reactivate (`status = 'active'`)** a role that a higher-priority Official API or Public ATS source has marked `closed` or `expired`.

---

## 📊 Stratified Data Quality Verification Mechanism (`n = 120`)

Before publishing internship counts or quality claims, the platform executes an automated stratified audit ([`backend/audit_data_quality.py`](backend/audit_data_quality.py)) across **120 real records** sampled proportionally across `official_api`, `public_ats`, `official_portal`, and `community_verified` tiers.

The live audit report is persisted in [`backend/data_quality_audit.json`](backend/data_quality_audit.json) and served via `GET /api/data-quality/audit`:

| Metric | Calculation Formula | Target | Audited Result (`n = 120`) | Status |
| :--- | :--- | :---: | :---: | :---: |
| **Valid Unique Detail URL Rate** (`独立岗位链接有效率`) | Valid dedicated job detail URLs / Sampled records | `≥ 98%` | **100.0%** (`120 / 120`) | ✅ PASS |
| **Internship Type Accuracy** (`实习岗位准确率`) | Verified target internship types (`internship`/`co-op`/`fellowship`) / Sampled records | `≥ 95%` | **100.0%** (`120 / 120`) | ✅ PASS |
| **Duplicate Record Rate** (`重复记录率`) | Records sharing a canonical URL or `canonical_key` / Sampled records | `≤ 2%` | **0.0%** (`0 / 120`) | ✅ PASS |
| **Posted Date Accuracy** (`发布日期准确率`) | Authentic employer `posted_at` matching upstream source / Records with `posted_at` | `≥ 95%` | **100.0%** (`45 / 45`) | ✅ PASS |
| **Salary Accuracy** (`薪资准确率`) | Structured `salary_min`/`max`/`period` matching verbatim `salary_quote` / Records with salary | `≥ 98%` | **100.0%** (`26 / 26`) | ✅ PASS |
| **Visa Evidence Coverage** (`签证状态证据覆盖率`) | Explicit visa judgments backed by verbatim `visa_evidence` / Explicit visa judgments | `100%` | **100.0%** (`7 / 7`) | ✅ PASS |

You can re-run the stratified verification suite at any time:
```bash
python3 backend/audit_data_quality.py
```

---

## 📂 Multi-Tier Data Sources

We prioritize official first-party APIs and public ATS feeds, enriched by cross-verified community tracking:

| Priority Tier | Source Type | Channels & Employers | Provenance Capabilities |
| :---: | :--- | :--- | :--- |
| **Tier 1 (`100`)** | `official_api` | **Microsoft Careers API**, **Morgan Stanley Talbot API** | Authentic `posted_at`, direct requisition IDs, authoritative open/close lifecycle |
| **Tier 2 (`90`)** | `public_ats` | **Greenhouse & Lever Public ATS APIs** (Stripe, Databricks, Anthropic, Cloudflare, Figma, Scale AI, SpaceX, Coinbase, Robinhood, Pinterest, Lyft, Reddit, Asana, Instacart, Vercel, Plaid, Palantir, Zoox) | Full HTML JD parsing, verbatim `salary_quote` compensation ranges, `required_skills` vs `preferred_skills`, ITAR/citizenship & sponsorship evidence |
| **Tier 3 (`80`)** | `official_portal` | **Apple**, **Meta**, **Google**, **Amazon**, **JPMorgan Chase**, **Goldman Sachs**, **NASA STEM** | Direct portal job detail URLs and official requisition tracking |
| **Tier 4 (`60`)** | `community_verified` | **SimplifyJobs Summer 2026 Internships** | Broad coverage across 600+ employers, explicit `🛂` (No Sponsor), `🇺🇸` (U.S. Citizen Required), and `🔒` (Closed) flags |

---

## 🔌 RESTful API Endpoints

### `GET /internships` (or `/api/internships`)
Retrieve a paginated list of verified active internships (`job_type IN ('internship', 'co-op', 'fellowship')` by default).

**Query Parameters:**
- `offset` (`int`, default `0`), `limit` (`int`, default `24`)
- `search` (`string`, optional): Search across company, role, location, or skills
- `visa_status` (`string`, optional): `open_to_international`, `sponsorship_explicitly_supported`, `not_specified`, `explicitly_restricted`, or `needs_review`
- `role_category` (`string`, optional): `ai_ml`, `software_engineering`, `data_analytics`, `research`, `other`, or `unclassified`
- `job_type` (`string`, optional): `internship`, `co-op`, `fellowship`, `new_grad_full_time`, or `other_student_program`
- `high_salary` (`bool`, optional): Filter for postings with verified disclosed compensation
- `source_type` (`string`, optional): `official_verified`, `official_api`, `public_ats`, `official_portal`, or `community_verified`

### `GET /stats` (or `/api/stats`)
Returns live verified internship counts, category/visa breakdowns, source tier distributions, and the embedded `audit_summary` verification status.

### `GET /data-quality/audit` (or `/api/data-quality/audit`)
Returns the full stratified 120-record data quality audit report, including per-tier sample breakdowns and all 6 verification metrics.

### `GET /crawler/health` (or `/api/crawler/health`)
Returns per-source collection telemetry, last run status, and any active zero-result or failure alerts (`CrawlerAlert`).

---

## 🛠️ Tech Stack

- **Frontend**: React 19 (Vite), Tailwind CSS, Lucide Icons, Axios
- **Backend**: FastAPI (Python), SQLModel / SQLAlchemy, Uvicorn
- **Database**: SQLite with idempotent schema migration & multi-source deduplication
- **Verification & Ingestion**: Greenhouse/Lever JSON APIs, Official Career APIs, BeautifulSoup4, Automated Stratified Audit (`audit_data_quality.py`)

---

## ⚙️ Getting Started

### 1. Backend Setup
```bash
git clone https://github.com/flamegrain/internship-aggregator.git
cd internship-aggregator

python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Run the verified multi-source sync & data quality audit
python3 backend/sync_verified_sources.py
python3 backend/audit_data_quality.py

# Start the FastAPI server
uvicorn backend.main:app --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 📁 Project Structure
```text
internship-aggregator/
├── api/
│   └── index.py                      # Vercel serverless FastAPI entrypoint
├── backend/
│   ├── main.py                       # FastAPI routes (/internships, /stats, /data-quality/audit)
│   ├── models.py                     # SQLModel schema (Internship, CrawlerAlert, EmailSubscriber)
│   ├── data_quality.py               # URL validation, visa/category/job_type classifiers, evidence extraction & merge authority
│   ├── sync_verified_sources.py      # Multi-tier ATS, Official API & community synchronization pipeline
│   ├── audit_data_quality.py         # Stratified 120-record data quality verification script
│   ├── data_quality_audit.json       # Generated stratified audit report (6 quality metrics)
│   └── crawlers/                     # Dedicated collectors (ats.py, microsoft.py, morgan_stanley.py, etc.)
├── frontend/
│   └── src/
│       ├── App.jsx                   # Unified dashboard & filter state
│       └── components/
│           ├── LiveStatsBanner.jsx   # Animated 6-digit counters & audit verification badge
│           ├── QuickFilterNav.jsx    # Auditable visa_status, role_category & compensation filters
│           └── InternshipCard.jsx    # Verbatim evidence tooltips & separated timestamps
├── README.md
└── README.zh-CN.md
```

---

## 📄 License
This project is licensed under the MIT License.
