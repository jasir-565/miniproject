from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

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
        return redirect('staff_dashboard')

    if hasattr(user, 'customer_profile'):
        return redirect('customer_dashboard')

    return redirect('home')


@never_cache
@csrf_protect
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

        if len(password) < 6:
            return render(request, 'core/register.html', {
                'error': 'Password must contain at least 6 characters.'
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
            phone=phone
        )

        login(request, user)

        return redirect('customer_dashboard')

    return render(request, 'core/register.html')


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
def user_logout(request):
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
        customer=customer
    ).exclude(
        status='COMPLETED'
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

        Vehicle.objects.create(
            customer=customer,
            registration_number=registration_number,
            brand=brand,
            model=model,
            year=year
        )

        return redirect('vehicles')

    return render(request, 'core/vehicles.html', {
        'vehicles': customer_vehicles
    })


@never_cache
@csrf_protect
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

        available_staff = StaffProfile.objects.annotate(
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
def assign_appointment(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    booking = get_object_or_404(
        ServiceBooking,
        id=booking_id,
        staff=staff
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
def update_service_status(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    booking = get_object_or_404(
        ServiceBooking,
        id=booking_id,
        staff=staff
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')
        current_work = request.POST.get(
            'current_work',
            ''
        ).strip()

        allowed_statuses = [
            'CONFIRMED',
            'IN_PROGRESS',
            'CANCELLED',
        ]

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
            location_link=location_link or None
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
def accept_assistance_request(request, assistance_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    assistance = get_object_or_404(
        AssistanceRequest,
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
def update_assistance_status(request, assistance_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    assistance = get_object_or_404(
        AssistanceRequest,
        id=assistance_id,
        staff=staff
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')

        allowed_statuses = [
            'ON_THE_WAY',
            'COMPLETED',
            'CANCELLED',
        ]

        if new_status in allowed_statuses:
            old_status = assistance.status

            if new_status == 'ON_THE_WAY':
                staff_location_link = request.POST.get(
                    'staff_location_link',
                    ''
                ).strip()

                if not staff_location_link:
                    return redirect('staff_assistance_requests')

                assistance.staff_location_link = staff_location_link
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
def save_service_record(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    booking = get_object_or_404(
        ServiceBooking,
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
            service_cost = Decimal(service_cost_value)
        except InvalidOperation:
            service_cost = Decimal('0.00')

        if service_cost < 0:
            service_cost = Decimal('0.00')

        ServiceRecord.objects.update_or_create(
            booking=booking,
            defaults={
                'inspection_details': inspection_details,
                'repair_details': repair_details,
                'parts_replaced': parts_replaced,
                'service_cost': service_cost,
                'completed_at': booking.updated_at,
            }
        )

    return redirect('staff_dashboard')


@never_cache
@csrf_protect
def complete_service_with_record(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'staff_profile'):
        return redirect_user_by_role(request.user)

    staff = request.user.staff_profile

    booking = get_object_or_404(
        ServiceBooking,
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
            service_cost = Decimal(service_cost_value)
        except InvalidOperation:
            service_cost = Decimal('0.00')

        if service_cost < 0:
            service_cost = Decimal('0.00')

        ServiceRecord.objects.update_or_create(
            booking=booking,
            defaults={
                'inspection_details': inspection_details,
                'repair_details': repair_details,
                'parts_replaced': parts_replaced,
                'service_cost': service_cost,
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
def cancel_service_booking(request, booking_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    customer = request.user.customer_profile

    booking = get_object_or_404(
        ServiceBooking,
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
def cancel_roadside_assistance(request, assistance_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if not hasattr(request.user, 'customer_profile'):
        return redirect_user_by_role(request.user)

    customer = request.user.customer_profile

    assistance = get_object_or_404(
        AssistanceRequest,
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