from rest_framework import serializers
from . import models
import users.models
import users.serializers


 

class FriendSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.Friend
        fields = '__all__'


from rest_framework import serializers
from django.db.models import Count
from . import models

class FriendSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Friend
        fields = '__all__'


class ThoughtCapsuleSerializer(serializers.ModelSerializer):
    user_category_name = serializers.CharField(source='user_category.name', read_only=True)

    class Meta:
        model = models.ThoughtCapsulez
        fields = [
            'id',
            'friend',
            'user',
            'user_category',
            'user_category_name',
            'capsule',
            'created_on',
            'updated_on',
            'pre_added_to_hello'
        ]


class FriendAndCapsuleSummarySerializer(serializers.ModelSerializer):
    capsule_count = serializers.SerializerMethodField()
    capsule_summary = serializers.SerializerMethodField()

    class Meta:
        model = models.Friend
        fields = '__all__'  # or list explicitly + ['capsule_count', 'capsule_summary']

    def get_capsule_count(self, obj):
        return models.ThoughtCapsulez.objects.filter(friend=obj).count()

    def get_capsule_summary(self, obj):
        # Example summary grouped by category
        summary = (
            models.ThoughtCapsulez.objects
            .filter(friend=obj)
            .values('user_category__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return [
            {
                "user_category_name": item['user_category__name'],
                "count": item['count']
            }
            for item in summary
        ]



class FriendMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Friend
        fields = ['id', 'name']   


class FriendSuggestionSettingsSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.FriendSuggestionSettings
        fields = ['id', 'friend', 'phone_number', 'user', 'can_schedule', 'effort_required', 'priority_level', 'category_limit_formula']
    

 

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

    # friend_id = serializers.IntegerField(source='friend.id', read_only=True)
    name = serializers.CharField(source='friend.name')
    # first_name = serializers.CharField(source='friend.first_name')
    # last_name = serializers.CharField(source='friend.last_name') 
    first_meet_entered = serializers.DateField(source='friend.first_meet_entered')
 
    class Meta:
        model = models.NextMeet
        fields = ['id', 'date', 'name', 'first_meet_entered', 'days_since', 'days_since_words', 
                  'time_score', 'future_date_in_words', 
                  'suggestion_settings', 'friend_faves']
   

    def get_friend_faves(self, obj):
        friend = obj.friend
        try:
            friend_faves_instance = friend.friendfaves  # This is the correct reverse OneToOneField accessor
            return FriendFavesSerializer(friend_faves_instance).data
        except models.FriendFaves.DoesNotExist:
            return None
 

class UpcomingMeetsSerializer(serializers.ModelSerializer):

    friend = FriendSerializer()

    friend_name = serializers.CharField(source='friend.name')
 
    
    class Meta():
        model = models.NextMeet
        fields = ['id', 'date', 'friend', 'days_since', 'days_since_words', 
                  'time_score', 'future_date_in_words',  'friend_name']
 


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
        fields = ['id', 'friend', 'user',  'user_category', 'user_category_name', 'capsule', 'created_on', 'updated_on', 'pre_added_to_hello']
    
    # may not need (?)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
 

class CompletedThoughtCapsuleSerializer(serializers.ModelSerializer): 
    user_category_name = serializers.CharField(source='user_category.name', read_only=True)
    class Meta:
        model = models.CompletedThoughtCapsulez
        fields = ['id', 'original_id', 'friend', 'user', 'time_score', 'hello', 'capsule', 'user_category', 'user_category_original_name', 'user_category_name', 'created_on', 'updated_on']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
 

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



 

class UpdatesTrackerSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.UpdatesTracker
        fields = '__all__'

class VoidedMeetLightSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.VoidedMeet
        fields = ['id', 'user', 
                    'date', 'past_date_in_words', 'manual_reset' ]


 

class PastMeetSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.PastMeet
        fields = ['id', 'friend', 'user', 'type','typed_location', 'location_name', 'location',
                    'date', 'additional_notes', 'past_date_in_words','thought_capsules_shared', 'delete_all_unshared_capsules', 'created_on', 'updated_on']



class PastMeetLightSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.PastMeet
        fields = ['id', 'user', 'type', 'location',
                    'date', 'past_date_in_words', 'freeze_effort_required', 'freeze_priority_level' ]





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