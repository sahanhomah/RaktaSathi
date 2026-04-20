import mimetypes

from django.conf import settings
from django.core.mail import EmailMessage

from donors.models import Donor
from .models import SmsNotification


def send_sms_notification(blood_request, donor: Donor, message: str) -> SmsNotification:
    """
    Stub SMS sender. Replace the body with a real gateway call (e.g. Sparrow SMS, Ncell, etc.).
    Currently records a demo entry so downstream functionality stays intact.
    """
    return SmsNotification.objects.create(
        phone=donor.phone,
        status='demo',
        gateway_response=f'DEMO: BloodBank -> {donor.phone}: {message}',
        blood_request=blood_request,
        donor=donor,
    )


def send_email_notification_to_donor(blood_request, donor: Donor, distance_km: float) -> bool:
    """Send an email alert for a nearby compatible blood request."""
    if donor.user_id is None:
        return False

    recipient_email = (donor.user.email or '').strip()
    if not recipient_email:
        return False

    subject = f'Urgent Blood Request Nearby ({blood_request.blood_group})'
    message = (
        f'Hello {donor.full_name},\n\n'
        f'A compatible blood request has been posted within {distance_km:.2f} km of your location.\n'
        f'Requester: {blood_request.requester_name}\n'
        f'Blood group needed: {blood_request.blood_group}\n'
        f'Urgency: {blood_request.get_urgency_display()}\n\n'
        'Please log in to RaktaSathi and check Incoming Requests if you are available to donate.\n\n'
        'Thank you for supporting emergency blood response.'
    )

    try:
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )

        if blood_request.prescription_image:
            prescription_name = blood_request.prescription_image.name
            try:
                mimetype, _ = mimetypes.guess_type(prescription_name)
                with blood_request.prescription_image.open('rb') as prescription_file:
                    email.attach(
                        filename=prescription_name.split('/')[-1],
                        content=prescription_file.read(),
                        mimetype=mimetype or 'application/octet-stream',
                    )
            except Exception:
                # Keep notification delivery working even if file read fails unexpectedly.
                pass

        email.send(fail_silently=False)
        return True
    except Exception:
        return False
