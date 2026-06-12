from django.urls import path
from .views import (
    RegisterView,
    ActivateView,
    LoginView,
    LogoutView,
    TokenRefreshCookieView,
    PasswordResetView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('activate/<str:uid>/<str:token>/', ActivateView.as_view(), name='activate'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshCookieView.as_view(), name='token-refresh'),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('password_confirm/<str:uidb64>/<str:token>/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
