from rest_framework import serializers
from accounts.models import User
from project.models import (
    Plan, Member, Subscription, Payment, Attendance,
    Enquiry, Equipment, WorkoutPlan, DietPlan,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'phone')
        read_only_fields = ('id', 'role')


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = '__all__'


class MemberSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    bmi = serializers.FloatField(read_only=True)

    class Meta:
        model = Member
        fields = (
            'id', 'name', 'contact', 'email', 'age', 'gender',
            'plan', 'plan_name', 'join_date', 'expiry_date', 'amount',
            'height_cm', 'weight_kg', 'goal', 'experience', 'diet',
            'is_active', 'days_remaining', 'bmi',
        )
        read_only_fields = ('expiry_date',)


class SubscriptionSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)

    class Meta:
        model = Subscription
        fields = ('id', 'member', 'member_name', 'plan', 'plan_name',
                  'start_date', 'end_date', 'is_active', 'created_at')
        read_only_fields = ('end_date', 'created_at')


class PaymentSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)

    class Meta:
        model = Payment
        fields = ('id', 'subscription', 'member', 'member_name',
                  'amount', 'mode', 'status', 'reference', 'paid_at')


class AttendanceSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)

    class Meta:
        model = Attendance
        fields = ('id', 'member', 'member_name', 'check_in', 'check_out')


class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = '__all__'


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = '__all__'


class WorkoutPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutPlan
        fields = ('id', 'member', 'goal', 'content', 'created_at')


class DietPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietPlan
        fields = ('id', 'member', 'goal', 'diet_type', 'content', 'created_at')
