# Hospitality Lead Generation System

## Technical Architecture Document

### 1. Project Overview

The Hospitality Lead Generation System is a Python-based data collection and enrichment platform that automatically discovers hospitality businesses (hotels, resorts, villas, boutique properties, etc.) using Google Places API and enriches the records with contact details, social media profiles, property classification, ratings, reviews, and website information.

The final output is generated as a CSV file containing structured hospitality leads for sales, marketing, partnership outreach, and business development purposes.

---

# 2. Technology Stack

| Layer                 | Technology         |
| --------------------- | ------------------ |
| Programming Language  | Python 3.11+       |
| API Integration       | Google Places API  |
| HTTP Requests         | Requests           |
| HTML Parsing          | BeautifulSoup4     |
| Data Processing       | Pandas             |
| Browser Automation    | Selenium           |
| Web Driver Management | WebDriver Manager  |
| Environment Variables | Python Dotenv      |
| Output Storage        | CSV                |
| IDE                   | Visual Studio Code |
| Version Control       | Git                |

---

# 3. High-Level Architecture

User Query
↓
Google Places API
↓
Place Search Results
↓
Place Details API
↓
Website Discovery
↓
Data Enrichment Layer

├── Email Extraction
├── Contact Page Scraping
├── Phone Extraction
├── Social Media Extraction
├── Property Type Classification
└── Price Extraction

↓
Data Aggregation
↓
Pandas DataFrame
↓
hospitality_leads.csv

---

# 4. File & Folder Structure

```text
dh-lead-gen/
│
├── output/
│   └── hospitality_leads.csv
│
├── venv/
│
├── .env
├── .gitignore
├── requirements.txt
│
├── main.py
│
├── places_api.py
├── contact_page_scraper.py
├── mail_extractor.py
├── phone_extractor.py
├── social_extractor.py
├── property_type.py
├── price_extractor.py
├── founder_extractor.py
│
├── test.py
├── test_phone.py
│
└── __pycache__/
```

---

# 5. Module Responsibilities

## main.py

Acts as the application orchestrator.

Responsibilities:

* Execute hotel search
* Fetch hotel details
* Call enrichment modules
* Create dataframe
* Generate final CSV

---

## places_api.py

Responsibilities:

* Google Places Text Search
* Place Details Lookup
* Website Extraction
* Ratings Extraction
* Reviews Extraction
* Contact Number Extraction

---

## contact_page_scraper.py

Responsibilities:

* Visit contact pages
* Extract emails
* Extract phone numbers
* Parse About Us pages

Pages scanned:

* /
* /contact
* /contact-us
* /about
* /about-us

---

## mail_extractor.py

Responsibilities:

* Extract email addresses
* Regex-based email detection

Output:

* EMAIL 1
* EMAIL 2
* EMAIL 3

---

## phone_extractor.py

Responsibilities:

* Extract mobile numbers
* Extract landline numbers
* Remove duplicates

Output:

* CONTACT NO 2
* CONTACT NO 3

---

## social_extractor.py

Responsibilities:

* Extract Instagram
* Extract Facebook
* Extract LinkedIn
* Extract YouTube
* Extract Twitter/X

---

## property_type.py

Responsibilities:

Classify property as:

* Hotel
* Luxury Hotel
* Resort
* Villa
* Farmhouse
* Boutique Hotel
* Wedding Venue

---

## price_extractor.py

Responsibilities:

* Scan hotel pages
* Detect room pricing
* Extract nightly rates

Pages checked:

* /rooms
* /offers
* /stays
* /accommodation

---

## founder_extractor.py

Responsibilities:

* Scan leadership pages
* Identify founder names
* Identify CEO names
* Identify management roles

Future enhancement module.

---

# 6. Database Schema (Current CSV Schema)

Table Name:
hospitality_leads

| Column          | Data Type |
| --------------- | --------- |
| SR NO           | Integer   |
| NAME            | String    |
| PROPERTY TYPE   | String    |
| LOCATION        | Text      |
| CITY            | String    |
| CONTACT NO 1    | String    |
| CONTACT NO 2    | String    |
| CONTACT NO 3    | String    |
| EMAIL 1         | String    |
| EMAIL 2         | String    |
| EMAIL 3         | String    |
| RATING OUT OF 5 | Float     |
| REVIEW COUNT    | Integer   |
| PRICE PER DAY   | String    |
| LOCATION TYPE   | String    |
| WEBSITE         | String    |
| INSTAGRAM       | String    |
| FACEBOOK        | String    |
| LINKEDIN        | String    |
| YOUTUBE         | String    |
| TWITTER         | String    |

---

# 7. Output Dataset Example

Example Record:

* Property Name:
  Taj Palace, New Delhi

* Property Type:
  Luxury Hotel

* Rating:
  4.7

* Reviews:
  34,712

* Website:
  Taj Hotels

* Contact:
  011 2611 0202

---

# 8. Environment Configuration

Environment Variables (.env)

```env
GOOGLE_API_KEY=YOUR_GOOGLE_PLACES_API_KEY
```

---

# 9. External Dependencies

requirements.txt

```text
pandas
requests
beautifulsoup4
selenium
webdriver-manager
python-dotenv
```

Install:

```bash
pip install -r requirements.txt
```

---

# 10. Execution Flow

Step 1:
Run main.py

Step 2:
Search hotels using Google Places API

Step 3:
Fetch place details

Step 4:
Collect website information

Step 5:
Extract contacts and social links

Step 6:
Classify property type

Step 7:
Extract pricing information

Step 8:
Create dataframe

Step 9:
Generate hospitality_leads.csv

---

# 11. Future Enhancements

* Founder/CEO Detection
* Hotel Chain Identification
* Luxury/Premium/Budget Classification
* Email Verification
* Phone Verification
* Lead Prioritization Engine
* Database Integration (MySQL/PostgreSQL)
* Streamlit Dashboard
* Bulk Multi-City Processing
* CRM Export (HubSpot/Salesforce)
* AI-based Lead Scoring
* Hospitality Industry Analytics Dashboard

```
```
