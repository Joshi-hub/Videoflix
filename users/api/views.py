from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
)
from users.models import CustomUser
from users.utils import send_activation_email, send_password_reset_email


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'detail': 'Bitte überprüfe deine Eingaben und versuche es erneut.'}, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        token = default_token_generator.make_token(user)
        send_activation_email(user, token)
        return Response({'user': {'id': user.pk, 'email': user.email}, 'token': token}, status=status.HTTP_201_CREATED)


class ActivateView(APIView):
    def get(self, request, uid, token):
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response({'detail': 'Aktivierung fehlgeschlagen.'}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({'detail': 'Aktivierung fehlgeschlagen.'}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = True
        user.save()
        return Response({'message': 'Account successfully activated.'}, status=status.HTTP_200_OK)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'detail': 'Ungültige Eingabe.'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(
            request,
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response({'detail': 'Ungültige E-Mail-Adresse oder Passwort.'}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(user)
        jwt_settings = settings.SIMPLE_JWT

        response = Response(
            {'detail': 'Login successful', 'user': {'id': user.pk, 'username': user.email}},
            status=status.HTTP_200_OK,
        )
        response.set_cookie(
            key='access_token',
            value=str(refresh.access_token),
            max_age=int(jwt_settings['ACCESS_TOKEN_LIFETIME'].total_seconds()),
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
        )
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            max_age=int(jwt_settings['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
        )
        return response


class LogoutView(APIView):
    def post(self, request):
        raw_refresh = request.COOKIES.get('refresh_token')
        if not raw_refresh:
            return Response({'detail': 'Refresh-Token fehlt.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(raw_refresh)
            token.blacklist()
        except Exception:
            return Response({'detail': 'Ungültiger Refresh-Token.'}, status=status.HTTP_400_BAD_REQUEST)
        response = Response(
            {'detail': 'Logout successful! All tokens will be deleted. Refresh token is now invalid.'},
            status=status.HTTP_200_OK,
        )
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response


class TokenRefreshCookieView(APIView):
    def post(self, request):
        raw_refresh = request.COOKIES.get('refresh_token')
        if not raw_refresh:
            return Response({'detail': 'Refresh-Token fehlt.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            refresh = RefreshToken(raw_refresh)
            new_access = str(refresh.access_token)
        except (InvalidToken, TokenError):
            return Response({'detail': 'Ungültiger Refresh-Token.'}, status=status.HTTP_401_UNAUTHORIZED)
        jwt_settings = settings.SIMPLE_JWT
        response = Response({'detail': 'Token refreshed', 'access': new_access}, status=status.HTTP_200_OK)
        response.set_cookie(
            key='access_token',
            value=new_access,
            max_age=int(jwt_settings['ACCESS_TOKEN_LIFETIME'].total_seconds()),
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
        )
        return response


class PasswordResetView(APIView):
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'detail': 'Ungültige E-Mail-Adresse.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = CustomUser.objects.get(email=serializer.validated_data['email'])
            token = default_token_generator.make_token(user)
            send_password_reset_email(user, token)
        except CustomUser.DoesNotExist:
            pass
        return Response({'detail': 'An email has been sent to reset your password.'}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    def post(self, request, uid, token):
        pass
