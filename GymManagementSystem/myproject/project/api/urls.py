from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from . import views

router = DefaultRouter()
router.register('plans', views.PlanViewSet)
router.register('members', views.MemberViewSet, basename='member')
router.register('subscriptions', views.SubscriptionViewSet, basename='subscription')
router.register('payments', views.PaymentViewSet, basename='payment')
router.register('attendance', views.AttendanceViewSet, basename='attendance')
router.register('enquiries', views.EnquiryViewSet)
router.register('equipment', views.EquipmentViewSet)
router.register('workout-plans', views.WorkoutPlanViewSet, basename='workoutplan')
router.register('diet-plans', views.DietPlanViewSet, basename='dietplan')


urlpatterns = [
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='token_verify'),

    path('me/', views.me, name='api_me'),

    path('', include(router.urls)),

    # Schema + docs
    path('schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api-schema'), name='api-redoc'),
]
