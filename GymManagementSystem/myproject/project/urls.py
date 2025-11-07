from project import views
from django.urls import path


urlpatterns = [
    path('',views.home,name="home"),
    path('admin_login',views.admin_login,name="admin_login"),
    path('admin_logout/', views.admin_logout, name="admin_logout"),
    path('admin_dashboard/',views.admin_dashboard,name="admin_dashboard"),
    path('admin_about/',views.admin_about,name="admin_about"),
    path('admin_contact/',views.admin_contact,name="admin_contact"),
     path('add-enquiry/', views.add_enquiry, name='add_enquiry'),
     path('view-enquiry/', views.view_enquiry, name='view_enquiry'),
    path('delete-enquiry/<int:enquiry_id>/',views.delete_enquiry, name='delete_enquiry'),
    path('add_plan/', views.add_plan, name='add_plan'),
    path('view_plan/', views.view_plan, name='view_plan'),
     path('delete-plan/<int:plan_id>/', views.delete_plan, name='delete_plan'),

      path('add_equipment/', views.add_equipment, name='add_equipment'),
    path('view_equipment/', views.view_equipment, name='view_equipment'),
    path('delete_equipment/<int:equipment_id>/', views.delete_equipment, name='delete_equipment'),

    path('add_member/', views.add_member, name='add_member'),
    path('view_member/', views.view_member, name='view_member'),
    path('delete_member/<int:member_id>/', views.delete_member, name='delete_member'),

    path('test/', views.test, name='test'),

    path('gallery',views.gallery,name='gallery'),
    path('home_gallery',views.home_gallery,name='home_gallery'),
    

   
    #   path('contact/', views.contact, name='contact')
    
   
]
