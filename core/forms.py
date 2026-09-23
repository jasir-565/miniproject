import re
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import EstimateLine


class AppointmentForm(forms.Form):
    appointment_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    appointment_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    duration_minutes = forms.IntegerField(min_value=15, max_value=480, initial=60)


class EstimateLineForm(forms.ModelForm):
    class Meta:
        model = EstimateLine
        fields = ['kind', 'description', 'quantity', 'unit_price']


EstimateLineFormSet = forms.formset_factory(EstimateLineForm, extra=3, min_num=1, max_num=20, validate_min=True, validate_max=True, can_delete=True)


class EstimateNoteForm(forms.Form):
    note = forms.CharField(required=False, max_length=2000, widget=forms.Textarea(attrs={'rows': 3}))


class ProfileForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()
    phone = forms.CharField(max_length=25)
    address = forms.CharField(required=False, max_length=2000, widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if hasattr(user, 'staff_profile'):
            self.fields.pop('address')
            self.fields['available_for_work'] = forms.BooleanField(required=False, label='Available for new assignments')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise ValidationError('This email address is already used by another account.')
        return email

    def clean_phone(self):
        phone = re.sub(r'\D', '', self.cleaned_data['phone'])
        if not 10 <= len(phone) <= 15:
            raise ValidationError('Enter a phone number with 10–15 digits.')
        return phone
