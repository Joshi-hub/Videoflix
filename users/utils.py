import os
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from django.core.mail import get_connection
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

_LOGO_PATH = os.path.join(os.path.dirname(__file__), 'templates', 'users', 'emails', 'logo.png')


def _send_with_logo(subject, text_body, html_body, to_email):
    root = MIMEMultipart('related')
    root['Subject'] = subject
    root['From'] = settings.DEFAULT_FROM_EMAIL
    root['To'] = to_email

    alt = MIMEMultipart('alternative')
    root.attach(alt)
    alt.attach(MIMEText(text_body, 'plain'))
    alt.attach(MIMEText(html_body, 'html'))

    with open(_LOGO_PATH, 'rb') as f:
        img = MIMEImage(f.read(), 'png')
    img.add_header('Content-ID', '<videoflix_logo>')
    img.add_header('Content-Disposition', 'inline', filename='logo.png')
    root.attach(img)

    conn = get_connection()
    conn.open()
    conn.connection.sendmail(settings.DEFAULT_FROM_EMAIL, [to_email], root.as_string())
    conn.close()


def send_activation_email(user, token):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    activation_link = f'{settings.FRONTEND_URL}/pages/auth/activate.html?uid={uid}&token={token}'
    html_body = render_to_string(
        'users/emails/activation_email.html',
        {'activation_link': activation_link, 'user_email': user.email},
    )
    _send_with_logo(
        subject='Confirm your email',
        text_body=f'Please activate your account: {activation_link}',
        html_body=html_body,
        to_email=user.email,
    )


def send_password_reset_email(user, token):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_link = f'{settings.FRONTEND_URL}/pages/auth/confirm_password.html?uid={uid}&token={token}'
    html_body = render_to_string(
        'users/emails/password_reset_email.html',
        {'reset_link': reset_link},
    )
    _send_with_logo(
        subject='Reset your Password',
        text_body=f'Reset your password: {reset_link}',
        html_body=html_body,
        to_email=user.email,
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
