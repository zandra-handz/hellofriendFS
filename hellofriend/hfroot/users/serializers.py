from . import models
from rest_framework import serializers



class AddressSerializer(serializers.Serializer):
    title = serializers.CharField()
    address = serializers.CharField()

class UserProfileSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer(many=True)

    class Meta:
        model = models.UserProfile
        fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'addresses']

    def validate_correct_formatted_addresses(self, value):
        for address_data in value:
            if 'title' not in address_data or 'address' not in address_data:
                raise serializers.ValidationError("Address data must include 'title' and 'address' fields.")
        return value

    def update(self, instance, validated_data):
        # Update standard fields
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.date_of_birth = validated_data.get('date_of_birth', instance.date_of_birth)
        instance.gender = validated_data.get('gender', instance.gender)

        # Update addresses field
        addresses_data = validated_data.get('addresses', [])
        for address_data in addresses_data:
            title = address_data.get('title')
            address = address_data.get('address')
            instance.add_address({'title': title, 'address': address})

        # Save the instance
        instance.save()
        return instance


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserSettings
        fields = ['receive_notifications', 'language_preference', 'large_text', 'high_contrast_mode', 'screen_reader']




class BadRainbowzUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    settings = UserSettingsSerializer(required=False)

    class Meta:
        model = models.BadRainbowzUser
        fields = ['id', 'username', 'password', 'email', 'app_setup_complete', 'phone_number', 'addresses', 'profile', 'settings']
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
