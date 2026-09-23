from django.urls import path
from . import views
from . import portal
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

urlpatterns = [
    path('account/', portal.account_settings, name='account_settings'),
    path('account/password/', auth_views.PasswordChangeView.as_view(template_name='core/account_form.html', success_url=reverse_lazy('password_change_done')), name='password_change'),
    path('account/password/done/', auth_views.PasswordChangeDoneView.as_view(template_name='core/account_form.html', extra_context={'message': 'Your password has been changed.'}), name='password_change_done'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='core/account_form.html', email_template_name='core/password_reset_email.txt', subject_template_name='core/password_reset_subject.txt'), name='password_reset'),
    path('password-reset/sent/', auth_views.PasswordResetDoneView.as_view(template_name='core/account_form.html', extra_context={'message': 'If an active account matches that email, a password reset link has been sent. Check your inbox.'}), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='core/account_form.html'), name='password_reset_confirm'),
    path('reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='core/account_form.html', extra_context={'message': 'Your password has been reset. You can now sign in.'}), name='password_reset_complete'),
    path('bookings/<int:booking_id>/', portal.booking_detail, name='booking_detail'),
    path('bookings/<int:booking_id>/estimate/', portal.estimate_create, name='estimate_create'),
    path('estimates/', portal.customer_estimates, name='customer_estimates'),
    path('bookings/<int:booking_id>/estimated-bill/', portal.estimate_detail, name='estimate_detail'),
    path('estimates/<int:estimate_id>/decision/', portal.estimate_decide, name='estimate_decide'),
    path('bookings/<int:booking_id>/receipt/', portal.invoice_detail, name='invoice_detail'),
    path('staff/schedule/', portal.schedule, name='staff_schedule'),
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('staff/register/', views.staff_register, name='staff_register'),
    path('staff/pending-approval/', views.staff_pending_approval, name='staff_pending_approval'),
    path('login/', views.user_login, name='login'),
    path('dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('vehicles/', views.vehicles, name='vehicles'),
    path('vehicles/<int:vehicle_id>/photo/update/', views.update_vehicle_photo, name='update_vehicle_photo'),
    path('vehicles/<int:vehicle_id>/photo/delete/', views.delete_vehicle_photo, name='delete_vehicle_photo'),
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
    'assistance/<int:assistance_id>/update-location/',
    views.update_staff_location,
    name='update_staff_location'
),

path(
    'assistance/<int:assistance_id>/tracking-data/',
    views.assistance_tracking_data,
    name='assistance_tracking_data'
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

path(
    'booking/<int:booking_id>/cancel/',
    views.cancel_service_booking,
    name='cancel_service_booking'
),

path(
    'roadside-assistance/<int:assistance_id>/cancel/',
    views.cancel_roadside_assistance,
    name='cancel_roadside_assistance'
),
]
