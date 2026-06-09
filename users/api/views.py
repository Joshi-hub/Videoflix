from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
)


class RegisterView(APIView):
    def post(self, request):
        pass


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
