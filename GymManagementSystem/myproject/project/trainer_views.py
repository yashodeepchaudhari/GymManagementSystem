"""Trainer-side views (login, dashboard, member detail, edit notes)."""
from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_POST

from accounts.models import User
from .forms import _BootstrapMixin
from .models import Member, MemberTrainer, Trainer


def _is_trainer(user):
    return user.is_authenticated and getattr(user, 'role', '') == User.Role.TRAINER


def _redirect_if_authed_trainer(request):
    if request.user.is_authenticated:
        if _is_trainer(request.user):
            return redirect('trainer_dashboard')
        logout(request)
    return None


def trainer_login(request):
    redir = _redirect_if_authed_trainer(request)
    if redir:
        return redir

    if request.method == 'POST':
        identifier = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        user = authenticate(request, username=identifier, password=password)
        if user is None and '@' in identifier:
            try:
                u = User.objects.get(email__iexact=identifier)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is None:
            messages.error(request, "Username/email or password is incorrect.")
        elif getattr(user, 'role', '') != User.Role.TRAINER:
            messages.error(request, "This account is not a trainer account.")
        else:
            login(request, user)
            messages.success(request, f"Welcome, {user.username}!")
            return redirect('trainer_dashboard')

    return render(request, 'trainer/login.html')


def trainer_logout(request):
    logout(request)
    return redirect('trainer_login')


@login_required(login_url='trainer_login')
def trainer_dashboard(request):
    if not _is_trainer(request.user):
        logout(request)
        return redirect('trainer_login')

    trainer = getattr(request.user, 'trainer_profile', None)
    if not trainer:
        messages.error(request, "No trainer profile linked. Contact admin.")
        logout(request)
        return redirect('trainer_login')

    assignments = trainer.members.select_related('member', 'member__plan').all()
    return render(request, 'trainer/dashboard.html', {
        'trainer': trainer,
        'assignments': assignments,
    })


@login_required(login_url='trainer_login')
def trainer_member_detail(request, member_id):
    if not _is_trainer(request.user):
        return redirect('trainer_login')
    trainer = get_object_or_404(Trainer, user=request.user)
    assignment = get_object_or_404(MemberTrainer, member_id=member_id, trainer=trainer)
    member = assignment.member

    workout = member.workout_plans.first()
    diet = member.diet_plans.first()
    return render(request, 'trainer/member_detail.html', {
        'trainer': trainer,
        'assignment': assignment,
        'member': member,
        'workout': workout,
        'diet': diet,
    })


@login_required(login_url='trainer_login')
@require_POST
def trainer_save_notes(request, member_id):
    if not _is_trainer(request.user):
        return redirect('trainer_login')
    trainer = get_object_or_404(Trainer, user=request.user)
    assignment = get_object_or_404(MemberTrainer, member_id=member_id, trainer=trainer)
    assignment.notes = request.POST.get('notes', '')
    assignment.save()
    messages.success(request, "Notes saved.")
    return redirect('trainer_member_detail', member_id=member_id)
