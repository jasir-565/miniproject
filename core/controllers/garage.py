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
def vehicles(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    customer = request.user.customer_profile

    customer_vehicles = Vehicle.objects.filter(
        customer=customer
    ).order_by('-created_at')

    if request.method == 'POST':
        registration_number = request.POST.get(
            'registration_number',
            ''
        ).strip().upper()

        brand = request.POST.get(
            'brand',
            ''
        ).strip()

        model = request.POST.get(
            'model',
            ''
        ).strip()

        year_value = request.POST.get(
            'year',
            ''
        ).strip()

        if len(registration_number) < 5:
            return render(request, 'core/vehicles.html', {
                'vehicles': customer_vehicles,
                'error': 'Please enter a valid registration number.'
            })

        if len(brand) < 2:
            return render(request, 'core/vehicles.html', {
                'vehicles': customer_vehicles,
                'error': 'Please enter a valid vehicle brand.'
            })

        if len(model) < 1:
            return render(request, 'core/vehicles.html', {
                'vehicles': customer_vehicles,
                'error': 'Please enter a valid vehicle model.'
            })

        try:
            year = int(year_value)
        except ValueError:
            return render(request, 'core/vehicles.html', {
                'vehicles': customer_vehicles,
                'error': 'Please enter a valid vehicle year.'
            })

        current_year = timezone.now().year

        if year < 1980 or year > current_year + 1:
            return render(request, 'core/vehicles.html', {
                'vehicles': customer_vehicles,
                'error': 'Please enter a realistic vehicle year.'
            })

        if Vehicle.objects.filter(
            registration_number=registration_number
        ).exists():
            return render(request, 'core/vehicles.html', {
                'vehicles': customer_vehicles,
                'error': 'This vehicle registration number already exists.'
            })

        photo = request.FILES.get('photo')
        if photo:
            try:
                photo = vehicle_photo(photo)
            except ValidationError as exc:
                return render(request, 'core/vehicles.html', {
                    'vehicles': customer_vehicles,
                    'error': ' '.join(exc.messages)
                })

        new_vehicle = Vehicle.objects.create(
            customer=customer,
            registration_number=registration_number,
            brand=brand,
            model=model,
            year=year,
            photo=photo if photo else None
        )

        messages.success(request, f"Vehicle '{new_vehicle.registration_number}' was successfully registered!")
        return redirect('vehicles')

    return render(request, 'core/vehicles.html', {
        'vehicles': customer_vehicles
    })

@never_cache
@csrf_protect
@require_POST
def update_vehicle_photo(request, vehicle_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    vehicle = get_object_or_404(
        Vehicle,
        id=vehicle_id,
        customer=request.user.customer_profile
    )

    if request.method == 'POST':
        photo = request.FILES.get('photo')
        if not photo:
            messages.error(request, 'Please select an image file to upload.')
            return redirect('vehicles')

        try:
            photo = vehicle_photo(photo)
        except ValidationError as exc:
            messages.error(request, ' '.join(exc.messages))
            return redirect('vehicles')

        old_name = vehicle.photo.name
        storage = vehicle.photo.storage
        vehicle.photo = photo
        vehicle.save()
        if old_name and old_name != vehicle.photo.name:
            transaction.on_commit(lambda: storage.delete(old_name))

        messages.success(request, f"Photo for vehicle '{vehicle.registration_number}' was updated successfully!")

    return redirect('vehicles')

@never_cache
@csrf_protect
@require_POST
def delete_vehicle_photo(request, vehicle_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    vehicle = get_object_or_404(
        Vehicle,
        id=vehicle_id,
        customer=request.user.customer_profile
    )

    if request.method == 'POST':
        if vehicle.photo:
            vehicle.photo.delete(save=True)
            messages.success(request, f"Photo for vehicle '{vehicle.registration_number}' has been removed.")
        else:
            messages.info(request, f"Vehicle '{vehicle.registration_number}' does not have a photo.")

    return redirect('vehicles')
