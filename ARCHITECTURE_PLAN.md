# York Construction Intelligence: System Architecture Plan

## Executive Summary
To achieve a robust, high-speed, and accurate intelligence platform, we must move away from the current "Pass-through" architecture (loading CSVs and scraping on-the-fly) to a **"Store & Sync"** architecture. 

The core philosophy is: **Your local database is the single source of truth.** The external sources (ArcGIS API and Idox Website) are merely inputs that feed your database.

---

## 1. Core Architecture Components

### A. The Data Store (SQLite / PostgreSQL)
Instead of `addresses.json` and `Planning_Applications.csv`, we will implement a robust structured database.
*   **Why?** Ensures data consistency, allows complex querying (e.g., "Show me all apps by Agent X in the last year"), and prevents data loss.
*   **Structure:**
    *   `applications`: The master record (Ref, Address, coords, dates, status).
    *   `agents`: Normalized agent data (to group "Smith Arch" and "Smith Architects Ltd").
    *   `history`: An audit log tracking status changes over time (Vital for "Intelligence").
    *   `scrape_queue`: A persistent priority queue for the scraper.

### B. The Feeder (ArcGIS API Sync)
Instead of downloading a CSV, a background process queries the York Open Data API.
*   **Method:** Incremental Sync.
    *   On first run: Fetch ALL data.
    *   Subsequent runs: Fetch only records where `OBJECTID > Last_Seen` or `Last_Updated > Last_Check`.
*   **Benefit:** Reduces bandwidth usage by 99%. ensuring we only process *deltas* (changes).

### C. The Enricher (Targeted Scraper)
A sophisticated background worker that visits the Idox website *only when necessary*.
*   **Trigger Logic:**
    *   **New Record:** API sees a new Reference -> Queue for scraping.
    *   **Status Change:** API sees "Pending" change to "Approved" -> Queue for scraping (to get the Decision Date).
    *   **Data Gap:** Record exists but has no Agent -> Queue for scraping.
    *   **Stale Data:** Record hasn't been re-checked in 30 days -> Queue for scraping.
*   **Benefit:** Minimizes server bans and ensures CPU is focused on high-value missing data.

### D. The User Interface (Read-Only)
The webpage never fetches external data directly. It only queries your local database.
*   **Benefit:** Zero loading times. Instant search. 100% uptime (even if Council site crashes, your data is accessible).

---

## 2. Implementation Roadmap

### Phase 1: Foundation (Database & API)
**Objective:** Replace CSV with a self-updating database.
1.  **Schema Design:** Create `applications.db` with correct tables and indices.
2.  **API Syncer:** Write a script to fetch from York ArcGIS API and Insert/Update the database.
3.  **Migration:** Import your existing cached data (`addresses.json`) into the DB to preserve current work.

### Phase 2: The Enrichment Engine
**Objective:** Automate the gathering of "Idox-only" data.
1.  **Queue System:** Build a logical queue that prioritizes *New* and *Decided* applications over old ones.
2.  **Scraper Upgrade:** Integrate the "Dual-Tab" scraper (Summary + Details) into this engine.
3.  **Normalization:** Implement logic to clean up scraped text (e.g., standardizing Agent names).

### Phase 3: Intelligence & Accuracy Features
**Objective:** Ensure 100% trust in the data.
1.  **Audit Logging:** When a status changes (Pending -> Approved), record the date. This allows you to generate reports on "Average Approval Time".
2.  **Cross-Validation:** If the API says "Refused" but the Scraper sees "Approved", flag the record for manual review (Data discrepancy alert).
3.  **Geocoding Fallback:** If API coords are missing, use the scraped address to geocode (using a service like OS Data Hub or Google).

### Phase 4: Performance & Scale
**Objective:** Production-grade reliability.
1.  **Headless Browser Support:** Prepare to switch to Playwright/Selenium if Idox blocks the simple requests.
2.  **Rate Limiting:** Implement "Politeness" delays automatically to stay under the radar.

---

## 3. Immediate "Wins" (Why do this?)

1.  **Speed:** Your dashboard will load 5,000 records in milliseconds because it's reading local SQL, not parsing remote HTML.
2.  **Resilience:** If the Council website goes down for maintenance (which it does), your tracker keeps working.
3.  **Insight:** You will be able to answer questions like *"Which Agent gets the fastest approvals in York?"*—something impossible with the current CSV setup.
