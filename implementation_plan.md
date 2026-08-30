# AVENTIX: Event Analytics Dashboard Implementation Plan

This document outlines the 7-phase plan to build the AVENTIX Django web app. As requested, I will stop after completing each phase to allow you to review and approve the work before moving on to the next.

## Goal Description
Build a Django web app called AVENTIX that serves as an event analytics dashboard for a university. The app will strictly use Django, SQLite, Pandas, Matplotlib, and plain HTML/CSS. It will focus entirely on descriptive analytics (no prediction or inference) and will be developed in 7 distinct phases.

## Open Questions
- You requested model-level validators like `attendance <= registrations` and `completion <= attendance`. Should I enforce these within the model's `clean()` method so that `ModelForm` validation and the Django Admin naturally respect them?
- For the Pandas logic, is there any specific version of Pandas or Matplotlib you would prefer? Otherwise I'll just use the latest versions compatible with our Python environment.

## Phase 1: Django Setup & Models
- Initialize Django project `aventix` and app `events`.
- Implement `Event` model in `events/models.py`:
  - Fields: `name`, `event_type`, `department`, `academic_year`, `event_date`, `status`, `registrations`, `attendance`, `completion`, `feedback_rating`, `feedback_responses`.
  - Add constraints/validation: `attendance <= registrations`, `completion <= attendance`, `feedback_rating` between 1 and 5, counts >= 0, `unique_together` on `(name, event_date, department)`.
  - Register the model in `events/admin.py`.
- Run migrations.

## Phase 2: Synthetic Data Generation
- Create a Django management command `generate_synthetic_data` in `events/management/commands/`.
- Generate exactly 30 synthetic events covering the required edge cases: normal events, zero-registration, zero-attendance, zero-feedback-response, 1-4 feedback responses, attendance == registrations, cancelled event.
- Spread events across 4 departments and 3 event types.
- Add a label clearly stating it is synthetic data in a temporary README (which will be expanded in Phase 7).

## Phase 3: Analytics Logic
- Create `events/analytics.py` to house all Pandas logic.
- Implement functions: `load_dataframe()`, `validate(df)`, `add_metrics(df)`, `add_reliability_tier(df)`, `add_score(df)`, `add_insights(df)`, `groupby` summaries, `make_charts(df)`, and `compute_dashboard()`.
- Save charts to `static/events/img/`.

## Phase 4: Views
- Implement a single dashboard view in `events/views.py` that calls `analytics.compute_dashboard()` and passes the result to the template context. The logic will be strictly under 10 lines.

## Phase 5: Templates
- Create `dashboard.html` with plain HTML/CSS (no JS).
- Sections: Overview (KPIs), Participation (charts), Performance (ranked event table), Insights, Reliability (warning panel).

## Phase 6: Testing
- Implement unit tests in `events/tests.py` covering: zero-denominator edge cases, reliability tier boundaries, score calculations (ensuring attendance isn't double-counted), insight engine rules priority, and model validation constraints.

## Phase 7: Documentation
- Expand `README.md` to document the schema, formulas, reliability tier table, and the explicit "What AVENTIX Cannot Conclude" section.

## Verification Plan
After each phase, I will run the dev server or tests (if applicable) and pause execution for you to manually verify the progress.

### Automated Tests
- Running `python manage.py test` during Phase 6.

### Manual Verification
- You will be asked to review the codebase and interact with the local development server after each phase is completed.
