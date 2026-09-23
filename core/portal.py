from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from .forms import EstimateLineFormSet, EstimateNoteForm, ProfileForm
from .models import ServiceBooking, Estimate, EstimateLine, Invoice, Notification
from .permissions import approved_staff
from .services import record_event


def accessible_booking(request, pk, *, lock=False):
    qs = ServiceBooking.objects
    if lock:
        qs = qs.select_for_update()
    booking = get_object_or_404(qs, pk=pk)
    staff = getattr(request.user, 'staff_profile', None)
    customer = getattr(request.user, 'customer_profile', None)
    if customer and booking.customer_id == customer.pk:
        return booking
    if staff and staff.is_approved and staff.status == 'APPROVED' and booking.staff_id == staff.pk:
        return booking
    raise PermissionDenied


@never_cache
@login_required
def booking_detail(request, booking_id):
    booking = accessible_booking(request, booking_id)
    estimates = booking.estimates.prefetch_related('lines').all()
    latest = estimates.first()
    return render(request, 'core/booking_detail.html', {
        'booking': booking, 'events': booking.events.select_related('actor'),
        'estimates': estimates, 'estimate': latest,
        'is_owner': booking.customer.user_id == request.user.pk,
        'can_estimate': hasattr(request.user, 'staff_profile') and booking.status in ('PENDING', 'CONFIRMED'),
    })


@never_cache
@login_required
def customer_estimates(request):
    customer = getattr(request.user, 'customer_profile', None)
    if customer is None:
        raise PermissionDenied
    from django.db.models import OuterRef, Subquery
    from .pagination import page_for
    latest = Estimate.objects.filter(booking_id=OuterRef('booking_id')).order_by('-revision').values('pk')[:1]
    estimates = Estimate.objects.filter(booking__customer=customer, pk=Subquery(latest)).select_related('booking__vehicle').prefetch_related('lines').order_by('-created_at')
    pending_count = estimates.filter(status='PENDING', booking__status__in=['PENDING', 'CONFIRMED']).count()
    return render(request, 'core/customer_estimates.html', {'estimates': page_for(request, estimates), 'pending_count': pending_count})


@never_cache
@login_required
def estimate_detail(request, booking_id):
    booking = accessible_booking(request, booking_id)
    estimates = booking.estimates.prefetch_related('lines').all()
    estimate = estimates.first()
    return render(request, 'core/estimate_detail.html', {
        'booking': booking, 'estimate': estimate, 'estimates': estimates,
        'is_owner': booking.customer.user_id == request.user.pk,
        'can_decide': booking.customer.user_id == request.user.pk and booking.status in ('PENDING', 'CONFIRMED') and estimate is not None and estimate.status == 'PENDING',
    })


@never_cache
@approved_staff
@transaction.atomic
def estimate_create(request, booking_id):
    booking = accessible_booking(request, booking_id, lock=True)
    if booking.status not in ('PENDING', 'CONFIRMED'):
        messages.error(request, 'Estimates can only be revised before work starts.')
        return redirect('booking_detail', booking_id=booking.pk)
    previous = booking.estimates.first()
    formset = EstimateLineFormSet(request.POST or None, prefix='lines')
    note_form = EstimateNoteForm(request.POST or None)
    if request.method == 'POST' and formset.is_valid() and note_form.is_valid():
        rows = [form.cleaned_data for form in formset if form.cleaned_data and not form.cleaned_data.get('DELETE')]
        total = sum((row['quantity'] * row['unit_price'] for row in rows), Decimal('0.00'))
        if total > Decimal('99999999.99'):
            note_form.add_error(None, 'The estimate total must not exceed ₹99,999,999.99.')
        else:
            booking.estimates.filter(status__in=['PENDING', 'APPROVED']).update(status='SUPERSEDED')
            estimate = Estimate.objects.create(booking=booking, revision=(previous.revision + 1 if previous else 1), note=note_form.cleaned_data['note'], created_by=request.user)
            EstimateLine.objects.bulk_create([EstimateLine(estimate=estimate, kind=row['kind'], description=row['description'], quantity=row['quantity'], unit_price=row['unit_price']) for row in rows])
            booking.requires_estimate_approval = True
            booking.save(update_fields=['requires_estimate_approval', 'updated_at'])
            record_event(booking, request.user, f'Estimate {estimate.revision} sent', f'₹{total:.2f} · Awaiting customer approval')
            Notification.objects.create(customer=booking.customer, booking=booking, title='Please review your service estimate', message=f'Estimate {estimate.revision} totals ₹{total:.2f}. Review the itemized work before approving.', notification_type='SERVICE')
            messages.success(request, 'Estimate sent to the customer for approval.')
            return redirect('booking_detail', booking_id=booking.pk)
    return render(request, 'core/estimate_form.html', {'booking': booking, 'formset': formset, 'form': note_form})


@never_cache
@login_required
@require_POST
@transaction.atomic
def estimate_decide(request, estimate_id):
    candidate = get_object_or_404(Estimate, pk=estimate_id)
    booking = accessible_booking(request, candidate.booking_id, lock=True)
    if booking.customer.user_id != request.user.pk:
        raise PermissionDenied
    estimate = get_object_or_404(Estimate.objects.select_for_update(), pk=estimate_id)
    latest = booking.estimates.first()
    if estimate.status != 'PENDING' or latest.pk != estimate.pk or booking.status not in ('PENDING', 'CONFIRMED'):
        messages.error(request, 'This estimate is no longer awaiting a decision. Review the latest version.')
        return redirect('estimate_detail', booking_id=booking.pk)
    decision = request.POST.get('decision')
    if decision not in ('APPROVED', 'REJECTED'):
        return HttpResponseBadRequest('Choose approve or reject.')
    estimate.status = decision
    estimate.decided_by = request.user
    estimate.decided_at = timezone.now()
    estimate.save(update_fields=['status', 'decided_by', 'decided_at'])
    record_event(booking, request.user, f'Estimate {estimate.revision} {decision.lower()}', f'Total ₹{estimate.total:.2f}')
    Notification.objects.create(customer=booking.customer, booking=booking, title=f'Estimate {decision.lower()}', message='Your decision has been recorded and is visible to your technician.', notification_type='SERVICE')
    messages.success(request, 'Your estimate decision has been recorded.')
    return redirect('estimate_detail', booking_id=booking.pk)


@never_cache
@login_required
def invoice_detail(request, booking_id):
    booking = accessible_booking(request, booking_id)
    invoice = get_object_or_404(Invoice.objects.prefetch_related('lines'), booking=booking)
    return render(request, 'core/invoice.html', {'invoice': invoice, 'booking': booking})


@never_cache
@login_required
@transaction.atomic
def account_settings(request):
    profile = getattr(request.user, 'customer_profile', None) or getattr(request.user, 'staff_profile', None)
    if profile is None:
        raise PermissionDenied
    initial = {name: getattr(request.user, name) for name in ('first_name', 'last_name', 'email')}
    initial.update(phone=profile.phone, address=getattr(profile, 'address', ''), available_for_work=getattr(profile, 'available_for_work', False))
    form = ProfileForm(request.POST or None, user=request.user, initial=initial)
    if request.method == 'POST' and form.is_valid():
        for name in ('first_name', 'last_name', 'email'):
            setattr(request.user, name, form.cleaned_data[name])
        request.user.save(update_fields=['first_name', 'last_name', 'email'])
        profile.phone = form.cleaned_data['phone']
        if hasattr(profile, 'address'):
            profile.address = form.cleaned_data['address']
        if hasattr(profile, 'available_for_work'):
            profile.available_for_work = form.cleaned_data['available_for_work']
        profile.save()
        messages.success(request, 'Your account details have been updated.')
        return redirect('account_settings')
    return render(request, 'core/account_settings.html', {'form': form, 'profile': profile})


@never_cache
@approved_staff
def schedule(request):
    bookings = ServiceBooking.objects.filter(staff=request.user.staff_profile, appointment_date__gte=timezone.localdate(), status__in=['CONFIRMED', 'IN_PROGRESS']).select_related('vehicle', 'customer__user').order_by('appointment_date', 'appointment_time')
    from .pagination import page_for
    from django.conf import settings
    return render(request, 'core/schedule.html', {'bookings': page_for(request, bookings), 'staff': request.user.staff_profile, 'workshop_hours': f'{settings.WORKSHOP_OPEN}–{settings.WORKSHOP_CLOSE}', 'timezone_name': settings.TIME_ZONE})
