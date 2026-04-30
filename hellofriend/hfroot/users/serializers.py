import math

from . import models
from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.utils import timezone
from . import constants



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

class GeckoScoreStateSerializer(serializers.ModelSerializer):
    recharge_per_second = serializers.SerializerMethodField()
    streak_recharge_per_second = serializers.SerializerMethodField()
    step_fatigue_per_step = serializers.SerializerMethodField()
    streak_fatigue_multiplier = serializers.SerializerMethodField()
    surplus_cap = serializers.SerializerMethodField()
    personality_type_label = serializers.SerializerMethodField()
    memory_type_label = serializers.SerializerMethodField()
    active_hours_type_label = serializers.SerializerMethodField()
    story_type_label = serializers.SerializerMethodField()
    available_choices = serializers.SerializerMethodField()
    thresholds = serializers.SerializerMethodField()

    class Meta():
        model = models.GeckoScoreState
        fields = [
            'user', 'multiplier', 'expires_at', 'created_on', 'updated_on',
            'base_multiplier', 'energy', 'surplus_energy', 'energy_updated_at',
            'revives_at',
            'recharge_per_second', 'streak_recharge_per_second',
            'step_fatigue_per_step', 'streak_fatigue_multiplier', 'surplus_cap',
            'personality_type', 'personality_type_label',
            'memory_type', 'memory_type_label',
            'active_hours_type', 'active_hours_type_label',
            'story_type', 'story_type_label',
            'stamina', 'max_active_hours', 'max_duration_till_revival',
            'max_score_multiplier', 'max_streak_length_seconds',
            'active_hours', 'gecko_created_on',
            'available_choices', 'thresholds', 'use_game_type_capsules_only',

        ]
        read_only_fields = [
            'base_multiplier', 'energy', 'surplus_energy', 'energy_updated_at', 'revives_at',
            'personality_type', 'memory_type', 'active_hours_type', 'story_type',
            'stamina', 'max_active_hours', 'max_duration_till_revival',
            'max_score_multiplier', 'max_streak_length_seconds',
            'active_hours', 'gecko_created_on',
        ]

    def _get_recharge_per_second(self, obj):
        full_rest_hours = 24 - obj.max_active_hours
        return 1.0 / (full_rest_hours * 3600)

    def get_recharge_per_second(self, obj):
        return self._get_recharge_per_second(obj)

    def get_streak_recharge_per_second(self, obj):
        return self._get_recharge_per_second(obj) * 0.5

    def get_step_fatigue_per_step(self, obj):
        return constants.STEP_FATIGUE_PER_STEP

    def get_streak_fatigue_multiplier(self, obj):
        return constants.STREAK_FATIGUE_MULTIPLIER

    def get_surplus_cap(self, obj):
        return constants.SURPLUS_CAP

    def get_personality_type_label(self, obj):
        return obj.get_personality_type_display()

    def get_memory_type_label(self, obj):
        return obj.get_memory_type_display()

    def get_active_hours_type_label(self, obj):
        return obj.get_active_hours_type_display()

    def get_story_type_label(self, obj):
        return obj.get_story_type_display()

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



class GeckoScoreStateConfigsSerializer(serializers.ModelSerializer):
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
    local_hour = serializers.IntegerField(
        min_value=0, max_value=23, write_only=True, required=False
    )

    available_choices = serializers.SerializerMethodField()
    thresholds = serializers.SerializerMethodField()

    class Meta:
        model = models.GeckoScoreState
        fields = [
            'personality_type', 'personality_type_label',
            'memory_type', 'memory_type_label',
            'active_hours_type', 'active_hours_type_label',
            'active_hours',
            'story_type', 'story_type_label',
            'available_choices',
            'thresholds',
            'local_hour',
            'max_duration_till_revival',
            'use_game_type_capsules_only',
            'created_on', 'updated_on',
          
        ]
        read_only_fields = ['created_on', 'stamina', 'updated_on']

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

    def validate(self, attrs):
        changing_hours = (
            'active_hours' in attrs
            or ('active_hours_type' in attrs and self.instance is not None
                and attrs['active_hours_type'] != self.instance.active_hours_type)
        )
        if changing_hours and self.instance is not None:
            self.instance.recompute_energy()
            # if self.instance.energy < 1.0:
            #     raise serializers.ValidationError(
            #         {'active_hours': 'Gecko must be fully rested to change active hours.'}
            #     )

        mode = attrs.get(
            'active_hours_type',
            getattr(self.instance, 'active_hours_type', None),
        )

        local_hour = attrs.get('local_hour')
        if local_hour is None:
            local_hour = self.context.get('local_hour')
        if local_hour is None:
            local_hour = timezone.now().hour

        max_hours = getattr(self.instance, 'max_active_hours', None) \
            or models.GeckoScoreState._meta.get_field('max_active_hours').default

        mode_changed = (
            self.instance is not None
            and 'active_hours_type' in attrs
            and attrs['active_hours_type'] != self.instance.active_hours_type
        )

        if 'active_hours' in attrs:
            hours = attrs['active_hours']
        elif self.instance is None:
            hours = self._defaults_for_mode(mode, max_hours)
        elif mode_changed:
            existing = list(self.instance.active_hours or [])
            if existing and self._hours_error(existing, mode, max_hours) is None:
                hours = existing
            else:
                hours = self._defaults_for_mode(mode, max_hours)
        else:
            hours = None

        if hours is not None:
            error = self._hours_error(hours, mode, max_hours)
            if error:
                raise serializers.ValidationError({'active_hours': error})
            attrs['active_hours'] = list(dict.fromkeys(hours))

        attrs.pop('local_hour', None)
        return attrs

    def _defaults_for_mode(self, mode, max_hours):
        n = min(max(int(max_hours), 0), 24)
        if mode == models.ActivityHours.DAY:
            start = 12 - n // 2
            return [(start + i) % 24 for i in range(n)]
        if mode == models.ActivityHours.NIGHT:
            start = (0 - n // 2) % 24
            return [(start + i) % 24 for i in range(n)]
        if mode == models.ActivityHours.RANDOM:
            if n == 0:
                return []
            step = 24 / n
            return sorted({int(round(i * step)) % 24 for i in range(n)})
        return []

    def _hours_error(self, hours, mode, max_hours):
        if len(hours) != len(set(hours)):
            return 'Hours must be unique.'
        if len(hours) > max_hours:
            return f'Cannot exceed {max_hours} active hours.'

        if mode in (models.ActivityHours.DAY, models.ActivityHours.NIGHT):
            if self._has_multiple_windows(hours):
                return 'Day/Night modes require a single contiguous block.'
            if hours:
                center = self._circular_center(hours)
                d_noon = self._circular_distance(center, 12)
                d_midnight = self._circular_distance(center, 0)
                if mode == models.ActivityHours.DAY and d_noon > d_midnight:
                    return 'Day mode requires the block to be centered closer to noon than midnight.'
                if mode == models.ActivityHours.NIGHT and d_midnight > d_noon:
                    return 'Night mode requires the block to be centered closer to midnight than noon.'
        elif mode == models.ActivityHours.RANDOM:
            return None
        else:
            if self._has_multiple_windows(hours):
                return 'This mode requires a single contiguous block.'
        return None

    @staticmethod
    def _circular_center(hours):
        angles = [h * (2 * math.pi / 24) for h in hours]
        mean_sin = sum(math.sin(a) for a in angles) / len(angles)
        mean_cos = sum(math.cos(a) for a in angles) / len(angles)
        mean_angle = math.atan2(mean_sin, mean_cos)
        if mean_angle < 0:
            mean_angle += 2 * math.pi
        return mean_angle * 24 / (2 * math.pi)

    @staticmethod
    def _circular_distance(a, b):
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
    gecko_game_types = serializers.SerializerMethodField()

    def get_pinned_friend_name(self, obj):
        return obj.pinned_friend.name if obj.pinned_friend else None

    def get_upcoming_friend_name(self, obj):
        return obj.upcoming_friend.name if obj.upcoming_friend else None

    def get_new_friend_name(self, obj):
        return obj.new_friend.name if obj.new_friend else None

    def get_gecko_game_types(self, obj):
        # static catalog built once at import; in-function import to avoid circular import with friends.models
        from friends.models import GECKO_GAME_TYPE_CATALOG
        return GECKO_GAME_TYPE_CATALOG

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
            'updated_on',
            'gecko_game_types',
        ]
        read_only_fields = ['id', 'user', 'updated_on', 'created_on', 'pinned_friend_name', 'upcoming_friend_name', 'new_friend_name', 'gecko_game_types']
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
        fields = ['id', 'friend', 'amount', 'reason', 'timestamp_earned', 'updated_on', 'created_on']


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


class GeckoEnergyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GeckoEnergyLog
        fields = ['id', 'energy', 'surplus_energy', 'steps', 'total_steps', 'friend', 'recorded_at']


class GeckoEnergyLogAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GeckoEnergyLog
        fields = ['id', 'user', 'energy', 'surplus_energy', 'steps', 'total_steps', 'friend', 'recorded_at']


class GeckoEnergySyncSampleSerializer(serializers.ModelSerializer):
    client_window_seconds = serializers.SerializerMethodField()

    def get_client_window_seconds(self, obj):
        if obj.client_started_on and obj.client_ended_on:
            return (obj.client_ended_on - obj.client_started_on).total_seconds()
        return None

    class Meta:
        model = models.GeckoEnergySyncSample
        fields = [
            'id',
            'created_at',
            'trigger',

            'client_energy',
            'client_surplus',
            'client_multiplier',
            'client_computed_at',
            'client_steps_in_payload',
            'client_distance_in_payload',
            'client_started_on',
            'client_ended_on',
            'client_window_seconds',
            'client_fatigue',
            'client_recharge',

            'server_energy_before',
            'server_energy_after',
            'server_surplus_before',
            'server_surplus_after',
            'server_updated_at_before',
            'server_updated_at_after',

            'recompute_window_seconds',
            'recompute_active_seconds',
            'recompute_new_steps',
            'recompute_fatigue',
            'recompute_recharge',
            'recompute_net',

            'pending_entries_count',
            'pending_entries_in_window',
            'pending_entries_stale',
            'pending_total_steps_all',
            'pending_total_steps_in_window',

            'energy_delta',
            'phantom_steps',

            'multiplier_active',
            'streak_expires_at',

            'total_steps_all_time',
        ]


class GeckoEnergySyncSampleAnalyticsSerializer(GeckoEnergySyncSampleSerializer):
    class Meta(GeckoEnergySyncSampleSerializer.Meta):
        fields = ['user'] + GeckoEnergySyncSampleSerializer.Meta.fields


class UserFriendLiveSeshInviteSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)

    class Meta:
        model = models.UserFriendLiveSeshInvite
        fields = [
            'id', 'sender', 'recipient', 'sender_username', 'recipient_username',
            'created_on', 'updated_on', 'accepted_on', 'invite_expires_on',
        ]


class UserFriendCurrentLiveSeshSerializer(serializers.ModelSerializer):
    other_user_username = serializers.CharField(source='other_user.username', read_only=True)

    class Meta:
        model = models.UserFriendCurrentLiveSesh
        fields = [
            'id', 'user', 'is_host', 'other_user', 'other_user_username',
            'session_start', 'expires_at', 'gecko_play_mode', 'created_on', 'updated_on'
        ]


class UserFriendLiveSeshLogSerializer(serializers.ModelSerializer):
    host_username = serializers.CharField(source='host.username', read_only=True)
    guest_username = serializers.CharField(source='guest.username', read_only=True)

    class Meta:
        model = models.UserFriendLiveSeshLog
        fields = [
            'id', 'host', 'guest', 'host_username', 'guest_username',
            'start', 'end', 'created_on', 'updated_on',
        ]


class GeckoGameWinSerializer(serializers.ModelSerializer):
    user_won_from_username = serializers.CharField(source='user_won_from.username', read_only=True, default=None)
    friend_name = serializers.CharField(source='friend.name', read_only=True, default=None)

    class Meta:
        model = models.GeckoGameWin
        fields = [
            'id',
            'user',
            'user_won_from',
            'user_won_from_username',
            'friend',
            'friend_name',
            'original_capsule_id',
            'capsule',
            'gecko_game_type',
            'gecko_game_type_label',
            'won_by_matching',
            'matched_capsule_id',
            'pinned',
            'pin_priority',
            'created_on',
            'updated_on',
        ]
        read_only_fields = [
            'id',
            'user',
            'user_won_from_username',
            'friend_name',
            'gecko_game_type_label',
            'pin_priority',
            'created_on',
            'updated_on',
        ]


class GeckoGameWinPendingCapsuleSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    capsule = serializers.CharField()
    gecko_game_type = serializers.IntegerField()
    user_category_name = serializers.CharField(
        source='user_category.name', allow_null=True, default=None,
    )


class GeckoGameWinPendingSerializer(serializers.ModelSerializer):
    sender_capsule = GeckoGameWinPendingCapsuleSerializer(read_only=True)

    class Meta:
        model = models.GeckoGameWinPending
        fields = [
            'id',
            'user',
            'sender',
            'sender_capsule',
            'accepted_on',
            'expires_at',
            'created_on',
            'updated_on',
        ]
        read_only_fields = fields
