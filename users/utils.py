from django.conf import settings
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken


def _get_activation_link(uid, token):
    """Returns the activation URL for the current environment (debug vs. production)."""
    if settings.DEBUG:
        return f'{settings.BACKEND_URL}/api/activate/{uid}/{token}/'
    return f'{settings.FRONTEND_URL}/activate/{uid}/{token}/'


def send_activation_email(user, token):
    """Sends an account activation link to the user's email address."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    send_mail(
        subject='Activate your Videoflix account',
        message=f'Please activate your account: {_get_activation_link(uid, token)}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_password_reset_email(user, token):
    """Sends a password reset link (always points to the frontend form) to the user."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_link = f'{settings.FRONTEND_URL}/password-reset-confirm/{uid}/{token}/'
    send_mail(
        subject='Reset your Videoflix password',
        message=f'Reset your password: {reset_link}',
        from_email=settings.DEFAULT_FROM_EMAIL,
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


def build_login_response(user):
    """Creates the login success response and sets JWT cookies."""
    refresh = RefreshToken.for_user(user)
    response = Response(
        {'detail': 'Login erfolgreich', 'user': {'id': user.pk, 'username': user.email}},
        status=status.HTTP_200_OK,
    )
    set_jwt_cookies(response, refresh)
    return response


def build_logout_response():
    """Creates the logout response and clears both JWT cookies."""
    response = Response(
        {'detail': 'Abmeldung erfolgreich! Alle Tokens werden gelöscht. Das Aktualisierungstoken ist jetzt ungültig.'},
        status=status.HTTP_200_OK,
    )
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response
