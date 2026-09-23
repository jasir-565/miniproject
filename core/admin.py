from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import (
    StaffShift, StaffTimeOff, ServiceEvent, Estimate, EstimateLine, Invoice, InvoiceLine,
    CustomerProfile,
    StaffProfile,
    Vehicle,
    ServiceBooking,
    ServiceRecord,
    AssistanceRequest,
    Notification,
)


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'get_full_name',
        'phone',
        'designation',
        'status_badge',
        'created_at',
        'approved_at',
        'approved_by',
    )
    list_filter = ('status', 'is_approved', 'designation', 'created_at')
    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'phone',
        'designation',
    )
    readonly_fields = ('created_at', 'approved_at', 'approved_by', 'is_approved')
    actions = ['approve_selected_staff', 'reject_selected_staff']

    def save_model(self, request, obj, form, change):
        obj.is_approved = obj.status == 'APPROVED'
        if obj.is_approved and not obj.approved_at:
            obj.approved_at = timezone.now()
            obj.approved_by = request.user
        if not obj.is_approved:
            obj.approved_at = None
            obj.approved_by = None
        super().save_model(request, obj, form, change)

    @admin.display(description='Full Name')
    def get_full_name(self, obj):
        return obj.user.get_full_name() or '-'

    @admin.display(description='Status')
    def status_badge(self, obj):
        if obj.status == 'APPROVED':
            color = '#10b981'
            bg = 'rgba(16, 185, 129, 0.15)'
            label = 'Approved'
        elif obj.status == 'REJECTED':
            color = '#ef4444'
            bg = 'rgba(239, 68, 68, 0.15)'
            label = 'Rejected'
        else:
            color = '#f59e0b'
            bg = 'rgba(245, 158, 11, 0.15)'
            label = 'Pending Review'

        return format_html(
            '<span style="display:inline-flex; align-items:center; gap:6px; padding:3px 10px; '
            'border-radius:9999px; font-weight:600; font-size:11px; color:{}; background:{}; '
            'border:1px solid {};">'
            '<span style="width:6px; height:6px; border-radius:50%; background:{};"></span>{}'
            '</span>',
            color, bg, color, color, label
        )

    @admin.action(description='Approve selected staff members')
    def approve_selected_staff(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(
            is_approved=True,
            status='APPROVED',
            approved_at=now,
            approved_by=request.user
        )
        self.message_user(request, f"{updated} staff profile(s) approved successfully.")

    @admin.action(description='Reject selected staff members')
    def reject_selected_staff(self, request, queryset):
        updated = queryset.update(
            is_approved=False,
            status='REJECTED', approved_at=None, approved_by=None,
        )
        self.message_user(request, f"{updated} staff profile(s) marked as rejected.")


admin.site.register(CustomerProfile)
admin.site.register(Vehicle)
admin.site.register(ServiceBooking)
admin.site.register(ServiceRecord)
admin.site.register(AssistanceRequest)
admin.site.register(Notification)


@admin.register(StaffShift)
class StaffShiftAdmin(admin.ModelAdmin):
    list_display = ('staff', 'weekday', 'starts_at', 'ends_at')
    list_filter = ('staff', 'weekday')


@admin.register(StaffTimeOff)
class StaffTimeOffAdmin(admin.ModelAdmin):
    list_display = ('staff', 'starts_at', 'ends_at', 'reason')
    list_filter = ('staff',)


class AuditAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ServiceEvent)
class ServiceEventAdmin(AuditAdmin):
    list_display = ('booking', 'title', 'actor', 'created_at')
    list_select_related = ('booking', 'actor')


@admin.register(Estimate)
class EstimateAdmin(AuditAdmin):
    list_display = ('booking', 'revision', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(Invoice)
class InvoiceAdmin(AuditAdmin):
    list_display = ('number', 'customer_name', 'vehicle_label', 'total', 'issued_at')
    search_fields = ('customer_name', 'vehicle_label')
