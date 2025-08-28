from rest_framework import serializers
from . import models
import users.models
import users.serializers





class CategorySerializer(serializers.ModelSerializer):
    class Meta():
        model = models.Category
        fields = ['id', 'name', 'item_type', 'created_on']

class FriendSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.Friend
        fields = '__all__'


class FriendMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Friend
        fields = ['id', 'name']   


class FriendSuggestionSettingsSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.FriendSuggestionSettings
        fields = ['id', 'friend', 'phone_number', 'user', 'can_schedule', 'effort_required', 'priority_level', 'category_limit_formula']
    

class CategoryLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FriendSuggestionSettings
        fields = ['friend', 'user', 'category_limit_formula']


class FriendFavesSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.FriendFaves
        fields = '__all__'


class ImageSerializer(serializers.ModelSerializer):
    # Override the image field to return HTTPS URLs
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        # Get the image URL from the object
        image_url = obj.image.url
        
        # Check if the URL starts with "http://", if so, replace it with "https://"
        if image_url.startswith('http://'):
            image_url = image_url.replace('http://', 'https://')
        
        return image_url

    class Meta:
        model = models.Image
        fields = '__all__'


class LocationSerializer(serializers.ModelSerializer):
    friends = serializers.PrimaryKeyRelatedField(queryset=models.Friend.objects.all(), many=True)

    class Meta:
        model = models.Location
        fields = '__all__'

    def create(self, validated_data):
        friends_data = validated_data.pop('friends', [])
        location = models.Location.objects.create(**validated_data)
        location.friends.set(friends_data)
        return location

    def update(self, instance, validated_data):
        friends_data = validated_data.pop('friends', [])
        instance.friends.set(friends_data)
        return super().update(instance, validated_data)


class LocationParkingTypeChoicesSerializer(serializers.Serializer):
    type_choices = serializers.ListField(child=serializers.CharField())

    def to_representation(self, instance):
        return {'type_choices': [choice[0] for choice in models.Location.TYPE_CHOICES]}



class FriendAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FriendAddress
        fields = '__all__'

    def update(self, instance, validated_data):
        validated_data.pop('address', None)
        return super().update(instance, validated_data)
    

class ValidateOnlyLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Location
        fields = ['title', 'address', 'latitude', 'longitude', 'calculate_distances_only', 'validated_address']
        read_only_fields = ['calculate_distances_only']   

    def create(self, validated_data):
        validated_data['calculate_distances_only'] = True   
        return super().create(validated_data)


class NextMeetSerializer(serializers.ModelSerializer):
    
    class Meta():
        model = models.NextMeet
        fields = '__all__'


class FriendDashboardSerializer(serializers.ModelSerializer):
    suggestion_settings = FriendSuggestionSettingsSerializer(source='friend_suggestion_settings', read_only=True)
    friend_faves = serializers.SerializerMethodField()
    # friend_addresses = serializers.SerializerMethodField()

    friend_id = serializers.IntegerField(source='friend.id', read_only=True)
    name = serializers.CharField(source='friend.name')
    # first_name = serializers.CharField(source='friend.first_name')
    # last_name = serializers.CharField(source='friend.last_name') 
    first_meet_entered = serializers.DateField(source='friend.first_meet_entered')
    # previous_meet_type = serializers.CharField(source='previous.type', read_only=True)  

    class Meta:
        model = models.NextMeet
        fields = ['id', 'friend_id', 'date', 'name', 'first_meet_entered', 'days_since', 'days_since_words', 
                  'time_score', 'future_date_in_words', 'category_activations_left', 
                  'suggestion_settings', 'friend_faves']
                    # 'previous_meet_type'  taking out for now
                    # 'first_name', 'last_name',  # not in use (yet)
                    #'friend_addresses',  # getting through a separate fetch on front end
                

 

    def get_friend_faves(self, obj):
        friend = obj.friend
        try:
            friend_faves_instance = friend.friendfaves  # This is the correct reverse OneToOneField accessor
            return FriendFavesSerializer(friend_faves_instance).data
        except models.FriendFaves.DoesNotExist:
            return None
        
    # def get_friend_addresses(self, obj):
    #     addresses = getattr(obj.friend, 'addresses_cache', None) or obj.friend.addresses.all()
    #     return FriendAddressSerializer(addresses, many=True).data



class UpcomingMeetsSerializer(serializers.ModelSerializer):

    friend = FriendSerializer()

    friend_name = serializers.CharField(source='friend.name')
    thought_capsules_by_category = serializers.SerializerMethodField()

    active_categories = serializers.SerializerMethodField()
    inactive_categories = serializers.SerializerMethodField()
    
    class Meta():
        model = models.NextMeet
        fields = ['id', 'date', 'friend', 'days_since', 'days_since_words', 
                  'time_score', 'future_date_in_words', 'category_activations_left',
                  'active_categories', 'inactive_categories', 'thought_capsules_by_category', 'friend_name']

    def get_active_categories(self, obj):
        return [category.name for category in obj.active_categories.all()]

    def get_inactive_categories(self, obj):
        return [category.name for category in obj.inactive_categories.all()]
    
    def get_thought_capsules_by_category(self, obj):
        thought_capsules = models.ThoughtCapsulez.objects.filter(
            friend=obj.friend,
            user=obj.user
        )

        capsules_by_category = {}
        for capsule in thought_capsules:
            category_name = capsule.category.name
            capsule_info = {'id': capsule.id, 'capsule': capsule.capsule}  # Include capsule ID along with its title
            capsules_by_category.setdefault(category_name, []).append(capsule_info)
        return capsules_by_category


class UpcomingMeetsLightSerializer(serializers.ModelSerializer):

    friend = FriendMiniSerializer()

   # friend_name = serializers.CharField(source='friend.name')
    
    
    class Meta():
        model = models.NextMeet
        fields = ['id', 'date', 'friend', 'days_since', 'days_since_words', 
                  'time_score', 'future_date_in_words', 'void_count', 'last_voided_date',
                  'miss_count', 'last_missed_date'] #, 'friend_name']



class UpcomingMeetsAllSerializer(serializers.ModelSerializer):
    friend = FriendSerializer()
    friend_name = serializers.CharField(source='friend.name') 
    user = users.serializers.UserDetailSerializer()  

    class Meta:
        model = models.NextMeet
        fields = ['id', 'date', 'friend', 'friend_name', 'days_since', 'days_since_words',
                  'time_score', 'future_date_in_words', 'user'] 

      
class ThoughtCapsuleSerializer(serializers.ModelSerializer):
    user_category_name = serializers.CharField(source='user_category.name', read_only=True)
    class Meta:
        model = models.ThoughtCapsulez
        fields = ['id', 'friend', 'user', 'typed_category', 'category', 'user_category', 'user_category_name', 'capsule', 'created_on', 'updated_on', 'pre_added_to_hello']
    
    # may not need (?)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        friend_id = self.context.get('friend_id')
        if request and friend_id:
            self.fields['category'].queryset = models.Category.objects.filter(
                user=request.user,
                friend_id=friend_id
            )
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     friend_id = self.context.get('friend_id')
    #     if friend_id:
    #         self.fields['category'].queryset = models.Category.objects.filter(user=self.context['request'].user, friend_id=friend_id)


class CompletedThoughtCapsuleSerializer(serializers.ModelSerializer): 
    user_category_name = serializers.CharField(source='user_category.name', read_only=True)
    class Meta:
        model = models.CompletedThoughtCapsulez
        fields = ['id', 'original_id', 'friend', 'user', 'time_score', 'hello', 'capsule', 'user_category', 'user_category_original_name', 'user_category_name', 'created_on', 'updated_on']

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     friend_id = self.context.get('friend_id')
    #     if friend_id:
    #         self.fields['category'].queryset = models.Category.objects.filter(user=self.context['request'].user, friend_id=friend_id)


class ImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = models.Image
        fields = '__all__'

    def get_image(self, obj):
        return obj.image.url  

class ImageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Image
        fields = ['id', 'image', 'image_category', 'title', 'image_notes', 'friend', 'user','user_category', 'thought_capsule']




class ImagesByCategorySerializer(serializers.ModelSerializer):
    friend_name = serializers.CharField(source='friend.name')
    images_by_category = serializers.SerializerMethodField()

    class Meta:
        model = models.Image
        fields = ['id', 'friend', 'image_category', 'title', 'image_notes', 'friend_name', 'images_by_category']

    def get_images_by_category(self, obj):
        images = models.Image.objects.filter(
            friend=obj.friend,
            user=obj.user
        )

        images_by_category = {}
        for image in images:
            image_data = {
                'id': image.id,
                'image_url': image.image.url,
                'title': image.title,
                'image_notes': image.image_notes
            }
            category_name = image.image_category
            if category_name not in images_by_category:
                images_by_category[category_name] = []
            images_by_category[category_name].append(image_data)
        return images_by_category
    


class UpdatesTrackerSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.UpdatesTracker
        fields = '__all__'

class VoidedMeetLightSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.VoidedMeet
        fields = ['id', 'user', 
                    'date', 'past_date_in_words', 'manual_reset' ]


# class CombinedMeetLightSerializer(serializers.Serializer):
#     id = serializers.UUIDField()
#     user = serializers.PrimaryKeyRelatedField(read_only=True)
#     date = serializers.DateField()
#     past_date_in_words = serializers.CharField()

#     def to_representation(self, instance):
#         # This will call the property 'past_date_in_words' from both models
#         rep = super().to_representation(instance)
#         rep['past_date_in_words'] = instance.past_date_in_words
#         return rep


class PastMeetSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.PastMeet
        fields = ['id', 'friend', 'user', 'type','typed_location', 'location_name', 'location',
                    'date', 'additional_notes', 'past_date_in_words','thought_capsules_shared', 'delete_all_unshared_capsules', 'created_on', 'updated_on']



class PastMeetLightSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.PastMeet
        fields = ['id', 'user', 'type',
                    'date', 'past_date_in_words' ]





class PastMeetTypeChoicesSerializer(serializers.Serializer):
    type_choices = serializers.ListField(child=serializers.CharField())

    def to_representation(self, instance):
        return {'type_choices': [choice[0] for choice in models.PastMeet.TYPE_CHOICES]}



class FriendProfileSerializer(serializers.ModelSerializer):

    suggestion_settings = FriendSuggestionSettingsSerializer()
    next_meet = NextMeetSerializer()

    # Define a SerializerMethodField to get FriendFaves data
    friend_faves = serializers.SerializerMethodField()

    class Meta:
        model = models.Friend
        fields = ['id', 'name', 'first_name', 'last_name', 'first_meet_entered_in_words', 'next_meet', 'suggestion_settings', 'friend_faves']

    def get_friend_faves(self, obj):
        # Access the FriendFaves data related to the current Friend object
        friend_faves_instance = models.FriendFaves.objects.filter(friend=obj).first()
        if friend_faves_instance:
            # Serialize the FriendFaves instance
            serializer = FriendFavesSerializer(friend_faves_instance)
            return serializer.data
        else:
            return None