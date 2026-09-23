from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


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
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )
    phone = models.CharField(max_length=15)
    designation = models.CharField(max_length=100)
    available_for_work = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_staff_profiles'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_status_display()})"


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
    photo = models.ImageField(upload_to='vehicle_photos/', null=True, blank=True)
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
    duration_minutes = models.PositiveIntegerField(default=60, validators=[MinValueValidator(15), MaxValueValidator(480)])
    requires_estimate_approval = models.BooleanField(default=False)

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
    customer_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    customer_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    staff_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    staff_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    staff_last_updated = models.DateTimeField(
        null=True,
        blank=True
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

    @property
    def safe_location_link(self):
        return self._safe_link(self.location_link)

    @property
    def safe_staff_location_link(self):
        return self._safe_link(self.staff_location_link)

    @staticmethod
    def _safe_link(value):
        from django.core.exceptions import ValidationError
        from .validation import location_url
        try:
            return location_url(value)
        except ValidationError:
            return None


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
    booking = models.ForeignKey(ServiceBooking, null=True, blank=True, on_delete=models.SET_NULL)
    assistance = models.ForeignKey(AssistanceRequest, null=True, blank=True, on_delete=models.SET_NULL)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.user.username} - {self.title}"

    def get_absolute_url(self):
        from django.urls import reverse
        if self.booking_id:
            return reverse('booking_detail', args=[self.booking_id])
        if self.assistance_id:
            return reverse('roadside_assistance') + f'#request-{self.assistance_id}'
        return reverse('my_bookings') if self.notification_type == 'SERVICE' else reverse('roadside_assistance')


class ServiceEvent(models.Model):
    booking = models.ForeignKey(ServiceBooking, on_delete=models.CASCADE, related_name='events')
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=120)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']


class Estimate(models.Model):
    STATES = [(s, s.title()) for s in ('PENDING', 'APPROVED', 'REJECTED', 'SUPERSEDED')]
    booking = models.ForeignKey(ServiceBooking, on_delete=models.CASCADE, related_name='estimates')
    revision = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATES, default='PENDING')
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='+')
    decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-revision']
        constraints = [models.UniqueConstraint(fields=['booking', 'revision'], name='unique_estimate_revision')]

    @property
    def total(self):
        return sum((line.total for line in self.lines.all()), Decimal('0.00'))


class EstimateLine(models.Model):
    estimate = models.ForeignKey(Estimate, on_delete=models.CASCADE, related_name='lines')
    kind = models.CharField(max_length=10, choices=[('LABOUR', 'Labour'), ('PART', 'Part')])
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(1000)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    @property
    def total(self):
        return self.quantity * self.unit_price


class Invoice(models.Model):
    booking = models.OneToOneField(ServiceBooking, on_delete=models.PROTECT, related_name='invoice')
    estimate = models.ForeignKey(Estimate, null=True, on_delete=models.PROTECT)
    customer_name = models.CharField(max_length=200)
    vehicle_label = models.CharField(max_length=250)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    issued_at = models.DateTimeField(auto_now_add=True)

    @property
    def number(self):
        return f'AN-{self.pk:06d}'


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(max_length=200)
    kind = models.CharField(max_length=10)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total(self):
        return self.quantity * self.unit_price


class StaffShift(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='shifts')
    weekday = models.PositiveSmallIntegerField(choices=list(enumerate(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])))
    starts_at = models.TimeField()
    ends_at = models.TimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['staff', 'weekday'], name='one_shift_per_weekday'), models.CheckConstraint(condition=models.Q(ends_at__gt=models.F('starts_at')), name='shift_end_after_start')]


class StaffTimeOff(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='time_off')
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(ends_at__gt=models.F('starts_at')), name='leave_end_after_start')]
