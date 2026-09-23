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
def roadside_assistance(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    customer = request.user.customer_profile

    vehicles = Vehicle.objects.filter(
        customer=customer
    ).order_by('-created_at')

    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle')

        assistance_type = request.POST.get(
            'assistance_type',
            ''
        ).strip()

        problem_description = request.POST.get(
            'problem_description',
            ''
        ).strip()

        location_details = request.POST.get(
            'location_details',
            ''
        ).strip()

        location_link = request.POST.get(
            'location_link',
            ''
        ).strip()

        if not vehicles.exists():
            assistance_requests = AssistanceRequest.objects.select_related('vehicle', 'customer__user', 'staff__user').filter(
                customer=customer
            ).exclude(
                status__in=['COMPLETED', 'CANCELLED']
            ).order_by('-created_at')

            return render(request, 'core/roadside_assistance.html', {
                'vehicles': vehicles,
                'assistance_requests': assistance_requests,
                'error': 'Please add a vehicle before requesting roadside assistance.'
            })

        if not vehicle_id:
            assistance_requests = AssistanceRequest.objects.select_related('vehicle', 'customer__user', 'staff__user').filter(
                customer=customer
            ).exclude(
                status__in=['COMPLETED', 'CANCELLED']
            ).order_by('-created_at')

            return render(request, 'core/roadside_assistance.html', {
                'vehicles': vehicles,
                'assistance_requests': assistance_requests,
                'error': 'Please select a vehicle.'
            })

        if not assistance_type:
            assistance_requests = AssistanceRequest.objects.select_related('vehicle', 'customer__user', 'staff__user').filter(
                customer=customer
            ).exclude(
                status__in=['COMPLETED', 'CANCELLED']
            ).order_by('-created_at')

            return render(request, 'core/roadside_assistance.html', {
                'vehicles': vehicles,
                'assistance_requests': assistance_requests,
                'error': 'Please select an assistance type.'
            })

        if len(problem_description) < 10:
            assistance_requests = AssistanceRequest.objects.select_related('vehicle', 'customer__user', 'staff__user').filter(
                customer=customer
            ).exclude(
                status__in=['COMPLETED', 'CANCELLED']
            ).order_by('-created_at')

            return render(request, 'core/roadside_assistance.html', {
                'vehicles': vehicles,
                'assistance_requests': assistance_requests,
                'error': 'Please enter at least 10 characters in problem description.'
            })

        if len(location_details) < 5:
            assistance_requests = AssistanceRequest.objects.select_related('vehicle', 'customer__user', 'staff__user').filter(
                customer=customer
            ).exclude(
                status__in=['COMPLETED', 'CANCELLED']
            ).order_by('-created_at')

            return render(request, 'core/roadside_assistance.html', {
                'vehicles': vehicles,
                'assistance_requests': assistance_requests,
                'error': 'Please enter proper location details.'
            })

        cust_lat_raw = request.POST.get('customer_latitude', '').strip()
        cust_lng_raw = request.POST.get('customer_longitude', '').strip()
        try:
            cust_lat, cust_lng = coordinates(cust_lat_raw, cust_lng_raw)
            location_link = location_url(location_link)
        except ValidationError as exc:
            messages.error(request, ' '.join(exc.messages))
            return redirect('roadside_assistance')

        vehicle = get_object_or_404(
            Vehicle,
            id=vehicle_id,
            customer=customer
        )

        assistance = AssistanceRequest.objects.create(
            customer=customer,
            vehicle=vehicle,
            assistance_type=assistance_type,
            problem_description=problem_description,
            location_details=location_details,
            location_link=location_link or None,
            customer_latitude=cust_lat,
            customer_longitude=cust_lng,
        )

        Notification.objects.create(
            customer=customer,
            title='Roadside Assistance Requested',
            assistance=assistance,
            message=(
                f'Your roadside assistance request for '
                f'{assistance.vehicle.registration_number} '
                f'has been submitted successfully.'
            ),
            notification_type='ASSISTANCE'
        )

        return redirect('roadside_assistance')

    assistance_requests = AssistanceRequest.objects.select_related('vehicle', 'customer__user', 'staff__user').filter(
        customer=customer
    ).exclude(
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('-created_at')

    return render(request, 'core/roadside_assistance.html', {
        'vehicles': vehicles,
        'assistance_requests': assistance_requests
    })

@never_cache
def staff_assistance_requests(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    if not request.user.staff_profile.is_approved or request.user.staff_profile.status != 'APPROVED':
        return redirect('staff_pending_approval')

    staff = request.user.staff_profile

    assistance_requests = AssistanceRequest.objects.select_related('vehicle', 'customer__user', 'staff__user').filter(
        Q(staff__isnull=True, status='PENDING') |
        Q(staff=staff, status__in=['ASSIGNED', 'ON_THE_WAY'])
    ).order_by('-created_at')

    return render(request, 'core/staff_assistance_requests.html', {
        'staff': staff,
        'assistance_requests': assistance_requests
    })

@never_cache
def staff_assistance_history(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    if not request.user.staff_profile.is_approved or request.user.staff_profile.status != 'APPROVED':
        return redirect('staff_pending_approval')

    staff = request.user.staff_profile

    assistance_history = AssistanceRequest.objects.select_related('vehicle', 'customer__user', 'staff__user').filter(
        staff=staff,
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('-updated_at')

    return render(request, 'core/staff_assistance_history.html', {
        'staff': staff,
        'assistance_history': page_for(request, assistance_history, 'assistance_history_page')
    })

@never_cache
@csrf_protect
@require_POST
@transaction.atomic
@approved_staff
def accept_assistance_request(request, assistance_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    assistance = get_object_or_404(
        AssistanceRequest.objects.select_for_update(),
        id=assistance_id,
        staff__isnull=True,
        status='PENDING'
    )

    if request.method == 'POST':
        assistance.staff = staff
        assistance.status = 'ASSIGNED'
        assistance.save()

        Notification.objects.create(
            customer=assistance.customer,
            title='Roadside Assistance Accepted',
            assistance=assistance,
            message=(
                f'Your roadside assistance request for '
                f'{assistance.vehicle.registration_number} '
                f'has been accepted by staff.'
            ),
            notification_type='ASSISTANCE'
        )

    return redirect('staff_assistance_requests')

@never_cache
@csrf_protect
@require_POST
@transaction.atomic
@approved_staff
def update_assistance_status(request, assistance_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    assistance = get_object_or_404(
        AssistanceRequest.objects.select_for_update(),
        id=assistance_id,
        staff=staff
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')

        allowed_statuses = {
            'ASSIGNED': {'ON_THE_WAY', 'COMPLETED', 'CANCELLED'},
            'ON_THE_WAY': {'ON_THE_WAY', 'COMPLETED', 'CANCELLED'},
        }.get(assistance.status, set())
        if new_status not in allowed_statuses:
            return JsonResponse({'error': 'Invalid assistance status transition.'}, status=409)

        if new_status in allowed_statuses:
            old_status = assistance.status

            if new_status == 'ON_THE_WAY':
                staff_location_link = request.POST.get(
                    'staff_location_link',
                    ''
                ).strip()

                staff_lat_raw = request.POST.get('staff_latitude', '').strip()
                staff_lng_raw = request.POST.get('staff_longitude', '').strip()
                try:
                    link = location_url(staff_location_link)
                    lat, lng = coordinates(staff_lat_raw, staff_lng_raw)
                except ValidationError as exc:
                    messages.error(request, ' '.join(exc.messages))
                    return redirect('staff_assistance_requests')
                if link:
                    assistance.staff_location_link = link
                if lat is not None:
                    assistance.staff_latitude = lat
                    assistance.staff_longitude = lng
                    assistance.staff_last_updated = timezone.now()

                assistance.status = 'ON_THE_WAY'
                assistance.save()

                if old_status != 'ON_THE_WAY':
                    Notification.objects.create(
                        customer=assistance.customer,
                        title='Staff On The Way',
                        assistance=assistance,
                        message=(
                            f'Staff is on the way for your roadside assistance '
                            f'request for {assistance.vehicle.registration_number}. '
                            f'You can now track the staff location.'
                        ),
                        notification_type='ASSISTANCE'
                    )

            elif new_status == 'COMPLETED':
                assistance.status = 'COMPLETED'
                assistance.completed_at = timezone.now()
                assistance.save()

                if old_status != 'COMPLETED':
                    Notification.objects.create(
                        customer=assistance.customer,
                        title='Roadside Assistance Completed',
            assistance=assistance,
                        message=(
                            f'Your roadside assistance request for '
                            f'{assistance.vehicle.registration_number} '
                            f'has been completed.'
                        ),
                        notification_type='ASSISTANCE'
                    )

            elif new_status == 'CANCELLED':
                assistance.status = 'CANCELLED'
                assistance.completed_at = timezone.now()
                assistance.save()

                if old_status != 'CANCELLED':
                    Notification.objects.create(
                        customer=assistance.customer,
                        title='Roadside Assistance Cancelled',
            assistance=assistance,
                        message=(
                            f'Your roadside assistance request for '
                            f'{assistance.vehicle.registration_number} '
                            f'has been cancelled.'
                        ),
                        notification_type='ASSISTANCE'
                    )

    return redirect('staff_assistance_requests')

@never_cache
@csrf_protect
@require_POST
@transaction.atomic
def cancel_roadside_assistance(request, assistance_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    customer = request.user.customer_profile

    assistance = get_object_or_404(
        AssistanceRequest.objects.select_for_update(),
        id=assistance_id,
        customer=customer,
        status__in=['PENDING', 'ASSIGNED', 'ON_THE_WAY']
    )

    if request.method == 'POST':
        assistance.status = 'CANCELLED'
        assistance.completed_at = timezone.now()
        assistance.save()

        Notification.objects.create(
            customer=customer,
            title='Roadside Assistance Cancelled',
            assistance=assistance,
            message=(
                f'Your roadside assistance request for '
                f'{assistance.vehicle.registration_number} '
                f'has been cancelled.'
            ),
            notification_type='ASSISTANCE'
        )

    return redirect('roadside_assistance')

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    try:
        r_km = 6371.0
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        a = (
            math.sin(dlat / 2) ** 2 +
            math.cos(math.radians(float(lat1))) *
            math.cos(math.radians(float(lat2))) *
            math.sin(dlon / 2) ** 2
        )
        a = min(1.0, max(0.0, a))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(r_km * c, 2)
    except (ValueError, TypeError):
        return None

@never_cache
@csrf_protect
@require_POST
@transaction.atomic
@approved_staff
def update_staff_location(request, assistance_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if not hasattr(request.user, 'staff_profile'):
        return JsonResponse({'error': 'Staff permission required'}, status=403)

    staff = request.user.staff_profile

    assistance = get_object_or_404(
        AssistanceRequest.objects.select_for_update(),
        id=assistance_id,
        staff=staff
    )

    if assistance.status not in {'ASSIGNED', 'ON_THE_WAY'}:
        return JsonResponse({'error': 'Location sharing has ended.'}, status=409)
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        if not isinstance(data, dict):
            raise ValidationError('Expected a location object.')
        lat, lng = coordinates(
            data.get('latitude', data.get('lat')),
            data.get('longitude', data.get('lng')),
            required=True,
        )
    except (ValueError, UnicodeDecodeError, ValidationError):
        return JsonResponse({'error': 'Provide valid latitude and longitude.'}, status=400)

    assistance.staff_latitude = lat
    assistance.staff_longitude = lng
    assistance.staff_last_updated = timezone.now()
    assistance.save(update_fields=['staff_latitude', 'staff_longitude', 'staff_last_updated'])
    return JsonResponse({
        'status': 'success',
        'assistance_id': assistance.id,
        'staff_latitude': float(lat),
        'staff_longitude': float(lng),
        'staff_last_updated': assistance.staff_last_updated.isoformat(),
    })

@never_cache
def assistance_tracking_data(request, assistance_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    assistance = get_object_or_404(AssistanceRequest, id=assistance_id)

    is_customer = (
        hasattr(request.user, 'customer_profile') and
        assistance.customer == request.user.customer_profile
    )
    is_staff = (
        hasattr(request.user, 'staff_profile') and
        request.user.staff_profile.is_approved and request.user.staff_profile.status == 'APPROVED' and
        assistance.staff_id == request.user.staff_profile.pk
    )

    if not (is_customer or is_staff):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    cust_lat = (
        float(assistance.customer_latitude)
        if assistance.customer_latitude is not None else None
    )
    cust_lng = (
        float(assistance.customer_longitude)
        if assistance.customer_longitude is not None else None
    )
    staff_lat = (
        float(assistance.staff_latitude)
        if assistance.staff_latitude is not None else None
    )
    staff_lng = (
        float(assistance.staff_longitude)
        if assistance.staff_longitude is not None else None
    )

    distance_km = None
    if (
        cust_lat is not None and cust_lng is not None and
        staff_lat is not None and staff_lng is not None
    ):
        distance_km = calculate_haversine_distance(
            cust_lat, cust_lng, staff_lat, staff_lng
        )

    staff_name = None
    staff_phone = None
    if assistance.staff:
        staff_name = (
            assistance.staff.user.get_full_name() or
            assistance.staff.user.username
        )
        staff_phone = assistance.staff.phone

    customer_name = (
        assistance.customer.user.get_full_name() or
        assistance.customer.user.username
    )
    customer_phone = assistance.customer.phone

    return JsonResponse({
        'id': assistance.id,
        'status': assistance.status,
        'status_display': assistance.get_status_display(),
        'assistance_type': assistance.assistance_type,
        'problem_description': assistance.problem_description,
        'location_details': assistance.location_details,
        'location_link': assistance.safe_location_link,
        'customer_name': customer_name,
        'customer_phone': customer_phone,
        'customer_latitude': cust_lat,
        'customer_longitude': cust_lng,
        'staff_name': staff_name,
        'staff_phone': staff_phone,
        'staff_latitude': staff_lat,
        'staff_longitude': staff_lng,
        'staff_last_updated': (
            assistance.staff_last_updated.isoformat()
            if assistance.staff_last_updated else None
        ),
        'distance_km': distance_km,
        'vehicle': (
            f"{assistance.vehicle.registration_number} "
            f"({assistance.vehicle.brand} {assistance.vehicle.model})"
        )
    })
