# AVENTIX
 
**AVENTIX** is a Django-based event analytics and planning dashboard for universities. It ingests multi-event data (registrations, attendance, completion, feedback) and produces descriptive analytics: conversion rates, completion rates, a composite participation-quality score, reliability-aware feedback analysis, and a rule-based insight engine — all rendered as a server-side dashboard with Matplotlib charts.
 
AVENTIX is a **descriptive analytics** tool. It reports what happened in the data. It does not predict, forecast, or infer *why* something happened — see [Limitations](#limitations) below.
 
---
 
## Tech Stack
 
Everything here is free and runs locally — no paid APIs, no cloud services required.
 
| Layer | Tool |
|---|---|
| Web framework | Django |
| Database | SQLite |
| Analytics | Pandas |
| Charts | Matplotlib |
| Frontend | Plain HTML/CSS (no JS framework) |
 
---
 
## Features
 
- **Event dataset** with model-level validation (attendance ≤ registrations, completion ≤ attendance, feedback rating 1–5, non-negative counts).
- **Core metrics**: Attendance Conversion Rate, Completion Rate, per-department and per-year summaries.
- **Reliability engine**: every feedback rating is tagged with a confidence tier (No Data / Insufficient Evidence / Low / Moderate / High Confidence) based on response count, so small samples are never presented with false certainty.
- **Composite Participation-Quality Score**: a transparent, equal-weighted, non-double-counted score combining participation, completion, and feedback.
- **Rule-based insight engine**: fixed-priority rules (e.g. "High Quality, Low Reach", "No-show Alert", "Strong Completion") that describe patterns without claiming causation.
- **Dashboard**: Overview, Participation, Performance, Insights, and Reliability sections, with Matplotlib charts embedded as static images.
- **Data quality panel**: invalid records are flagged and shown, never silently dropped.
---
 
## Project Status
 
- [x] Phase 1 — Django setup & `Event` model
- [x] Phase 2 — Synthetic dataset (30 events)
- [x] Phase 3 — Analytics engine (`analytics.py`)
- [x] Phase 4 — Dashboard view
- [x] Phase 5 — Dashboard template
- [x] Phase 6 — Test suite
- [x] Phase 7 — Documentation
---
 
## Getting Started
 
### Prerequisites
- Python 3.10+
- pip
### Setup
 
```bash
git clone https://github.com/<your-username>/aventix.git
cd aventix
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
 
python manage.py migrate
python manage.py generate_synthetic_data   # loads 30 sample events
python manage.py createsuperuser           # optional, for /admin access
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` for the dashboard and `http://127.0.0.1:8000/admin/` to manage event records.

### Local Network (LAN) Testing

If you want to test the app on your phone, tablet, or another computer on the same Wi-Fi network:

1. Ensure your host machine's firewall allows inbound connections on port `8000`.
   - **Windows (PowerShell as Admin):** `New-NetFirewallRule -DisplayName "Django LAN" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow`
   - **macOS:** System Settings > Network > Firewall > Options > "Automatically allow built-in software to receive incoming connections" (or explicitly add python).
   - **Linux (ufw):** `sudo ufw allow 8000/tcp`
2. Run the LAN helper script from your terminal:
   ```bash
   python run_lan.py
   ```
3. The script will print the exact URL (e.g., `http://192.168.1.5:8000`) and display a QR code to easily open the app on your phone.
4. *(Optional)* If you submit forms from another device (like logging into the admin panel), ensure you set `CSRF_TRUSTED_ORIGINS=http://192.168.x.x:8000` in your environment to prevent CSRF errors.
 
### Running Tests
 
```bash
python manage.py test
```
 
---
 
## Dataset Schema
 
| Field | Type | Rule |
|---|---|---|
| `event_id` | AutoField (PK) | Auto-generated |
| `name` | CharField | Required |
| `event_type` | CharField (choices) | Required — Workshop, Seminar, Cultural, Fest, Sports |
| `department` | CharField (choices) | Required — fixed list to prevent typos |
| `academic_year` | CharField (choices) | Required — one consistent format, e.g. `2025-26` |
| `event_date` | DateField | Required |
| `status` | CharField (choices) | Planned / Completed / Cancelled. Only `Completed` events enter analytics. |
| `registrations` | PositiveIntegerField | ≥ 0 |
| `attendance` | PositiveIntegerField | ≥ 0 and ≤ `registrations` |
| `completion` | PositiveIntegerField (optional) | ≥ 0 and ≤ `attendance`; null = not tracked |
| `feedback_rating` | FloatField (optional) | 1.0–5.0; null if `feedback_responses` = 0 |
| `feedback_responses` | PositiveIntegerField | ≥ 0 |
 
Validation is enforced at the model layer (`clean()`), the form layer, and re-checked in the Pandas layer. Invalid rows are **flagged**, not deleted — they stay visible in the dashboard's Data Quality Warnings panel.
 
---
 
## Metrics & Formulas
 
**Attendance Conversion Rate**
```
conversion_rate = attendance / registrations * 100
# NaN if registrations == 0
```
 
**Completion Rate**
```
completion_rate = completion / attendance * 100
# NaN if attendance == 0 or completion is not tracked
```
 
### Feedback Reliability Tiers
 
| Responses | Tier | Dashboard treatment |
|---|---|---|
| 0 | No Data | Rating shown as N/A; never scored |
| 1–4 | Insufficient Evidence | Shown greyed out with a warning; excluded from scoring |
| 5–19 | Low Confidence | Used in scoring, tagged "low confidence" |
| 20–49 | Moderate Confidence | Used normally, tagged "moderate confidence" |
| 50+ | High Confidence | Used normally, no tag |
 
### Composite Participation-Quality Score
 
```python
attendance_norm  = attendance / attendance.max()
conversion_norm  = conversion_rate / 100
completion_norm  = completion_rate / 100
feedback_norm    = (feedback_rating - 1) / 4
 
# Attendance and Conversion are collapsed into ONE term so attendance
# is never counted twice in the score.
participation_score = (attendance_norm + conversion_norm) / 2
 
score = (1/3) * participation_score \
      + (1/3) * completion_norm \
      + (1/3) * feedback_norm
```
 
Equal weighting (1/3 each) is the default and is documented as a stated choice, not a derived optimum. A sensitivity check (re-ranking with each weight shifted ±10 points) is used to confirm the top-5 ranking is stable before trusting it.
 
Only events with `is_valid == True` and a feedback tier above "Insufficient Evidence" are scored and ranked.
 
### Insight Engine (fixed priority order)
 
| Priority | Rule | Condition |
|---|---|---|
| 1 | Data Quality Issue | `is_valid == False` |
| 2 | Exceptional Score | Score in top decile, feedback tier ≥ Low Confidence |
| 3 | High Quality, Low Reach | Feedback in top quartile AND attendance in bottom quartile (within event type) |
| 4 | High Reach, Low Satisfaction | Attendance in top quartile AND feedback in bottom quartile |
| 5 | No-show Alert | Conversion rate < 30% |
| 6 | Strong Completion | Completion rate > 90% |
 
Only the first matching rule becomes an event's headline insight. A "Low Reliability" tag is attached separately whenever feedback is in the Insufficient or Low tier — it never replaces the headline insight. All insight text describes patterns in the data; it never states or implies a cause.
 
---
 
## Limitations
 
AVENTIX is descriptive only. It explicitly **cannot**:
 
- Predict or forecast future attendance.
- Infer *why* an outcome occurred (e.g. it will not say "students disliked the timing" — only that conversion was low).
- Correct for feedback response bias (e.g. only satisfied attendees responding).
- Compare departments or years on a true per-capita basis — eligible population size is not collected in v1.
- Guarantee statistical significance for small feedback samples — it only flags them as lower confidence.
---
 
## Project Structure
 
```
aventix/
  aventix/                 # settings, urls, wsgi
  events/
    models.py              # Event model + validators
    admin.py
    analytics.py            # all Pandas logic
    views.py                 # thin dashboard view
    urls.py
    tests.py
    management/commands/generate_synthetic_data.py
    templates/dashboard.html
    static/events/css/, static/events/img/
```
 
---
 
## License
 
MIT License
