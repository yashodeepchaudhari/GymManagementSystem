from datetime import timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from django.http import JsonResponse, HttpResponse
from .models import (
    Member, Plan, Subscription, Payment, Attendance,
    WorkoutPlan, DietPlan, ChatMessage, BodyAnalysis,
)
from .forms import _BootstrapMixin
from .ai_service import generate_fitness_plan, chat_reply, analyze_body_photo
from .pdf_service import render_plan_pdf, render_receipt_pdf


def _is_member(user):
    return user.is_authenticated and getattr(user, 'role', '') == User.Role.MEMBER


def _redirect_if_authenticated_member(request):
    """If a member is already logged in, send them to the dashboard.
    If a non-member is logged in (e.g. admin), log them out so they can sign in here."""
    if request.user.is_authenticated:
        if _is_member(request.user):
            return redirect('member_dashboard')
        logout(request)
    return None


# =========================
# FORMS
# =========================
class MemberSignupForm(_BootstrapMixin, forms.Form):
    username = forms.CharField(
        max_length=150,
        help_text="3-150 characters. Used to log in.",
    )
    email = forms.EmailField()
    password = forms.CharField(
        widget=forms.PasswordInput, min_length=6,
        help_text="At least 6 characters.",
    )

    name = forms.CharField(max_length=100, label="Full Name")
    contact = forms.CharField(max_length=15, label="Phone Number")
    age = forms.IntegerField(min_value=10, max_value=100)
    gender = forms.ChoiceField(choices=Member.GENDER_CHOICES)
    plan = forms.ModelChoiceField(queryset=Plan.objects.all(), empty_label="-- Choose a plan --")

    height_cm = forms.IntegerField(required=False, min_value=80, max_value=250, label="Height (cm)")
    weight_kg = forms.IntegerField(required=False, min_value=20, max_value=300, label="Weight (kg)")
    goal = forms.ChoiceField(required=False, choices=[('', '— Select —')] + Member.GOAL_CHOICES)
    experience = forms.ChoiceField(required=False, choices=[('', '— Select —')] + Member.EXPERIENCE_CHOICES)
    diet = forms.ChoiceField(required=False, choices=[('', '— Select —')] + Member.DIET_CHOICES)

    def clean_username(self):
        u = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError("That username is already taken. Try another.")
        return u

    def clean_email(self):
        e = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=e).exists() or Member.objects.filter(email__iexact=e).exists():
            raise forms.ValidationError("This email is already registered. Try logging in instead.")
        return e


class MemberProfileForm(_BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Member
        fields = ['contact', 'height_cm', 'weight_kg', 'goal', 'experience', 'diet']
        labels = {
            'contact': 'Phone Number',
            'height_cm': 'Height (cm)',
            'weight_kg': 'Weight (kg)',
        }


# =========================
# AUTH
# =========================
def member_signup(request):
    redir = _redirect_if_authenticated_member(request)
    if redir:
        return redir

    if not Plan.objects.exists():
        messages.warning(request, "No membership plans available right now. Please contact the gym.")

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
            messages.success(
                request,
                f"Welcome, {member.name}! Your {cd['plan'].name} plan is active until {member.expiry_date:%d %b %Y}."
            )
            return redirect('member_dashboard')
        else:
            messages.error(request, "Please fix the errors below and try again.")
    else:
        form = MemberSignupForm()
    return render(request, 'portal/signup.html', {'form': form})


def member_login(request):
    redir = _redirect_if_authenticated_member(request)
    if redir:
        return redir

    if request.method == 'POST':
        identifier = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''

        # Allow login by either username or email
        user = authenticate(request, username=identifier, password=password)
        if user is None and '@' in identifier:
            try:
                u = User.objects.get(email__iexact=identifier)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is None:
            messages.error(request, "Username/email or password is incorrect.")
        elif getattr(user, 'role', '') != User.Role.MEMBER:
            messages.error(
                request,
                "This account is not a member account. Use the Admin Login if you're an administrator."
            )
        else:
            login(request, user)
            member_name = getattr(getattr(user, 'member_profile', None), 'name', user.username)
            messages.success(request, f"Welcome back, {member_name}!")
            return redirect('member_dashboard')

    return render(request, 'portal/login.html')


def member_logout(request):
    if request.user.is_authenticated:
        messages.info(request, "You have been logged out.")
    logout(request)
    return redirect('member_login')


# =========================
# DASHBOARD
# =========================
@login_required(login_url='member_login')
def member_dashboard(request):
    if not _is_member(request.user):
        logout(request)
        return redirect('member_login')

    member = getattr(request.user, 'member_profile', None)
    if not member:
        messages.error(request, "No member profile linked to this account. Please contact admin.")
        logout(request)
        return redirect('member_login')

    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    workout_plan = member.workout_plans.first()
    diet_plan = member.diet_plans.first()
    context = {
        'member': member,
        'attendance_this_month': member.attendance.filter(check_in__gte=month_start).count(),
        'attendance_recent': member.attendance.all()[:10],
        'payments': member.payments.all()[:5],
        'workout_plan': workout_plan,
        'diet_plan': diet_plan,
        'workout_summary': (workout_plan.content.get('summary') if workout_plan and workout_plan.content else ''),
        'workout_first_day': (workout_plan.content.get('workout', [None])[0] if workout_plan and workout_plan.content else None),
        'diet_first_day': (diet_plan.content.get('diet', [None])[0] if diet_plan and diet_plan.content else None),
        'expiring_soon': member.is_active and member.days_remaining <= 7,
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


# =========================
# RENEWAL
# =========================
@login_required(login_url='member_login')
def member_renew(request):
    if not _is_member(request.user):
        return redirect('member_login')
    member = get_object_or_404(Member, user=request.user)
    plans = Plan.objects.all()

    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        plan = get_object_or_404(Plan, id=plan_id)
        today = timezone.now().date()
        # New cycle starts today (or after current expiry if still active)
        start = max(today, member.expiry_date or today)
        sub = Subscription.objects.create(member=member, plan=plan, start_date=start)
        Payment.objects.create(
            subscription=sub, member=member,
            amount=plan.amount, mode='cash', status='paid',
        )
        member.plan = plan
        member.expiry_date = sub.end_date
        member.amount = int(plan.amount)
        member.save()
        messages.success(
            request,
            f"Renewed! New expiry: {member.expiry_date:%d %b %Y}."
        )
        return redirect('member_dashboard')

    return render(request, 'portal/renew.html', {'member': member, 'plans': plans})


# =========================
# AI
# =========================
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
            content={
                "workout": parsed.get('workout', []),
                "summary": parsed.get('summary', ''),
                "tips": parsed.get('tips', []),
            },
            raw_text=raw,
        )
        DietPlan.objects.create(
            member=member,
            goal=member.goal,
            diet_type=member.diet or 'mixed',
            content={"diet": parsed.get('diet', [])},
            raw_text=raw,
        )
        messages.success(request, "AI plan generated! Scroll down to see it.")
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
def member_qr(request):
    """Render the member's unique QR PNG for gym entry."""
    if not _is_member(request.user):
        return redirect('member_login')
    member = get_object_or_404(Member, user=request.user)

    import qrcode
    from io import BytesIO
    payload = f"GYMPRO:MEMBER:{member.id}"
    img = qrcode.make(payload, box_size=10, border=2)
    buf = BytesIO()
    img.save(buf, format='PNG')
    return HttpResponse(buf.getvalue(), content_type='image/png')


@login_required(login_url='member_login')
def body_analysis(request):
    if not _is_member(request.user):
        return redirect('member_login')
    member = get_object_or_404(Member, user=request.user)

    if request.method == 'POST':
        photo = request.FILES.get('photo')
        weight = request.POST.get('weight_kg') or None
        if not photo:
            messages.error(request, "Please choose a photo first.")
            return redirect('body_analysis')
        if photo.size > 5 * 1024 * 1024:
            messages.error(request, "Image too large (>5 MB). Try a smaller file.")
            return redirect('body_analysis')

        photo.seek(0)
        image_bytes = photo.read()
        photo.seek(0)
        mime = photo.content_type or 'image/jpeg'

        try:
            text = analyze_body_photo(member, image_bytes, mime_type=mime)
        except Exception as e:
            messages.error(request, f"Analysis failed: {e}")
            return redirect('body_analysis')

        ba = BodyAnalysis.objects.create(
            member=member, photo=photo, analysis=text,
            weight_kg=int(weight) if weight else None,
        )
        messages.success(request, "Body analysis ready.")
        return redirect('body_analysis')

    history = member.body_analyses.all()[:10]
    return render(request, 'portal/body_analysis.html', {
        'member': member,
        'history': history,
    })


@login_required(login_url='member_login')
def download_plan_pdf(request):
    if not _is_member(request.user):
        return redirect('member_login')
    member = get_object_or_404(Member, user=request.user)
    workout = member.workout_plans.first()
    diet = member.diet_plans.first()
    if not workout:
        messages.error(request, "Generate an AI plan first before downloading.")
        return redirect('ai_generate_plan')
    pdf = render_plan_pdf(member, workout, diet)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="GymPro_Plan_{member.name.replace(" ", "_")}.pdf"'
    return response


@login_required(login_url='member_login')
def download_receipt_pdf(request, payment_id):
    if not _is_member(request.user):
        return redirect('member_login')
    member = get_object_or_404(Member, user=request.user)
    payment = get_object_or_404(Payment, id=payment_id, member=member)
    pdf = render_receipt_pdf(payment)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{payment.id}.pdf"'
    return response


@login_required(login_url='member_login')
@require_POST
def chat_send(request):
    """JSON endpoint: takes a user message, returns assistant reply."""
    if not _is_member(request.user):
        return JsonResponse({'error': 'unauthorized'}, status=401)
    member = get_object_or_404(Member, user=request.user)

    user_message = (request.POST.get('message') or '').strip()
    if not user_message:
        return JsonResponse({'error': 'empty message'}, status=400)
    if len(user_message) > 1000:
        return JsonResponse({'error': 'message too long'}, status=400)

    # Pass last 10 messages as context (5 exchanges)
    recent = list(member.chat_messages.order_by('-created_at')[:10])
    recent.reverse()
    history = [{'role': m.role, 'content': m.content} for m in recent]

    ChatMessage.objects.create(member=member, role='user', content=user_message)
    reply = chat_reply(member, user_message, history)
    ChatMessage.objects.create(member=member, role='assistant', content=reply)

    return JsonResponse({'reply': reply})


@login_required(login_url='member_login')
def chat_history(request):
    """JSON endpoint: returns last 20 messages."""
    if not _is_member(request.user):
        return JsonResponse({'error': 'unauthorized'}, status=401)
    member = get_object_or_404(Member, user=request.user)
    msgs = list(member.chat_messages.order_by('-created_at')[:20])
    msgs.reverse()
    return JsonResponse({
        'messages': [{'role': m.role, 'content': m.content,
                      'time': m.created_at.strftime('%H:%M')} for m in msgs]
    })


@login_required(login_url='member_login')
@require_POST
def member_check_in(request):
    if not _is_member(request.user):
        return redirect('member_login')
    member = get_object_or_404(Member, user=request.user)
    if not member.is_active:
        messages.error(request, "Your membership has expired. Please renew before checking in.")
        return redirect('member_renew')

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if member.attendance.filter(check_in__gte=today_start).exists():
        messages.info(request, "You've already checked in today.")
    else:
        Attendance.objects.create(member=member)
        messages.success(request, "Checked in. Have a great workout! 💪")
    return redirect('member_dashboard')
