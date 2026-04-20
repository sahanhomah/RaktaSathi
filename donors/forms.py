from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import Donor
from .utils import normalize_nepali_phone


User = get_user_model()


class DonorRegistrationForm(forms.ModelForm):
    email = forms.EmailField(label='Email')
    password1 = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(),
    )
    password2 = forms.CharField(
        label='Confirm password',
        strip=False,
        widget=forms.PasswordInput(),
    )

    class Meta:
        model = Donor
        fields = [
            'full_name',
            'phone',
            'blood_group',
            'latitude',
            'longitude',
            'is_available',
        ]
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': '+97798XXXXXXXX'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'is_available': forms.CheckboxInput(attrs={'class': 'toggle'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'full_name': 'Enter full name',
            'phone': '+97798XXXXXXXX',
            'email': 'name@example.com',
            'password1': 'Create password',
            'password2': 'Confirm password',
        }
        for name, field in self.fields.items():
            if name in ['latitude', 'longitude']:
                continue
            if name == 'is_available':
                field.widget.attrs.update({'class': 'form-check-input'})
                continue

            existing_class = field.widget.attrs.get('class', '')
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = f'{existing_class} form-select'.strip()
            else:
                field.widget.attrs['class'] = f'{existing_class} form-control'.strip()

            if name in placeholders:
                field.widget.attrs.setdefault('placeholder', placeholders[name])

    def clean_phone(self):
        phone = self.cleaned_data.get('phone') or ''
        normalized = normalize_nepali_phone(phone)
        if normalized:
            return normalized

        raise forms.ValidationError(
            'Enter a valid Nepali mobile number (example: 98XXXXXXXX or +97798XXXXXXXX).'
        )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        phone = cleaned_data.get('phone')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Passwords do not match.')

        if password1:
            try:
                validate_password(password1)
            except forms.ValidationError as exc:
                self.add_error('password1', exc)

        if phone and User.objects.filter(username=phone).exists():
            self.add_error('phone', 'An account with this phone number already exists.')

        if email and User.objects.filter(email__iexact=email).exists():
            self.add_error('email', 'An account with this email already exists.')

        return cleaned_data


class EmailOtpVerificationForm(forms.Form):
    otp = forms.CharField(label='Email OTP', max_length=6, min_length=6)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['otp'].widget.attrs.update(
            {
                'class': 'form-control form-control-lg text-center',
                'placeholder': 'Enter 6-digit OTP',
                'inputmode': 'numeric',
                'autocomplete': 'one-time-code',
            }
        )


class DonorLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Email or phone number',
        widget=forms.TextInput(attrs={'autofocus': True, 'placeholder': 'Email or phone number'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Email or phone number'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
