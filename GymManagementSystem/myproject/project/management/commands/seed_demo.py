"""
Seeds realistic demo data so the churn model has signal:
- Plans (monthly, quarterly, yearly)
- 60 members across 4-month timeframe
- Each member's attendance + payments simulated based on a hidden "engagement"
  factor; engaged members renew, disengaged ones churn.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from project.models import Plan, Member, Subscription, Payment, Attendance


FIRST_NAMES = ['Aarav', 'Vivaan', 'Aditya', 'Diya', 'Saanvi', 'Ishaan', 'Anaya', 'Reyansh',
               'Myra', 'Ayaan', 'Riya', 'Arjun', 'Kavya', 'Krish', 'Aanya', 'Vihaan',
               'Pari', 'Atharv', 'Rudra', 'Sara']
LAST_NAMES = ['Sharma', 'Patel', 'Kumar', 'Singh', 'Reddy', 'Gupta', 'Iyer', 'Joshi',
              'Nair', 'Mehta']


class Command(BaseCommand):
    help = "Seed demo plans, members, attendance, and payments for ML training."

    def add_arguments(self, parser):
        parser.add_argument('--members', type=int, default=60)
        parser.add_argument('--clear', action='store_true', help='Wipe existing demo data first')

    def handle(self, *args, **opts):
        random.seed(42)

        if opts['clear']:
            self.stdout.write("Clearing existing members + subs + payments + attendance...")
            Attendance.objects.all().delete()
            Payment.objects.all().delete()
            Subscription.objects.all().delete()
            Member.objects.all().delete()

        # Plans
        plans_data = [
            ('Monthly Basic', 1500, 'Monthly Plans', 30),
            ('Quarterly', 4000, 'Monthly Plans', 90),
            ('Yearly Pro', 12000, 'Yearly Plans', 365),
        ]
        plans = []
        for name, amt, dur, days in plans_data:
            p, _ = Plan.objects.update_or_create(
                name=name,
                defaults={'amount': Decimal(amt), 'duration': dur, 'duration_days': days},
            )
            plans.append(p)

        n = opts['members']
        today = timezone.now().date()
        created = 0

        for i in range(n):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            name = f"{first} {last}"
            email = f"{first.lower()}.{last.lower()}{i}@demo.local"
            if Member.objects.filter(email=email).exists():
                continue

            plan = random.choice(plans)
            # Hidden engagement score 0..1 — drives attendance + renewal probability
            engagement = random.random()
            # Most members joined 30-180 days ago
            days_ago_join = random.randint(30, 180)
            join_date = today - timedelta(days=days_ago_join)

            m = Member.objects.create(
                name=name,
                contact=f"9{random.randint(100000000, 999999999)}",
                email=email,
                age=random.randint(18, 55),
                gender=random.choice(['Male', 'Female']),
                plan=plan,
                join_date=join_date,
                amount=int(plan.amount),
                height_cm=random.randint(150, 190),
                weight_kg=random.randint(50, 100),
                goal=random.choice(['lose', 'gain', 'maintain']),
                experience=random.choice(['beginner', 'intermediate', 'advanced']),
                diet=random.choice(['veg', 'nonveg', 'vegan']),
            )
            # First subscription
            sub_start = join_date
            sub_end = sub_start + timedelta(days=plan.duration_days)
            sub = Subscription.objects.create(
                member=m, plan=plan, start_date=sub_start, end_date=sub_end,
                is_active=(sub_end >= today),
            )
            Payment.objects.create(
                subscription=sub, member=m, amount=plan.amount,
                mode=random.choice(['cash', 'upi', 'card']), status='paid',
                paid_at=timezone.now() - timedelta(days=days_ago_join),
            )

            # Attendance — high engagement => many visits
            cycle_days = min(plan.duration_days, days_ago_join)
            visit_freq_per_week = engagement * 5  # 0..5 visits/week
            n_visits = int((cycle_days / 7) * visit_freq_per_week)
            for _ in range(n_visits):
                offset = random.randint(0, cycle_days)
                Attendance.objects.create(
                    member=m,
                    check_in=timezone.now() - timedelta(days=offset, hours=random.randint(6, 21)),
                )

            # Renewal: high engagement renews; low engagement churns
            if sub_end < today:
                if engagement > 0.45:
                    # Renewed shortly after expiry
                    renew_delay = random.randint(0, 7)
                    new_start = sub_end + timedelta(days=renew_delay)
                    if new_start <= today:
                        new_end = new_start + timedelta(days=plan.duration_days)
                        new_sub = Subscription.objects.create(
                            member=m, plan=plan,
                            start_date=new_start, end_date=new_end,
                            is_active=(new_end >= today),
                        )
                        Payment.objects.create(
                            subscription=new_sub, member=m, amount=plan.amount,
                            mode=random.choice(['cash', 'upi', 'card']), status='paid',
                            paid_at=timezone.now() - timedelta(days=(today - new_start).days),
                        )
                        # Update member expiry
                        m.expiry_date = new_end
                        m.save()
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} members across {len(plans)} plans."))
