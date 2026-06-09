import os
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def send_activation_email(user, token):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:4200')
    activation_link = f'{frontend_url}/activate/{uid}/{token}/'
    send_mail(
        subject='Activate your Videoflix account',
        message=f'Welcome to Videoflix!\n\nPlease activate your account:\n\n{activation_link}',
        from_email=os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@videoflix.com'),
        recipient_list=[user.email],
        fail_silently=False,
    )
