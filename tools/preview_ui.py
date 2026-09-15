"""Ephemeral UI preview with synthetic data. Never uses the application database.

Run: python tools/preview_ui.py
Public: / ; customer: /dashboard/?preview_role=customer
Staff: /staff-dashboard/?preview_role=staff
"""
import os
import sys
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.test_settings'
import django
from django.conf import settings
settings.DEBUG = True
settings.ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': 'file:autonexa_preview?mode=memory&cache=shared', 'OPTIONS': {'uri': True}}}


class PreviewUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.contrib.auth.models import User, AnonymousUser
        role = request.GET.get('preview_role', request.COOKIES.get('preview_role', 'public'))
        request.user = User.objects.get(username='preview_' + role) if role in ('customer', 'staff') else AnonymousUser()
        response = self.get_response(request)
        if 'preview_role' in request.GET:
            response.set_cookie('preview_role', role, httponly=True, samesite='Lax')
        return response


if __name__ == '__main__':
    settings.MIDDLEWARE.append('__main__.PreviewUserMiddleware')
    django.setup()
    from django.core.management import call_command
    from django.contrib.auth.models import User
    from django.utils import timezone
    from core.models import CustomerProfile, StaffProfile, Vehicle, ServiceBooking, Notification
    call_command('migrate', verbosity=0)
    customer = CustomerProfile.objects.create(user=User.objects.create_user('preview_customer', first_name='Alex'), phone='0000000000')
    staff = StaffProfile.objects.create(user=User.objects.create_user('preview_staff', first_name='Sam'), phone='0000000000', designation='Technician')
    vehicle = Vehicle.objects.create(customer=customer, registration_number='KL 07 AB 2024', brand='Volkswagen', model='Polo', year=2022)
    Vehicle.objects.create(customer=customer, registration_number='KL 07 CD 1986', brand='Honda', model='City', year=2024)
    ServiceBooking.objects.create(customer=customer, vehicle=vehicle, staff=staff, service_type='General Service', issue_description='Routine inspection and engine oil change.', status='CONFIRMED', appointment_date=(timezone.now()+timedelta(days=2)).date(), appointment_time='10:30')
    Notification.objects.create(customer=customer, title='Your appointment is confirmed', message='Your vehicle is booked in for a general service.', notification_type='SERVICE')
    print('Synthetic in-memory UI preview. Stop this process to discard all preview data.')
    call_command('runserver', '127.0.0.1:8765', use_reloader=False)
