from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='customer_profile'
    )
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class StaffProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )
    phone = models.CharField(max_length=15)
    designation = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Vehicle(models.Model):
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='vehicles'
    )
    registration_number = models.CharField(max_length=20, unique=True)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.registration_number} - {self.brand} {self.model}"


class ServiceBooking(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='service_bookings'
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='service_bookings'
    )

    staff = models.ForeignKey(
        StaffProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_bookings'
    )

    service_type = models.CharField(max_length=100)
    issue_description = models.TextField()
    current_work = models.CharField(
        max_length=255,
        blank=True
    )
    appointment_date = models.DateField(null=True, blank=True)
    appointment_time = models.TimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.vehicle.registration_number} - {self.service_type}"


class ServiceRecord(models.Model):
    booking = models.OneToOneField(
        ServiceBooking,
        on_delete=models.CASCADE,
        related_name='service_record'
    )

    inspection_details = models.TextField(blank=True)
    repair_details = models.TextField(blank=True)
    parts_replaced = models.TextField(blank=True)
    service_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Service Record - {self.booking.vehicle.registration_number}"


class AssistanceRequest(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ASSIGNED', 'Assigned'),
        ('ON_THE_WAY', 'On the Way'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='assistance_requests'
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='assistance_requests'
    )

    staff = models.ForeignKey(
        StaffProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assistance_requests'
    )

    assistance_type = models.CharField(max_length=100)
    problem_description = models.TextField()

    location_details = models.TextField()
    location_link = models.URLField(
        blank=True,
        null=True
    )
    staff_location_link = models.URLField(
    blank=True,
    null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.vehicle.registration_number} - {self.assistance_type}"


class Notification(models.Model):

    NOTIFICATION_TYPES = [
        ('SERVICE', 'Service'),
        ('ASSISTANCE', 'Assistance'),
        ('GENERAL', 'General'),
    ]

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    title = models.CharField(max_length=200)
    message = models.TextField()

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='GENERAL'
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.user.username} - {self.title}"
