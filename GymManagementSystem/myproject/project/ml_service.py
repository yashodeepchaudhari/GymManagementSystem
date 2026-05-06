"""
Churn predictor: classical ML (RandomForest) on member behavioral features.

Workflow:
  1. extract_features(member) -> dict of numeric features
  2. build_dataset() -> pandas DataFrame from current Members + past Subscriptions
  3. train_and_save() -> fits RandomForestClassifier, persists to ml_models/churn.pkl
  4. predict_for_member(member) -> probability of churn (0..1)
  5. predict_at_risk_members(threshold) -> queryset-like list of (member, prob)

Churn label = member's most recent subscription expired AND no new subscription
started within RENEWAL_WINDOW_DAYS afterwards.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import joblib
import pandas as pd
from django.conf import settings
from django.utils import timezone

from .models import Member, Subscription, Attendance, Payment

MODEL_DIR = settings.BASE_DIR / 'ml_models'
MODEL_PATH = MODEL_DIR / 'churn.pkl'
RENEWAL_WINDOW_DAYS = 14

FEATURE_COLUMNS = [
    'age',
    'days_since_join',
    'days_to_expiry',
    'attendance_last_30',
    'attendance_total',
    'payments_count',
    'avg_days_between_visits',
    'plan_amount',
]


def extract_features(member: Member) -> dict:
    today = timezone.now().date()
    join = member.join_date or today
    expiry = member.expiry_date or today
    days_since_join = max((today - join).days, 0)
    days_to_expiry = (expiry - today).days  # negative if already expired

    thirty_days_ago = timezone.now() - timedelta(days=30)
    attendance_qs = member.attendance.all()
    attendance_total = attendance_qs.count()
    attendance_last_30 = attendance_qs.filter(check_in__gte=thirty_days_ago).count()

    if attendance_total > 1 and days_since_join > 0:
        avg_gap = days_since_join / attendance_total
    else:
        avg_gap = float(days_since_join or 30)

    return {
        'age': member.age or 0,
        'days_since_join': days_since_join,
        'days_to_expiry': days_to_expiry,
        'attendance_last_30': attendance_last_30,
        'attendance_total': attendance_total,
        'payments_count': member.payments.count(),
        'avg_days_between_visits': avg_gap,
        'plan_amount': float(member.plan.amount) if member.plan_id else 0.0,
    }


def _label_member(member: Member) -> int | None:
    """1 = churned, 0 = retained, None = unknown (e.g., still active first cycle)."""
    subs = list(member.subscriptions.order_by('start_date'))
    if not subs:
        return None
    last = subs[-1]
    today = timezone.now().date()
    if last.end_date >= today:
        return 0  # still active = retained
    grace_end = last.end_date + timedelta(days=RENEWAL_WINDOW_DAYS)
    if today < grace_end:
        return None  # too soon to call
    renewed = any(s.start_date <= grace_end and s.start_date > last.end_date for s in subs)
    return 0 if renewed else 1


def build_dataset() -> pd.DataFrame:
    rows = []
    for m in Member.objects.select_related('plan').all():
        label = _label_member(m)
        if label is None:
            continue
        feats = extract_features(m)
        feats['churned'] = label
        feats['member_id'] = m.id
        rows.append(feats)
    return pd.DataFrame(rows)


def train_and_save() -> dict:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report

    df = build_dataset()
    if len(df) < 20:
        raise ValueError(f"Need at least 20 labeled members, got {len(df)}. Run `seed_demo` first.")

    X = df[FEATURE_COLUMNS]
    y = df['churned']

    if y.nunique() < 2:
        raise ValueError("Dataset has only one class. Need both churned and retained members.")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    clf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    clf.fit(X_train, y_train)

    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    report = classification_report(y_test, preds, zero_division=0, output_dict=True)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({'model': clf, 'columns': FEATURE_COLUMNS}, MODEL_PATH)

    return {
        'rows': len(df),
        'accuracy': round(acc, 3),
        'feature_importances': dict(zip(FEATURE_COLUMNS, clf.feature_importances_.round(3).tolist())),
        'report': report,
    }


def _load_model():
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def predict_for_member(member: Member) -> float | None:
    bundle = _load_model()
    if bundle is None:
        return None
    feats = extract_features(member)
    df = pd.DataFrame([[feats[c] for c in bundle['columns']]], columns=bundle['columns'])
    return float(bundle['model'].predict_proba(df)[0][1])


def forecast_signups(months_ahead: int = 3) -> dict:
    """
    Forecast next N months of signups using a simple LinearRegression on past
    monthly signup counts (with a 12-month seasonal feature).

    Returns:
        {
          'history':  [{'month': 'Jan 2026', 'count': 8}, ...],
          'forecast': [{'month': 'Jun 2026', 'count': 11}, ...],
        }
    """
    import calendar
    from datetime import date
    from collections import OrderedDict
    from sklearn.linear_model import LinearRegression
    import numpy as np

    members = Member.objects.values_list('join_date', flat=True)
    if not members:
        return {'history': [], 'forecast': []}

    # Bucket by year-month
    buckets = OrderedDict()
    for d in members:
        if not d:
            continue
        key = (d.year, d.month)
        buckets[key] = buckets.get(key, 0) + 1

    if len(buckets) < 3:
        # Not enough data to fit
        history = [{'month': f"{calendar.month_abbr[m]} {y}", 'count': c}
                   for (y, m), c in sorted(buckets.items())]
        return {'history': history, 'forecast': []}

    # Fill gaps in months between min and max
    all_keys = sorted(buckets.keys())
    start_y, start_m = all_keys[0]
    end_y, end_m = all_keys[-1]
    series_keys = []
    y, m = start_y, start_m
    while (y, m) <= (end_y, end_m):
        series_keys.append((y, m))
        m += 1
        if m > 12:
            y += 1
            m = 1
    counts = [buckets.get(k, 0) for k in series_keys]

    # Features: month index + sin/cos of month-of-year for seasonality
    X = np.array([[i, np.sin(2 * np.pi * k[1] / 12), np.cos(2 * np.pi * k[1] / 12)]
                  for i, k in enumerate(series_keys)])
    y_arr = np.array(counts)

    model = LinearRegression().fit(X, y_arr)

    # Forecast
    last_y, last_m = series_keys[-1]
    forecast = []
    for step in range(1, months_ahead + 1):
        last_m += 1
        if last_m > 12:
            last_y += 1
            last_m = 1
        idx = len(series_keys) - 1 + step
        Xf = np.array([[idx, np.sin(2 * np.pi * last_m / 12), np.cos(2 * np.pi * last_m / 12)]])
        pred = max(0, int(round(float(model.predict(Xf)[0]))))
        forecast.append({'month': f"{calendar.month_abbr[last_m]} {last_y}", 'count': pred})

    history = [{'month': f"{calendar.month_abbr[m]} {y}", 'count': c}
               for (y, m), c in zip(series_keys, counts)]
    return {'history': history, 'forecast': forecast}


def predict_at_risk_members(threshold: float = 0.0, top_n: int | None = None) -> list[tuple[Member, float]]:
    """Return active members sorted by descending churn probability.

    threshold: only include members with prob >= this value (0.0 = include all)
    top_n: cap result list to this many members
    """
    bundle = _load_model()
    if bundle is None:
        return []
    results = []
    for m in Member.objects.select_related('plan').all():
        if not m.is_active:
            continue
        feats = extract_features(m)
        df = pd.DataFrame([[feats[c] for c in bundle['columns']]], columns=bundle['columns'])
        prob = float(bundle['model'].predict_proba(df)[0][1])
        if prob >= threshold:
            results.append((m, prob))
    results.sort(key=lambda x: -x[1])
    if top_n:
        results = results[:top_n]
    return results
