<div align="center">

# 🎟️ GoAttend

### *Discover, Attend & Organize Events — All in One Place*

[![Django](https://img.shields.io/badge/Django-6.0.5-0c4b33?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/Django_REST-3.17-a30000?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-3ecf8e?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![Vercel](https://img.shields.io/badge/Frontend-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/)
[![Render](https://img.shields.io/badge/Backend-Render-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com/)
[![JWT](https://img.shields.io/badge/Auth-JWT-d63aff?style=for-the-badge&logo=jsonwebtokens&logoColor=white)](https://jwt.io/)
[![Cloudinary](https://img.shields.io/badge/Media-Cloudinary-3448C5?style=for-the-badge&logo=cloudinary&logoColor=white)](https://cloudinary.com/)

<br/>

**🌐 Live Demo:** &nbsp;[goattend.vercel.app](https://go-attend.vercel.app/) &nbsp;|&nbsp; **🔗 API:** &nbsp;[eventmanagement-api-5krr.onrender.com](https://eventmanagement-api-5krr.onrender.com/health/)

<br/>

> A **full-stack local event & ticketing platform** with role-based dashboards, QR-code ticket generation, live camera scanning, and a real-time organizer analytics panel — all deployed on a modern cloud stack.

</div>

---

## 📸 Platform Overview

| Role | View | Capability |
|------|------|------------|
| 🎟️ **Member** | Discover Page | Browse, filter & buy event tickets |
| 🎟️ **Member** | My Tickets | View QR-code tickets by status |
| 🎭 **Organizer** | Dashboard | Create, edit & delete events with live stats |
| 🎭 **Organizer** | Attendees | View ticket holders per event |
| 🎭 **Organizer** | Scanner | Live camera QR scan or manual hash verify |

---

## ✨ Features

### 👤 Role-Based Registration & Access
- **Self-registration** as either **Attendee** or **Event Organizer** via toggle cards
- Separate dashboards loaded automatically on login based on JWT role claim
- Server-enforced role whitelist — only `regular` or `organizer` accepted at registration
- Defense-in-depth: `is_staff` / `is_superuser` impossible via the public API

### 🎭 Organizer Dashboard
- **Full CRUD** — Create, edit, delete events with robust image upload (Cloudinary CDN with automatic unique UUID naming to prevent image overwriting)
- **Live stats panel** — Total revenue, tickets sold, scanned count, live event count
- **Attendees List** — Per-event table of ticket holders with scan status
- Status badges: `live` / `draft` / `past` / `sold_out` computed server-side
- Search & sort events from the dashboard
- **Robust Edit & Preview UI** — Built-in image preview loading states, and automatic error fallbacks to graceful default cards if image fails to load

### 🎟️ Member Experience
- Discover events with **category filter** (Music, Tech, Food, Arts), search, and date filter
- One-click ticket purchase with **atomic oversell protection** (PostgreSQL `SELECT FOR UPDATE`)
- **My Tickets** wallet with tabbed filter (All / Upcoming / Past / Used)
- **QR Code generation** — purple-branded, auto-rendered on page load
- Liked Events saved locally (no backend required)

### 📷 QR Scanner (Organizer)
- **Live camera scan** using `html5-qrcode` (browser media API)
- **Manual hash entry** for fallback verification
- `POST /api/tickets/verify/` → marks ticket as scanned in Supabase DB
- Shows: attendee name, email, event name, venue, price paid
- Handles **409 Already Scanned** with yellow warning card
- Scan history panel (last 20 scans)

### 🔐 Security
- **JWT Access + Refresh token** flow (`djangorestframework-simplejwt`)
- 401 → auto-refresh → retry in `api.js`; refresh fail → redirect to login
- CORS locked to Vercel origin in production
- Rate limiting on auth endpoints (`django-ratelimit`)
- Request timeout (10s) on all frontend API calls

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        CLIENT                           │
│              Vanilla HTML + JS + TailwindCSS            │
│                   Hosted on Vercel                      │
│                                                         │
│  index.html   organizer.html   scanner.html             │
│  tickets.html register.html    login.html  ...          │
│                                                         │
│  api.js ──────── window.GOATTEND_API ──────────────┐   │
│  config.js (generated at Vercel build by build.js)  │   │
└─────────────────────────────────────────────────────│───┘
                                                      │ HTTPS
┌─────────────────────────────────────────────────────▼───┐
│                       BACKEND                           │
│            Django 6 + Django REST Framework             │
│               Gunicorn + WhiteNoise                     │
│                   Hosted on Render                      │
│                                                         │
│  /api/auth/         accounts app (JWT, register, role)  │
│  /api/events/       events app  (CRUD, filtering)       │
│  /api/tickets/      tickets app (purchase, verify, scan)│
│  /api/organizer/    organizer-only dashboard endpoints  │
│  /health/           Render health check                 │
│  /health/cloudinary/ Cloudinary storage status & ping   │
└─────────────────────────────────────────────────────│───┘
                                                      │
              ┌───────────────────┬──────────────────┘
              │                   │
┌─────────────▼──────┐  ┌────────▼────────┐
│ Supabase Postgres  │  │   Cloudinary    │
│  (Serverless DB)   │  │ (Event Images)  │
│  User, Event,      │  │  Media Storage  │
│  Ticket tables     │  │  (ephemeral-    │
│                    │  │   safe on Render│
└────────────────────┘  └─────────────────┘
```

---

## 🛠️ Tech Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| ![Django](https://img.shields.io/badge/-Django-0c4b33?logo=django&logoColor=white) **Django** | 6.0.5 | Web framework & ORM |
| ![DRF](https://img.shields.io/badge/-DRF-a30000?logo=django&logoColor=white) **Django REST Framework** | 3.17.1 | REST API layer |
| ![JWT](https://img.shields.io/badge/-SimpleJWT-d63aff?logo=jsonwebtokens&logoColor=white) **SimpleJWT** | 5.5.1 | JWT access + refresh tokens |
| ![PostgreSQL](https://img.shields.io/badge/-PostgreSQL-4169e1?logo=postgresql&logoColor=white) **psycopg2** | 2.9.12 | PostgreSQL adapter |
| ![Gunicorn](https://img.shields.io/badge/-Gunicorn-499848?logo=gunicorn&logoColor=white) **Gunicorn** | 26.0.0 | Production WSGI server |
| ![WhiteNoise](https://img.shields.io/badge/-WhiteNoise-555?logo=python&logoColor=white) **WhiteNoise** | 6.12.0 | Compressed static file serving |
| ![Cloudinary](https://img.shields.io/badge/-Cloudinary-3448C5?logo=cloudinary&logoColor=white) **Cloudinary** | 1.41.0 | Event image storage |
| **django-cors-headers** | 4.9.0 | Cross-origin request handling |
| **django-filter** | 25.1 | Query filtering for event list |
| **django-ratelimit** | 4.1.0 | Auth endpoint rate limiting |
| **dj-database-url** | 3.1.2 | `DATABASE_URL` env → Django config |
| **Pillow** | 12.2.0 | ImageField processing |

### Frontend
| Technology | Purpose |
|------------|---------|
| ![HTML5](https://img.shields.io/badge/-HTML5-E34F26?logo=html5&logoColor=white) **Vanilla HTML5** | Markup — zero build step |
| ![JavaScript](https://img.shields.io/badge/-JavaScript-F7DF1E?logo=javascript&logoColor=black) **Vanilla JS (ES2020+)** | Logic — `async/await`, optional chaining |
| ![TailwindCSS](https://img.shields.io/badge/-TailwindCSS-06B6D4?logo=tailwindcss&logoColor=white) **TailwindCSS v3** | Utility-first styling (CDN) |
| **QRCode.js** | Client-side QR code generation |
| **html5-qrcode** | Camera-based QR code scanning |
| **Google Fonts** | Inter + Space Grotesk typography |
| **Material Symbols** | Icon set |

### Infrastructure
| Service | Role |
|---------|------|
| ![Render](https://img.shields.io/badge/-Render-46E3B7?logo=render&logoColor=black) **Render** | Backend hosting (free tier) |
| ![Vercel](https://img.shields.io/badge/-Vercel-000?logo=vercel&logoColor=white) **Vercel** | Frontend hosting (free tier) |
| ![Supabase](https://img.shields.io/badge/-Supabase-3ecf8e?logo=supabase&logoColor=white) **Supabase** | Serverless PostgreSQL |
| ![Cloudinary](https://img.shields.io/badge/-Cloudinary-3448C5?logo=cloudinary&logoColor=white) **Cloudinary** | Media CDN |
| ![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github&logoColor=white) **GitHub** | Source control + CI trigger |

---

## 📁 Project Structure

```
event_platform/
│
├── 📂 accounts/                   # User auth app
│   ├── models.py                  # Custom User model (role field)
│   ├── serializers.py             # Registration (role whitelist), JWT, Profile
│   ├── views.py                   # Register, Login, Profile, IsOrganizerCheck
│   ├── urls.py                    # /api/auth/* routes
│   └── admin.py                   # Admin registration
│
├── 📂 events/                     # Events & Tickets app
│   ├── models.py                  # Event, Ticket (QR hash, scan tracking)
│   ├── serializers.py             # EventList, EventDetail, Organizer, Ticket (QR + attendee)
│   ├── views.py                   # CRUD + Purchase + Verify + Scan
│   ├── permissions.py             # IsOrganizer, IsOrganizerOrReadOnly, IsEventOwnerOrReadOnly
│   ├── filters.py                 # EventFilter (category, date, price)
│   └── urls.py                    # /api/events/* + /api/tickets/* + /api/organizer/*
│
├── 📂 core/                       # Django project core
│   ├── settings.py                # All configuration (env-driven for prod)
│   └── urls.py                    # Root URL conf + health check
│
├── 📂 frontend/                   # Static frontend (deployed to Vercel)
│   ├── index.html                 # 🏠 Member: Event discovery
│   ├── register.html              # 📝 Attendee / Organizer role selection
│   ├── login.html                 # 🔐 Login → role-aware redirect
│   ├── event.html                 # 📋 Single event detail + buy ticket
│   ├── tickets.html               # 🎟️ My tickets wallet + QR codes
│   ├── liked.html                 # ❤️ Liked events (localStorage)
│   ├── profile.html               # 👤 User profile
│   ├── organizer.html             # 🎭 Organizer: event CRUD dashboard
│   ├── organizer-attendees.html   # 📊 Organizer: attendees per event
│   ├── scanner.html               # 📷 Organizer: QR camera scanner
│   ├── api.js                     # 🔌 All API calls (fetch wrapper, auth, helpers)
│   └── config.js                  # ⚙️ API base URL (overwritten at Vercel build)
│
├── build.js                       # Vercel build script (generates config.js)
├── vercel.json                    # Vercel config (outputDirectory: frontend)
├── render.yaml                    # Render service config
├── requirements.txt               # Python dependencies (pinned)
├── manage.py                      # Django management
└── .env.example                   # Environment variable template
```

---

## 🔌 API Reference

Base URL: `https://eventmanagement-api-5krr.onrender.com/api`

### Auth Endpoints (`/api/auth/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register/` | Public | Create account. Body: `{username, email, password, password2, role}`. Role: `"regular"` or `"organizer"` |
| `POST` | `/auth/token/` | Public | Login. Returns `{access, refresh}` JWT tokens |
| `POST` | `/auth/token/refresh/` | Public | Exchange refresh token for new access token |
| `POST` | `/auth/logout/` | Auth | Blacklist refresh token |
| `GET/PATCH` | `/auth/profile/` | Auth | Get or update user profile |
| `GET` | `/auth/is-organizer/` | Auth | Returns `{is_organizer, username, role}` — used by scanner gate |

### Event Endpoints (`/api/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/events/` | Public | List published events. Query: `?category=music&search=jazz&ordering=date` |
| `POST` | `/events/` | Organizer | Create event (multipart/form-data for image) |
| `GET` | `/events/<id>/` | Public | Single event detail |
| `PATCH` | `/events/<id>/` | Owner Organizer | Update event fields |
| `DELETE` | `/events/<id>/` | Owner Organizer | Delete event |
| `GET` | `/organizer/events/` | Organizer | Own events with stats (`revenue`, `tickets_sold`, `scanned_count`, `status_label`) |
| `GET` | `/organizer/events/<id>/attendees/` | Owner Organizer | Ticket holders for one event |

### Ticket Endpoints (`/api/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/tickets/purchase/` | Auth | Buy ticket. Body: `{event: <id>}`. Returns ticket with `qr_data` |
| `GET` | `/user/tickets/` | Auth | Own tickets with `qr_data`, `attendee_name`, `event_status` |
| `POST` | `/tickets/verify/` | Organizer | Scan ticket by hash. Body: `{ticket_hash: "..."}` |
| `POST` | `/tickets/<hash>/scan/` | Organizer | Alternative scan endpoint via URL param |

### Health & Diagnostics (`/health/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health/` | Public | Core platform health check (returns `{"status": "ok"}`) |
| `GET` | `/health/cloudinary/` | Public | Live Cloudinary connectivity test & credentials status check |

### Response Shapes

<details>
<summary><b>Ticket Purchase Response</b></summary>

```json
{
  "id": 1,
  "ticket_hash": "d6bfa9f20e06510b...",
  "qr_data": "d6bfa9f20e06510b...",
  "attendee_name": "john_doe",
  "attendee_email": "john@example.com",
  "is_scanned": false,
  "event_status": "Upcoming",
  "price_paid": "200.00",
  "purchased_at": "2026-05-17T04:47:37Z",
  "event": {
    "id": 2,
    "title": "Live Jazz Night",
    "category": "music",
    "date": "2026-06-14T18:00:00Z",
    "venue_name": "City Hall",
    "price": "200.00",
    "tickets_remaining": 49
  }
}
```
</details>

<details>
<summary><b>QR Scan Success Response (200)</b></summary>

```json
{
  "status": "success",
  "message": "Access granted.",
  "ticket": {
    "attendee_name": "john_doe",
    "attendee_email": "john@example.com",
    "is_scanned": true,
    "event": { "title": "Live Jazz Night", "venue_name": "City Hall" },
    "price_paid": "200.00"
  }
}
```
</details>

<details>
<summary><b>QR Scan Already-Scanned Response (409)</b></summary>

```json
{
  "status": "error",
  "message": "Ticket already scanned.",
  "attendee": "john_doe",
  "event": "Live Jazz Night",
  "scanned_at": "2026-05-17T06:30:00Z"
}
```
</details>

<details>
<summary><b>Organizer Event Stats</b></summary>

```json
{
  "id": 2,
  "title": "Live Jazz Night",
  "status_label": "live",
  "tickets_sold": 12,
  "tickets_remaining": 38,
  "scanned_count": 5,
  "revenue": "2400.00",
  "is_published": true,
  "is_upcoming": true
}
```
</details>

---

## 🚀 Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ (for Vercel build script)
- PostgreSQL (or use SQLite for local dev)

### 1. Clone & Install Backend

```bash
git clone https://github.com/07pavan/EventManagement_Sys.git
cd EventManagement_Sys

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env
```

Edit `.env` with your values:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (use SQLite locally or Supabase for full-stack)
DATABASE_URL=sqlite:///db.sqlite3
# Or Supabase: DATABASE_URL=postgresql://postgres.xxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require

# Cloudinary (optional locally — images won't upload without it)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# CORS (allow frontend origin)
CORS_ALLOWED_ORIGINS=http://127.0.0.1:5500,http://localhost:5500
```

### 3. Run Migrations & Start Backend

```bash
python manage.py migrate
python manage.py createsuperuser   # optional — for Django Admin
python manage.py runserver 8001
```

Backend is now at: `http://127.0.0.1:8001`

### 4. Start Frontend

Open `frontend/index.html` in your browser using **Live Server** (VS Code extension) on port 5500,  
or use any static file server:

```bash
# Python built-in server
cd frontend
python -m http.server 5500
```

The `frontend/config.js` already points to `http://127.0.0.1:8001/api` for local dev.

### 5. Access the App

| URL | Page |
|-----|------|
| `http://localhost:5500/index.html` | Member: Discover events |
| `http://localhost:5500/register.html` | Register (choose Attendee or Organizer) |
| `http://localhost:5500/login.html` | Login |
| `http://localhost:5500/organizer.html` | Organizer dashboard |
| `http://localhost:5500/scanner.html` | QR scanner |
| `http://127.0.0.1:8001/admin/` | Django Admin |

---

## ☁️ Production Deployment

### Backend → Render

1. Connect your GitHub repo to [Render](https://render.com/)
2. Create a **Web Service** with:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn core.wsgi:application`
3. Add environment variables in Render dashboard:

```
SECRET_KEY          = <generate a long random string>
DEBUG               = False
ALLOWED_HOSTS       = your-app.onrender.com,localhost
DATABASE_URL        = postgresql://...  (from Supabase Connection Pooler)
CLOUDINARY_CLOUD_NAME / API_KEY / API_SECRET
CORS_ALLOWED_ORIGINS = https://your-app.vercel.app
```

> **Note:** Free tier Render services spin down after inactivity. First request may take 30–60s.

### Frontend → Vercel

1. Connect your GitHub repo to [Vercel](https://vercel.com/)
2. Set these in **Project Settings → Environment Variables**:

```
RENDER_API_URL = https://your-app.onrender.com
```

3. Vercel will auto-detect `vercel.json` and:
   - Run `node build.js` (generates `frontend/config.js` with production API URL)
   - Serve the `frontend/` directory

### Database → Supabase

1. Create a free project at [supabase.com](https://supabase.com/)
2. Copy the Connection Pooler connection string (Transaction Mode, port 6543) into `DATABASE_URL` on Render
3. First deploy runs `python manage.py migrate` automatically via Render's pre-deploy hook

---

## 🔒 Security Implementation

| Concern | Implementation |
|---------|---------------|
| **Authentication** | JWT (access: 2h TTL, refresh: 7d TTL) |
| **Role enforcement** | Server-side `is_organizer` check on every protected route |
| **Ticket overselling** | `SELECT FOR UPDATE` row lock in `TicketPurchaseSerializer.create()` |
| **Duplicate tickets** | `unique_together = [(user, event)]` at DB level |
| **Role injection** | Registration whitelist: only `regular`/`organizer` accepted |
| **Privilege escalation** | `is_staff`, `is_superuser` stripped in serializer |
| **CORS** | Locked to Vercel origin via `CORS_ALLOWED_ORIGINS` |
| **Rate limiting** | `django-ratelimit` on auth endpoints |
| **Secrets** | All secrets in env vars, never in code |
| **Token refresh** | `api.js` auto-retries 401 with refresh token before redirect |

---

## 📊 Data Models

```
User (accounts.User)
├── username, email, password
├── role: "regular" | "organizer"    ← custom field
├── first_name, last_name
└── is_active, is_staff, is_superuser

Event (events.Event)
├── title, description
├── category: "music" | "tech" | "food" | "arts"
├── date (DateTimeField)
├── venue_name, latitude, longitude
├── price (Decimal), total_tickets
├── image (Cloudinary ImageField)
├── organizer → FK(User)
├── is_published (Bool)
└── created_at, updated_at

Ticket (events.Ticket)
├── user → FK(User)
├── event → FK(Event)
├── ticket_hash (SHA-256, unique)    ← encoded as QR code
├── is_scanned (Bool)
├── scanned_at (DateTime)
├── price_paid (Decimal snapshot)
└── purchased_at
    [unique_together: (user, event)] ← no duplicate tickets
```

---

## 🗺️ User Flow

```
MEMBER FLOW
───────────
Register (role: regular) → Login → index.html
    │
    ├─ Browse events (filter by category/search/date)
    ├─ View event detail → Buy ticket (atomic, oversell-safe)
    ├─ My Tickets → View QR code (purple-branded)
    └─ Liked events (client-side favorites)

ORGANIZER FLOW
──────────────
Register (role: organizer) → Login → organizer.html
    │
    ├─ Dashboard: view all own events + stats (revenue, sold, scanned)
    ├─ Create event (title, date, category, price, image upload)
    ├─ Edit / Delete events
    ├─ Attendees list → per-event ticket holder table
    └─ Scanner → open camera → scan member QR → instant verify
           ✓ Access Granted (green)
           ⚠ Already Scanned (yellow + timestamp)
           ✗ Invalid / Denied (red)
```

---

## 🤝 Contributing

Contributions are welcome! Here's how:

```bash
# 1. Fork the repo and clone
git clone https://github.com/your-username/EventManagement_Sys.git

# 2. Create a feature branch
git checkout -b feature/your-feature-name

# 3. Make your changes, then commit
git commit -m "feat: describe your change"

# 4. Push and open a Pull Request
git push origin feature/your-feature-name
```

**Commit conventions:**
- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation
- `refactor:` — code cleanup
- `chore:` — config/build changes

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<div align="center">

**Built with ❤️ using Django + Vanilla JS**

[![GitHub](https://img.shields.io/badge/GitHub-07pavan-181717?style=flat-square&logo=github)](https://github.com/07pavan/EventManagement_Sys)
[![Live Demo](https://img.shields.io/badge/Live_Demo-GoAttend-630ed4?style=flat-square&logo=vercel)](https://go-attend.vercel.app/)
[![API Health](https://img.shields.io/badge/API-Healthy-46E3B7?style=flat-square&logo=render)](https://eventmanagement-api-5krr.onrender.com/health/)

*GoAttend — Where every event finds its audience.*

</div>
