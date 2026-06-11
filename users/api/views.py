from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
)
from users.models import CustomUser
from users.utils import send_activation_email


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
        pass


class LogoutView(APIView):
    def post(self, request):
        pass


class PasswordResetView(APIView):
    def post(self, request):
        pass


class PasswordResetConfirmView(APIView):
    def post(self, request, uid, token):
        pass
