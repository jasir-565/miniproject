import json
import math
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from ..validation import coordinates, location_url, service_cost, vehicle_photo
from ..permissions import approved_staff
from ..services import record_event, validate_appointment, approved_estimate, issue_invoice
from ..forms import AppointmentForm
from ..pagination import page_for

from ..models import (
    CustomerProfile,
    Vehicle,
    ServiceBooking,
    StaffProfile,
    Notification,
    AssistanceRequest,
    ServiceRecord,
)


from .common import redirect_user_by_role

@never_cache
@csrf_protect
@transaction.atomic
def service_booking(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    customer = request.user.customer_profile

    customer_vehicles = Vehicle.objects.filter(
        customer=customer
    ).order_by('-created_at')

    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle')
        service_type = request.POST.get(
            'service_type',
            ''
        ).strip()

        issue_description = request.POST.get(
            'issue_description',
            ''
        ).strip()

        if not customer_vehicles.exists():
            return render(request, 'core/service_booking.html', {
                'vehicles': customer_vehicles,
                'error': 'Please add a vehicle before booking a service.'
            })

        if not vehicle_id:
            return render(request, 'core/service_booking.html', {
                'vehicles': customer_vehicles,
                'error': 'Please select a vehicle.'
            })

        if not service_type:
            return render(request, 'core/service_booking.html', {
                'vehicles': customer_vehicles,
                'error': 'Please select or enter a service type.'
            })

        if len(issue_description) < 10:
            return render(request, 'core/service_booking.html', {
                'vehicles': customer_vehicles,
                'error': 'Please enter at least 10 characters in issue description.'
            })

        vehicle = get_object_or_404(
            Vehicle,
            id=vehicle_id,
            customer=customer
        )

        staff_ids = list(StaffProfile.objects.select_for_update().filter(
            user__is_active=True, is_approved=True, status='APPROVED', available_for_work=True
        ).order_by('pk').values_list('pk', flat=True))
        available_staff = StaffProfile.objects.filter(pk__in=staff_ids).annotate(
            active_job_count=Count(
                'assigned_bookings',
                filter=Q(
                    assigned_bookings__status__in=[
                        'PENDING',
                        'CONFIRMED',
                        'IN_PROGRESS'
                    ]
                )
            )
        ).order_by(
            'active_job_count',
            'id'
        ).first()

        if available_staff is None:
            return render(request, 'core/service_booking.html', {
                'vehicles': customer_vehicles,
                'error': 'No service staff is available right now. Please try again later.'
            })

        booking = ServiceBooking.objects.create(
            customer=customer,
            vehicle=vehicle,
            service_type=service_type,
            issue_description=issue_description,
            staff=available_staff,
            requires_estimate_approval=True,
        )

        record_event(booking, request.user, 'Service requested', issue_description)

        Notification.objects.create(
            customer=customer,
            title='Service Booking Created',
            booking=booking,
            message=(
                f'Your service booking for '
                f'{booking.vehicle.registration_number} '
                f'has been created and assigned to staff.'
            ),
            notification_type='SERVICE'
        )

        return redirect('my_bookings')

    return render(request, 'core/service_booking.html', {
        'vehicles': customer_vehicles
    })

@never_cache
def my_bookings(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    customer = request.user.customer_profile

    customer_bookings = ServiceBooking.objects.select_related('vehicle', 'staff__user').prefetch_related('estimates__lines').filter(
        customer=customer
    ).exclude(
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('-created_at')

    return render(request, 'core/my_bookings.html', {
        'bookings': page_for(request, customer_bookings, 'bookings_page')
    })

@never_cache
@csrf_protect
@require_POST
@transaction.atomic
@approved_staff
def assign_appointment(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    # Serialize scheduling for this technician, including different bookings.
    StaffProfile.objects.select_for_update().get(pk=staff.pk)

    booking = get_object_or_404(
        ServiceBooking.objects.select_for_update(),
        id=booking_id,
        staff=staff,
        status='PENDING'
    )

    if request.method == 'POST':
        data = request.POST.copy()
        data.setdefault('duration_minutes', booking.duration_minutes)
        form = AppointmentForm(data)
        if not form.is_valid():
            messages.error(request, ' '.join(error for errors in form.errors.values() for error in errors))
            return redirect('staff_dashboard')
        try:
            validate_appointment(booking, form.cleaned_data['appointment_date'], form.cleaned_data['appointment_time'], form.cleaned_data['duration_minutes'])
        except ValidationError as exc:
            messages.error(request, ' '.join(exc.messages))
            return redirect('staff_dashboard')
        booking.appointment_date = form.cleaned_data['appointment_date']
        booking.appointment_time = form.cleaned_data['appointment_time']
        booking.duration_minutes = form.cleaned_data['duration_minutes']
        booking.status = 'CONFIRMED'
        booking.save()
        record_event(booking, request.user, 'Appointment confirmed', f'{booking.appointment_date} at {booking.appointment_time} · {booking.duration_minutes} minutes')
        Notification.objects.create(customer=booking.customer, booking=booking, title='Service Appointment Confirmed', message='Your workshop appointment has been scheduled.', notification_type='SERVICE')

    return redirect('staff_dashboard')

@never_cache
@csrf_protect
@require_POST
@transaction.atomic
@approved_staff
def update_service_status(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    booking = get_object_or_404(
        ServiceBooking.objects.select_for_update(),
        id=booking_id,
        staff=staff
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')
        current_work = request.POST.get(
            'current_work',
            ''
        ).strip()

        allowed_statuses = {
            'CONFIRMED': {'CONFIRMED', 'IN_PROGRESS', 'CANCELLED'},
            'IN_PROGRESS': {'IN_PROGRESS', 'CANCELLED'},
        }.get(booking.status, set())

        if new_status not in allowed_statuses:
            return JsonResponse({'error': 'Invalid service status transition.'}, status=409)
        if len(current_work) > 255:
            return JsonResponse({'error': 'Work note must be at most 255 characters.'}, status=400)

        if new_status == 'IN_PROGRESS':
            try:
                approved_estimate(booking)
            except ValidationError as exc:
                messages.error(request, ' '.join(exc.messages))
                return redirect('booking_detail', booking_id=booking.pk)

        if new_status in allowed_statuses:
            old_status = booking.status

            booking.status = new_status
            booking.current_work = current_work
            booking.save()
            record_event(booking, request.user, booking.get_status_display(), current_work)

            if new_status == 'IN_PROGRESS' and old_status != 'IN_PROGRESS':
                Notification.objects.create(
                    customer=booking.customer,
                    title='Service In Progress',
                    booking=booking,
                    message=(
                        f'Your vehicle service for '
                        f'{booking.vehicle.registration_number} '
                        f'is now in progress.'
                    ),
                    notification_type='SERVICE'
                )

            if new_status == 'CANCELLED' and old_status != 'CANCELLED':
                Notification.objects.create(
                    customer=booking.customer,
                    title='Service Cancelled',
                    booking=booking,
                    message=(
                        f'Your vehicle service for '
                        f'{booking.vehicle.registration_number} '
                        f'has been cancelled.'
                    ),
                    notification_type='SERVICE'
                )

    return redirect('staff_dashboard')

@never_cache
def notifications(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    customer = request.user.customer_profile

    customer_notifications = Notification.objects.filter(
        customer=customer
    ).order_by('-created_at')

    return render(request, 'core/notifications.html', {
        'notifications': page_for(request, customer_notifications, 'notifications_page')
    })

@never_cache
@csrf_protect
@require_POST
def mark_notification_read(request, notification_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    customer = request.user.customer_profile

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        customer=customer
    )

    if request.method == 'POST':
        notification.is_read = True
        notification.save()

    return redirect('notifications')

@never_cache
def service_history(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    customer = request.user.customer_profile

    completed_services = ServiceBooking.objects.select_related('vehicle', 'staff__user', 'service_record').filter(
        customer=customer,
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('-updated_at')

    roadside_history = AssistanceRequest.objects.select_related('vehicle', 'customer__user', 'staff__user').filter(
        customer=customer,
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('-updated_at')

    return render(request, 'core/service_history.html', {
        'completed_services': page_for(request, completed_services, 'completed_services_page'),
        'roadside_history': page_for(request, roadside_history, 'roadside_history_page')
    })

@never_cache
@csrf_protect
@require_POST
@transaction.atomic
@approved_staff
def save_service_record(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    booking = get_object_or_404(
        ServiceBooking.objects.select_for_update(),
        id=booking_id,
        staff=staff,
        status='COMPLETED'
    )

    if hasattr(booking, 'invoice'):
        messages.error(request, 'This record has an issued receipt and cannot be changed.')
        return redirect('booking_detail', booking_id=booking.pk)

    if request.method == 'POST':
        inspection_details = request.POST.get(
            'inspection_details',
            ''
        ).strip()

        repair_details = request.POST.get(
            'repair_details',
            ''
        ).strip()

        parts_replaced = request.POST.get(
            'parts_replaced',
            ''
        ).strip()

        service_cost_value = request.POST.get(
            'service_cost',
            '0'
        ).strip()

        try:
            validated_cost = service_cost(service_cost_value)
        except ValidationError as exc:
            messages.error(request, ' '.join(exc.messages))
            return redirect('staff_dashboard')

        ServiceRecord.objects.update_or_create(
            booking=booking,
            defaults={
                'inspection_details': inspection_details,
                'repair_details': repair_details,
                'parts_replaced': parts_replaced,
                'service_cost': validated_cost,
                'completed_at': booking.updated_at,
            }
        )

        record_event(booking, request.user, 'Service record updated', repair_details)

    return redirect('staff_dashboard')

@never_cache
@csrf_protect
@require_POST
@transaction.atomic
@approved_staff
def complete_service_with_record(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    booking = get_object_or_404(
        ServiceBooking.objects.select_for_update(),
        id=booking_id,
        staff=staff,
        status__in=['CONFIRMED', 'IN_PROGRESS']
    )

    if request.method == 'POST':
        inspection_details = request.POST.get(
            'inspection_details',
            ''
        ).strip()

        repair_details = request.POST.get(
            'repair_details',
            ''
        ).strip()

        parts_replaced = request.POST.get(
            'parts_replaced',
            ''
        ).strip()

        service_cost_value = request.POST.get(
            'service_cost',
            '0'
        ).strip()

        try:
            validated_cost = service_cost(service_cost_value)
            estimate = approved_estimate(booking)
            if estimate and validated_cost != estimate.total:
                raise ValidationError('The final total must match the approved estimate.')
        except ValidationError as exc:
            messages.error(request, ' '.join(exc.messages))
            return redirect('staff_dashboard')

        ServiceRecord.objects.update_or_create(
            booking=booking,
            defaults={
                'inspection_details': inspection_details,
                'repair_details': repair_details,
                'parts_replaced': parts_replaced,
                'service_cost': validated_cost,
                'completed_at': timezone.now(),
            }
        )

        old_status = booking.status

        booking.status = 'COMPLETED'
        booking.current_work = 'Service completed'
        booking.save()
        issue_invoice(booking, validated_cost)
        record_event(booking, request.user, 'Service completed', repair_details)

        if old_status != 'COMPLETED':
            Notification.objects.create(
                customer=booking.customer,
                title='Service Completed',
                booking=booking,
                message=(
                    f'Your vehicle service for '
                    f'{booking.vehicle.registration_number} '
                    f'has been completed.'
                ),
                notification_type='SERVICE'
            )

    return redirect('staff_dashboard')

@never_cache
@approved_staff
def staff_service_history(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    service_history = ServiceBooking.objects.select_related('vehicle', 'customer__user', 'service_record').filter(
        staff=staff,
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('-updated_at')

    return render(request, 'core/staff_service_history.html', {
        'staff': staff,
        'service_history': page_for(request, service_history, 'service_history_page')
    })

@never_cache
@csrf_protect
@require_POST
@transaction.atomic
def cancel_service_booking(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    customer = request.user.customer_profile

    booking = get_object_or_404(
        ServiceBooking.objects.select_for_update(),
        id=booking_id,
        customer=customer,
        status__in=['PENDING', 'CONFIRMED']
    )

    if request.method == 'POST':
        booking.status = 'CANCELLED'
        booking.current_work = 'Booking cancelled by customer'
        booking.save()
        record_event(booking, request.user, 'Booking cancelled', booking.current_work)

        Notification.objects.create(
            customer=customer,
            title='Service Booking Cancelled',
            booking=booking,
            message=(
                f'Your service booking for '
                f'{booking.vehicle.registration_number} '
                f'has been cancelled.'
            ),
            notification_type='SERVICE'
        )

    return redirect('my_bookings')
