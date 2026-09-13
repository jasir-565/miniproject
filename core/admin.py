from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import (
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
    readonly_fields = ('created_at', 'approved_at', 'approved_by')
    actions = ['approve_selected_staff', 'reject_selected_staff']

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
            status='REJECTED'
        )
        self.message_user(request, f"{updated} staff profile(s) marked as rejected.")


admin.site.register(CustomerProfile)
admin.site.register(Vehicle)
admin.site.register(ServiceBooking)
admin.site.register(ServiceRecord)
admin.site.register(AssistanceRequest)
admin.site.register(Notification)