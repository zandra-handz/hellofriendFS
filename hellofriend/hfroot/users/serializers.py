from . import models
from rest_framework import serializers


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserProfile
        fields = ['first_name', 'last_name', 'date_of_birth', 'gender']

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserSettings
        fields = ['receive_notifications', 'language_preference', 'large_text', 'high_contrast_mode', 'screen_reader']




class BadRainbowzUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    settings = UserSettingsSerializer(required=False)

    class Meta:
        model = models.BadRainbowzUser
        fields = ['id', 'username', 'password', 'email', 'phone_number', 'addresses', 'profile', 'settings']
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        settings_data = validated_data.pop('settings', {})
        user = models.BadRainbowzUser.objects.create_user(**validated_data)
        if profile_data:
            models.UserProfile.objects.create(user=user, **profile_data)
        if settings_data:
            models.UserSettings.objects.create(user=user, **settings_data)
        return user

