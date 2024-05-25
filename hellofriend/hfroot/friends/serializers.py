from rest_framework import serializers
from . import models





class CategorySerializer(serializers.ModelSerializer):
    class Meta():
        model = models.Category
        fields = ['id', 'name', 'item_type', 'created_on']

class FriendSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.Friend
        fields = '__all__'


class FriendSuggestionSettingsSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.FriendSuggestionSettings
        fields = ['id', 'friend', 'user', 'can_schedule', 'effort_required', 'priority_level', 'category_limit_formula']
    

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

    friends = FriendSerializer(many=True, read_only=True)

    class Meta():
        model = models.Location
        fields = '__all__'

    #def get_friends(self, obj):
     #   friends_data = [{'id': friend.id, 'name': friend.name} for friend in obj.friends.all()]
      #  return friends_data

    # Removes address requirement when updating only
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
    name = serializers.CharField(source='friend.name')
    first_name = serializers.CharField(source='friend.first_name')
    last_name = serializers.CharField(source='friend.last_name')
    first_meet_entered = serializers.DateField(source='friend.first_meet_entered')

    class Meta:
        model = models.NextMeet
        fields = ['id', 'date', 'name', 'first_name', 'last_name', 'first_meet_entered', 'days_since', 'days_since_words', 
                  'time_score', 'future_date_in_words', 'category_activations_left', 
                  'suggestion_settings', 'friend_faves']

    def get_friend_faves(self, obj):
        friend = obj.friend  # Get the friend associated with the NextMeet instance
        friend_faves_instance = models.FriendFaves.objects.filter(friend=friend).first()
        if friend_faves_instance:
            return FriendFavesSerializer(instance=friend_faves_instance).data
        else:
            return None



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


 
class ThoughtCapsuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ThoughtCapsulez
        fields = ['id', 'friend', 'user', 'typed_category', 'category', 'capsule', 'created_on', 'updated_on']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        friend_id = self.context.get('friend_id')
        if friend_id:
            self.fields['category'].queryset = models.Category.objects.filter(user=self.context['request'].user, friend_id=friend_id)


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Image
        fields = '__all__'



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




class PastMeetSerializer(serializers.ModelSerializer):

    class Meta():
        model = models.PastMeet
        fields = ['id', 'friend', 'user', 'type','typed_location', 'location_name', 'location', 
                    'date', 'past_date_in_words','thought_capsules_shared', 'delete_all_unshared_capsules']




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