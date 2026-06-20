from http.cookies import SimpleCookie
from unittest.mock import MagicMock

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.api.authentication import JWTCookieAuthentication
from users.api.serializers import (
    PasswordResetConfirmSerializer,
    RegisterSerializer,
)
from users.models import CustomUser
from users.utils import (
    send_activation_email,
    send_password_reset_email,
    set_access_cookie,
    set_jwt_cookies,
)

EMAIL_OVERRIDE = override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
)


def make_active_user(email='user@test.com', password='StrongPass123!'):
    user = CustomUser.objects.create_user(email=email, password=password)
    user.is_active = True
    user.save()
    return user


def make_uid_token(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token


# ---------------------------------------------------------------------------
# Model / Manager
# ---------------------------------------------------------------------------

class CustomUserManagerTest(TestCase):
    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(email='', password='pass')

    def test_create_user_defaults(self):
        user = CustomUser.objects.create_user(email='a@b.com', password='pass')
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_checks_password(self):
        user = CustomUser.objects.create_user(email='a@b.com', password='secret')
        self.assertTrue(user.check_password('secret'))

    def test_create_user_normalises_email(self):
        user = CustomUser.objects.create_user(email='A@EXAMPLE.COM', password='x')
        self.assertEqual(user.email, 'A@example.com')

    def test_create_superuser_flags(self):
        user = CustomUser.objects.create_superuser(email='sup@b.com', password='p')
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_str(self):
        user = CustomUser.objects.create_user(email='str@b.com', password='x')
        self.assertEqual(str(user), 'str@b.com')

    def test_email_unique(self):
        CustomUser.objects.create_user(email='dup@b.com', password='x')
        with self.assertRaises(Exception):
            CustomUser.objects.create_user(email='dup@b.com', password='y')


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class RegisterSerializerTest(TestCase):
    VALID = {'email': 'new@test.com', 'password': 'StrongPass123!', 'confirmed_password': 'StrongPass123!'}

    def test_valid_data(self):
        s = RegisterSerializer(data=self.VALID)
        self.assertTrue(s.is_valid(), s.errors)

    def test_password_mismatch(self):
        data = {**self.VALID, 'confirmed_password': 'Wrong123!'}
        s = RegisterSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn('confirmed_password', s.errors)

    def test_weak_password_rejected(self):
        data = {**self.VALID, 'password': '123', 'confirmed_password': '123'}
        s = RegisterSerializer(data=data)
        self.assertFalse(s.is_valid())

    def test_missing_email(self):
        data = {'password': 'StrongPass123!', 'confirmed_password': 'StrongPass123!'}
        s = RegisterSerializer(data=data)
        self.assertFalse(s.is_valid())

    def test_creates_inactive_user(self):
        s = RegisterSerializer(data=self.VALID)
        self.assertTrue(s.is_valid())
        user = s.save()
        self.assertFalse(user.is_active)
        self.assertEqual(user.email, 'new@test.com')

    def test_confirmed_password_not_in_output(self):
        s = RegisterSerializer(data=self.VALID)
        s.is_valid()
        user = s.save()
        self.assertNotIn('confirmed_password', RegisterSerializer(user).data)


class PasswordResetConfirmSerializerTest(TestCase):
    def test_valid(self):
        s = PasswordResetConfirmSerializer(
            data={'new_password': 'NewPass123!', 'confirm_password': 'NewPass123!'}
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_mismatch(self):
        s = PasswordResetConfirmSerializer(
            data={'new_password': 'NewPass123!', 'confirm_password': 'Other123!'}
        )
        self.assertFalse(s.is_valid())
        self.assertIn('confirm_password', s.errors)

    def test_weak_password(self):
        s = PasswordResetConfirmSerializer(
            data={'new_password': '123', 'confirm_password': '123'}
        )
        self.assertFalse(s.is_valid())


# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------

@EMAIL_OVERRIDE
class UsersUtilsTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email='u@test.com', password='x')

    def test_send_activation_email_sent(self):
        send_activation_email(self.user, 'tok')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('u@test.com', mail.outbox[0].to)
        self.assertIn('Confirm', mail.outbox[0].subject)

    def test_send_activation_email_contains_link(self):
        send_activation_email(self.user, 'mytoken')
        body = mail.outbox[0].body
        self.assertIn('mytoken', body)

    def test_send_password_reset_email_sent(self):
        send_password_reset_email(self.user, 'rtok')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Reset', mail.outbox[0].subject)

    def test_set_access_cookie_sets_key(self):
        response = Response()
        set_access_cookie(response, 'access-val')
        self.assertIn('access_token', response.cookies)
        self.assertEqual(response.cookies['access_token'].value, 'access-val')

    def test_set_jwt_cookies_sets_both(self):
        self.user.is_active = True
        self.user.save()
        refresh = RefreshToken.for_user(self.user)
        response = Response()
        set_jwt_cookies(response, refresh)
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)

    def test_activation_link_always_uses_frontend_url(self):
        with self.settings(DEBUG=True, FRONTEND_URL='http://myfrontend.com'):
            send_activation_email(self.user, 'tok')
        self.assertIn('myfrontend.com', mail.outbox[0].body)
        self.assertIn('/pages/auth/activate.html', mail.outbox[0].body)

    def test_activation_link_uses_frontend_url_in_production(self):
        with self.settings(DEBUG=False, FRONTEND_URL='http://myfrontend.com'):
            send_activation_email(self.user, 'tok')
        self.assertIn('myfrontend.com', mail.outbox[0].body)

    def test_reset_link_uses_frontend_url(self):
        with self.settings(FRONTEND_URL='http://myfrontend.com'):
            send_password_reset_email(self.user, 'tok')
        self.assertIn('myfrontend.com', mail.outbox[0].body)


# ---------------------------------------------------------------------------
# Authentication backend
# ---------------------------------------------------------------------------

class JWTCookieAuthenticationTest(TestCase):
    def setUp(self):
        self.user = make_active_user()
        self.auth = JWTCookieAuthentication()

    def _request_with_cookie(self, token):
        request = MagicMock()
        request.COOKIES = {'access_token': token}
        return request

    def test_valid_token_returns_user(self):
        token = str(RefreshToken.for_user(self.user).access_token)
        request = self._request_with_cookie(token)
        result = self.auth.authenticate(request)
        self.assertIsNotNone(result)
        self.assertEqual(result[0].pk, self.user.pk)

    def test_missing_cookie_returns_none(self):
        request = MagicMock()
        request.COOKIES = {}
        self.assertIsNone(self.auth.authenticate(request))

    def test_invalid_token_returns_none(self):
        request = self._request_with_cookie('not-a-token')
        self.assertIsNone(self.auth.authenticate(request))


# ---------------------------------------------------------------------------
# View helpers
# ---------------------------------------------------------------------------

def auth_client(client, user):
    refresh = RefreshToken.for_user(user)
    client.cookies = SimpleCookie({'access_token': str(refresh.access_token)})
    return client


# ---------------------------------------------------------------------------
# RegisterView
# ---------------------------------------------------------------------------

@EMAIL_OVERRIDE
class RegisterViewTest(APITestCase):
    URL = reverse('register')
    VALID = {'email': 'reg@test.com', 'password': 'StrongPass123!', 'confirmed_password': 'StrongPass123!'}

    def test_register_returns_201(self):
        r = self.client.post(self.URL, self.VALID, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_register_creates_inactive_user(self):
        self.client.post(self.URL, self.VALID, format='json')
        user = CustomUser.objects.get(email='reg@test.com')
        self.assertFalse(user.is_active)

    def test_register_sends_activation_email(self):
        self.client.post(self.URL, self.VALID, format='json')
        self.assertEqual(len(mail.outbox), 1)

    def test_register_returns_user_data(self):
        r = self.client.post(self.URL, self.VALID, format='json')
        self.assertIn('user', r.data)
        self.assertEqual(r.data['user']['email'], 'reg@test.com')

    def test_register_returns_activation_token(self):
        r = self.client.post(self.URL, self.VALID, format='json')
        self.assertIn('token', r.data)
        self.assertTrue(r.data['token'])

    def test_register_password_mismatch_returns_400(self):
        data = {**self.VALID, 'confirmed_password': 'Wrong123!'}
        r = self.client.post(self.URL, data, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email_returns_400(self):
        CustomUser.objects.create_user(email='reg@test.com', password='x')
        r = self.client.post(self.URL, self.VALID, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# ActivateView
# ---------------------------------------------------------------------------

class ActivateViewTest(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email='act@test.com', password='x')

    def _url(self, uid, token):
        return reverse('activate', args=[uid, token])

    def test_valid_activation(self):
        uid, token = make_uid_token(self.user)
        r = self.client.get(self._url(uid, token))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_invalid_token_returns_400(self):
        uid, _ = make_uid_token(self.user)
        r = self.client.get(self._url(uid, 'badtoken'))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_uid_returns_400(self):
        _, token = make_uid_token(self.user)
        r = self.client.get(self._url('invaliduid', token))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_user_returns_400(self):
        uid = urlsafe_base64_encode(force_bytes(99999))
        r = self.client.get(self._url(uid, 'tok'))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# LoginView
# ---------------------------------------------------------------------------

class LoginViewTest(APITestCase):
    URL = reverse('login')

    def setUp(self):
        self.user = make_active_user(email='login@test.com', password='StrongPass123!')

    def test_login_success_200(self):
        r = self.client.post(self.URL, {'email': 'login@test.com', 'password': 'StrongPass123!'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_login_sets_access_cookie(self):
        r = self.client.post(self.URL, {'email': 'login@test.com', 'password': 'StrongPass123!'}, format='json')
        self.assertIn('access_token', r.cookies)

    def test_login_sets_refresh_cookie(self):
        r = self.client.post(self.URL, {'email': 'login@test.com', 'password': 'StrongPass123!'}, format='json')
        self.assertIn('refresh_token', r.cookies)

    def test_login_wrong_password_400(self):
        r = self.client.post(self.URL, {'email': 'login@test.com', 'password': 'Wrong!'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_inactive_user_400(self):
        inactive = CustomUser.objects.create_user(email='inactive@test.com', password='StrongPass123!')
        r = self.client.post(self.URL, {'email': 'inactive@test.com', 'password': 'StrongPass123!'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_user_400(self):
        r = self.client.post(self.URL, {'email': 'nobody@test.com', 'password': 'x'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_fields_400(self):
        r = self.client.post(self.URL, {}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# LogoutView
# ---------------------------------------------------------------------------

class LogoutViewTest(APITestCase):
    URL = reverse('logout')

    def setUp(self):
        self.user = make_active_user()

    def _login(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies = SimpleCookie({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
        })

    def test_logout_success_200(self):
        self._login()
        r = self.client.post(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_logout_clears_cookies(self):
        self._login()
        r = self.client.post(self.URL)
        self.assertEqual(r.cookies.get('access_token', MagicMock()).value, '')
        self.assertEqual(r.cookies.get('refresh_token', MagicMock()).value, '')

    def test_logout_without_refresh_cookie_400(self):
        r = self.client.post(self.URL)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_invalid_refresh_token_400(self):
        self.client.cookies = SimpleCookie({'refresh_token': 'not-a-token'})
        r = self.client.post(self.URL)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# TokenRefreshCookieView
# ---------------------------------------------------------------------------

class TokenRefreshCookieViewTest(APITestCase):
    URL = reverse('token-refresh')

    def setUp(self):
        self.user = make_active_user()

    def test_refresh_returns_200(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies = SimpleCookie({'refresh_token': str(refresh)})
        r = self.client.post(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_refresh_sets_new_access_cookie(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies = SimpleCookie({'refresh_token': str(refresh)})
        r = self.client.post(self.URL)
        self.assertIn('access_token', r.cookies)

    def test_refresh_without_cookie_400(self):
        r = self.client.post(self.URL)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_invalid_token_401(self):
        self.client.cookies = SimpleCookie({'refresh_token': 'invalid'})
        r = self.client.post(self.URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# PasswordResetView
# ---------------------------------------------------------------------------

@EMAIL_OVERRIDE
class PasswordResetViewTest(APITestCase):
    URL = reverse('password-reset')

    def setUp(self):
        self.user = make_active_user(email='reset@test.com')

    def test_known_email_returns_200(self):
        r = self.client.post(self.URL, {'email': 'reset@test.com'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_known_email_sends_email(self):
        self.client.post(self.URL, {'email': 'reset@test.com'}, format='json')
        self.assertEqual(len(mail.outbox), 1)

    def test_unknown_email_still_returns_200(self):
        r = self.client.post(self.URL, {'email': 'nobody@test.com'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_unknown_email_sends_no_email(self):
        self.client.post(self.URL, {'email': 'nobody@test.com'}, format='json')
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_email_400(self):
        r = self.client.post(self.URL, {'email': 'not-an-email'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# PasswordResetConfirmView
# ---------------------------------------------------------------------------

class PasswordResetConfirmViewTest(APITestCase):
    def setUp(self):
        self.user = make_active_user(email='confirm@test.com', password='OldPass123!')

    def _url(self, uid, token):
        return reverse('password-reset-confirm', args=[uid, token])

    def test_valid_reset_returns_200(self):
        uid, token = make_uid_token(self.user)
        r = self.client.post(
            self._url(uid, token),
            {'new_password': 'NewPass456!', 'confirm_password': 'NewPass456!'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_password_actually_changed(self):
        uid, token = make_uid_token(self.user)
        self.client.post(
            self._url(uid, token),
            {'new_password': 'NewPass456!', 'confirm_password': 'NewPass456!'},
            format='json',
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass456!'))

    def test_invalid_token_400(self):
        uid, _ = make_uid_token(self.user)
        r = self.client.post(
            self._url(uid, 'badtoken'),
            {'new_password': 'NewPass456!', 'confirm_password': 'NewPass456!'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_uid_400(self):
        _, token = make_uid_token(self.user)
        r = self.client.post(
            self._url('invalid', token),
            {'new_password': 'NewPass456!', 'confirm_password': 'NewPass456!'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_mismatch_400(self):
        uid, token = make_uid_token(self.user)
        r = self.client.post(
            self._url(uid, token),
            {'new_password': 'NewPass456!', 'confirm_password': 'Different!'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
