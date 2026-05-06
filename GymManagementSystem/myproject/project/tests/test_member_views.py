"""Tests for member portal views (signup, login, dashboard, renew)."""
from datetime import date, timedelta

import pytest
from django.urls import reverse

from accounts.models import User
from project.models import Member, Subscription, Payment


@pytest.mark.django_db
class TestMemberSignup:
    def test_signup_get_renders(self, client, plan):
        r = client.get(reverse('member_signup'))
        assert r.status_code == 200
        assert b'Become a Member' in r.content

    def test_signup_post_creates_user_member_subscription_payment(self, client, plan):
        data = {
            'username': 'newuser', 'email': 'new@x.com', 'password': 'secret123',
            'name': 'New User', 'contact': '9990001111', 'age': '25',
            'gender': 'Male', 'plan': str(plan.id),
        }
        r = client.post(reverse('member_signup'), data)
        assert r.status_code == 302
        assert User.objects.filter(username='newuser', role='member').exists()
        member = Member.objects.get(email='new@x.com')
        assert member.user.username == 'newuser'
        assert Subscription.objects.filter(member=member).exists()
        assert Payment.objects.filter(member=member, amount=plan.amount).exists()
        assert member.expiry_date == date.today() + timedelta(days=plan.duration_days)

    def test_signup_rejects_duplicate_email(self, client, plan, member):
        data = {
            'username': 'other', 'email': member.email, 'password': 'secret123',
            'name': 'Other', 'contact': '1', 'age': '25', 'gender': 'Male', 'plan': str(plan.id),
        }
        r = client.post(reverse('member_signup'), data)
        assert r.status_code == 200
        assert b'already registered' in r.content


@pytest.mark.django_db
class TestMemberLogin:
    def test_login_with_username(self, client, member):
        r = client.post(reverse('member_login'),
                        {'username': 'member_test', 'password': 'pass1234'})
        assert r.status_code == 302
        assert r.url == reverse('member_dashboard')

    def test_login_with_email(self, client, member):
        r = client.post(reverse('member_login'),
                        {'username': 'member_test@x.com', 'password': 'pass1234'})
        assert r.status_code == 302

    def test_wrong_password_shows_credentials_error(self, client, member):
        r = client.post(reverse('member_login'),
                        {'username': 'member_test', 'password': 'WRONG'})
        assert r.status_code == 200
        assert b'incorrect' in r.content

    def test_admin_attempting_member_portal_gets_role_error(self, client, admin_user):
        r = client.post(reverse('member_login'),
                        {'username': 'admin_test', 'password': 'pass1234'})
        assert r.status_code == 200
        assert b'not a member account' in r.content

    def test_already_authed_member_redirects_to_dashboard(self, client, member, member_user):
        client.force_login(member_user)
        r = client.get(reverse('member_login'))
        assert r.status_code == 302
        assert reverse('member_dashboard') in r.url


@pytest.mark.django_db
class TestDashboard:
    def test_dashboard_requires_login(self, client):
        r = client.get(reverse('member_dashboard'))
        assert r.status_code == 302

    def test_dashboard_renders_for_member(self, client, member, member_user):
        client.force_login(member_user)
        r = client.get(reverse('member_dashboard'))
        assert r.status_code == 200
        assert member.name.encode() in r.content

    def test_check_in_creates_attendance(self, client, member, member_user):
        client.force_login(member_user)
        r = client.post(reverse('member_check_in'))
        assert r.status_code == 302
        assert member.attendance.count() == 1

    def test_check_in_blocked_for_expired_member(self, client, expired_member, member_user):
        client.force_login(member_user)
        r = client.post(reverse('member_check_in'))
        assert r.status_code == 302
        assert expired_member.attendance.count() == 0


@pytest.mark.django_db
class TestRenewal:
    def test_renew_extends_subscription(self, client, expired_member, member_user, yearly_plan):
        client.force_login(member_user)
        r = client.post(reverse('member_renew'), {'plan_id': str(yearly_plan.id)})
        assert r.status_code == 302
        expired_member.refresh_from_db()
        assert expired_member.is_active
        assert expired_member.plan == yearly_plan
        assert Subscription.objects.filter(member=expired_member).count() == 1
