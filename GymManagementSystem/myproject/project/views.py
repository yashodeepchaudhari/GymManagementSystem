import csv
from datetime import timedelta

from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import TeamMember, Enquiry, Plan, Equipment, Member, Image, Payment
from .forms import (
    ContactFormModelForm, EnquiryForm, PlanForm,
    EquipmentForm, MemberForm, ImageForm,
)


# =========================
# PUBLIC PAGES
# =========================
def home(request):
    services = [
        {'count': 1, 'title': 'Personal Training', 'icon': 'bi-activity', 'description': 'Work one-on-one with our expert trainers...'},
        {'count': 2, 'title': 'Group Classes', 'icon': 'bi-person-lines-fill', 'description': 'Join our group fitness classes...'},
        {'count': 3, 'title': 'Yoga', 'icon': 'bi-yoga', 'description': 'Enhance your flexibility and mental well-being with yoga classes...'},
        {'count': 4, 'title': 'Cardio Training', 'icon': 'bi-heart', 'description': 'Boost your stamina with cardio-based exercises...'},
        {'count': 5, 'title': 'Nutrition Counseling', 'icon': 'bi-apple', 'description': 'Get personalized nutrition plans from our expert dieticians...'},
        {'count': 6, 'title': 'Massage Therapy', 'icon': 'bi-hand-thumbs-up', 'description': 'Relax and recover with professional massage therapy...'},
    ]

    team_members = TeamMember.objects.all()

    if request.method == 'POST':
        form = ContactFormModelForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thanks! We will get back to you soon.")
            return redirect('home')
    else:
        form = ContactFormModelForm()

    return render(request, 'index.html', {
        'services': services,
        'team_members': team_members,
        'form': form,
    })


def home_gallery(request):
    images = Image.objects.all()
    return render(request, "home_gallery.html", {"img": images})


def test(request):
    return render(request, "test.html")


# =========================
# AUTH
# =========================
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('admin_dashboard')
        messages.error(request, "Invalid credentials or insufficient permissions.")
    return render(request, "admin_login.html")


def admin_logout(request):
    logout(request)
    return redirect("admin_login")


# =========================
# ADMIN PANEL
# =========================
@login_required(login_url="admin_login")
def admin_dashboard(request):
    from .ml_service import predict_at_risk_members, MODEL_PATH, forecast_signups
    raw_at_risk = predict_at_risk_members(top_n=10) if MODEL_PATH.exists() else []
    at_risk = [(m, prob, int(prob * 100)) for m, prob in raw_at_risk]

    fc = forecast_signups(months_ahead=3)
    forecast_labels = [r['month'] for r in fc['history']] + [r['month'] for r in fc['forecast']]
    forecast_history = [r['count'] for r in fc['history']] + [None] * len(fc['forecast'])
    forecast_predicted = [None] * len(fc['history']) + [r['count'] for r in fc['forecast']]
    # Make the boundary connect: repeat last history value at first forecast slot
    if fc['history'] and fc['forecast']:
        idx = len(fc['history']) - 1
        forecast_predicted[idx] = fc['history'][-1]['count']

    # Last 6 months revenue for Chart.js
    today = timezone.now().date()
    six_months_ago = (today.replace(day=1) - timedelta(days=31 * 5)).replace(day=1)
    revenue = (
        Payment.objects.filter(status='paid', paid_at__date__gte=six_months_ago)
        .annotate(month=TruncMonth('paid_at'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    chart_labels = [r['month'].strftime('%b %Y') for r in revenue]
    chart_data = [float(r['total']) for r in revenue]

    active_members = sum(1 for m in Member.objects.all() if m.is_active)

    context = {
        'member_count': Member.objects.count(),
        'active_member_count': active_members,
        'enquiry_count': Enquiry.objects.count(),
        'plan_count': Plan.objects.count(),
        'equipment_count': Equipment.objects.count(),
        'at_risk': at_risk,
        'model_trained': MODEL_PATH.exists(),
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'total_revenue': sum(chart_data),
        'forecast_labels': forecast_labels,
        'forecast_history': forecast_history,
        'forecast_predicted': forecast_predicted,
    }
    return render(request, "admin_panel/admin_dashboard.html", context)


@login_required(login_url="admin_login")
def qr_scanner(request):
    """Render the staff QR scanner page (uses webcam + jsQR)."""
    return render(request, "admin_panel/qr_scanner.html")


@login_required(login_url="admin_login")
@require_POST
def qr_check_in(request):
    """JSON: receives a scanned QR payload, records attendance for that member."""
    from django.http import JsonResponse
    payload = (request.POST.get('payload') or '').strip()
    prefix = "GYMPRO:MEMBER:"
    if not payload.startswith(prefix):
        return JsonResponse({'ok': False, 'error': 'Invalid QR'}, status=400)
    try:
        member_id = int(payload[len(prefix):])
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Invalid QR'}, status=400)

    from .models import Member, Attendance
    try:
        member = Member.objects.select_related('plan').get(id=member_id)
    except Member.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Member not found'}, status=404)

    if not member.is_active:
        return JsonResponse({
            'ok': False, 'error': 'Membership expired',
            'member': {'name': member.name, 'expiry': str(member.expiry_date)},
        }, status=403)

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if member.attendance.filter(check_in__gte=today_start).exists():
        return JsonResponse({
            'ok': True, 'duplicate': True,
            'member': {'name': member.name, 'plan': member.plan.name, 'days_left': member.days_remaining},
        })
    Attendance.objects.create(member=member)
    return JsonResponse({
        'ok': True,
        'member': {'name': member.name, 'plan': member.plan.name, 'days_left': member.days_remaining},
    })


@login_required(login_url="admin_login")
def export_members_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="members.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Name', 'Email', 'Contact', 'Age', 'Gender', 'Plan',
        'Join Date', 'Expiry Date', 'Active', 'Days Remaining',
        'Height (cm)', 'Weight (kg)', 'BMI', 'Goal',
    ])
    for m in Member.objects.select_related('plan').order_by('name'):
        writer.writerow([
            m.name, m.email, m.contact, m.age, m.gender,
            m.plan.name if m.plan_id else '',
            m.join_date, m.expiry_date,
            'Yes' if m.is_active else 'No', m.days_remaining,
            m.height_cm or '', m.weight_kg or '', m.bmi or '', m.get_goal_display() or '',
        ])
    return response


@login_required(login_url="admin_login")
def admin_about(request):
    return render(request, "admin_panel/admin_about.html")


@login_required(login_url="admin_login")
def admin_contact(request):
    return render(request, "admin_panel/admin_contact.html")


# =========================
# ENQUIRY CRUD
# =========================
@login_required(login_url="admin_login")
def add_enquiry(request):
    form = EnquiryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Enquiry added.")
        return redirect('view_enquiry')
    return render(request, 'admin_panel/add_enquiry.html', {'form': form})


@login_required(login_url="admin_login")
def view_enquiry(request):
    enquiries = Enquiry.objects.all().order_by('-created_at')
    return render(request, 'admin_panel/view_enquiry.html', {'enquiries': enquiries})


@login_required(login_url="admin_login")
@require_POST
def delete_enquiry(request, enquiry_id):
    enquiry = get_object_or_404(Enquiry, id=enquiry_id)
    enquiry.delete()
    messages.success(request, "Enquiry deleted.")
    return redirect('view_enquiry')


# =========================
# PLAN CRUD
# =========================
@login_required(login_url="admin_login")
def add_plan(request):
    form = PlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Plan added.")
        return redirect('view_plan')
    return render(request, 'admin_panel/add_plan.html', {'form': form})


@login_required(login_url="admin_login")
def view_plan(request):
    plans = Plan.objects.all()
    return render(request, 'admin_panel/view_plan.html', {'plans': plans})


@login_required(login_url="admin_login")
@require_POST
def delete_plan(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    plan.delete()
    messages.success(request, "Plan deleted.")
    return redirect('view_plan')


# =========================
# EQUIPMENT CRUD
# =========================
@login_required(login_url="admin_login")
def add_equipment(request):
    form = EquipmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Equipment added.")
        return redirect('view_equipment')
    return render(request, 'admin_panel/add_equipment.html', {'form': form})


@login_required(login_url="admin_login")
def view_equipment(request):
    equipment_list = Equipment.objects.all()
    return render(request, 'admin_panel/view_equipment.html', {'equipment_list': equipment_list})


@login_required(login_url="admin_login")
@require_POST
def delete_equipment(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id)
    equipment.delete()
    messages.success(request, "Equipment deleted.")
    return redirect('view_equipment')


# =========================
# MEMBER CRUD
# =========================
@login_required(login_url="admin_login")
def add_member(request):
    form = MemberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Member added.")
        return redirect('view_member')
    return render(request, 'admin_panel/add_member.html', {'form': form})


@login_required(login_url="admin_login")
def view_member(request):
    q = request.GET.get('q', '').strip()
    qs = Member.objects.select_related('plan').all()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(contact__icontains=q))
    page_obj = Paginator(qs.order_by('-id'), 10).get_page(request.GET.get('page'))
    return render(request, 'admin_panel/view_member.html', {
        'members': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
    })


@login_required(login_url="admin_login")
def edit_member(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    form = MemberForm(request.POST or None, instance=member)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Member updated.")
        return redirect('view_member')
    return render(request, 'admin_panel/add_member.html', {'form': form, 'editing': True})


@login_required(login_url="admin_login")
@require_POST
def delete_member(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    member.delete()
    messages.success(request, "Member deleted.")
    return redirect('view_member')


# =========================
# GALLERY
# =========================
@login_required(login_url="admin_login")
def gallery(request):
    if request.method == "POST":
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("gallery")
    else:
        form = ImageForm()

    images = Image.objects.all()
    return render(request, "admin_panel/gallery.html", {"form": form, "img": images})
