from django.urls import path
from project import views
from project import member_views as mv

urlpatterns = [
    # ---------- Public ----------
    path('', views.home, name='home'),
    path('home_gallery/', views.home_gallery, name='home_gallery'),
    path('test/', views.test, name='test'),

    # ---------- Admin auth ----------
    path('admin_login/', views.admin_login, name='admin_login'),
    path('admin_logout/', views.admin_logout, name='admin_logout'),

    # ---------- Admin panel ----------
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin_about/', views.admin_about, name='admin_about'),
    path('admin_contact/', views.admin_contact, name='admin_contact'),

    # Enquiries
    path('add-enquiry/', views.add_enquiry, name='add_enquiry'),
    path('view-enquiry/', views.view_enquiry, name='view_enquiry'),
    path('delete-enquiry/<int:enquiry_id>/', views.delete_enquiry, name='delete_enquiry'),

    # Plans
    path('add_plan/', views.add_plan, name='add_plan'),
    path('view_plan/', views.view_plan, name='view_plan'),
    path('delete-plan/<int:plan_id>/', views.delete_plan, name='delete_plan'),

    # Equipment
    path('add_equipment/', views.add_equipment, name='add_equipment'),
    path('view_equipment/', views.view_equipment, name='view_equipment'),
    path('delete_equipment/<int:equipment_id>/', views.delete_equipment, name='delete_equipment'),

    # Members
    path('add_member/', views.add_member, name='add_member'),
    path('view_member/', views.view_member, name='view_member'),
    path('edit_member/<int:member_id>/', views.edit_member, name='edit_member'),
    path('delete_member/<int:member_id>/', views.delete_member, name='delete_member'),
    path('members/export.csv', views.export_members_csv, name='export_members_csv'),

    # Gallery
    path('gallery/', views.gallery, name='gallery'),

    # ---------- Member portal ----------
    path('portal/signup/', mv.member_signup, name='member_signup'),
    path('portal/login/', mv.member_login, name='member_login'),
    path('portal/logout/', mv.member_logout, name='member_logout'),
    path('portal/dashboard/', mv.member_dashboard, name='member_dashboard'),
    path('portal/profile/', mv.member_profile, name='member_profile'),
    path('portal/check-in/', mv.member_check_in, name='member_check_in'),
    path('portal/ai/generate/', mv.ai_generate_plan, name='ai_generate_plan'),
    path('portal/ai/plan/', mv.ai_view_plan, name='ai_view_plan'),
]
