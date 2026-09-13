from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


def coordinates(latitude, longitude, *, required=False):
    missing_lat = latitude is None or latitude == ''
    missing_lng = longitude is None or longitude == ''
    if missing_lat and missing_lng and not required:
        return None, None
    if missing_lat or missing_lng:
        raise ValidationError('Provide both latitude and longitude.')
    try:
        lat, lng = Decimal(str(latitude)), Decimal(str(longitude))
        if not lat.is_finite() or not lng.is_finite():
            raise ValueError
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValueError
        return lat.quantize(Decimal('0.0000001')), lng.quantize(Decimal('0.0000001'))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError('Enter valid GPS coordinates.') from None


def location_url(value):
    if value:
        if len(value) > 200:
            raise ValidationError('Location link must be at most 200 characters.')
        URLValidator(schemes=['http', 'https'])(value)
    return value or None


def service_cost(value):
    return forms.DecimalField(
        min_value=0, max_digits=10, decimal_places=2,
    ).clean(value)


def vehicle_photo(upload):
    if upload.size > 10 * 1024 * 1024:
        raise ValidationError('Vehicle photo must be smaller than 10 MB.')
    upload = forms.ImageField().clean(upload)
    if upload.image.format not in {'JPEG', 'PNG', 'WEBP'}:
        raise ValidationError('Upload a JPEG, PNG, or WebP image.')
    if upload.image.width * upload.image.height > 25_000_000:
        raise ValidationError('Vehicle photo must not exceed 25 megapixels.')
    upload.seek(0)
    return upload
