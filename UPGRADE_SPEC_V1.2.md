# UPGRADE_SPEC_V1.2 — Technical Upgrade Specification
## Founder Co-Pilot: Multi-Platform CLI → Automated SaaS Growth Engine

**Version:** 1.2  
**Date:** 2026-02-09  
**Status:** DRAFT  
**Goal:** Transition to a full-stack growth engine with automated outreach, web visualization, and deeper CRM integration.

---

## 1. Executive Summary

Founder Co-Pilot V1.1 established a robust foundation for multi-platform discovery and scoring. V1.2 focuses on **actionability** and **visualization**. We will introduce a web-based dashboard for easier data exploration, automated outreach modules to engage with the discovered leads, and direct synchronization with common CRM platforms.

### 1.1 Core Objectives
- **Visualization:** Move beyond terminal tables to a searchable Web Dashboard.
- **Outreach:** Automatically generate and track engagement with potential leads.
- **Expansion:** Add IndieHackers and Product Hunt as high-signal sources.
- **Integration:** One-click sync to HubSpot/Salesforce.

---

## 2. Web Dashboard Architecture

### 2.1 Backend: FastAPI
- **Path:** `copilot/dashboard/api.py`
- **Purpose:** Serve as the bridge between the SQLite database and the Frontend.
- **Endpoints:**
    - `GET /signals`: Search/filter discovered opportunities.
    - `GET /personas`: Retrieve generated ICPs.
    - `POST /outreach/generate`: Generate draft messages for a lead.
    - `POST /sync/crm`: Push selected leads to configured CRM.

### 2.2 Frontend: Streamlit / React
- **Choice:** **Streamlit** for Phase 1 (rapid prototyping), **React** for Phase 2 (full interactivity).
- **Features:**
    - Interactive "Opportunity Map" (Bubble chart of Pain vs. Engagement).
    - Persona Detail Cards.
    - Lead Management Table with "One-Click Outreach" buttons.

---

## 3. Outreach Automation Engine

### 3.1 OutreachModule
- **Path:** `copilot/modules/outreach.py`
- **Logic:** Uses LLM (Opus 4.6) to draft tailored outreach messages based on the specific pain point detected.
- **Channels:**
    - **Reddit:** Draft DM/Comment response.
    - **LinkedIn:** Generate connection request and personalized pitch.
    - **Twitter/X:** Draft direct replies.
- **Tracking:** Maintain an `outreach_history` table in SQLite to avoid double-contacting.

---

## 4. Advanced Data Sources

### 4.1 New Scrapers
- **IndieHackersScraper:** Fetching "Product Ideas" and "Validation Stories" (via RSS/Scraping).
- **ProductHuntScraper:** Monitoring daily launches and "Hunter" feedback (via GraphQL API).
- **Integration:** Registered in the existing `ScraperRegistry` with `REALTIME` capabilities.

---

## 5. CRM Synchronization

### 5.1 SyncModule
- **Path:** `copilot/modules/sync.py`
- **Providers:**
    - **HubSpot:** Via HubSpot API.
    - **Salesforce:** Via Salesforce REST API.
    - **Webhook:** Generic outbound webhook for Zapier/Make.
- **Features:** Automated mapping of `Lead` fields to CRM `Contact` properties.

---

## 6. Data Schema Evolution (Additive)

### 6.1 Schema Updates (`copilot/models/schemas.py`)
- **`Lead` Model Extensions:**
    - `outreach_status`: `[pending, drafted, contacted, converted, ignored]`
    - `crm_id`: External ID from HubSpot/Salesforce.
    - `last_contacted_at`: Timestamp.
- **New Table: `outreach_history`**
    - `post_id`, `lead_id`, `channel`, `message_draft`, `sent_at`.

---

## 7. Implementation Roadmap

### Phase 1: Dashboard & Expansion (Week 1-2)
- Implement FastAPI backend.
- Build initial Streamlit dashboard.
- Add IndieHackers & Product Hunt scrapers.

### Phase 2: Outreach & Tracking (Week 3-4)
- Implement `OutreachModule`.
- Add outreach status tracking to database.
- CLI command: `copilot outreach --lead-id <id>`.

### Phase 3: CRM & Final Polish (Week 5-6)
- Implement `SyncModule` (HubSpot focus).
- Transition Dashboard to a more robust UI.
- Final V1.2 documentation and E2E tests.

---

*End of UPGRADE_SPEC_V1.2 — Technical Upgrade Specification*  
*Drafted: 2026-02-09 | Assisted by Opus 4.6*
