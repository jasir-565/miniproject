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
def customer_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    customer = request.user.customer_profile

    vehicles_count = Vehicle.objects.filter(
        customer=customer
    ).count()

    active_bookings_count = ServiceBooking.objects.filter(
        customer=customer,
        status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS']
    ).count()

    completed_services_count = ServiceBooking.objects.filter(
        customer=customer,
        status='COMPLETED'
    ).count()

    unread_notifications_count = Notification.objects.filter(
        customer=customer,
        is_read=False
    ).count()

    roadside_requests_count = AssistanceRequest.objects.filter(
        customer=customer
    ).count()

    return render(request, 'core/customer_dashboard.html', {
        'featured_vehicle': customer.vehicles.order_by('-created_at').first(),
        'next_booking': customer.service_bookings.filter(
            status__in=['CONFIRMED', 'IN_PROGRESS']
        ).select_related('vehicle').order_by('appointment_date', 'appointment_time').first(),
        'vehicles_count': vehicles_count,
        'active_bookings_count': active_bookings_count,
        'completed_services_count': completed_services_count,
        'unread_notifications_count': unread_notifications_count,
        'roadside_requests_count': roadside_requests_count,
    })

@never_cache
def staff_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    if not request.user.staff_profile.is_approved or request.user.staff_profile.status != 'APPROVED':
        return redirect('staff_pending_approval')

    staff = request.user.staff_profile

    active_bookings = ServiceBooking.objects.select_related('vehicle', 'customer__user', 'staff__user').filter(
        staff=staff,
        status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS']
    ).order_by('-created_at')

    pending_count = ServiceBooking.objects.filter(
        staff=staff,
        status='PENDING'
    ).count()

    confirmed_count = ServiceBooking.objects.filter(
        staff=staff,
        status='CONFIRMED'
    ).count()

    in_progress_count = ServiceBooking.objects.filter(
        staff=staff,
        status='IN_PROGRESS'
    ).count()

    completed_count = ServiceBooking.objects.filter(
        staff=staff,
        status='COMPLETED'
    ).count()

    cancelled_count = ServiceBooking.objects.filter(
        staff=staff,
        status='CANCELLED'
    ).count()

    available_assistance_count = AssistanceRequest.objects.filter(
        staff__isnull=True,
        status='PENDING'
    ).count()

    my_active_assistance_count = AssistanceRequest.objects.filter(
        staff=staff
    ).exclude(
        status__in=['COMPLETED', 'CANCELLED']
    ).count()

    return render(request, 'core/staff_dashboard.html', {
        'staff': staff,
        'bookings': page_for(request, active_bookings, 'bookings_page'),
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'available_assistance_count': available_assistance_count,
        'my_active_assistance_count': my_active_assistance_count,
    })
