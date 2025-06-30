from . import models
from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.utils import timezone



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

class UserCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = models.UserCategory
        fields = ['id', 'user', 'name', 'thought_capsules', 'images', 'is_active', 'max_active', 'is_in_top_five', 'is_deletable', 'created_on', 'updated_on']

class UserSettingsSerializer(serializers.ModelSerializer):
    user_categories = serializers.SerializerMethodField()

    class Meta:
        model = models.UserSettings
        fields = [
            'receive_notifications', 'simplify_app_for_focus', 'language_preference',
            'large_text', 'high_contrast_mode', 'screen_reader',
            'manual_dark_mode', 'expo_push_token', 'user_categories'
        ]

    def get_user_categories(self, obj): 
        categories = obj.user.user_categories.all()  
        return UserCategorySerializer(categories, many=True).data


class BadRainbowzUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    settings = UserSettingsSerializer(required=False)
    user_categories = UserCategorySerializer(many=True, read_only=True, required=False)

    class Meta:
        model = models.BadRainbowzUser
        fields = ['user_categories', 'id', 'created_on', 'is_banned_user', 'is_subscribed_user', 'subscription_expiration_date', 'username', 'password', 'email', 'app_setup_complete', 'is_test_user', 'phone_number', 'addresses', 'profile', 'settings']
        extra_kwargs = {
            "password": {"write_only": True}, 
        }

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        settings_data = validated_data.pop('settings', {})
        user = models.BadRainbowzUser.objects.create_user(**validated_data)
        if profile_data:
            models.UserProfile.objects.create(user=user, **profile_data)
        if settings_data:
            models.UserSettings.objects.create(user=user, **settings_data)
        return user
    


class PasswordResetCodeValidationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    reset_code = serializers.CharField(max_length=6)

    def validate(self, data):
        email = data['email']
        reset_code = data['reset_code']

        try:
            user = models.BadRainbowzUser.objects.get(email=email)
        except models.BadRainbowzUser.DoesNotExist:
            raise serializers.ValidationError("Invalid email or reset code.")
 
        if user.password_reset_code != reset_code:
            raise serializers.ValidationError("Invalid reset code.")
        if not user.code_expires_at or user.code_expires_at < now():
            raise serializers.ValidationError("Reset code has expired.")

        return data
    
class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    reset_code = serializers.CharField(max_length=6)
    new_password = serializers.CharField()

    def validate(self, data):
        email = data['email']
        reset_code = data['reset_code']

        try:
            user = models.BadRainbowzUser.objects.get(email=email)
        except models.BadRainbowzUser.DoesNotExist:
            raise serializers.ValidationError("Invalid email or reset code.")

        # Check if the code is correct and not expired
        if user.password_reset_code != reset_code:
            raise serializers.ValidationError("Invalid reset code.")
        if not user.code_expires_at or user.code_expires_at < now():
            raise serializers.ValidationError("Reset code has expired.")

        return user

    def save(self, user, new_password):
        user.set_password(new_password)
        user.password_reset_code = None  # Clear the reset code
        user.code_expires_at = None
        user.save()



class UpdateSubscriptionSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = models.BadRainbowzUser
        fields = ['subscription_id', 'subscription_expiration_date', 'is_subscribed_user']
        extra_kwargs = {
            'subscription_id': {'required': False, 'allow_null': True},
            'subscription_expiration_date': {'required': False, 'allow_null': True},
            'is_subscribed_user': {'required': False},
        }

    def update(self, instance, validated_data):
        instance.update_subscription(
            subscription_id=validated_data.get('subscription_id', instance.subscription_id),
            expiration_date=validated_data.get('subscription_expiration_date', instance.subscription_expiration_date),
            is_subscribed=validated_data.get('is_subscribed_user', instance.is_subscribed_user),
        )
        return instance
    
    


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise ValidationError("Old password is incorrect.")
        return value

    def validate_new_password(self, value):
        if len(value) < 8:
            raise ValidationError("New password must be at least 8 characters long.")
        return value
    

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
