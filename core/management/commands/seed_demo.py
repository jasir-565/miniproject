import os
from datetime import timedelta, time
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from core.models import CustomerProfile, StaffProfile, Vehicle, ServiceBooking, Estimate, EstimateLine, ServiceRecord, AssistanceRequest, Notification
from core.services import record_event, issue_invoice


class Command(BaseCommand):
    help = 'Create isolated demo accounts and realistic sample workflows in a development database.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Demo seeding is disabled when DEBUG is false.')
        password = os.environ.get('AUTONEXA_DEMO_PASSWORD', '')
        if len(password) < 12:
            raise CommandError('Set AUTONEXA_DEMO_PASSWORD to a development-only password of at least 12 characters.')
        names = ['demo_customer', 'demo_technician', 'demo_pending']
        if User.objects.filter(username__in=names).exists():
            self.stdout.write('Demo usernames already exist. No records were changed.')
            return
        owner = User.objects.create_user(names[0], email='demo.customer@example.test', password=password, first_name='Alex', last_name='Rao')
        tech = User.objects.create_user(names[1], email='demo.technician@example.test', password=password, first_name='Sam', last_name='Kumar')
        pending = User.objects.create_user(names[2], password=password, first_name='New', last_name='Technician')
        customer = CustomerProfile.objects.create(user=owner, phone='9000000001', address='Demo address, Bengaluru')
        staff = StaffProfile.objects.create(user=tech, phone='9000000002', designation='Mechanic', is_approved=True, status='APPROVED', approved_at=timezone.now())
        StaffProfile.objects.create(user=pending, phone='9000000003', designation='Mechanic')
        vehicle = Vehicle.objects.create(customer=customer, registration_number='DEMO-001', brand='Honda', model='City', year=2023)
        Vehicle.objects.create(customer=customer, registration_number='DEMO-002', brand='Volkswagen', model='Polo', year=2021)
        for index, state in enumerate(['CONFIRMED', 'COMPLETED']):
            booking = ServiceBooking.objects.create(customer=customer, vehicle=vehicle, staff=staff, service_type='Brake Service' if index == 0 else 'Oil Change', issue_description='Inspection and routine maintenance.', status='CONFIRMED', requires_estimate_approval=True, appointment_date=timezone.localdate()+timedelta(days=2), appointment_time=time(10+index*2), duration_minutes=90)
            record_event(booking, owner, 'Demo service requested', booking.issue_description)
            estimate = Estimate.objects.create(booking=booking, revision=1, created_by=tech, status='PENDING' if index == 0 else 'APPROVED', decided_by=owner if index else None, decided_at=timezone.now() if index else None)
            EstimateLine.objects.create(estimate=estimate, kind='LABOUR', description='Inspection and labour', quantity=1, unit_price=Decimal('500.00'))
            EstimateLine.objects.create(estimate=estimate, kind='PART', description='Replacement service parts', quantity=2, unit_price=Decimal('350.00'))
            record_event(booking, tech, 'Estimate sent', '₹1200.00')
            if index:
                record_event(booking, owner, 'Estimate approved', '₹1200.00')
                booking.status = 'COMPLETED'
                booking.current_work = 'Service completed'
                booking.save()
                ServiceRecord.objects.create(booking=booking, repair_details='Routine service completed.', inspection_details='Components inspected.', parts_replaced='Service parts', service_cost=estimate.total, completed_at=timezone.now())
                issue_invoice(booking, estimate.total)
                record_event(booking, tech, 'Service completed', 'Final inspection completed.')
            Notification.objects.create(customer=customer, booking=booking, title='Your service update', message='Review the service timeline and estimate.', notification_type='SERVICE')
        assistance = AssistanceRequest.objects.create(customer=customer, vehicle=vehicle, assistance_type='Battery Assistance', problem_description='Vehicle will not start.', location_details='Demo location near the workshop.', customer_latitude=12.9716, customer_longitude=77.5946)
        Notification.objects.create(customer=customer, assistance=assistance, title='Roadside request received', message='Waiting for technician assignment.', notification_type='ASSISTANCE')
        self.stdout.write(self.style.SUCCESS('Created demo_customer, demo_technician, and demo_pending. Use the password from AUTONEXA_DEMO_PASSWORD.'))
