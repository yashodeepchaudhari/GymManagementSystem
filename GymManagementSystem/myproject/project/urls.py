from django.urls import path
from project import views
from project import member_views as mv
from project import trainer_views as tv

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
    path('scanner/', views.qr_scanner, name='qr_scanner'),
    path('scanner/check-in/', views.qr_check_in, name='qr_check_in'),

    # Gallery
    path('gallery/', views.gallery, name='gallery'),

    # ---------- Member portal ----------
    path('portal/signup/', mv.member_signup, name='member_signup'),
    path('portal/login/', mv.member_login, name='member_login'),
    path('portal/logout/', mv.member_logout, name='member_logout'),
    path('portal/dashboard/', mv.member_dashboard, name='member_dashboard'),
    path('portal/profile/', mv.member_profile, name='member_profile'),
    path('portal/renew/', mv.member_renew, name='member_renew'),
    path('portal/check-in/', mv.member_check_in, name='member_check_in'),
    path('portal/qr.png', mv.member_qr, name='member_qr'),
    path('portal/chat/send/', mv.chat_send, name='chat_send'),
    path('portal/chat/history/', mv.chat_history, name='chat_history'),
    path('portal/plan.pdf', mv.download_plan_pdf, name='download_plan_pdf'),
    path('portal/receipt/<int:payment_id>.pdf', mv.download_receipt_pdf, name='download_receipt_pdf'),
    path('portal/ai/generate/', mv.ai_generate_plan, name='ai_generate_plan'),
    path('portal/ai/plan/', mv.ai_view_plan, name='ai_view_plan'),
    path('portal/ai/body/', mv.body_analysis, name='body_analysis'),

    # ---------- Trainer portal ----------
    path('trainer/login/', tv.trainer_login, name='trainer_login'),
    path('trainer/logout/', tv.trainer_logout, name='trainer_logout'),
    path('trainer/dashboard/', tv.trainer_dashboard, name='trainer_dashboard'),
    path('trainer/member/<int:member_id>/', tv.trainer_member_detail, name='trainer_member_detail'),
    path('trainer/member/<int:member_id>/notes/', tv.trainer_save_notes, name='trainer_save_notes'),
]
