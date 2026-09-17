import json
import re
import shutil
import subprocess
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from unittest import skipUnless

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import CustomerProfile, StaffProfile, Vehicle, ServiceBooking, ServiceRecord, AssistanceRequest, Notification


class WorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer_user = User.objects.create_user('customer', password='a-test-password')
        cls.customer = CustomerProfile.objects.create(user=cls.customer_user, phone='1234567890')
        cls.other_customer_user = User.objects.create_user('other_customer')
        cls.other_customer = CustomerProfile.objects.create(user=cls.other_customer_user, phone='1234567890')
        cls.staff_user = User.objects.create_user('technician')
        cls.staff = StaffProfile.objects.create(user=cls.staff_user, phone='1234567890', designation='Mechanic', is_approved=True, status='APPROVED')
        cls.other_staff_user = User.objects.create_user('other_technician')
        cls.other_staff = StaffProfile.objects.create(user=cls.other_staff_user, phone='1234567890', designation='Mechanic', is_approved=True, status='APPROVED')
        cls.vehicle = Vehicle.objects.create(customer=cls.customer, registration_number='TEST123', brand='Test', model='Car', year=2024)

    def booking(self, status='PENDING'):
        return ServiceBooking.objects.create(customer=self.customer, vehicle=self.vehicle, staff=self.staff, service_type='Oil Change', issue_description='Routine service required', status=status)

    def assistance(self, status='ASSIGNED', assigned=True):
        return AssistanceRequest.objects.create(customer=self.customer, vehicle=self.vehicle, staff=self.staff if assigned else None, assistance_type='Battery', problem_description='Battery failed', location_details='<img src=x onerror=alert(1)>', customer_latitude=0, customer_longitude=77, status=status)

    def post(self, name, obj, data=None):
        return self.client.post(reverse(name, args=[obj.pk]), data or {})

    def test_appointment_validation_and_conflict(self):
        self.client.force_login(self.staff_user)
        booking = self.booking()
        for date in ['bad-date', (timezone.now() - timedelta(days=1)).date().isoformat()]:
            self.post('assign_appointment', booking, {'appointment_date':date, 'appointment_time':'10:00'})
            booking.refresh_from_db()
            self.assertEqual(booking.status, 'PENDING')
        date = (timezone.now() + timedelta(days=3)).date().isoformat()
        data = {'appointment_date':date, 'appointment_time':'10:00'}
        self.assertEqual(self.post('assign_appointment', booking, data).status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CONFIRMED')
        second = self.booking()
        self.post('assign_appointment', second, data)
        second.refresh_from_db()
        self.assertEqual(second.status, 'PENDING')
        self.assertEqual(self.post('assign_appointment', self.booking('COMPLETED'), data).status_code, 404)

    def test_staff_navigation_and_customer_count(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('staff_dashboard'))
        self.assertContains(response, 'Roadside Requests')
        self.assertNotContains(response, 'My Vehicles')
        self.booking('CANCELLED')
        self.booking('COMPLETED')
        self.booking('PENDING')
        self.client.force_login(self.customer_user)
        self.assertEqual(self.client.get(reverse('customer_dashboard')).context['active_bookings_count'], 1)

    def test_terminal_service_and_assistance_states_are_protected(self):
        self.client.force_login(self.staff_user)
        for status in ['COMPLETED', 'CANCELLED']:
            booking = self.booking(status)
            self.assertEqual(self.post('update_service_status', booking, {'status':'IN_PROGRESS'}).status_code, 409)
            booking.refresh_from_db()
            self.assertEqual(booking.status, status)
            assistance = self.assistance(status)
            self.assertEqual(self.post('update_assistance_status', assistance, {'status':'ON_THE_WAY'}).status_code, 409)
            self.assertEqual(self.post('update_staff_location', assistance, {'latitude':12, 'longitude':77}).status_code, 409)

    def test_forward_workflow_and_completion(self):
        self.client.force_login(self.staff_user)
        booking = self.booking('CONFIRMED')
        self.post('update_service_status', booking, {'status':'IN_PROGRESS', 'current_work':'Repairing brakes'})
        self.post('complete_service_with_record', booking, {'service_cost':'125.50', 'repair_details':'Brake repair'})
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'COMPLETED')
        self.assertEqual(booking.service_record.service_cost, Decimal('125.50'))
        self.assertEqual(self.post('complete_service_with_record', booking, {'service_cost':'20'}).status_code, 404)

    def test_assignment_cannot_be_claimed_twice(self):
        assistance = self.assistance('PENDING', assigned=False)
        self.client.force_login(self.staff_user)
        self.assertEqual(self.post('accept_assistance_request', assistance).status_code, 302)
        self.client.force_login(self.other_staff_user)
        self.assertEqual(self.post('accept_assistance_request', assistance).status_code, 404)
        assistance.refresh_from_db()
        self.assertEqual(assistance.staff_id, self.staff.pk)
        self.assertEqual(Notification.objects.count(), 1)

    def test_completion_rolls_back_on_failure(self):
        self.client.force_login(self.staff_user)
        booking = self.booking('IN_PROGRESS')
        with patch('core.views.Notification.objects.create', side_effect=RuntimeError('simulated failure')):
            with self.assertRaises(RuntimeError):
                self.post('complete_service_with_record', booking, {'service_cost':'25.00'})
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'IN_PROGRESS')
        self.assertFalse(ServiceRecord.objects.filter(booking=booking).exists())

    def test_tracking_access_and_gps_validation(self):
        assistance = self.assistance()
        url = reverse('assistance_tracking_data', args=[assistance.pk])
        self.assertEqual(self.client.get(url).status_code, 401)
        for user in [self.other_staff_user, self.other_customer_user]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(url).status_code, 403)
        for user in [self.customer_user, self.staff_user]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(url).status_code, 200)
        location_url = reverse('update_staff_location', args=[assistance.pk])
        self.assertEqual(self.client.post(location_url, {'latitude':'0', 'longitude':'77'}).status_code, 200)
        for data in [dict(latitude=0, longitude=0), dict(lat=-90, lng=180)]:
            self.assertEqual(self.client.post(location_url, json.dumps(data), content_type='application/json').status_code, 200)
        for data in [dict(latitude=91, longitude=0), dict(latitude=0, longitude=181), dict(latitude='NaN', longitude=1), dict(latitude='Infinity', longitude=1), dict(latitude=1), [], {'latitude':{}, 'longitude':0}]:
            self.assertEqual(self.client.post(location_url, json.dumps(data), content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post(location_url, '{', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.get(location_url).status_code, 405)

    def test_invalid_cost_does_not_complete_service(self):
        self.client.force_login(self.staff_user)
        booking = self.booking('IN_PROGRESS')
        for cost in ['NaN', 'Infinity', '-1', '100000000.00', '1.001', 'not-money']:
            self.post('complete_service_with_record', booking, {'service_cost':cost})
            booking.refresh_from_db()
            self.assertEqual(booking.status, 'IN_PROGRESS')
            self.assertFalse(ServiceRecord.objects.filter(booking=booking).exists())

    def test_other_accounts_cannot_mutate_records(self):
        booking = self.booking('CONFIRMED')
        self.client.force_login(self.other_staff_user)
        self.assertEqual(self.post('update_service_status', booking, {'status':'IN_PROGRESS'}).status_code, 404)
        self.client.force_login(self.other_customer_user)
        self.assertEqual(self.post('cancel_service_booking', booking).status_code, 404)
        self.assertEqual(self.post('delete_vehicle_photo', self.vehicle).status_code, 404)

    def test_invalid_customer_location_is_not_saved(self):
        self.client.force_login(self.customer_user)
        data = {'vehicle':self.vehicle.pk, 'assistance_type':'Battery', 'problem_description':'Battery will not start', 'location_details':'Test road'}
        for extra in [{'location_link':'javascript:alert(1)'}, {'customer_latitude':'200', 'customer_longitude':'10'}, {'customer_latitude':'12'}]:
            self.client.post(reverse('roadside_assistance'), {**data, **extra})
            self.assertFalse(AssistanceRequest.objects.exists())
        self.client.post(reverse('roadside_assistance'), {**data, 'customer_latitude':'0', 'customer_longitude':'0'})
        self.assertEqual(AssistanceRequest.objects.get().customer_latitude, 0)

    def test_fake_image_is_rejected(self):
        self.client.force_login(self.customer_user)
        image = SimpleUploadedFile('fake.png', b'not an image', content_type='image/png')
        self.post('update_vehicle_photo', self.vehicle, {'photo':image})
        self.vehicle.refresh_from_db()
        self.assertFalse(self.vehicle.photo)

    def test_weak_password_rejected_and_phone_normalized(self):
        data = dict(username='newcustomer', first_name='New', last_name='Customer', email='new@example.com', phone='+91 98765-43210', password='123456', confirm_password='123456')
        self.client.post(reverse('register'), data)
        self.assertFalse(User.objects.filter(username='newcustomer').exists())
        data.update(password='A-random-test-passphrase-94!', confirm_password='A-random-test-passphrase-94!')
        self.assertEqual(self.client.post(reverse('register'), data).status_code, 302)
        self.assertEqual(CustomerProfile.objects.get(user__username='newcustomer').phone, '919876543210')

    def test_logout_requires_post(self):
        self.client.force_login(self.customer_user)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertEqual(self.client.post(reverse('logout')).status_code, 302)

    def test_booking_assignment_and_atomic_notification(self):
        self.client.force_login(self.customer_user)
        data = {'vehicle':self.vehicle.pk, 'service_type':'Oil Change', 'issue_description':'Please check the brakes'}
        self.assertEqual(self.client.post(reverse('service_booking'), data).status_code, 302)
        self.assertEqual(ServiceBooking.objects.get().staff_id, self.staff.pk)
        with patch('core.views.Notification.objects.create', side_effect=RuntimeError('simulated failure')):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('service_booking'), data)
        self.assertEqual(ServiceBooking.objects.count(), 1)

    def test_map_templates_render_with_untrusted_text(self):
        self.assistance()
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('staff_assistance_requests'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AutoNexa.popup(')
        self.assertNotContains(response, '<img src=x onerror=alert(1)>')
        self.client.force_login(self.customer_user)
        self.assertEqual(self.client.get(reverse('roadside_assistance')).status_code, 200)

    def test_existing_unsafe_links_are_not_rendered(self):
        assistance = self.assistance()
        assistance.location_link = 'javascript:alert(123)'
        assistance.staff_location_link = 'data:text/html,unsafe'
        assistance.save()
        self.client.force_login(self.customer_user)
        response = self.client.get(reverse('roadside_assistance'))
        self.assertNotContains(response, 'href="javascript:')
        self.assertNotContains(response, 'href="data:')
        self.assertIsNone(self.client.get(reverse('assistance_tracking_data', args=[assistance.pk])).json()['location_link'])

    @skipUnless(shutil.which('node'), 'Node is needed to check rendered JavaScript syntax')
    def test_rendered_javascript_syntax(self):
        self.assistance()
        self.vehicle.brand = "Owner's </script> brand"
        self.vehicle.save()
        for user, page in [(self.staff_user, 'staff_assistance_requests'), (self.customer_user, 'roadside_assistance'), (self.customer_user, 'vehicles')]:
            self.client.force_login(user)
            html = self.client.get(reverse(page)).content.decode()
            for script in re.findall(r'<script\b[^>]*>(.*?)</script>', html, re.S):
                result = subprocess.run([shutil.which('node'), '--check', '-'], input=script, text=True, encoding='utf-8', capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_staff_registration_creates_pending_quarantined_profile(self):
        data = {
            'username': 'newtech',
            'first_name': 'New',
            'last_name': 'Mechanic',
            'email': 'newtech@example.com',
            'phone': '9876543210',
            'designation': 'Master Technician',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
        }
        response = self.client.post(reverse('staff_register'), data)
        self.assertRedirects(response, reverse('staff_pending_approval'))

        new_user = User.objects.get(username='newtech')
        self.assertTrue(hasattr(new_user, 'staff_profile'))
        self.assertFalse(new_user.staff_profile.is_approved)
        self.assertEqual(new_user.staff_profile.status, 'PENDING')
        self.assertEqual(new_user.staff_profile.designation, 'Master Technician')

    def test_unapproved_staff_quarantined_from_dashboard(self):
        unapproved_user = User.objects.create_user('unapproved_tech', password='Password123!')
        StaffProfile.objects.create(
            user=unapproved_user,
            phone='1234567890',
            designation='Technician',
            is_approved=False,
            status='PENDING'
        )
        self.client.force_login(unapproved_user)

        # Attempting dashboard access should bounce to pending approval
        response = self.client.get(reverse('staff_dashboard'))
        self.assertRedirects(response, reverse('staff_pending_approval'))

        # Pending approval page itself should render 200 with notice
        pending_response = self.client.get(reverse('staff_pending_approval'))
        self.assertEqual(pending_response.status_code, 200)
        self.assertContains(pending_response, 'Staff Verification Pending')

    def test_admin_approval_unlocks_staff_access(self):
        new_tech = User.objects.create_user('approved_tech', password='Password123!')
        profile = StaffProfile.objects.create(
            user=new_tech,
            phone='1234567890',
            designation='Diagnostic Specialist',
            is_approved=False,
            status='PENDING'
        )
        self.client.force_login(new_tech)

        # Before approval -> blocked
        self.assertRedirects(self.client.get(reverse('staff_dashboard')), reverse('staff_pending_approval'))

        # Admin approves
        profile.is_approved = True
        profile.status = 'APPROVED'
        profile.save()

        # After approval -> granted access to staff dashboard
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Visiting pending approval page now auto-routes to dashboard
        self.assertRedirects(self.client.get(reverse('staff_pending_approval')), reverse('staff_dashboard'))

