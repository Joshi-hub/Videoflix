import os
from django.conf import settings
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def send_activation_email(user, token):
    """Sends an account activation link to the user's email address."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:4200')
    activation_link = f'{frontend_url}/activate/{uid}/{token}/'
    send_mail(
        subject='Activate your Videoflix account',
        message=f'Please activate your account: {activation_link}',
        from_email=os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@videoflix.com'),
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_password_reset_email(user, token):
    """Sends a password reset link to the user's email address."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:4200')
    reset_link = f'{frontend_url}/password-reset-confirm/{uid}/{token}/'
    send_mail(
        subject='Reset your Videoflix password',
        message=f'Reset your password: {reset_link}',
        from_email=os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@videoflix.com'),
        recipient_list=[user.email],
        fail_silently=False,
    )


def set_access_cookie(response, access_token):
    """Attaches the access token as an HttpOnly cookie to the response."""
    jwt = settings.SIMPLE_JWT
    response.set_cookie(
        key='access_token', value=access_token,
        max_age=int(jwt['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        httponly=True, secure=not settings.DEBUG, samesite='Lax',
    )


def set_jwt_cookies(response, refresh):
    """Attaches both the access and refresh tokens as HttpOnly cookies to the response."""
    jwt = settings.SIMPLE_JWT
    set_access_cookie(response, str(refresh.access_token))
    response.set_cookie(
        key='refresh_token', value=str(refresh),
        max_age=int(jwt['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        httponly=True, secure=not settings.DEBUG, samesite='Lax',
    )
