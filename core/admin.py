from django.contrib import admin

# Register your models here.
from .models import (
    CustomerProfile,
    StaffProfile,
    Vehicle,
    ServiceBooking,
    ServiceRecord,
    AssistanceRequest,
    Notification,
)


admin.site.register(CustomerProfile)
admin.site.register(StaffProfile)
admin.site.register(Vehicle)
admin.site.register(ServiceBooking)
admin.site.register(ServiceRecord)
admin.site.register(AssistanceRequest)
admin.site.register(Notification)