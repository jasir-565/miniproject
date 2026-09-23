from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.contrib.auth.models import User
from django.db import connection, close_old_connections, connections
from django.test import TransactionTestCase, Client
from django.urls import reverse
from .models import CustomerProfile, StaffProfile, Vehicle, AssistanceRequest


@skipUnless(connection.vendor == 'mysql', 'Row-lock concurrency is verified by the MySQL CI job.')
class DispatchConcurrencyTests(TransactionTestCase):
    def test_only_one_technician_can_claim_a_request(self):
        customer = CustomerProfile.objects.create(user=User.objects.create_user('owner'), phone='1234567890')
        vehicle = Vehicle.objects.create(customer=customer, registration_number='RACE01', brand='Test', model='Car', year=2024)
        request = AssistanceRequest.objects.create(customer=customer, vehicle=vehicle, assistance_type='Battery', problem_description='No start', location_details='Test road')
        user_ids = []
        for name in ['tech_one', 'tech_two']:
            user = User.objects.create_user(name)
            StaffProfile.objects.create(user=user, phone='1234567890', designation='Mechanic', is_approved=True, status='APPROVED')
            user_ids.append(user.pk)
        barrier = Barrier(2)

        def claim(pk):
            close_old_connections()
            try:
                client = Client()
                client.force_login(User.objects.get(pk=pk))
                barrier.wait(timeout=10)
                return client.post(reverse('accept_assistance_request', args=[request.pk])).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(claim, user_ids))
        self.assertEqual(sorted(statuses), [302, 404])
        request.refresh_from_db()
        self.assertEqual(request.status, 'ASSIGNED')
        self.assertIsNotNone(request.staff_id)
