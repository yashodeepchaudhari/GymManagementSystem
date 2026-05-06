"""Tests for ML churn predictor."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from project.models import Plan, Member, Subscription
from project.ml_service import (
    extract_features, _label_member, FEATURE_COLUMNS,
)


@pytest.mark.django_db
class TestFeatureExtraction:
    def test_features_have_all_columns(self, member):
        feats = extract_features(member)
        assert set(feats.keys()) == set(FEATURE_COLUMNS)

    def test_features_numeric(self, member):
        feats = extract_features(member)
        for v in feats.values():
            assert isinstance(v, (int, float))


@pytest.mark.django_db
class TestLabeling:
    def test_active_member_returns_zero(self, member, plan):
        Subscription.objects.create(
            member=member, plan=plan,
            start_date=date.today() - timedelta(days=5),
        )
        assert _label_member(member) == 0

    def test_recently_expired_member_returns_none(self, expired_member, plan):
        Subscription.objects.create(
            member=expired_member, plan=plan,
            start_date=date.today() - timedelta(days=20),
            end_date=date.today() - timedelta(days=5),
        )
        # Within 14-day grace window → too soon to call
        assert _label_member(expired_member) is None

    def test_long_expired_no_renewal_returns_one(self, expired_member, plan):
        Subscription.objects.create(
            member=expired_member, plan=plan,
            start_date=date.today() - timedelta(days=90),
            end_date=date.today() - timedelta(days=30),
        )
        assert _label_member(expired_member) == 1
