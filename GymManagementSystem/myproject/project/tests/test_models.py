"""Model behavior tests."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from project.models import Plan, Member, Subscription, Payment, Attendance


@pytest.mark.django_db
class TestMemberModel:
    def test_expiry_auto_computed_from_plan_duration(self, plan, member_user):
        today = date.today()
        m = Member.objects.create(
            user=member_user,
            name='X', contact='1', email='x@x.com', age=20,
            gender='Male', plan=plan, join_date=today, amount=1500,
        )
        assert m.expiry_date == today + timedelta(days=plan.duration_days)

    def test_explicit_expiry_not_overwritten(self, plan, member_user):
        custom = date.today() + timedelta(days=99)
        m = Member.objects.create(
            user=member_user, name='X', contact='1', email='x@x.com',
            age=20, gender='Male', plan=plan, amount=1500,
            join_date=date.today(), expiry_date=custom,
        )
        assert m.expiry_date == custom

    def test_is_active_true_when_future_expiry(self, member):
        assert member.is_active is True

    def test_is_active_false_when_past_expiry(self, expired_member):
        assert expired_member.is_active is False

    def test_days_remaining_clamps_at_zero(self, expired_member):
        assert expired_member.days_remaining == 0

    def test_bmi_computed(self, member):
        # 72kg / 1.75m^2 = 23.5
        assert member.bmi == pytest.approx(23.5, abs=0.1)

    def test_bmi_none_when_missing_height_or_weight(self, plan, member_user):
        m = Member.objects.create(
            user=member_user, name='X', contact='1', email='x@x.com',
            age=20, gender='Male', plan=plan, amount=1500, join_date=date.today(),
        )
        assert m.bmi is None


@pytest.mark.django_db
class TestSubscriptionModel:
    def test_end_date_auto_computed(self, plan, member):
        sub = Subscription.objects.create(member=member, plan=plan)
        assert sub.end_date == sub.start_date + timedelta(days=plan.duration_days)


@pytest.mark.django_db
class TestPlanModel:
    def test_str(self, plan):
        assert plan.name in str(plan)
        assert plan.duration in str(plan)
