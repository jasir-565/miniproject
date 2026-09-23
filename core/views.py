"""Compatibility exports for existing URLs and integrations."""
from .models import Notification  # Shared manager used by transactional regression checks.
from .controllers.common import (
    home,
    redirect_user_by_role,
)
from .controllers.accounts import (
    register,
    staff_register,
    staff_pending_approval,
    user_login,
    user_logout,
)
from .controllers.dashboards import (
    customer_dashboard,
    staff_dashboard,
)
from .controllers.garage import (
    vehicles,
    update_vehicle_photo,
    delete_vehicle_photo,
)
from .controllers.workshop import (
    service_booking,
    my_bookings,
    assign_appointment,
    update_service_status,
    notifications,
    mark_notification_read,
    service_history,
    save_service_record,
    complete_service_with_record,
    staff_service_history,
    cancel_service_booking,
)
from .controllers.roadside import (
    roadside_assistance,
    staff_assistance_requests,
    staff_assistance_history,
    accept_assistance_request,
    update_assistance_status,
    cancel_roadside_assistance,
    calculate_haversine_distance,
    update_staff_location,
    assistance_tracking_data,
)
