"""
Password Setup Token Utilities for CampusOS Auth Service.
Provides cryptographic, time-limited, single-use tokens using Django's default_token_generator.
"""

from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from .models import CustomUser


def generate_setup_token(user):
    """
    Generates a secure, time-limited, single-use URL-safe UID and token for initial password setup.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token


def get_user_from_uid(uidb64):
    """
    Decodes the URL-safe base64 UID and retrieves the corresponding CustomUser.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.filter(pk=uid).first()
        return user
    except (TypeError, ValueError, OverflowError):
        return None


def verify_setup_token(uidb64, token):
    """
    Verifies the setup token for the user specified by uidb64.
    Returns (is_valid: bool, user: CustomUser | None).
    """
    user = get_user_from_uid(uidb64)
    if user is None:
        return False, None
    is_valid = default_token_generator.check_token(user, token)
    return is_valid, user
