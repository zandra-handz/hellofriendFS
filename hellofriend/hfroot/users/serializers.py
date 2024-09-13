from . import models
from rest_framework import serializers



class UserAddressSerializer(serializers.ModelSerializer):
 
    class Meta():
        model = models.UserAddress
        fields = '__all__'
        
    def update(self, instance, validated_data): 
        validated_data.pop('address', None)
        return super().update(instance, validated_data)



class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.UserProfile
        fields = ['first_name', 'last_name', 'date_of_birth', 'gender']



class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserSettings
        fields = ['receive_notifications', 'simplify_app_for_focus', 'language_preference', 'large_text', 'high_contrast_mode', 'screen_reader', 'manual_dark_mode', 'expo_push_token']




class BadRainbowzUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    settings = UserSettingsSerializer(required=False)

    class Meta:
        model = models.BadRainbowzUser
        fields = ['id', 'username', 'password', 'email', 'app_setup_complete', 'is_test_user', 'phone_number', 'addresses', 'profile', 'settings']
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
    

class UserDetailSerializer(serializers.ModelSerializer):
    expo_push_token = serializers.CharField(source='settings.expo_push_token', allow_blank=True, allow_null=True)

    class Meta:
        model = models.BadRainbowzUser
        fields = ['id', 'username', 'expo_push_token']


class AddAddressSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    address = serializers.CharField(max_length=255)

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BadRainbowzUser
        fields = ['addresses']  # Only include the address field

class BadRainbowzUserAddressSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer()

    class Meta:
        model = models.BadRainbowzUser
        fields = ['addresses']
