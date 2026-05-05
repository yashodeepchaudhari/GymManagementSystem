from datetime import timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from .models import Member, Plan, Subscription, Payment, Attendance, WorkoutPlan, DietPlan
from .forms import _BootstrapMixin
from .ai_service import generate_fitness_plan


def _is_member(user):
    return user.is_authenticated and getattr(user, 'role', '') == User.Role.MEMBER


# =========================
# FORMS
# =========================
class MemberSignupForm(_BootstrapMixin, forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)

    name = forms.CharField(max_length=100)
    contact = forms.CharField(max_length=15)
    age = forms.IntegerField(min_value=10, max_value=100)
    gender = forms.ChoiceField(choices=Member.GENDER_CHOICES)
    plan = forms.ModelChoiceField(queryset=Plan.objects.all(), empty_label="Choose a plan")

    height_cm = forms.IntegerField(required=False, min_value=80, max_value=250)
    weight_kg = forms.IntegerField(required=False, min_value=20, max_value=300)
    goal = forms.ChoiceField(required=False, choices=[('', '—')] + Member.GOAL_CHOICES)
    experience = forms.ChoiceField(required=False, choices=[('', '—')] + Member.EXPERIENCE_CHOICES)
    diet = forms.ChoiceField(required=False, choices=[('', '—')] + Member.DIET_CHOICES)

    def clean_username(self):
        u = self.cleaned_data['username']
        if User.objects.filter(username=u).exists():
            raise forms.ValidationError("Username already taken.")
        return u

    def clean_email(self):
        e = self.cleaned_data['email']
        if User.objects.filter(email=e).exists() or Member.objects.filter(email=e).exists():
            raise forms.ValidationError("Email already in use.")
        return e


class MemberProfileForm(_BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Member
        fields = ['contact', 'height_cm', 'weight_kg', 'goal', 'experience', 'diet']


# =========================
# AUTH
# =========================
def member_signup(request):
    if request.method == 'POST':
        form = MemberSignupForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = User.objects.create_user(
                username=cd['username'],
                email=cd['email'],
                password=cd['password'],
                role=User.Role.MEMBER,
                phone=cd['contact'],
            )
            today = timezone.now().date()
            member = Member.objects.create(
                user=user,
                name=cd['name'],
                contact=cd['contact'],
                email=cd['email'],
                age=cd['age'],
                gender=cd['gender'],
                plan=cd['plan'],
                join_date=today,
                amount=int(cd['plan'].amount),
                height_cm=cd.get('height_cm'),
                weight_kg=cd.get('weight_kg'),
                goal=cd.get('goal') or '',
                experience=cd.get('experience') or '',
                diet=cd.get('diet') or '',
            )
            sub = Subscription.objects.create(member=member, plan=cd['plan'], start_date=today)
            Payment.objects.create(
                subscription=sub, member=member,
                amount=cd['plan'].amount, mode='cash', status='paid',
            )
            login(request, user)
            messages.success(request, "Welcome! Your membership is active.")
            return redirect('member_dashboard')
    else:
        form = MemberSignupForm()
    return render(request, 'portal/signup.html', {'form': form})


def member_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and getattr(user, 'role', '') == User.Role.MEMBER:
            login(request, user)
            return redirect('member_dashboard')
        messages.error(request, "Invalid credentials.")
    return render(request, 'portal/login.html')


def member_logout(request):
    logout(request)
    return redirect('member_login')


# =========================
# DASHBOARD
# =========================
@login_required(login_url='member_login')
def member_dashboard(request):
    if not _is_member(request.user):
        return redirect('member_login')

    member = getattr(request.user, 'member_profile', None)
    if not member:
        messages.error(request, "No member profile linked to this account. Contact admin.")
        return redirect('member_login')

    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    context = {
        'member': member,
        'attendance_this_month': member.attendance.filter(check_in__gte=month_start).count(),
        'attendance_recent': member.attendance.all()[:10],
        'payments': member.payments.all()[:5],
        'workout_plan': member.workout_plans.first(),
        'diet_plan': member.diet_plans.first(),
    }
    return render(request, 'portal/dashboard.html', context)


@login_required(login_url='member_login')
def member_profile(request):
    if not _is_member(request.user):
        return redirect('member_login')
    member = get_object_or_404(Member, user=request.user)
    if request.method == 'POST':
        form = MemberProfileForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('member_dashboard')
    else:
        form = MemberProfileForm(instance=member)
    return render(request, 'portal/profile.html', {'form': form, 'member': member})


@login_required(login_url='member_login')
def ai_generate_plan(request):
    if not _is_member(request.user):
        return redirect('member_login')
    member = get_object_or_404(Member, user=request.user)

    if request.method == 'POST':
        if not (member.height_cm and member.weight_kg and member.goal):
            messages.error(request, "Please fill height, weight, and goal in your profile first.")
            return redirect('member_profile')

        try:
            parsed, raw = generate_fitness_plan(member)
        except Exception as e:
            messages.error(request, f"AI generation failed: {e}")
            return redirect('member_dashboard')

        WorkoutPlan.objects.create(
            member=member,
            goal=member.goal,
            content={"workout": parsed.get('workout', []), "summary": parsed.get('summary', ''), "tips": parsed.get('tips', [])},
            raw_text=raw,
        )
        DietPlan.objects.create(
            member=member,
            goal=member.goal,
            diet_type=member.diet or 'mixed',
            content={"diet": parsed.get('diet', [])},
            raw_text=raw,
        )
        messages.success(request, "AI plan generated!")
        return redirect('ai_view_plan')

    return render(request, 'portal/ai_generate.html', {'member': member})


@login_required(login_url='member_login')
def ai_view_plan(request):
    if not _is_member(request.user):
        return redirect('member_login')
    member = get_object_or_404(Member, user=request.user)
    workout = member.workout_plans.first()
    diet = member.diet_plans.first()
    return render(request, 'portal/ai_view.html', {
        'member': member,
        'workout': workout,
        'diet': diet,
    })


@login_required(login_url='member_login')
@require_POST
def member_check_in(request):
    if not _is_member(request.user):
        return redirect('member_login')
    member = get_object_or_404(Member, user=request.user)
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if member.attendance.filter(check_in__gte=today_start).exists():
        messages.info(request, "Already checked in today.")
    else:
        Attendance.objects.create(member=member)
        messages.success(request, "Checked in. Have a great workout!")
    return redirect('member_dashboard')
