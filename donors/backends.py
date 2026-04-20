from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .utils import normalize_nepali_phone


class EmailOrPhoneBackend(ModelBackend):
    """Authenticate users with email/password or phone(username)/password."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        identifier = username or kwargs.get(user_model.USERNAME_FIELD)

        if identifier is None or password is None:
            return None

        identifier = identifier.strip()
        user = None

        if '@' in identifier:
            user = user_model._default_manager.filter(email__iexact=identifier).order_by('id').first()
        else:
            normalized_phone = normalize_nepali_phone(identifier)
            candidates = [identifier]
            if normalized_phone and normalized_phone != identifier:
                candidates.append(normalized_phone)
            user = user_model._default_manager.filter(username__in=candidates).order_by('id').first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
