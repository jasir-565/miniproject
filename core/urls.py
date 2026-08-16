from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('vehicles/', views.vehicles, name='vehicles'),
    path('service-booking/', views.service_booking, name='service_booking'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('staff-dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path(
    'assign-appointment/<int:booking_id>/',
    views.assign_appointment,
    name='assign_appointment'),
    path(
    'update-service-status/<int:booking_id>/',
    views.update_service_status,
    name='update_service_status'),
    path('notifications/', views.notifications, name='notifications'),
    path(
    'notifications/<int:notification_id>/read/',
    views.mark_notification_read,
    name='mark_notification_read'
),
path(
    'service-history/',
    views.service_history,
    name='service_history'
),

path(
    'roadside-assistance/',
    views.roadside_assistance,
    name='roadside_assistance'
),

path(
    'staff-assistance/',
    views.staff_assistance_requests,
    name='staff_assistance_requests'
),

path(
    'assistance/<int:assistance_id>/accept/',
    views.accept_assistance_request,
    name='accept_assistance_request'
),

path(
    'assistance/<int:assistance_id>/update-status/',
    views.update_assistance_status,
    name='update_assistance_status'
),

path(
    'service-record/<int:booking_id>/save/',
    views.save_service_record,
    name='save_service_record'
),

path(
    'service/<int:booking_id>/complete-with-record/',
    views.complete_service_with_record,
    name='complete_service_with_record'
),

path('logout/', views.user_logout, name='logout'),

path(
    'staff-assistance-history/',
    views.staff_assistance_history,
    name='staff_assistance_history'
),

path(
    'staff-service-history/',
    views.staff_service_history,
    name='staff_service_history'
),
]