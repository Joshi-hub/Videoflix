from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from users.models import CustomUser


class RegisterSerializer(serializers.ModelSerializer):
    """Validates registration input and creates an inactive user."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'confirmed_password']

    def validate(self, data):
        """Ensures both password fields match."""
        if data['password'] != data['confirmed_password']:
            raise serializers.ValidationError({'confirmed_password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        """Removes the confirmation field before passing data to create_user."""
        validated_data.pop('confirmed_password')
        return CustomUser.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """Validates login credentials."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class PasswordResetSerializer(serializers.Serializer):
    """Validates the email address for a password reset request."""

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Validates the new password and its confirmation for a password reset."""

    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        """Ensures both new password fields match."""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data
