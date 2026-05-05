"""Shared fixtures for project tests."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from accounts.models import User
from project.models import Plan, Member, Subscription, Payment


@pytest.fixture
def plan(db):
    return Plan.objects.create(
        name='Test Monthly', amount=Decimal('1500.00'),
        duration='Monthly Plans', duration_days=30,
    )


@pytest.fixture
def yearly_plan(db):
    return Plan.objects.create(
        name='Test Yearly', amount=Decimal('12000.00'),
        duration='Yearly Plans', duration_days=365,
    )


@pytest.fixture
def admin_user(db):
    u = User.objects.create_user(
        username='admin_test', email='admin_test@x.com',
        password='pass1234', role='admin',
    )
    u.is_staff = True
    u.is_superuser = True
    u.save()
    return u


@pytest.fixture
def member_user(db):
    return User.objects.create_user(
        username='member_test', email='member_test@x.com',
        password='pass1234', role='member',
    )


@pytest.fixture
def member(db, plan, member_user):
    today = date.today()
    m = Member.objects.create(
        user=member_user,
        name='Test Member', contact='9999999999', email='member_test@x.com',
        age=28, gender='Male', plan=plan,
        join_date=today, amount=int(plan.amount),
        height_cm=175, weight_kg=72,
        goal='gain', experience='intermediate', diet='nonveg',
    )
    return m


@pytest.fixture
def expired_member(db, plan, member_user):
    today = date.today()
    m = Member.objects.create(
        user=member_user,
        name='Expired Member', contact='8888888888', email='member_test@x.com',
        age=28, gender='Male', plan=plan,
        join_date=today - timedelta(days=60),
        expiry_date=today - timedelta(days=30),
        amount=int(plan.amount),
    )
    return m
