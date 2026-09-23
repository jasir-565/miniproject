from datetime import datetime, timedelta, time
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import ServiceBooking, ServiceEvent, Invoice, InvoiceLine


def record_event(booking, actor, title, note=''):
    return ServiceEvent.objects.create(booking=booking, actor=actor, title=title, note=note, status=booking.status)


def validate_appointment(booking, date, start, duration):
    """Caller locks the technician before validating and writing the appointment."""
    starts = timezone.make_aware(datetime.combine(date, start))
    ends = starts + timedelta(minutes=duration)
    if starts <= timezone.now():
        raise ValidationError('Choose an appointment in the future.')
    opening = time.fromisoformat(settings.WORKSHOP_OPEN)
    closing = time.fromisoformat(settings.WORKSHOP_CLOSE)
    if date.weekday() not in settings.WORKSHOP_DAYS or start < opening or ends.date() != date or ends.time() > closing:
        raise ValidationError(f'Choose a slot within workshop hours ({settings.WORKSHOP_OPEN}–{settings.WORKSHOP_CLOSE}).')
    staff = booking.staff
    if not staff.available_for_work:
        raise ValidationError('This technician is unavailable for scheduling.')
    shifts = staff.shifts.all()
    if shifts.exists():
        shift = shifts.filter(weekday=date.weekday()).first()
        if not shift or start < shift.starts_at or ends.time() > shift.ends_at:
            raise ValidationError('The appointment must fit within the technician’s shift.')
    if staff.time_off.filter(starts_at__lt=ends, ends_at__gt=starts).exists():
        raise ValidationError('The technician is on leave during this appointment.')
    others = ServiceBooking.objects.filter(staff=staff, appointment_date=date, status__in=['CONFIRMED', 'IN_PROGRESS']).exclude(pk=booking.pk)
    for other in others:
        if other.appointment_time is None:
            continue
        other_start = timezone.make_aware(datetime.combine(date, other.appointment_time))
        if starts < other_start + timedelta(minutes=other.duration_minutes) and ends > other_start:
            raise ValidationError('This appointment overlaps another assigned job.')


def approved_estimate(booking):
    estimate = booking.estimates.order_by('-revision').first()
    if estimate and estimate.status != 'APPROVED':
        raise ValidationError('The customer must approve the latest estimate before work starts or is completed.')
    if booking.requires_estimate_approval and not estimate:
        raise ValidationError('Send an estimate and obtain customer approval before starting work.')
    return estimate


def issue_invoice(booking, amount):
    if Invoice.objects.filter(booking=booking).exists():
        raise ValidationError('A receipt has already been issued for this job.')
    estimate = approved_estimate(booking)
    if estimate and amount != estimate.total:
        raise ValidationError('The final total must match the approved estimate.')
    invoice = Invoice.objects.create(booking=booking, estimate=estimate,
        customer_name=booking.customer.user.get_full_name() or booking.customer.user.username,
        vehicle_label=f'{booking.vehicle.registration_number} · {booking.vehicle.brand} {booking.vehicle.model}', total=amount)
    if estimate:
        InvoiceLine.objects.bulk_create([InvoiceLine(invoice=invoice, kind=line.kind, description=line.description, quantity=line.quantity, unit_price=line.unit_price) for line in estimate.lines.all()])
    else:
        InvoiceLine.objects.create(invoice=invoice, kind='SERVICE', description='Service total (legacy booking)', quantity=1, unit_price=amount)
    return invoice
