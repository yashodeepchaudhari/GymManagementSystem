# GymPro — AI-Powered Gym Management System

A full-stack Django application for running a gym end-to-end, with **three AI integrations** and **two classical-ML models**:

| | What it does | Stack |
|---|---|---|
| 🤖 **AI #1 — Plan Generator** | Generates personalized 7-day workout + diet plans | Google Gemini (`gemini-flash-latest`) with structured JSON output |
| 🤖 **AI #2 — Member Chatbot** | Conversational fitness coach on the member dashboard | Gemini chat API with member-aware system prompt + 10-message history |
| 🤖 **AI #3 — Body Vision Analyzer** | Member uploads a photo → posture & focus-area analysis | Gemini Vision (multi-modal) |
| 🧠 **ML #1 — Churn Predictor** | Ranks active members by likelihood of not renewing | scikit-learn `RandomForestClassifier` on 8 behavioral features |
| 🧠 **ML #2 — Signup Forecaster** | Predicts next 3 months of new signups | scikit-learn `LinearRegression` with 12-month seasonality |

The same Django app exposes a **JWT-secured REST API** (Swagger UI at `/api/docs/`), a **member portal**, an **admin panel**, a **trainer portal**, and a **QR-code attendance scanner**.

---

## ✨ Highlights

| Area | Detail |
|---|---|
| Three user roles | `admin`, `trainer`, `member` — each with its own login & dashboard |
| Custom user model | `accounts.User` extends `AbstractUser` with `role` + `phone` |
| Member portal | Self-service signup → choose plan → dashboard, attendance, profile, AI plans, body analysis, chatbot, plan/receipt PDF download |
| Admin panel | Members, Plans, Equipment, Enquiries, Gallery — full CRUD with search, pagination, edit, CSV export |
| Trainer portal | Dashboard with assigned members, AI plan view, notes editor |
| QR attendance | Member's dashboard shows their unique QR; staff `/scanner/` reads it via webcam (jsQR) |
| REST API | DRF + SimpleJWT + drf-spectacular, role-scoped permissions |
| Reports | Admin dashboard: monthly revenue chart, ML at-risk members, signup forecast |
| Tests | 32 pytest-django tests covering models, views, AI service, ML labelling |
| PDF | Multi-page AI plan PDF, single-page payment receipt PDF (reportlab) |
| Local-first | SQLite + local media by default; flip env flags for MySQL/RDS + S3 |

---

## 🧱 Tech Stack

- **Django 5.1** with custom user model
- **Django REST Framework** + `djangorestframework-simplejwt` + `drf-spectacular`
- **SQLite** for local dev (MySQL-ready via `USE_MYSQL=True`)
- **Bootstrap 5** + **Chart.js** + **Bootstrap Icons** for UI
- **google-generativeai** for the three AI surfaces
- **scikit-learn** + **pandas** + **joblib** for the two ML models
- **reportlab** for PDF generation
- **qrcode** + **jsQR** (browser) for QR attendance
- **pytest-django** for testing
- **python-decouple** for `.env` config

Optional extras (gated behind env flags): AWS S3 (`django-storages`), `mysqlclient`, `gunicorn`.

---

## 🚀 Setup (Local)

```powershell
# 1. Create virtual env and activate
py -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env — at minimum:
#   SECRET_KEY=any-long-random-string
#   GEMINI_API_KEY=your_key   (free key at https://aistudio.google.com/apikey)

# 4. Run migrations
python manage.py migrate

# 5. (Demo) Seed fake data + train churn model
python manage.py seed_demo --clear
python manage.py train_churn

# 6. Run dev server
python manage.py runserver
```

Open http://127.0.0.1:8000/

### Default demo credentials

| Role | URL | Username | Password |
|---|---|---|---|
| Admin | `/admin_login/` | `admin` | `admin12345` |
| Member | `/portal/login/` | `newtest` | `secret123` |
| Trainer | `/trainer/login/` | `coach_ravi` | `coach1234` |

---

## 🎬 Demo Walk-through (~7 min)

1. **Public site** → `/` — services, team, contact form, Member Login + Join Now buttons
2. **Member sign-up** — `/portal/signup/` → fill profile, pick plan, auto-login
3. **Member dashboard** — `/portal/dashboard/`
   - Stats: days remaining, BMI, attendance count
   - **Your Gym Entry QR** — printable code
   - **Generate AI Plan** → calls Gemini → 7-day workout + diet
   - **Chat bubble** (bottom-right) → conversational AI fitness coach
   - **Body Analysis** button → upload photo → Gemini Vision response
   - Download plan & receipts as PDF
4. **QR scanner demo** — log in as admin → SCANNER in nav → grant camera permission → point at the QR on a member's dashboard → JSON response with member name + plan + days left
5. **Trainer portal** — `/trainer/login/` (coach_ravi/coach1234)
   - 5 assigned members in a table
   - Click any → see their full profile + AI workout in accordion + notes editor
6. **Admin dashboard** — `/admin_login/` (admin/admin12345)
   - 6 stat cards including active members + 6-month revenue
   - **Monthly Revenue** bar chart
   - **Signup Forecast** line chart (solid actual + dashed predicted)
   - **Churn Risk (ML)** table with probability bars
   - CSV export, members search/edit/paginate
7. **REST API** — `/api/docs/` opens Swagger UI
   - `POST /api/auth/login/` with admin creds → returns JWT
   - `GET /api/me/` with `Authorization: Bearer <token>` → user + member
   - `GET /api/members/` — admin sees all 60+, member sees only own record

---

## 🤖 AI Integrations (Detail)

### #1 — Workout & Diet Plan Generator
**File:** `project/ai_service.py` → `generate_fitness_plan(member)`

Flow:
```
Member profile (age, BMI, goal, diet, experience)
   ↓ embedded in PROMPT_TEMPLATE
Gemini gemini-flash-latest with response_mime_type='application/json'
   ↓
{ summary, workout: [7 days × exercises], diet: [7 days × meals], tips: [...] }
   ↓
WorkoutPlan + DietPlan (JSONField) — re-rendered without re-calling API
```
**Graceful fallback:** if `GEMINI_API_KEY` is empty, a deterministic mock plan is returned so the UI works offline.

### #2 — Member Chatbot
**File:** `project/ai_service.py` → `chat_reply(member, message, history)`

- Floating widget injected via `templates/portal/base.html` for any logged-in member
- System prompt embeds member profile (age, BMI, goal, plan, expiry)
- Each request sends last 10 messages as Gemini chat history
- Endpoint: `POST /portal/chat/send/` (JSON), `GET /portal/chat/history/` (JSON)
- Persists every turn in the `ChatMessage` model

### #3 — Body Vision Analyzer
**File:** `project/ai_service.py` → `analyze_body_photo(member, image_bytes)`

- Member uploads JPEG/PNG (≤5 MB) at `/portal/ai/body/`
- Sent to Gemini Vision as multi-part content alongside the prompt
- Returns 3 sections: posture & proportions, focus areas, encouragement
- Photo + analysis stored in `BodyAnalysis` for history & progress tracking
- Refuses to claim exact body-fat % (responsible-AI guardrail in prompt)

### Cross-cutting design
- All three AIs share the same `GEMINI_API_KEY`
- All three have a mock fallback so the project works without internet/key
- Errors are logged and surfaced to the user via Django messages framework

---

## 🧠 ML Models (Detail)

### Churn Predictor — `project/ml_service.py`

| Component | Detail |
|---|---|
| Model | `RandomForestClassifier(n_estimators=100, max_depth=6)` |
| Features | age, days_since_join, days_to_expiry, attendance_last_30, attendance_total, payments_count, avg_days_between_visits, plan_amount |
| Label | 1 if last subscription expired AND no renewal within 14 days |
| Storage | `joblib.dump` → `ml_models/churn.pkl` |
| Surface | `predict_at_risk_members(top_n=10)` → admin dashboard with progress bars |

```bash
python manage.py seed_demo --clear   # 60 synthetic members
python manage.py train_churn          # trains + reports feature importances
```

### Signup Demand Forecaster — `project/ml_service.py`

| Component | Detail |
|---|---|
| Model | `LinearRegression()` with 3 features: time index + sin(2π·m/12) + cos(2π·m/12) |
| Why | Captures linear trend + 12-month seasonality without needing Prophet |
| Output | Next 3 months of predicted signup counts |
| Surface | Line chart on admin dashboard (solid history + dashed forecast) |

The seasonal feature lets the model say *"July has been strong every year, so July 2026 will likely be strong too"* even if the trend is flat.

---

## 🔌 REST API

Base URL: `/api/`

### Auth
```
POST /api/auth/login/   { "username": "...", "password": "..." }   → { access, refresh }
POST /api/auth/refresh/ { "refresh": "..." }                       → { access }
POST /api/auth/verify/  { "token": "..." }                         → 200/401
```
Pass `Authorization: Bearer <access>` on subsequent requests.

### Resources
| URL | Verbs | Notes |
|---|---|---|
| `/api/me/` | GET | Authenticated user + linked member if any |
| `/api/plans/` | GET, POST, PUT, DELETE | Members can list; only admins write |
| `/api/members/` | GET, POST, PUT, DELETE | Members see only their own row |
| `/api/subscriptions/` | GET, POST, PUT, DELETE | Same scope as members |
| `/api/payments/` | GET, POST, PUT, DELETE | Same scope as members |
| `/api/attendance/` | GET, POST, PUT, DELETE | Same scope as members |
| `/api/enquiries/` | POST (public), others admin-only | Lead capture |
| `/api/equipment/` | All verbs | Admin-only |
| `/api/workout-plans/` | GET (read-only) | Member sees own |
| `/api/diet-plans/` | GET (read-only) | Member sees own |

### Docs
- `/api/docs/` — Swagger UI
- `/api/redoc/` — ReDoc
- `/api/schema/` — OpenAPI schema (JSON)

---

## 🗂️ Project Structure

```
myproject/
├── accounts/                       # Custom User (admin / trainer / member)
├── project/
│   ├── models.py                   # 16 models including Trainer, ChatMessage, BodyAnalysis
│   ├── views.py                    # Public + admin CRUD + reports + CSV + QR scanner
│   ├── member_views.py             # Member-portal (signup/login/dashboard/chat/AI/PDFs/QR)
│   ├── trainer_views.py            # Trainer-portal (login/dashboard/member detail/notes)
│   ├── forms.py                    # ModelForms with Bootstrap auto-styling mixin
│   ├── ai_service.py               # Gemini: plan generator, chat, vision
│   ├── ml_service.py               # Churn predictor + signup forecaster
│   ├── pdf_service.py              # AI plan PDF + receipt PDF
│   ├── api/
│   │   ├── serializers.py          # 10 DRF serializers
│   │   ├── views.py                # Viewsets with role-scoped querysets
│   │   └── urls.py                 # Router + JWT + Swagger
│   ├── management/commands/
│   │   ├── seed_demo.py            # Generates 60 fake members
│   │   └── train_churn.py          # Trains the churn model
│   └── tests/
│       ├── test_models.py          # 11 model tests
│       ├── test_member_views.py    # 13 portal flow tests
│       ├── test_ai_service.py      # 5 AI tests (mock + real path with patched SDK)
│       └── test_ml_service.py      # 6 ML feature/labelling tests
├── myproject/                      # settings, root URLs
├── templates/
│   ├── admin_panel/                # Admin pages (shared .panel CSS in navbar)
│   ├── portal/                     # Member portal pages + chatbot widget
│   └── trainer/                    # Trainer portal pages
├── static/                         # CSS / images
├── ml_models/                      # Persisted .pkl files (gitignored)
├── pytest.ini
└── manage.py
```

---

## 🔐 Environment Variables

See `.env.example`. Key vars:

| Var | Default | Purpose |
|---|---|---|
| `DEBUG` | `True` | Dev mode |
| `SECRET_KEY` | — | **Required** |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | |
| `USE_MYSQL` | `False` | Switch from SQLite to MySQL |
| `USE_S3` | `False` | Switch from local storage to AWS S3 |
| `GEMINI_API_KEY` | empty | Enables real AI; mock fallback otherwise |
| `CSRF_TRUSTED_ORIGINS` | `http://127.0.0.1:8000` | Add prod hosts when deploying |

---

## 🧪 Testing

```bash
python -m pytest
```

```
================================================== 32 passed in 11s ==================================================
```

The AI tests use `unittest.mock.patch` to replace `google.generativeai.GenerativeModel`, so the suite never makes real API calls — fast and free to run in CI.

---

## 🛠️ Useful Management Commands

```bash
python manage.py seed_demo --clear   # 60 synthetic members + plans + payments + attendance
python manage.py train_churn         # retrain ML model with current data
python manage.py createsuperuser     # standard Django admin user
```

---

## 🪜 Roadmap

Already shipped — see Highlights table at top.

Possible next steps:
- [ ] Razorpay/Stripe live payments (replaces dummy `Payment` records)
- [ ] Email expiry reminders (Django Q2 + console backend → real SMTP later)
- [ ] PWA manifest so the member portal installs on phones
- [ ] Anomaly detection on attendance patterns (IsolationForest)
- [ ] Mobile-friendly trainer attendance scanner
- [ ] Multi-language support via Django's `i18n`

---

## 📝 What's intentionally NOT included

- Production deployment (Docker / CI / monitoring) — kept local-first for clarity
- Payment gateway integration — `Payment` rows are created manually or via signup
- SMTP email — easy to enable via `EMAIL_BACKEND` setting
- Cloud-only services — every feature runs on your laptop; only Gemini calls leave the machine

---

## 🙏 Credits & License

Educational project. Free to fork, study, and extend.

> *Three AI integrations, two ML models, three user roles, REST API, and 32 tests — all running on a free Gemini key and a single SQLite file.*
