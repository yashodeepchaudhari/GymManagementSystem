from django.contrib import admin
from .models import (
    TeamMember, Contact, Enquiry, Plan, Equipment, Member, Image,
    Subscription, Payment, Attendance, WorkoutPlan, DietPlan, ChatMessage,
    BodyAnalysis, Trainer, MemberTrainer,
)


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'position')
    search_fields = ('name', 'position')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at')
    search_fields = ('name', 'email', 'subject')
    list_filter = ('created_at',)


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'contact', 'age', 'gender', 'created_at')
    search_fields = ('name', 'email', 'contact')
    list_filter = ('gender', 'created_at')


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'duration', 'duration_days')
    list_filter = ('duration',)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'unit', 'date')
    search_fields = ('name',)
    list_filter = ('date',)


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'plan', 'join_date', 'expiry_date', 'is_active')
    search_fields = ('name', 'email', 'contact')
    list_filter = ('plan', 'gender', 'goal')

    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('member', 'plan', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'plan')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('member', 'amount', 'mode', 'status', 'paid_at')
    list_filter = ('status', 'mode', 'paid_at')
    search_fields = ('member__name', 'reference')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('member', 'check_in', 'check_out')
    list_filter = ('check_in',)
    search_fields = ('member__name',)


@admin.register(WorkoutPlan)
class WorkoutPlanAdmin(admin.ModelAdmin):
    list_display = ('member', 'goal', 'created_at')
    list_filter = ('goal', 'created_at')


@admin.register(DietPlan)
class DietPlanAdmin(admin.ModelAdmin):
    list_display = ('member', 'goal', 'diet_type', 'created_at')
    list_filter = ('goal', 'diet_type', 'created_at')


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialty', 'user')
    list_filter = ('specialty',)
    search_fields = ('name', 'user__username')


@admin.register(MemberTrainer)
class MemberTrainerAdmin(admin.ModelAdmin):
    list_display = ('member', 'trainer', 'updated_at')
    search_fields = ('member__name', 'trainer__name')
    autocomplete_fields = ('member', 'trainer')


@admin.register(BodyAnalysis)
class BodyAnalysisAdmin(admin.ModelAdmin):
    list_display = ('member', 'weight_kg', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('member__name',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('member', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('member__name', 'content')


admin.site.register(Image)
