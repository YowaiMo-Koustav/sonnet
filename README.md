
# Sonnet – Smart Scheme & Job Informer

[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)

Sonnet is an AI-powered scholarship and scheme discovery web app that helps students and individuals quickly find, understand, and track opportunities they are actually eligible for.[file:1]  
It is being built for the **AI for Bharat** hackathon under the **AI for Communities, Access & Public Impact** problem track.[file:1]

---

## ✨ Problem & Motivation

Across India there are thousands of scholarships, government schemes, CSR/DGO programs, institute-specific schemes, and local opportunities, but most people never hear about the ones that apply to them.[file:1]  
Information is scattered across PDFs, brochures, websites, and notice boards, leading to missed financial support and lost opportunities.[file:1]

Sonnet tackles this by:

- Centralizing schemes from multiple sources (city/district → state → CSR/DGO → college → national).[file:1]  
- Using AI to parse brochures and PDFs into clear, short explanations and checklists.[file:1]  
- Matching users to relevant opportunities based on their profile and location.[file:1]  
- Letting users track their application progress in one place.[file:1]

---

## 🎯 Core Features

- **Location‑first discovery**  
  Browse and search schemes starting from district/city, then state, CSR/DGO, institutional, and national levels, with locality-aware ranking.[file:1]

- **AI brochure & PDF understanding**  
  Ingest scholarship brochures and PDFs, extract key fields (eligibility, deadlines, required documents), and generate ~100‑word “crisp blog” summaries.[file:1]

- **Eligibility matching & scoring**  
  Match user profiles (location, income, course, caste, etc.) against scheme criteria, compute a match/eligibility score, and rank opportunities accordingly.[file:1]

- **Application tracking dashboard**  
  Track the full lifecycle of each application (interested → in progress → submitted → under review → accepted/rejected) with a timeline-style UI.[file:1]

- **Multi-language friendly UX**  
  Designed to support Indian languages (English + regional), with a simple, mobile-first interface targeting rural and low-bandwidth users.[file:1]

- **Hackathon-ready demo flow**  
  Upload a real brochure, see AI extract information and generate a summary, then walk through the application tracking flow in a 2–3 minute demo.[file:1]

---

## 🛠 Tech Stack

### Frontend (current MVP – Lovable.dev)

- **Framework:** React + Vite + TypeScript (generated and iterated via [Lovable.dev](https://lovable.dev)).[file:1]  
- **UI:** Tailwind CSS + component abstractions (cards, badges, modals, forms, toasts).*[file:1]*  
- **App type:** Mobile‑first SPA/PWA, optimized for students on low‑end devices and networks.[file:1]  
- **Deployment:** Vercel (via GitHub integration) – live URL used for hackathon demo.[file:1]

*(Adjust this section to match your actual UI libs: e.g., add “shadcn/ui” if you’re using it.)*

### Backend (MVP runtime)

- **Supabase** as the primary backend in the Lovable app:  
  - PostgreSQL database for users, schemes, applications, and locations.[file:1]  
  - Auth (email/OTP) and row‑level security for multi‑tenant data isolation.[file:1]  
  - Storage and Edge Functions for any custom server logic.[file:1]

- **AI layer:**  
  - **Google Gemini API** for: brochure summarization, eligibility explanation, and recommendation logic.[file:1]  
  - **Firecrawl API** (optional) to crawl and normalize external scheme/job pages when needed.[file:1]

### Spec‑driven Python backend (separate Kiro repo)

In parallel, a spec‑first backend has been generated using **Kiro IDE** (AWS‑aligned, FastAPI + PostgreSQL) based on formal `requirements.md`, `design.md`, and `tasks.md` artifacts.[file:1]  
This backend includes rich domain models, property‑based tests (Hypothesis), and REST API designs, and lives in a separate GitHub repository that can be referenced as the **“Kiro backend”** for the hackathon submission.[file:1]

---

## 🏗 High-Level Architecture

**Current MVP path (what’s live):**

- React/Vite frontend (Lovable) deployed to Vercel.[file:1]  
- Frontend talks to Supabase (Postgres + Auth + Storage + Edge Functions) via environment-configured client.[file:1]  
- Frontend/Edge Functions call Google Gemini for summarization, matching, and search semantics, and optionally Firecrawl for web extraction.[file:1]

**Planned / parallel path (Kiro-driven backend):**

- Python FastAPI backend, PostgreSQL, and property‑based tests auto‑scaffolded/managed via Kiro (using the detailed `requirements.md`, `design.md`, and `tasks.md`).[file:1]  
- This backend is currently not wired to the Lovable frontend, but can be evolved post‑hackathon as the production-grade core service.[file:1]

---

## 🧩 Key Screens & Flows

- **Home / Discovery**  
  - Shows a prioritized feed of nearby opportunities based on the user’s location and profile.  
  - Uses “location‑first” ordering: district/city → state → CSR/DGO → college → national.[file:1]

- **Location Browser**  
  - Breadcrumbed hierarchy: country → state → district.[file:1]  
  - Search‑as‑you‑type + “use my location” shortcut for quick navigation (e.g., Ranchi-first testing).*[file:1]*

- **Search**  
  - Full‑text and semantic search across schemes by name, description, and criteria.  
  - Filters for location, scheme type, deadline range, education level, and “only eligible”.[file:1]

- **Scheme Detail**  
  - Shows “crisp blog” summary, eligibility criteria, required documents checklist, deadlines, and source brochure link.[file:1]  
  - If the user is logged in, shows a match percentage and explains which criteria passed/failed.[file:1]

- **Profile & Matches**  
  - Lets a user maintain their profile (location, income, course, caste, etc.).[file:1]  
  - Fetches and displays ranked recommendations based on that profile.[file:1]

- **Applications Dashboard**  
  - Central view of all applied/interested schemes with statuses and a simple timeline per application.[file:1]

- **Admin / Ingestion (MVP/simple)**  
  - Minimal admin surface to upload new brochures, review extracted fields, and correct low‑confidence data.[file:1]

---

## 🚀 Getting Started (MVP – Lovable + Supabase)

### Prerequisites

- Node.js 18+  
- A Supabase project (URL + anon/public key)[file:1]  
- Google Gemini API key (and Firecrawl key if you enable crawling)[file:1]

### 1. Clone the Repository

```bash
git clone <YOUR_FRONTEND_REPO_URL>

npm install
VITE_SUPABASE_URL=YOUR_SUPABASE_URL
VITE_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY

VITE_GEMINI_API_KEY=YOUR_GEMINI_API_KEY
npm run dev

## 📦 Production Deployment

### Frontend

- Connect the GitHub repo to **Vercel**.  
- Set all environment variables in Vercel’s dashboard (Supabase, Gemini, Firecrawl, etc.).[file:1]  
- Deploy the `main` branch and use the generated Vercel URL as your **Live Demo URL** for the hackathon.[file:1]

### Backend (MVP)

- Supabase is used as the hosted backend, so there are no extra deployment steps beyond configuring your project and SQL schema.[file:1]  
- Edge functions or API routes used by the frontend can be deployed via the Supabase CLI or dashboard.[file:1]

### Kiro Backend (separate repo)

- Keep the Kiro‑generated Python/Postgres backend in its own GitHub repo and link it in the hackathon submission under **“Backend / Spec‑driven repo”**.[file:1]  
- This highlights your use of Kiro for requirements, design, and property‑based testing, even if the live MVP is currently served via Supabase.[file:1]

---

## 🧭 Hackathon Submission Notes

For the **AI for Bharat** submission, a solid strategy is:

- **Live URL:** Vercel deployment of the Lovable React/Vite app (primary demo).[file:1]  
- **GitHub Repo (Backend / Spec):** Kiro‑generated backend repo (FastAPI + Postgres + property tests) to showcase AWS/Kiro and spec‑driven engineering.[file:1]

You can optionally link the frontend repo separately if the portal allows multiple GitHub links.[file:1]

---

## 🛣 Roadmap

Planned next steps include:

- Deeper integration between the Lovable frontend and the Kiro backend (FastAPI + Postgres) instead of Supabase‑only.[file:1]  
- Integrating **Bhashini** for multilingual text and audio summaries for rural users.[file:1]  
- More robust admin tools and analytics for CSR partners and government stakeholders (uptake rates, success metrics, regional insights).[file:1]  
- More automation for ingesting official portals via Firecrawl and/or direct APIs.[file:1]

---

## 🤝 Contributing

This is primarily a hackathon project, but contributions and feedback are welcome.

1. Fork the repository.  
2. Create a feature branch: `git checkout -b feature/amazing-feature`.  
3. Commit your changes: `git commit -m "Add amazing feature"`.  
4. Push to the branch: `git push origin feature/amazing-feature`.  
5. Open a Pull Request.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

**Built for AI for Bharat to make scholarships and schemes more discoverable, understandable, and actionable for students across India.**[file:1]


