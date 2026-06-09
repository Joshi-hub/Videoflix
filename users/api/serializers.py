from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from users.models import CustomUser


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'confirmed_password']

    def validate(self, data):
        if data['password'] != data['confirmed_password']:
            raise serializers.ValidationError({'confirmed_password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        validated_data.pop('confirmed_password')
        return CustomUser.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirmed_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password'] != data['confirmed_password']:
            raise serializers.ValidationError({'confirmed_password': 'Passwords do not match.'})
        return data
