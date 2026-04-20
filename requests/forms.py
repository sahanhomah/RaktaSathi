from django import forms
from django.conf import settings

from .models import BloodRequest


class BloodRequestForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'requester_name': 'Full name of requester',
            'requester_phone': '98XXXXXXXX',
        }
        for name, field in self.fields.items():
            if name in ['latitude', 'longitude']:
                continue

            existing_class = field.widget.attrs.get('class', '')
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = f'{existing_class} form-select'.strip()
            else:
                field.widget.attrs['class'] = f'{existing_class} form-control'.strip()
            if name in placeholders:
                field.widget.attrs.setdefault('placeholder', placeholders[name])

        max_bytes = int(getattr(settings, 'PRESCRIPTION_MAX_UPLOAD_BYTES', 5 * 1024 * 1024))
        max_size_mb = max_bytes / (1024 * 1024)
        self.fields['prescription_image'].help_text = (
            f'Upload doctor-prescribed document image (JPG/PNG, up to {max_size_mb:g} MB, paper with visible text).'
        )
        self.fields['prescription_image'].widget.attrs.update(
            {
                'accept': '.jpg,.jpeg,.png,image/jpeg,image/png',
                'data-max-bytes': str(max_bytes),
                'data-min-width': str(int(getattr(settings, 'PRESCRIPTION_DOC_MIN_WIDTH', 300))),
                'data-min-height': str(int(getattr(settings, 'PRESCRIPTION_DOC_MIN_HEIGHT', 300))),
                'data-min-bright-ratio': str(float(getattr(settings, 'PRESCRIPTION_DOC_MIN_BRIGHT_RATIO', 0.50))),
                'data-min-text-ratio': str(float(getattr(settings, 'PRESCRIPTION_DOC_MIN_TEXT_RATIO', 0.005))),
                'data-max-text-ratio': str(float(getattr(settings, 'PRESCRIPTION_DOC_MAX_TEXT_RATIO', 0.45))),
                'data-text-pixel-threshold': str(int(getattr(settings, 'PRESCRIPTION_DOC_TEXT_PIXEL_THRESHOLD', 140))),
                'data-min-edge-ratio': str(float(getattr(settings, 'PRESCRIPTION_DOC_MIN_EDGE_RATIO', 0.003))),
            }
        )

    class Meta:
        model = BloodRequest
        fields = [
            'requester_name',
            'requester_phone',
            'prescription_image',
            'blood_group',
            'latitude',
            'longitude',
            'urgency',
        ]
        widgets = {
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }
