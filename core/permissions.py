from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect


def approved_staff(view):
    """Guard the action itself, including sessions whose approval was revoked."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        staff = getattr(request.user, 'staff_profile', None)
        if not staff or not request.user.is_active:
            return JsonResponse({'error': 'Approved staff access required.'}, status=403)
        if not staff.is_approved or staff.status != 'APPROVED':
            return JsonResponse({'error': 'Your staff account is not approved.'}, status=403)
        return view(request, *args, **kwargs)
    return wrapped
