from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
)
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
        pass


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
