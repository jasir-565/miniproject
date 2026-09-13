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
from .validation import coordinates, location_url, service_cost, vehicle_photo

from .models import (
    CustomerProfile,
    Vehicle,
    ServiceBooking,
    StaffProfile,
    Notification,
    AssistanceRequest,
    ServiceRecord,
)


def home(request):
    return render(request, 'core/home.html')


def redirect_user_by_role(user):
    if hasattr(user, 'staff_profile'):
        if not user.staff_profile.is_approved:
            return redirect('staff_pending_approval')
        return redirect('staff_dashboard')

    if hasattr(user, 'customer_profile'):
        return redirect('customer_dashboard')

    return redirect('home')


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
    if staff.is_approved:
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
    logout(request)
    return redirect('login')


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

    if not request.user.staff_profile.is_approved:
        return redirect('staff_pending_approval')

    staff = request.user.staff_profile

    active_bookings = ServiceBooking.objects.filter(
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
        'bookings': active_bookings,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'available_assistance_count': available_assistance_count,
        'my_active_assistance_count': my_active_assistance_count,
    })


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
            user__is_active=True
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
            staff=available_staff
        )

        Notification.objects.create(
            customer=customer,
            title='Service Booking Created',
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

    customer_bookings = ServiceBooking.objects.filter(
        customer=customer
    ).exclude(
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('-created_at')

    return render(request, 'core/my_bookings.html', {
        'bookings': customer_bookings
    })


@never_cache
@csrf_protect
@require_POST
@transaction.atomic
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
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')

        active_bookings = ServiceBooking.objects.filter(
            staff=staff
        ).exclude(
            status='COMPLETED'
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

        available_assistance_count = AssistanceRequest.objects.filter(
            staff__isnull=True,
            status='PENDING'
        ).count()

        my_active_assistance_count = AssistanceRequest.objects.filter(
            staff=staff
        ).exclude(
            status__in=['COMPLETED', 'CANCELLED']
        ).count()

        try:
            selected_datetime = datetime.strptime(
                f'{appointment_date} {appointment_time}',
                '%Y-%m-%d %H:%M'
            )

            selected_datetime = timezone.make_aware(
                selected_datetime,
                timezone.get_current_timezone()
            )

        except ValueError:
            return render(request, 'core/staff_dashboard.html', {
                'staff': staff,
                'bookings': active_bookings,
                'pending_count': pending_count,
                'confirmed_count': confirmed_count,
                'in_progress_count': in_progress_count,
                'completed_count': completed_count,
                'available_assistance_count': available_assistance_count,
                'my_active_assistance_count': my_active_assistance_count,
                'error': 'Invalid appointment date or time.'
            })

        if selected_datetime < timezone.now():
            return render(request, 'core/staff_dashboard.html', {
                'staff': staff,
                'bookings': active_bookings,
                'pending_count': pending_count,
                'confirmed_count': confirmed_count,
                'in_progress_count': in_progress_count,
                'completed_count': completed_count,
                'available_assistance_count': available_assistance_count,
                'my_active_assistance_count': my_active_assistance_count,
                'error': 'You cannot assign an appointment in the past.'
            })

        conflict = ServiceBooking.objects.filter(
            staff=staff,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status__in=['CONFIRMED', 'IN_PROGRESS']
        ).exclude(id=booking.id).exists()

        if conflict:
            return render(request, 'core/staff_dashboard.html', {
                'staff': staff,
                'bookings': active_bookings,
                'pending_count': pending_count,
                'confirmed_count': confirmed_count,
                'in_progress_count': in_progress_count,
                'completed_count': completed_count,
                'available_assistance_count': available_assistance_count,
                'my_active_assistance_count': my_active_assistance_count,
                'error': 'This appointment slot is already occupied.'
            })

        booking.appointment_date = appointment_date
        booking.appointment_time = appointment_time
        booking.status = 'CONFIRMED'
        booking.save()

        Notification.objects.create(
            customer=booking.customer,
            title='Service Appointment Confirmed',
            message=(
                f'Your service appointment for '
                f'{booking.vehicle.registration_number} '
                f'has been scheduled.'
            ),
            notification_type='SERVICE'
        )

    return redirect('staff_dashboard')


@never_cache
@csrf_protect
@require_POST
@transaction.atomic
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

        if new_status in allowed_statuses:
            old_status = booking.status

            booking.status = new_status
            booking.current_work = current_work
            booking.save()

            if new_status == 'IN_PROGRESS' and old_status != 'IN_PROGRESS':
                Notification.objects.create(
                    customer=booking.customer,
                    title='Service In Progress',
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
        'notifications': customer_notifications
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

    completed_services = ServiceBooking.objects.filter(
        customer=customer,
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('-updated_at')

    roadside_history = AssistanceRequest.objects.filter(
        customer=customer,
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('-updated_at')

    return render(request, 'core/service_history.html', {
        'completed_services': completed_services,
        'roadside_history': roadside_history
    })


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
            assistance_requests = AssistanceRequest.objects.filter(
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
            assistance_requests = AssistanceRequest.objects.filter(
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
            assistance_requests = AssistanceRequest.objects.filter(
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
            assistance_requests = AssistanceRequest.objects.filter(
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
            assistance_requests = AssistanceRequest.objects.filter(
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
            message=(
                f'Your roadside assistance request for '
                f'{assistance.vehicle.registration_number} '
                f'has been submitted successfully.'
            ),
            notification_type='ASSISTANCE'
        )

        return redirect('roadside_assistance')

    assistance_requests = AssistanceRequest.objects.filter(
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

    if not request.user.staff_profile.is_approved:
        return redirect('staff_pending_approval')

    staff = request.user.staff_profile

    assistance_requests = AssistanceRequest.objects.filter(
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

    if not request.user.staff_profile.is_approved:
        return redirect('staff_pending_approval')

    staff = request.user.staff_profile

    assistance_history = AssistanceRequest.objects.filter(
        staff=staff,
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('-updated_at')

    return render(request, 'core/staff_assistance_history.html', {
        'staff': staff,
        'assistance_history': assistance_history
    })


@never_cache
@csrf_protect
@require_POST
@transaction.atomic
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

    return redirect('staff_dashboard')


@never_cache
@csrf_protect
@require_POST
@transaction.atomic
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

        if old_status != 'COMPLETED':
            Notification.objects.create(
                customer=booking.customer,
                title='Service Completed',
                message=(
                    f'Your vehicle service for '
                    f'{booking.vehicle.registration_number} '
                    f'has been completed.'
                ),
                notification_type='SERVICE'
            )

    return redirect('staff_dashboard')


@never_cache
def staff_service_history(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    service_history = ServiceBooking.objects.filter(
        staff=staff,
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('-updated_at')

    return render(request, 'core/staff_service_history.html', {
        'staff': staff,
        'service_history': service_history
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

        Notification.objects.create(
            customer=customer,
            title='Service Booking Cancelled',
            message=(
                f'Your service booking for '
                f'{booking.vehicle.registration_number} '
                f'has been cancelled.'
            ),
            notification_type='SERVICE'
        )

    return redirect('my_bookings')


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
