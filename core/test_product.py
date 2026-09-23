from datetime import timedelta, time
from decimal import Decimal
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import CustomerProfile, StaffProfile, Vehicle, ServiceBooking, AssistanceRequest, Estimate, Invoice, ServiceEvent, StaffShift, StaffTimeOff, Notification


class ProductWorkflowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', email='owner@example.com', password='Owner-password-123!')
        self.customer = CustomerProfile.objects.create(user=self.owner, phone='9876543210')
        self.technician = User.objects.create_user('technician')
        self.staff = StaffProfile.objects.create(user=self.technician, phone='9876543210', designation='Mechanic', is_approved=True, status='APPROVED')
        self.pending_user = User.objects.create_user('pending')
        self.pending = StaffProfile.objects.create(user=self.pending_user, phone='9876543210', designation='Mechanic')
        self.vehicle = Vehicle.objects.create(customer=self.customer, registration_number='TEST001', brand='Test', model='Car', year=2024)
        self.booking = ServiceBooking.objects.create(customer=self.customer, vehicle=self.vehicle, staff=self.staff, service_type='Inspection', issue_description='Check brakes', status='CONFIRMED', requires_estimate_approval=True)

    def estimate_data(self):
        return {'lines-TOTAL_FORMS': '2', 'lines-INITIAL_FORMS': '0', 'lines-MIN_NUM_FORMS': '1', 'lines-MAX_NUM_FORMS': '20', 'lines-0-kind': 'LABOUR', 'lines-0-description': 'Inspection labour', 'lines-0-quantity': '1', 'lines-0-unit_price': '500.00', 'lines-1-kind': 'PART', 'lines-1-description': 'Brake pads', 'lines-1-quantity': '2', 'lines-1-unit_price': '250.00', 'note': 'All charges included.'}

    def send_estimate(self):
        self.client.force_login(self.technician)
        self.assertEqual(self.client.post(reverse('estimate_create', args=[self.booking.pk]), self.estimate_data()).status_code, 302)
        return self.booking.estimates.first()

    def approve(self, estimate):
        self.client.force_login(self.owner)
        return self.client.post(reverse('estimate_decide', args=[estimate.pk]), {'decision': 'APPROVED'})

    def test_pending_staff_blocked_from_actions_and_allocation(self):
        request = AssistanceRequest.objects.create(customer=self.customer, vehicle=self.vehicle, assistance_type='Battery', problem_description='Battery failed', location_details='Test road')
        self.client.force_login(self.pending_user)
        self.assertEqual(self.client.post(reverse('accept_assistance_request', args=[request.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('update_service_status', args=[self.booking.pk]), {'status': 'IN_PROGRESS'}).status_code, 403)
        self.client.force_login(self.owner)
        self.client.post(reverse('service_booking'), {'vehicle': self.vehicle.pk, 'service_type': 'Oil Change', 'issue_description': 'Oil service requested'})
        newest = ServiceBooking.objects.latest('pk')
        self.assertEqual(newest.staff_id, self.staff.pk)
        self.assertTrue(newest.requires_estimate_approval)

    def test_unavailable_staff_not_allocated(self):
        self.staff.available_for_work = False
        self.staff.save()
        self.client.force_login(self.owner)
        self.client.post(reverse('service_booking'), {'vehicle': self.vehicle.pk, 'service_type': 'Oil Change', 'issue_description': 'Oil service requested'})
        self.assertEqual(ServiceBooking.objects.count(), 1)

    def test_full_estimate_approval_receipt_and_timeline(self):
        estimate = self.send_estimate()
        self.assertEqual(estimate.total, Decimal('1000.00'))
        self.client.post(reverse('update_service_status', args=[self.booking.pk]), {'status': 'IN_PROGRESS', 'current_work': 'Starting repair'})
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'CONFIRMED')
        self.approve(estimate)
        self.client.force_login(self.technician)
        self.client.post(reverse('update_service_status', args=[self.booking.pk]), {'status': 'IN_PROGRESS', 'current_work': 'Replacing brake pads'})
        self.client.post(reverse('complete_service_with_record', args=[self.booking.pk]), {'service_cost': '1100', 'repair_details': 'Pads replaced'})
        self.assertFalse(Invoice.objects.exists())
        self.client.post(reverse('complete_service_with_record', args=[self.booking.pk]), {'service_cost': '1000', 'repair_details': 'Pads replaced'})
        invoice = Invoice.objects.get(booking=self.booking)
        self.assertEqual(invoice.lines.count(), 2)
        self.assertEqual(invoice.total, Decimal('1000.00'))
        self.assertEqual(self.booking.events.count(), 4)
        self.client.post(reverse('save_service_record', args=[self.booking.pk]), {'service_cost': '1'})
        self.assertEqual(self.booking.service_record.service_cost, Decimal('1000.00'))
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse('booking_detail', args=[self.booking.pk])), 'Replacing brake pads')
        self.assertContains(self.client.get(reverse('invoice_detail', args=[self.booking.pk])), invoice.number)

    def test_revised_estimate_invalidates_old_approval(self):
        first = self.send_estimate()
        self.approve(first)
        second = self.send_estimate()
        first.refresh_from_db()
        self.assertEqual(first.status, 'SUPERSEDED')
        self.assertEqual(second.revision, 2)
        self.approve(first)
        second.refresh_from_db()
        self.assertEqual(second.status, 'PENDING')
        self.client.force_login(self.technician)
        self.client.post(reverse('complete_service_with_record', args=[self.booking.pk]), {'service_cost': '1000'})
        self.assertFalse(Invoice.objects.exists())

    def test_estimate_bounds_and_cross_account_access(self):
        self.client.force_login(self.technician)
        data = self.estimate_data()
        data['lines-0-quantity'] = '0'
        self.assertEqual(self.client.post(reverse('estimate_create', args=[self.booking.pk]), data).status_code, 200)
        self.assertFalse(Estimate.objects.exists())
        outsider = User.objects.create_user('outsider')
        CustomerProfile.objects.create(user=outsider, phone='9876543210')
        estimate = self.send_estimate()
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(reverse('booking_detail', args=[self.booking.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('invoice_detail', args=[self.booking.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('estimate_decide', args=[estimate.pk]), {'decision': 'APPROVED'}).status_code, 403)

    def test_schedule_rejects_overlap_but_accepts_adjacent_slot(self):
        date = timezone.localdate() + timedelta(days=3)
        self.booking.appointment_date = date
        self.booking.appointment_time = time(10)
        self.booking.duration_minutes = 120
        self.booking.save()
        second = ServiceBooking.objects.create(customer=self.customer, vehicle=self.vehicle, staff=self.staff, service_type='Oil Change', issue_description='Oil service')
        self.client.force_login(self.technician)
        url = reverse('assign_appointment', args=[second.pk])
        self.client.post(url, {'appointment_date': date, 'appointment_time': '11:00', 'duration_minutes': 60})
        second.refresh_from_db()
        self.assertEqual(second.status, 'PENDING')
        self.client.post(url, {'appointment_date': date, 'appointment_time': '12:00', 'duration_minutes': 60})
        second.refresh_from_db()
        self.assertEqual(second.status, 'CONFIRMED')

    def test_schedule_respects_shift_leave_and_closing_time(self):
        date = timezone.localdate() + timedelta(days=4)
        self.booking.status = 'PENDING'
        self.booking.save()
        StaffShift.objects.create(staff=self.staff, weekday=date.weekday(), starts_at=time(10), ends_at=time(16))
        start = timezone.make_aware(__import__('datetime').datetime.combine(date, time(12)))
        StaffTimeOff.objects.create(staff=self.staff, starts_at=start, ends_at=start+timedelta(hours=2))
        self.client.force_login(self.technician)
        for hour, duration in [('09:00', 60), ('12:30', 60), ('15:30', 60), ('17:30', 60)]:
            self.client.post(reverse('assign_appointment', args=[self.booking.pk]), {'appointment_date': date, 'appointment_time': hour, 'duration_minutes': duration})
            self.booking.refresh_from_db()
            self.assertEqual(self.booking.status, 'PENDING')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_profile_and_password_reset(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('account_settings'), {'first_name': 'Alex', 'last_name': 'Owner', 'email': 'owner@example.com', 'phone': '+91 98765 43210', 'address': 'Test address'})
        self.assertEqual(response.status_code, 302)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.phone, '919876543210')
        self.client.logout()
        response = self.client.post(reverse('password_reset'), {'email': 'owner@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/reset/', mail.outbox[0].body)

    def test_receipt_snapshot_survives_vehicle_rename(self):
        self.approve(self.send_estimate())
        self.client.force_login(self.technician)
        self.client.post(reverse('complete_service_with_record', args=[self.booking.pk]), {'service_cost': '1000'})
        self.vehicle.registration_number = 'CHANGED'
        self.vehicle.save()
        invoice = Invoice.objects.get()
        self.assertIn('TEST001', invoice.vehicle_label)
        self.assertNotIn('CHANGED', invoice.vehicle_label)

    def test_list_pagination(self):
        from .models import Notification
        Notification.objects.bulk_create([Notification(customer=self.customer, booking=self.booking, title=f'Update {i}', message='Update') for i in range(15)])
        self.client.force_login(self.owner)
        page = self.client.get(reverse('notifications')).context['notifications']
        self.assertEqual(len(page), 12)
        self.assertTrue(page.has_next())


class CustomerEstimateNavigationTests(TestCase):
    setUp = ProductWorkflowTests.setUp
    estimate_data = ProductWorkflowTests.estimate_data
    send_estimate = ProductWorkflowTests.send_estimate
    approve = ProductWorkflowTests.approve

    def test_bill_discoverable_and_decision_persists(self):
        estimate = self.send_estimate()
        self.client.force_login(self.owner)
        detail = reverse('estimate_detail', args=[self.booking.pk])
        self.assertContains(self.client.get(reverse('my_bookings')), reverse('booking_detail', args=[self.booking.pk]))
        self.assertContains(self.client.get(reverse('booking_detail', args=[self.booking.pk])), detail)
        self.assertContains(self.client.get(reverse('customer_estimates')), '1 awaiting approval')
        bill = self.client.get(detail)
        for text in ('Inspection labour', 'Brake pads', '1000.00', 'All charges included.', 'Approve'):
            self.assertContains(bill, text)
        self.assertTrue(Notification.objects.filter(customer=self.customer, title='Please review your service estimate').exists())
        self.assertRedirects(self.approve(estimate), detail)
        self.assertNotContains(self.client.get(detail), 'value="APPROVED"')
        self.assertContains(self.client.get(reverse('customer_estimates')), '0 awaiting approval')

    def test_only_current_owned_estimates_listed_and_cancelled_cannot_be_approved(self):
        first = self.send_estimate()
        second = self.send_estimate()
        self.client.force_login(self.owner)
        response = self.client.get(reverse('customer_estimates'))
        self.assertEqual([e.pk for e in response.context['estimates']], [second.pk])
        self.client.post(reverse('estimate_decide', args=[first.pk]), {'decision': 'APPROVED'})
        second.refresh_from_db()
        self.assertEqual(second.status, 'PENDING')
        self.booking.status = 'CANCELLED'
        self.booking.save()
        self.assertNotContains(self.client.get(reverse('estimate_detail', args=[self.booking.pk])), 'value="APPROVED"')
        self.approve(second)
        second.refresh_from_db()
        self.assertEqual(second.status, 'PENDING')
        outsider = User.objects.create_user('other_customer')
        CustomerProfile.objects.create(user=outsider, phone='1234567890')
        self.client.force_login(outsider)
        self.assertContains(self.client.get(reverse('customer_estimates')), 'No estimates yet')
        self.assertEqual(self.client.get(reverse('estimate_detail', args=[self.booking.pk])).status_code, 403)
        self.client.force_login(self.technician)
        self.assertEqual(self.client.get(reverse('customer_estimates')).status_code, 403)

    def test_booking_validation_keeps_customer_input(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('service_booking'), {'vehicle': self.vehicle.pk, 'service_type': 'Brake Service', 'issue_description': 'Squeaks'})
        self.assertContains(response, 'Squeaks</textarea>')
        self.assertContains(response, 'value="Brake Service" selected')
