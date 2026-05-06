from rest_framework import viewsets, permissions, decorators, response, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from accounts.models import User
from project.models import (
    Plan, Member, Subscription, Payment, Attendance,
    Enquiry, Equipment, WorkoutPlan, DietPlan,
)
from .serializers import (
    UserSerializer, PlanSerializer, MemberSerializer, SubscriptionSerializer,
    PaymentSerializer, AttendanceSerializer, EnquirySerializer,
    EquipmentSerializer, WorkoutPlanSerializer, DietPlanSerializer,
)


class IsAdminOrReadOnlyMember(permissions.BasePermission):
    """Admins/staff can do anything; members can only read their own data."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if request.method in permissions.SAFE_METHODS:
            owner = getattr(obj, 'member', None) or obj
            return getattr(owner, 'user_id', None) == request.user.id
        return False


@decorators.api_view(['GET'])
@decorators.permission_classes([IsAuthenticated])
def me(request):
    """Returns the authenticated user's own profile + linked Member if any."""
    data = UserSerializer(request.user).data
    member = Member.objects.filter(user=request.user).first()
    if member:
        data['member'] = MemberSerializer(member).data
    return response.Response(data)


class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer

    def get_permissions(self):
        # All authenticated users can list/read; only staff can write
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAdminUser()]


class MemberViewSet(viewsets.ModelViewSet):
    serializer_class = MemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Member.objects.select_related('plan').all()
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Subscription.objects.select_related('member', 'plan').all()
        if self.request.user.is_staff:
            return qs
        return qs.filter(member__user=self.request.user)


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Payment.objects.select_related('member').all()
        if self.request.user.is_staff:
            return qs
        return qs.filter(member__user=self.request.user)


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Attendance.objects.select_related('member').all()
        if self.request.user.is_staff:
            return qs
        return qs.filter(member__user=self.request.user)


class EnquiryViewSet(viewsets.ModelViewSet):
    queryset = Enquiry.objects.all()
    serializer_class = EnquirySerializer
    # Public can create an enquiry (lead-capture); admins can read/delete
    def get_permissions(self):
        if self.action == 'create':
            return []
        return [IsAdminUser()]


class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    permission_classes = [IsAdminUser]


class WorkoutPlanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WorkoutPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = WorkoutPlan.objects.select_related('member').all()
        if self.request.user.is_staff:
            return qs
        return qs.filter(member__user=self.request.user)


class DietPlanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DietPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DietPlan.objects.select_related('member').all()
        if self.request.user.is_staff:
            return qs
        return qs.filter(member__user=self.request.user)
