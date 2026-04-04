import math

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
        fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'total_points']


class UserGeckoCombinedSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GeckoCombinedData
        fields = ['total_steps', 'total_distance', 'total_duration', 'total_gecko_points', 'updated_on']
# class UserCategorySerializer(serializers.ModelSerializer):

#     class Meta:
#         model = models.UserCategory
#         fields = ['id', 'user', 'name', 'description', 'thought_capsules', 'images', 'is_active', 'max_active', 'is_in_top_five', 'is_deletable', 'created_on', 'updated_on']


class GeckoCombinedDataSessionSerializer(serializers.ModelSerializer):
    class Meta():
        model = models.GeckoCombinedSession
        fields = ['id', 'friend', 'started_on', 'ended_on', 'steps', 'distance']



class GeckoConfigsSerializer(serializers.ModelSerializer):
    personality_type_label = serializers.CharField(source='get_personality_type_display', read_only=True)
    memory_type_label = serializers.CharField(source='get_memory_type_display', read_only=True)
    active_hours_type_label = serializers.CharField(source='get_active_hours_type_display', read_only=True)
    story_type_label = serializers.CharField(source='get_story_type_display', read_only=True)

    active_hours = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=23),
        max_length=24,
        allow_empty=True,
        required=False,
    )
    # frontend sends user's current local hour (0-23) per request — no stored tz
    local_hour = serializers.IntegerField(
        min_value=0, max_value=23, write_only=True, required=False
    )

    available_choices = serializers.SerializerMethodField()
    thresholds = serializers.SerializerMethodField()

    class Meta:
        model = models.GeckoConfigs
        fields = [
            'personality_type', 'personality_type_label',
            'memory_type', 'memory_type_label',
            'active_hours_type', 'active_hours_type_label',
            'active_hours',
            'story_type', 'story_type_label',
            'available_choices',
            'thresholds',
            'local_hour',
            'created_on', 'updated_on',
        ]
        read_only_fields = ['created_on', 'updated_on']

    def get_available_choices(self, obj):
        return {
            'personality_types': [{'value': v, 'label': l} for v, l in models.Personality.choices],
            'memory_types': [{'value': v, 'label': l} for v, l in models.Memory.choices],
            'active_hours_types': [{'value': v, 'label': l} for v, l in models.ActivityHours.choices],
            'story_types': [{'value': v, 'label': l} for v, l in models.Story.choices],
        }

    def get_thresholds(self, obj):
        return {
            'max_active_hours': obj.max_active_hours,
        }

    # Default hour sets per mode (all 12 hours, well under the 16 cap).
    DEFAULT_DAY_HOURS = list(range(6, 18))                         # 6am–5pm, noon-centered
    DEFAULT_NIGHT_HOURS = [18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5]  # 6pm–5am, midnight-centered
    DEFAULT_RANDOM_HOURS = list(range(0, 24, 2))                   # every other hour, evenly spread

    def validate(self, attrs):
        mode = attrs.get(
            'active_hours_type',
            getattr(self.instance, 'active_hours_type', None),
        )
        hours = attrs.get('active_hours')

        # local_hour: prefer payload, then view context, then server time
        local_hour = attrs.get('local_hour')
        if local_hour is None:
            local_hour = self.context.get('local_hour')
        if local_hour is None:
            local_hour = timezone.now().hour

        max_hours = getattr(self.instance, 'max_active_hours', None) \
            or models.GeckoConfigs._meta.get_field('max_active_hours').default

        # Apply defaults when hours weren't sent AND either this is a create
        # or the mode is changing to a new value.
        if hours is None:
            mode_changed = (
                self.instance is not None
                and 'active_hours_type' in attrs
                and attrs['active_hours_type'] != self.instance.active_hours_type
            )
            if self.instance is None or mode_changed:
                if mode == models.ActivityHours.DAY:
                    hours = list(self.DEFAULT_DAY_HOURS)
                elif mode == models.ActivityHours.NIGHT:
                    hours = list(self.DEFAULT_NIGHT_HOURS)
                elif mode == models.ActivityHours.RANDOM:
                    hours = list(self.DEFAULT_RANDOM_HOURS)
                if hours is not None:
                    attrs['active_hours'] = hours

        if hours is not None:
            if len(hours) != len(set(hours)):
                raise serializers.ValidationError(
                    {'active_hours': 'Hours must be unique.'}
                )
            if len(hours) > max_hours:
                raise serializers.ValidationError(
                    {'active_hours': f'Cannot exceed {max_hours} active hours.'}
                )

            if mode in (models.ActivityHours.DAY, models.ActivityHours.NIGHT):
                if self._has_multiple_windows(hours):
                    raise serializers.ValidationError(
                        {'active_hours': 'Day/Night modes require a single contiguous block.'}
                    )
                if hours:
                    center = self._circular_center(hours)
                    d_noon = self._circular_distance(center, 12)
                    d_midnight = self._circular_distance(center, 0)
                    if mode == models.ActivityHours.DAY and d_noon > d_midnight:
                        raise serializers.ValidationError(
                            {'active_hours': 'Day mode requires the block to be centered closer to noon than midnight.'}
                        )
                    if mode == models.ActivityHours.NIGHT and d_midnight > d_noon:
                        raise serializers.ValidationError(
                            {'active_hours': 'Night mode requires the block to be centered closer to midnight than noon.'}
                        )
            elif mode == models.ActivityHours.RANDOM:
                pass  # any hours, multiple blocks allowed — only the max cap applies
            else:
                if self._has_multiple_windows(hours):
                    raise serializers.ValidationError(
                        {'active_hours': 'This mode requires a single contiguous block.'}
                    )

            attrs['active_hours'] = sorted(set(hours))

        attrs.pop('local_hour', None)
        return attrs

    # --- helpers ---

    @staticmethod
    def _circular_center(hours):
        """Circular mean of hours on a 24-hour clock (float in [0, 24))."""
        angles = [h * (2 * math.pi / 24) for h in hours]
        mean_sin = sum(math.sin(a) for a in angles) / len(angles)
        mean_cos = sum(math.cos(a) for a in angles) / len(angles)
        mean_angle = math.atan2(mean_sin, mean_cos)
        if mean_angle < 0:
            mean_angle += 2 * math.pi
        return mean_angle * 24 / (2 * math.pi)

    @staticmethod
    def _circular_distance(a, b):
        """Shortest distance between two points on a 24-hour clock."""
        d = abs(a - b) % 24
        return min(d, 24 - d)

    @staticmethod
    def _has_multiple_windows(hours):
        if len(hours) <= 1:
            return False
        s = sorted(hours)
        gaps = sum(
            1 for i in range(len(s))
            if (s[(i + 1) % len(s)] - s[i]) % 24 != 1
        )
        return gaps > 1

class UserCategorySerializer(serializers.ModelSerializer):
    thought_capsules = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    images = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = models.UserCategory
        fields = ['id', 'user', 'name', 'description', 'thought_capsules', 'images', 'is_active', 'max_active', 'is_in_top_five', 'is_deletable', 'created_on', 'updated_on']
        read_only_fields = ['id', 'user', 'is_active', 'is_in_top_five', 'is_deletable', 'max_active', 'created_on', 'updated_on']

class UserCategoriesFriendHistorySerializer(serializers.ModelSerializer):
    completed_capsules = serializers.SerializerMethodField()

    class Meta:
        model = models.UserCategory
        fields = [
            'id',
            'name',
            'description',
            'created_on',
            'updated_on',
            'completed_capsules'
        ]

    def get_completed_capsules(self, obj):
        from friends.serializers import CompletedThoughtCapsuleSerializer
        friend_id = self.context.get('friend_id')
        capsules = getattr(obj, 'prefetched_capsules', [])

        # Only return capsules for this friend
        if friend_id:
            capsules = [c for c in capsules if c.friend_id == int(friend_id)]

        return CompletedThoughtCapsuleSerializer(capsules, many=True).data


# class UserCategoriesHistorySerializer(serializers.ModelSerializer):
#     completed_capsules = serializers.SerializerMethodField()

#     class Meta:
#         model = models.UserCategory
#         fields = [
#             'id',
#             'name',
#             'description',
#             'created_on',
#             'updated_on',
#             'completed_capsules'
#         ]

#     def get_completed_capsules(self, obj):
#         from friends.serializers import CompletedThoughtCapsuleSerializer
#         capsules = getattr(obj, "prefetched_capsules", [])
#         return CompletedThoughtCapsuleSerializer(capsules, many=True).data


class UserCategoriesHistorySerializer(serializers.ModelSerializer):
    completed_capsules = serializers.SerializerMethodField()

    class Meta:
        model = models.UserCategory
        fields = [
            'id',
            'name',
            'description',
            'created_on',
            'updated_on',
            'completed_capsules'
        ]

    def get_completed_capsules(self, obj):
        from friends.serializers import CompletedThoughtCapsuleSerializer
        friend_id = self.context.get('friend_id')

        capsules = getattr(obj, "prefetched_capsules", [])
        if friend_id:
            capsules = [c for c in capsules if str(c.friend_id) == str(friend_id)]

        return CompletedThoughtCapsuleSerializer(capsules, many=True).data
    

class UserCategoriesHistoryCountSerializer(serializers.ModelSerializer):
    # completed_capsules = serializers.SerializerMethodField()
    capsule_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.UserCategory
        fields = [
            'id',
            'name',
            'description',
            'created_on',
            'updated_on',
            'capsule_count',
        ]

    def get_completed_capsules(self, obj):
        from friends.serializers import CompletedThoughtCapsuleSerializer
        friend_id = self.context.get('friend_id')

        capsules = getattr(obj, "prefetched_capsules", [])
        if friend_id:
            capsules = [c for c in capsules if str(c.friend_id) == str(friend_id)]

        return CompletedThoughtCapsuleSerializer(capsules, many=True).data
    
class UserCategoriesHistoryCapsuleIdsSerializer(serializers.ModelSerializer):
    capsule_ids = serializers.SerializerMethodField()

    class Meta:
        model = models.UserCategory
        fields = [
            'id',
            'name',
            'description',
            'created_on',
            'updated_on',
            'capsule_ids',
        ]

    def get_capsule_ids(self, obj):
        # You assume that capsules were prefetched and attached as `prefetched_capsules`
        capsules = getattr(obj, "prefetched_capsules", [])
        friend_id = self.context.get('friend_id')

        if friend_id:
            capsules = [c for c in capsules if str(c.friend_id) == str(friend_id)]

        return [c.id for c in capsules]

class UserSettingsSerializer(serializers.ModelSerializer): 
    pinned_friend_name = serializers.SerializerMethodField()
    upcoming_friend_name = serializers.SerializerMethodField()

    new_friend_name = serializers.SerializerMethodField()

    def get_pinned_friend_name(self, obj):
        return obj.pinned_friend.name if obj.pinned_friend else None

    def get_upcoming_friend_name(self, obj):
        return obj.upcoming_friend.name if obj.upcoming_friend else None

    def get_new_friend_name(self, obj):
        return obj.new_friend.name if obj.new_friend else None

    def validate_user_default_category(self, value): 
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError("Default category must belong to the authenticated user.")
        return value

    class Meta:
        model = models.UserSettings
        fields = [
            'id',
            'user',
            'receive_notifications',
            'simplify_app_for_focus',
            'lock_in_next',
            'lock_in_custom_string',
            'language_preference',
            'large_text',
            'high_contrast_mode',
            'screen_reader',
            'manual_dark_mode',
            'expo_push_token',
            'user_default_category',
            'use_auto_select',
            'pinned_friend',
            'pinned_friend_name',
            'upcoming_friend',
            'upcoming_friend_name',
            'new_friend',
            'new_friend_name',
            'created_on',
            'updated_on'
        ]
        read_only_fields = ['id', 'user', 'updated_on', 'created_on', 'pinned_friend_name', 'upcoming_friend_name', 'new_friend_name']
    # class Meta:
    #     model = models.UserSettings
    #     fields = [
    #         'receive_notifications',
    #         'simplify_app_for_focus',
    #         'language_preference',
    #         'large_text',
    #         'high_contrast_mode',
    #         'screen_reader',
    #         'manual_dark_mode',
    #         'expo_push_token',
    #         'user_default_category',
 
    #     ]
 


# class BadRainbowzUserSerializer(serializers.ModelSerializer):
#     profile = UserProfileSerializer(required=False)
#     settings = UserSettingsSerializer(required=False)
#     user_categories = UserCategorySerializer(many=True, read_only=True, required=False)

#     class Meta:
#         model = models.BadRainbowzUser
#         fields = ['user_categories', 'id', 'created_on', 'is_banned_user', 'is_subscribed_user', 'subscription_expiration_date', 'username', 'password', 'email', 'app_setup_complete', 'is_test_user', 'phone_number', 'addresses', 'profile', 'settings']
#         extra_kwargs = {
#             "password": {"write_only": True}, 
#         }

#     def create(self, validated_data):
#         profile_data = validated_data.pop('profile', {})
#         settings_data = validated_data.pop('settings', {})
#         user = models.BadRainbowzUser.objects.create_user(**validated_data)
#         if profile_data:
#             models.UserProfile.objects.create(user=user, **profile_data)
#         if settings_data:
#             models.UserSettings.objects.create(user=user, **settings_data)
#         return user




class BadRainbowzUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    geckocombineddata = UserGeckoCombinedSerializer(required=False)

    class Meta:
        model = models.BadRainbowzUser
        fields = [
            'user_categories',
            'id', 'created_on', 'is_banned_user', 'is_subscribed_user', 'subscription_expiration_date',
            'username', 'password', 'email', 'app_setup_complete', 'is_test_user', 'phone_number', 'addresses',
            'profile', 'geckocombineddata',
        ]
        extra_kwargs = {"password": {"write_only": True}}

    # def get_user_categories(self, obj):
    #     # Use the prefetched cache if available
    #     categories = getattr(obj, '_prefetched_user_categories_cache', None)
    #     if categories is None:
    #         categories = obj.user_categories.all()
    #     return UserCategorySerializer(categories, many=True).data


class CreateBadRainbowzUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    
    #settings = UserSettingsSerializer(required=False)
    # user_categories = serializers.SerializerMethodField()

    class Meta:
        model = models.BadRainbowzUser
        fields = [ 
           
            'username', 'password', 'email', 'phone_number', 'addresses',
            'profile', '' #,  'settings'
        ]
        extra_kwargs = {"password": {"write_only": True}}


class CreateBadRainbowzUserSerializer(serializers.ModelSerializer):
  

    class Meta:
        model = models.BadRainbowzUser
        fields = ["username", "password", "email" ]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data): 
        password = validated_data.pop("password")

        # create_user calls save() internally, so your custom save() logic runs
        user = models.BadRainbowzUser.objects.create_user(
            password=password,
            **validated_data
        )

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
 
        from django.contrib.auth.hashers import check_password
        if not user.password_reset_code or not check_password(reset_code, user.password_reset_code):
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
        from django.contrib.auth.hashers import check_password
        if not user.password_reset_code or not check_password(reset_code, user.password_reset_code):
            raise serializers.ValidationError("Invalid reset code.")
        if not user.code_expires_at or user.code_expires_at < now():
            raise serializers.ValidationError("Reset code has expired.")

        return user

    def save(self, user, new_password):
        user.set_password(new_password)
        user.password_reset_code = None  # Clear the reset code
        user.code_expires_at = None
        user.save()

class GeckoPointsLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GeckoPointsLedger
        fields = ['id', 'friend', 'amount', 'reason', 'updated_on', 'created_on']


class PointsLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PointsLedger
        fields = ['id', 'amount', 'reason', 'created_at']

class AddGeckoPointsSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1) 


class AddPointsSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=100)

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
