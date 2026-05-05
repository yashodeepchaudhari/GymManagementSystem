# GymPro — AI-Powered Gym Management System

A full-stack Django application for running a gym, with **two AI integrations**:

1. **Generative AI** — Google Gemini produces personalized 7-day workout & diet plans for each member.
2. **Classical ML** — A scikit-learn `RandomForestClassifier` predicts member-churn probability so admins can intervene before renewals are lost.

---

## ✨ Highlights

| Area | What it does |
|---|---|
| Custom user model | `accounts.User` with `admin` / `trainer` / `member` roles |
| Admin panel | Members, Plans, Equipment, Enquiries, Gallery — full CRUD with search & pagination |
| Member portal | Self-service signup → choose plan → dashboard, attendance check-in, profile, AI plans |
| AI generator (Gemini) | Structured JSON workout + diet plans, stored in `WorkoutPlan` / `DietPlan` |
| Churn predictor (sklearn) | Trains on real attendance/payment/tenure data; ranks at-risk active members |
| Reports | Admin dashboard with monthly revenue chart (Chart.js), CSV export, ML risk table |
| Local-first | SQLite + local media by default; flip a flag in `.env` for MySQL/RDS + S3 |

---

## 🧱 Tech Stack

- **Django 5.1** with custom user model
- **SQLite** for local dev (MySQL-ready via `USE_MYSQL=True`)
- **Bootstrap 5** + Chart.js for UI
- **google-generativeai** SDK for Gemini API
- **scikit-learn** for churn prediction
- **python-decouple** for `.env` config

Optional production extras: AWS S3 (`django-storages`), `gunicorn`, `mysqlclient`.

---

## 🚀 Setup (Local)

```powershell
# 1. Create venv and activate
py -m venv venv
venv\Scripts\activate

# 2. Install
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env — at minimum set SECRET_KEY (any long random string).
# To enable real AI plans, add your Gemini key from
# https://aistudio.google.com/apikey

# 4. Run migrations
python manage.py migrate

# 5. Create admin user
python manage.py createsuperuser
# (or use the seeded admin: username=admin, password=admin12345)

# 6. (Demo) Seed fake data + train churn model
python manage.py seed_demo --clear
python manage.py train_churn

# 7. Run dev server
python manage.py runserver
```

Open http://127.0.0.1:8000/

---

## 🎬 Demo Walk-through (5 min)

1. **Public site** — `/` shows services, team members, and contact form.
2. **Member sign-up** — `/portal/signup/` → fill profile, pick a plan, get auto-logged-in.
3. **Member dashboard** — `/portal/dashboard/` — stats: days remaining, BMI, attendance count, payments. Click **Check In** to log a visit.
4. **AI plan generation** — click **Generate AI Plan** → calls Gemini → saves a `WorkoutPlan` + `DietPlan`. View the parsed JSON rendered as a 7-day accordion.
5. **Admin panel** — `/admin_login/` (admin / admin12345)
   - Dashboard: live KPIs, **monthly revenue bar chart**, **ML-predicted at-risk members** with probability bars
   - Members list: search box, pagination, edit, delete, **CSV export**
6. **Django admin** — `/admin/` for raw model access (custom User, Subscription, Payment, Attendance, AI plans).

---

## 🤖 AI Integration #1 — Gemini Workout & Diet Generator

**File:** `project/ai_service.py`

Flow:
```
Member profile
  ↓ (PROMPT_TEMPLATE with goal, BMI, experience, diet preference)
Gemini 1.5 Flash (response_mime_type=application/json)
  ↓
Parsed dict → saved to WorkoutPlan + DietPlan (JSONField)
  ↓
Rendered as 7-day accordion + meal cards
```

**Graceful fallback:** if `GEMINI_API_KEY` is empty, a deterministic mock plan is returned. The UI works end-to-end without an internet connection or API key.

**Why this is interesting in an interview:**
- Real prompt-engineering with structured JSON output
- Schema-driven generation (`response_mime_type='application/json'`)
- Error handling for malformed responses (regex strip + JSON parse fallback)
- Storage as `JSONField` — query-able and re-rendered without re-calling the API

---

## 🧠 AI Integration #2 — Churn Predictor (scikit-learn)

**File:** `project/ml_service.py`

| Component | Detail |
|---|---|
| Model | `RandomForestClassifier(n_estimators=100, max_depth=6)` |
| Features | age, days_since_join, days_to_expiry, attendance_last_30, attendance_total, payments_count, avg_days_between_visits, plan_amount |
| Label | `1` if member's last subscription expired AND they didn't renew within 14 days |
| Storage | `joblib.dump` → `ml_models/churn.pkl` |
| Surface | `predict_at_risk_members(top_n=10)` → admin dashboard with progress bars |

```bash
python manage.py seed_demo --clear   # 60 synthetic members with varied engagement
python manage.py train_churn          # trains + reports feature importances
```

Sample output:
```
Trained on 57 rows · accuracy=1.0
Top features:
  days_to_expiry                 0.466
  avg_days_between_visits        0.146
  plan_amount                    0.131
  attendance_total               0.106
  ...
```

**Honest note:** the synthetic seed data has clean separability, hence the high accuracy. Real-world churn data would land in the 70–85 % range — the same code applies; only the data changes.

---

## 🗂️ Project Structure

```
myproject/
├── accounts/                 # Custom User model (admin / trainer / member)
├── project/
│   ├── models.py            # 12 models: Member, Plan, Subscription, Payment,
│   │                        #   Attendance, WorkoutPlan, DietPlan, ...
│   ├── views.py             # Public + admin CRUD + reports + CSV export
│   ├── member_views.py      # Member-portal views (signup/login/dashboard/AI)
│   ├── forms.py             # ModelForms with Bootstrap auto-styling mixin
│   ├── ai_service.py        # Gemini integration
│   ├── ml_service.py        # Churn predictor (train + predict)
│   └── management/commands/
│       ├── seed_demo.py     # Generates demo data
│       └── train_churn.py   # Trains the churn model
├── myproject/                # Settings, root URLs
├── templates/
│   ├── admin_panel/         # Admin pages
│   └── portal/              # Member-portal pages
├── static/                  # CSS / images
├── ml_models/               # Trained .pkl files (gitignored)
└── manage.py
```

---

## 🔐 Environment Variables

See `.env.example`. Key vars:

| Var | Default | Purpose |
|---|---|---|
| `DEBUG` | True | Dev mode |
| `SECRET_KEY` | — | Required |
| `USE_MYSQL` | False | Switch from SQLite to MySQL |
| `USE_S3` | False | Switch from local storage to AWS S3 |
| `GEMINI_API_KEY` | empty | Enable real Gemini calls (mock fallback otherwise) |

---

## 📝 What's intentionally NOT in scope

- Production deployment (Docker / CI / monitoring) — kept local-first for clarity
- Payment gateway integration (Razorpay / Stripe) — `Payment` records are manually created
- Email notifications / Celery — easy add via Django's email backend, deferred for demo brevity
- REST API — DRF would slot into this codebase cleanly; out of scope for v1

---

## 🪜 Roadmap

- [ ] Razorpay/Stripe live payments
- [ ] Email expiry reminders via Celery + Redis
- [ ] DRF API + JWT auth for a mobile client
- [ ] Trainer dashboard (assign workouts, view assigned members)
- [ ] QR-code attendance scanner
