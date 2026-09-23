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
def register(request):
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    if request.method == 'POST':
        username = request.POST.get(
            'username',
            ''
        ).strip()

        first_name = request.POST.get(
            'first_name',
            ''
        ).strip()

        last_name = request.POST.get(
            'last_name',
            ''
        ).strip()

        email = request.POST.get(
            'email',
            ''
        ).strip()

        phone = request.POST.get(
            'phone',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        confirm_password = request.POST.get(
            'confirm_password',
            ''
        )

        if len(username) < 4:
            return render(request, 'core/register.html', {
                'error': 'Username must contain at least 4 characters.'
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'core/register.html', {
                'error': 'Username already exists.'
            })

        if not first_name:
            return render(request, 'core/register.html', {
                'error': 'First name is required.'
            })

        if not last_name:
            return render(request, 'core/register.html', {
                'error': 'Last name is required.'
            })

        try:
            validate_email(email)
        except ValidationError:
            return render(request, 'core/register.html', {
                'error': 'Please enter a valid email address.'
            })

        if User.objects.filter(email=email).exists():
            return render(request, 'core/register.html', {
                'error': 'Email already exists.'
            })

        cleaned_phone = phone.replace(' ', '').replace('-', '')

        if cleaned_phone.startswith('+'):
            cleaned_phone = cleaned_phone[1:]

        if not cleaned_phone.isdigit():
            return render(request, 'core/register.html', {
                'error': 'Phone number should contain only numbers.'
            })

        if len(cleaned_phone) < 10 or len(cleaned_phone) > 15:
            return render(request, 'core/register.html', {
                'error': 'Phone number must contain 10 to 15 digits.'
            })

        try:
            candidate = User(username=username, first_name=first_name, last_name=last_name, email=email)
            candidate.full_clean(exclude=['password'])
            validate_password(password, candidate)
        except ValidationError as exc:
            return render(request, 'core/register.html', {
                'error': ' '.join(exc.messages)
            })

        if password != confirm_password:
            return render(request, 'core/register.html', {
                'error': 'Passwords do not match.'
            })

        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password
        )

        CustomerProfile.objects.create(
            user=user,
            phone=cleaned_phone
        )

        login(request, user)

        return redirect('customer_dashboard')

    return render(request, 'core/register.html')

@never_cache
@csrf_protect
@transaction.atomic
def staff_register(request):
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    designation_options = [
        'Master Technician',
        'Automotive Diagnostic Specialist',
        'Service Advisor & Estimator',
        'Mechanical Workshop Technician',
        'Auto Electrical & ECU Specialist',
        'Brake & Suspension Specialist',
        'Quick Lube & Detailing Technician',
    ]

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        designation = request.POST.get('designation', '').strip()
        custom_designation = request.POST.get('custom_designation', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if designation == 'OTHER' and custom_designation:
            final_designation = custom_designation
        else:
            final_designation = designation or 'Technician'

        context = {
            'designation_options': designation_options,
            'prev': {
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'designation': designation,
                'custom_designation': custom_designation,
            }
        }

        if len(username) < 4:
            context['error'] = 'Username must contain at least 4 characters.'
            return render(request, 'core/staff_register.html', context)

        if User.objects.filter(username=username).exists():
            context['error'] = 'Username already exists.'
            return render(request, 'core/staff_register.html', context)

        if not first_name:
            context['error'] = 'First name is required.'
            return render(request, 'core/staff_register.html', context)

        if not last_name:
            context['error'] = 'Last name is required.'
            return render(request, 'core/staff_register.html', context)

        try:
            validate_email(email)
        except ValidationError:
            context['error'] = 'Please enter a valid work email address.'
            return render(request, 'core/staff_register.html', context)

        if User.objects.filter(email=email).exists():
            context['error'] = 'An account with this email already exists.'
            return render(request, 'core/staff_register.html', context)

        cleaned_phone = phone.replace(' ', '').replace('-', '')
        if cleaned_phone.startswith('+'):
            cleaned_phone = cleaned_phone[1:]

        if not cleaned_phone.isdigit():
            context['error'] = 'Phone number should contain only numbers.'
            return render(request, 'core/staff_register.html', context)

        if len(cleaned_phone) < 10 or len(cleaned_phone) > 15:
            context['error'] = 'Phone number must contain 10 to 15 digits.'
            return render(request, 'core/staff_register.html', context)

        try:
            candidate = User(username=username, first_name=first_name, last_name=last_name, email=email)
            candidate.full_clean(exclude=['password'])
            validate_password(password, candidate)
        except ValidationError as exc:
            context['error'] = ' '.join(exc.messages)
            return render(request, 'core/staff_register.html', context)

        if password != confirm_password:
            context['error'] = 'Passwords do not match.'
            return render(request, 'core/staff_register.html', context)

        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password
        )

        StaffProfile.objects.create(
            user=user,
            phone=cleaned_phone,
            designation=final_designation,
            is_approved=False,
            status='PENDING'
        )

        login(request, user)
        messages.success(request, 'Your staff registration has been submitted and is currently pending administrator verification.')
        return redirect('staff_pending_approval')

    return render(request, 'core/staff_register.html', {
        'designation_options': designation_options
    })

@never_cache
def staff_pending_approval(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile
    if staff.is_approved and staff.status == 'APPROVED':
        return redirect('staff_dashboard')

    return render(request, 'core/staff_pending_approval.html', {
        'staff': staff
    })

@never_cache
@csrf_protect
def user_login(request):
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect_user_by_role(user)

        return render(request, 'core/login.html', {
            'error': 'Invalid username or password.'
        })

    return render(request, 'core/login.html')

@never_cache
@require_POST
def user_logout(request):
    logout(request)
    return redirect('login')
