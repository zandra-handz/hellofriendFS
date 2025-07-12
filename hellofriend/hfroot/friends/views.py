import datetime
from . import models
import users.models
import users.serializers
from . import serializers

from django.core.exceptions import ValidationError
from django.db.models import Min

from django.shortcuts import render, get_object_or_404
from rest_framework import generics, response, status, viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import api_view, throttle_classes, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from .utils import Distance, NearbyDetails, PlaceDetailsFetcher, GeocodingFetcher


# Create your views here.
def index(request):
    return render(request, 'index.html', {})


class FriendsView(generics.ListAPIView):
    serializer_class = serializers.FriendSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user 
        return models.Friend.objects.filter(user=user)
 

class UpdateAppSetupComplete(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user

        # Query the user's friends
        user_friends_count = models.Friend.objects.filter(user=user).count()
        
        # Check if the user has at least one friend
        if user_friends_count > 0:
            # Update the user's app_setup_complete field if it's not already true
            if not user.app_setup_complete:
                user.app_setup_complete = True
                user.save()
                return response.Response({"message": "User's app setup is now complete."}, status=status.HTTP_200_OK)
            else:
                return response.Response({"message": "User's app setup was already complete."}, status=status.HTTP_200_OK)
        else:
            return response.Response({"message": "User does not have any friends."}, status=status.HTTP_200_OK)



class FriendCreateView(APIView):
    
    def post(self, request):
        user = request.user
        data = request.data
        data['user'] = user.id
        serializer = serializers.FriendSerializer(data=data)
        if serializer.is_valid(): 
            friend = serializer.save()
            
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    '''
    {
    "name": "Friend Name",
    "first_name": "First Name",
    "last_name": "Last Name",
    "first_meet_entered": "2024-03-31"
    }
    '''

class FriendDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.FriendSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        return models.Friend.objects.filter(user=user, id=friend_id)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        id = instance.id
        self.perform_destroy(instance)
        return response.Response({
            "message": "Friend deleted successfully",
            "id": id 
        }, status=200)

class FriendAddressesAll(generics.ListAPIView):
    serializer_class = serializers.FriendAddressSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        return models.FriendAddress.objects.filter(user=user, friend_id=friend_id)


class FriendAddressesValidated(generics.ListAPIView):
    serializer_class = serializers.FriendAddressSerializer
    permissions_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        return models.FriendAddress.objects.filter(user=user, id=friend_id, validated_address=True)


class FriendAddressCreate(generics.CreateAPIView):
    serializer_class = serializers.FriendAddressSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def perform_create(self, serializer):
        friend_id = self.kwargs['friend_id']
        friend = get_object_or_404(models.Friend, pk=friend_id)
        serializer.save(user=self.request.user, friend=friend)


class FriendAddressDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.FriendAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        address_id = self.kwargs['pk']  
        return models.FriendAddress.objects.filter(user=user, friend_id=friend_id, id=address_id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        id = instance.id
        self.perform_destroy(instance)
        return response.Response({
            "message": "Friend address deleted successfully",
            "id": id 
        }, status=200)

class FriendProfile(generics.RetrieveUpdateAPIView, generics.DestroyAPIView):
    serializer_class = serializers.FriendProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        return models.Friend.objects.filter(user=user, id=friend_id)


class FriendSuggestionSettingsDetail(generics.RetrieveUpdateAPIView):
    serializer_class = serializers.FriendSuggestionSettingsSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        return models.FriendSuggestionSettings.objects.filter(user=user, friend_id=friend_id)
    

    def perform_update(self, serializer):
        instance = serializer.save()  # Save the FriendSuggestionSettings instance first
        friend = instance.friend
        next_meet = models.NextMeet.objects.filter(user=self.request.user, friend=friend).first()
 
        if next_meet:
            next_meet.create_new_date_clean()
            next_meet.save()

        return instance



class FriendSuggestionSettingsCategoryLimit(generics.RetrieveAPIView):
    serializer_class = serializers.CategoryLimitSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_object(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        return models.FriendSuggestionSettings.objects.get(user=user, friend_id=friend_id)
    
class FriendFavesDetail(generics.RetrieveUpdateAPIView):
    serializer_class = serializers.FriendFavesSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        return models.FriendFaves.objects.filter(user=user, friend_id=friend_id)

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()

        # Validate input data
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Ensure the user is authorized to update this instance
        if request.user != instance.user:
            return response.Response({"error": "User is not authorized to update this friend faves."},
                                     status=status.HTTP_403_FORBIDDEN)

        # Update instance with validated data
        serializer.save()

        return response.Response(serializer.data)

    
class FriendFavesLocationAdd(generics.RetrieveUpdateAPIView):
    serializer_class = serializers.FriendFavesSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        return models.FriendFaves.objects.filter(user=user, friend_id=friend_id)

    # send user, friend, and location_id
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.data.get('user')
        friend = request.data.get('friend')
        location_id = request.data.get('location_id')
        dark_color = request.data.get('dark_color')
        light_color = request.data.get('light_color')


        if user == instance.user.id and friend == instance.friend.id:
            if location_id:
                location = models.Location.objects.get(id=location_id)
                instance.locations.add(location)
                instance.save()
                serializer = self.get_serializer(instance)
                return response.Response(serializer.data)
            else:
                return response.Response({"error": "location_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return response.Response({"error": "User or Friend mismatch"}, status=status.HTTP_403_FORBIDDEN)



class FriendFavesLocationRemove(generics.UpdateAPIView):
    serializer_class = serializers.FriendFavesSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        return models.FriendFaves.objects.filter(user=user, friend_id=friend_id)

    # send user, friend, and location_id
    def patch(self, request, *args, **kwargs):
        user = request.user
        friend_id = self.kwargs['friend_id']
        location_id = request.data.get('location_id')

        try:
            friend_faves = models.FriendFaves.objects.get(user=user, friend_id=friend_id)
            location = models.Location.objects.get(id=location_id)

            if location in friend_faves.locations.all():
                friend_faves.locations.remove(location)
                serializer = serializers.FriendFavesSerializer(friend_faves)
                return response.Response(serializer.data)
            else:
                return response.Response({"error": "Location not found in friend's favorites"}, status=status.HTTP_400_BAD_REQUEST)

        except models.FriendFaves.DoesNotExist:
            return response.Response({"error": "Friend faves not found"}, status=status.HTTP_404_NOT_FOUND)
        except models.Location.DoesNotExist:
            return response.Response({"error": "Location not found"}, status=status.HTTP_404_NOT_FOUND)


class CategoriesView(generics.ListAPIView):
    serializer_class = serializers.CategorySerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        return models.Category.objects.filter(user=user, friend_id=friend_id)

class NextMeetView(generics.ListAPIView):
    serializer_class = serializers.UpcomingMeetsSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        return models.NextMeet.objects.filter(user=user, friend_id=friend_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remix_all_next_meets(request):
    user = request.user

    # Check if user is authenticated
    if not user.is_authenticated:
        return response.Response({"message": "User is not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)

    next_meets = models.NextMeet.objects.filter(user=user)

    for next_meet in next_meets:
        next_meet.reset_date()
        next_meet.create_new_date_if_needed()
        next_meet.save()

    return response.Response({"message": "All next meets have been remixed successfully."})


class FriendDashboardView(generics.ListAPIView):
    serializer_class = serializers.FriendDashboardSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    # def get_queryset(self):
    #     user = self.request.user
    #     friend_id = self.kwargs['friend_id']
    #     return models.NextMeet.objects.filter(user=user, friend_id=friend_id)

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        return models.NextMeet.objects.filter(user=user, friend_id=friend_id).select_related(
            'friend',                             # Friend object
            'friend_suggestion_settings',        # FK from NextMeet to FriendSuggestionSettings
            'previous',                          # FK to PastMeet
        ).prefetch_related(
            'friend__addresses',                 # Friend's addresses (reverse FK/many)
            'friend__friendfaves',          # Friend's favorites (reverse FK/many)
            # 'friend__suggestion_settings_friend', # Usually not needed here, NextMeet already links FriendSuggestionSettings directly
        )
    



class NextMeetsAllView(generics.ListCreateAPIView):
    serializer_class = serializers.NextMeetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return models.NextMeet.objects.filter(user=user)


# Limits to four here instead of in the front end

import datetime
from django.utils import timezone

class UpcomingMeetsView(generics.ListCreateAPIView):
    serializer_class = serializers.UpcomingMeetsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        today = timezone.now().date()
        ten_days_from_now = today + datetime.timedelta(days=10)

        expired_meets = models.NextMeet.objects.expired_dates().filter(user=user)
        for meet in expired_meets:
            meet.save()

        update_tracker, _ = models.UpdatesTracker.objects.get_or_create(user=user)
        if update_tracker.last_upcoming_update != today:
            update_tracker.upcoming_updated()

        
        queryset = models.NextMeet.objects.filter(user=user, date__range=[today, ten_days_from_now])
        if not queryset.exists():
            soonest_date = models.NextMeet.objects.filter(user=user, date__gt=ten_days_from_now).aggregate(Min('date'))['date__min']
            if soonest_date:
                queryset = models.NextMeet.objects.filter(user=user, date=soonest_date)

        return queryset


class UpcomingMeetsLightView(generics.ListCreateAPIView):
    serializer_class = serializers.UpcomingMeetsLightSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        today = timezone.now().date()


        # expired_meets = models.NextMeet.objects.expired_dates().filter(user=user)
        # for meet in expired_meets:
        #     meet.save()

 
        # get last update date, if today then do not re-update
        update_tracker, _ = models.UpdatesTracker.objects.get_or_create(user=user)
        if update_tracker.last_upcoming_update != today:
            expired_meets = models.NextMeet.objects.user_expired_dates(user)
            for meet in expired_meets:
                meet.save()

            # mark as last updated on today's date:
            update_tracker.upcoming_updated()


        ten_days_from_now = today + datetime.timedelta(days=10)
        
        queryset = models.NextMeet.objects.filter(user=user, date__range=[today, ten_days_from_now])
        if not queryset.exists():
            soonest_date = models.NextMeet.objects.filter(user=user, date__gt=ten_days_from_now).aggregate(Min('date'))['date__min']
            if soonest_date:
                queryset = models.NextMeet.objects.filter(user=user, date=soonest_date)
        return queryset

 

class UpcomingMeetsAll48(generics.ListCreateAPIView):
    serializer_class = serializers.UpcomingMeetsAllSerializer 

    def get_queryset(self):
        today = timezone.now()
        two_days_from_now = today + datetime.timedelta(days=2)
        
        # Get meetings for all users within the next 48 hours
        queryset = models.NextMeet.objects.filter(date__range=[today, two_days_from_now])
        
        return queryset


class UpcomingMeetsAll36(generics.ListCreateAPIView):
    serializer_class = serializers.UpcomingMeetsAllSerializer 

    def get_queryset(self):
        today = timezone.now()
        one_and_a_half_days_from_now = today + datetime.timedelta(days=1.5)
        
        # Get meetings for all users within the next 36 hours
        queryset = models.NextMeet.objects.filter(date__range=[today, one_and_a_half_days_from_now])
        
        return queryset


class UpcomingMeetsAll24(generics.ListCreateAPIView):
    serializer_class = serializers.UpcomingMeetsAllSerializer 

    def get_queryset(self):
        today = timezone.now()
        one_day_from_now = today + datetime.timedelta(days=1)
        
        # Get meetings for all users within the next 24 hours
        queryset = models.NextMeet.objects.filter(date__range=[today, one_day_from_now])
        
        return queryset

class CompletedThoughtCapsulesAll(generics.ListAPIView):
    serializer_class = serializers.CompletedThoughtCapsuleSerializer
    permissions_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id'] 
        return models.CompletedThoughtCapsulez.objects.filter(user=user, friend_id=friend_id)



class ThoughtCapsulesAll(generics.ListAPIView):
    serializer_class = serializers.ThoughtCapsuleSerializer
    permissions_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id'] 
        return models.ThoughtCapsulez.objects.filter(user=user, friend_id=friend_id)



class ThoughtCapsulesByCategory(generics.ListAPIView):
    serializer_class = serializers.ThoughtCapsuleSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id'] 
        return models.ThoughtCapsulez.objects.filter(user=user, friend_id=friend_id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        friend_id = self.kwargs['friend_id']
        
        categories = models.Category.objects.filter(user=request.user, friend_id=friend_id)
        
        capsules_by_category = {}
        
        for category in categories:
            capsules = queryset.filter(category=category)
            serialized_capsules = self.get_serializer(capsules, many=True).data
            capsules_by_category[category.name] = serialized_capsules
        
        return response.Response(capsules_by_category, status=status.HTTP_200_OK)



class ThoughtCapsuleCreate(generics.ListCreateAPIView):
    serializer_class = serializers.ThoughtCapsuleSerializer
    permissions_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id'] 
        return models.ThoughtCapsulez.objects.filter(user=user, friend_id=friend_id)

    def perform_create(self, serializer):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        serializer.save(user=user, friend_id=friend_id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['friend_id'] = self.kwargs['friend_id']
        return context


class ThoughtCapsuleDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.ThoughtCapsuleSerializer
    permission_classes = [IsAuthenticated]

    # Returns only user's thought capsules
    def get_queryset(self):
        user = self.request.user
        return models.ThoughtCapsulez.objects.filter(user=user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        id = instance.id
        self.perform_destroy(instance)
        return response.Response({
            "message": "Moment deleted successfully",
            "id": id 
        }, status=200)

class ThoughtCapsulesUpdateMultiple(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs): 
        capsules_data = request.data.get('capsules', [])
        
        if not capsules_data:
            return response.Response(
                {"error": "Capsules data is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Initialize lists to store updated capsules and potential errors
        updated_capsules = []
        errors = []
        
        user = request.user
        
        # Iterate over each capsule data in the request
        for capsule_data in capsules_data:
            capsule_id = capsule_data.get('id')
            fields_to_update = capsule_data.get('fields_to_update', {})
            
            # Ensure that both id and fields_to_update are provided
            if not capsule_id or not fields_to_update:
                errors.append({"error": f"Capsule ID and fields to update are required for each capsule."})
                continue
            
            # Try to retrieve the capsule
            try:
                capsule = models.ThoughtCapsulez.objects.get(id=capsule_id, user=user)
            except models.ThoughtCapsulez.DoesNotExist:
                errors.append({"error": f"Capsule with ID {capsule_id} does not exist or does not belong to the user."})
                continue
            
            # Update the capsule with the provided fields
            for field, value in fields_to_update.items():
                setattr(capsule, field, value)
            
            # Save the updated capsule
            capsule.save()
            updated_capsules.append(capsule)
        
        # If there are errors, return them along with successful updates
        if errors:
            return response.Response({
                "updated_capsules": serializers.ThoughtCapsuleSerializer(updated_capsules, many=True).data,
                "errors": errors
            }, status=status.HTTP_207_MULTI_STATUS)

        # If no errors, return only the updated capsules
        return response.Response(serializers.ThoughtCapsuleSerializer(updated_capsules, many=True).data, status=status.HTTP_200_OK)

class ImagesAll(generics.ListAPIView):
    serializer_class = serializers.ImageSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        return models.Image.objects.filter(user=user, friend_id=friend_id)

class ImageCreate(generics.CreateAPIView):
    queryset = models.Image.objects.all()
    serializer_class = serializers.ImageCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        friend = get_object_or_404(models.Friend, pk=friend_id, user=user)
        
        serializer.save(user=user, friend=friend)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return response.Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    

class ImageDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.ImageSerializer
    permission_classes = [IsAuthenticated]

    # Returns only user's thought capsules
    def get_queryset(self):
        user = self.request.user
        return models.Image.objects.filter(user=user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        id = instance.id
        self.perform_destroy(instance)
        return response.Response({
            "message": "Image deleted successfully",
            "id": id 
        }, status=200)


class HelloesAll(generics.ListAPIView):
    serializer_class = serializers.PastMeetSerializer
    permissions_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id'] 
        return models.PastMeet.objects.filter(user=user, friend_id=friend_id)


class ImagesByCategoryView(APIView):

    # For testing
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        user = self.request.user
        friend_id = kwargs.get('friend_id')

        # Filter images for the specific user and friend_id, excluding images where image field is null
        images = models.Image.objects.filter(user=user, friend_id=friend_id).exclude(image='')

        # Group images by category
        images_by_category = {}
        for image in images:
            category = image.image_category
            if category not in images_by_category:
                images_by_category[category] = []

            serializer = serializers.ImageSerializer(image, context={'request': request})
            images_by_category[category].append(serializer.data)

        return response.Response(images_by_category, status=status.HTTP_200_OK)

class HelloCreate(generics.ListCreateAPIView):
    serializer_class = serializers.PastMeetSerializer
    permissions_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id'] 
        return models.PastMeet.objects.filter(user=user, friend_id=friend_id)

    def perform_create(self, serializer):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        serializer.save(user=user, friend_id=friend_id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['friend_id'] = self.kwargs['friend_id']
        return context

    def post(self, request, *args, **kwargs): 
        hello_response = super().post(request, *args, **kwargs) 
        # The instance is already created, so no need to save again
        return hello_response

class HelloDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.PastMeetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return models.PastMeet.objects.filter(user=user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        try:
            instance.delete()
            return response.Response({
                "message": "PastMeet deleted successfully",
                "id": instance.id 
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return response.Response({
                "message": str(e),
            }, status=status.HTTP_400_BAD_REQUEST)


class HelloTypeChoices(APIView):
    permission_classes = [IsAuthenticated, AllowAny]

    def get(self, request, format=None):
        type_choices = models.PastMeet.TYPE_CHOICES
        serializer = serializers.PastMeetTypeChoicesSerializer({'type_choices': type_choices})
        return response.Response(serializer.data, status=status.HTTP_200_OK)



class UserLocationsAll(generics.ListAPIView):
    serializer_class = serializers.LocationSerializer
    permissions_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return models.Location.objects.filter(user=user).prefetch_related('friends')

class LocationParkingTypeChoices(APIView):
    permission_classes = [IsAuthenticated, AllowAny]

    def get(self, request, format=None):
        type_choices = models.Location.TYPE_CHOICES
        serializer = serializers.LocationParkingTypeChoicesSerializer({'type_choices': type_choices})
        return response.Response(serializer.data, status=status.HTTP_200_OK)


class UserLocationsValidated(generics.ListAPIView):
    serializer_class = serializers.LocationSerializer
    permissions_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return models.Location.objects.filter(user=user, validated_address=True)


class UserLocationCreate(generics.CreateAPIView):
    serializer_class = serializers.LocationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FriendLocationsAll(generics.ListAPIView):
    serializer_class = serializers.LocationSerializer
    permissions_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id'] 
        return models.Location.objects.filter(user=user, friend_id=friend_id)


'''

Not finished -- need to be for Location model

class ThoughtCapsuleCreate(generics.ListCreateAPIView):
    serializer_class = serializers.ThoughtCapsuleSerializer
    permissions_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs['friend_id'] 
        return models.ThoughtCapsulez.objects.filter(user=user, friend_id=friend_id)

    def perform_create(self, serializer):
        user = self.request.user
        friend_id = self.kwargs['friend_id']
        serializer.save(user=user, friend_id=friend_id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['friend_id'] = self.kwargs['friend_id']
        return context

class ThoughtCapsuleDetail(generics.RetrieveDestroyAPIView):
    serializer_class = serializers.ThoughtCapsuleSerializer
    permission_classes = [IsAuthenticated]

    # Returns only user's thought capsules
    def get_queryset(self):
        user = self.request.user
        return models.ThoughtCapsulez.objects.filter(user=user)

'''


class ValidateLocation(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        address = request.data.get('address')
        if address:
            location = models.Location(address=address)
            location.calculate_coordinates()
            return response.Response({
                'address': location.address,
                'latitude': location.latitude,
                'longitude': location.longitude
            }, status=status.HTTP_200_OK)
        else:
            return response.Response({'error': 'Address not provided'}, status=status.HTTP_400_BAD_REQUEST)

    

@api_view(['POST', 'GET', 'OPTION'])
@permission_classes([IsAuthenticated])
def consider_the_drive(request):


    if request.method == 'OPTIONS':
        return response.Response(status=status.HTTP_200_OK)


    if request.method == 'GET':

        if not request.user.is_authenticated:
            return response.Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

        return response.Response({'message': 'Enter address'}, status=status.HTTP_200_OK)


    if request.method == 'POST':
        data = request.data
 
        origin_a = data.get('address_a_address')
        destination = data.get('destination_address')
        friend_address = data.get('address_b_address')
        friend_origins = {'friend':friend_address}
        perform_search = data.get('perform_search')
        search = data.get('search')
        radius = data.get('radius')
        length = data.get('length')
 
        try:
            distance_object = Distance(origin_a=origin_a, destination=destination, search=search, radius=radius, suggested_length=length, perform_search=perform_search, **friend_origins)
        except ValueError as e:
            return response.Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
 
        response_data = {
            'origin_a': distance_object.origin_a,
            'destination': distance_object.destination,
            'friend_origins': distance_object.friend_origins,
            'midpoint': distance_object.get_midpoint(),
            'compare_directions': distance_object.compare_directions(many=False),
            'suggested_places': distance_object.get_directions_to_midpoint_places(),
        }

        return response.Response(response_data, status=status.HTTP_200_OK)
 
    return response.Response({'detail': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

@api_view(['POST', 'GET', 'OPTIONS'])
@permission_classes([IsAuthenticated])
def consider_midpoint_locations(request):
    
    if request.method == 'OPTIONS':
        return response.Response(status=status.HTTP_200_OK)

    if request.method == 'GET':
        if not request.user.is_authenticated:
            return response.Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

        return response.Response({'message': 'Enter address'}, status=status.HTTP_200_OK)

    if request.method == 'POST':
        data = request.data

        origin_a = data.get('address_a_address')
        friend_address = data.get('address_b_address')
        friend_origins = {'friend':friend_address}
        search = data.get('search', "restaurants")   
        radius = data.get('radius', 5000)   
        length = data.get('length', 8) 

        try:
            distance_object = Distance(origin_a=origin_a, search=search, radius=radius, suggested_length=length, perform_search=True, search_only=True, **friend_origins)
        except ValueError as e:
            return response.Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        response_data = {
            'origin_a': distance_object.origin_a,
            'friend_origins': distance_object.friend_origins,
            'midpoint': distance_object.get_midpoint(),  # Calculate midpoint
            'suggested_places': distance_object.get_directions_to_midpoint_places(many=False),  # Call with many=False
        }

        return response.Response(response_data, status=status.HTTP_200_OK)

    return response.Response({'detail': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

 

@api_view(['POST', 'GET', 'OPTIONS'])
@permission_classes([IsAuthenticated])
def place_id(request):
    
    if request.method == 'OPTIONS':
        return response.Response(status=status.HTTP_200_OK)

    if request.method == 'GET':
        if not request.user.is_authenticated:
            return response.Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

        return response.Response({'message': 'Provide origin address and search criteria'}, status=status.HTTP_200_OK)

    if request.method == 'POST':
        data = request.data

        origin_address = data.get('origin_address')
        origin_lat = data.get('origin_lat')
        origin_lon = data.get('origin_lon')

        if not origin_address and (not origin_lat or not origin_lon):
            return response.Response({'detail': 'Either origin address or coordinates are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            place_details = PlaceDetailsFetcher(
                origin_address=origin_address,
                origin_lat=origin_lat,
                origin_lon=origin_lon
            )

            place_id = place_details.get_nearest_place_id()  # Get the nearest place ID
            
            response_data = {
                'place_id': place_id
            }

        except ValueError as e:
            return response.Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return response.Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response.Response(response_data, status=status.HTTP_200_OK)

    return response.Response({'detail': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['POST', 'GET', 'OPTIONS'])
@permission_classes([IsAuthenticated])
def place_details(request):
    if request.method == 'OPTIONS':
        return response.Response(status=status.HTTP_200_OK)

    if request.method == 'GET':
        if not request.user.is_authenticated:
            return response.Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

        return response.Response({'message': 'Provide address or coordinates to retrieve place details'}, status=status.HTTP_200_OK)

    if request.method == 'POST':
        data = request.data
        address = data.get('address')
        lat = data.get('lat')
        lon = data.get('lon')

        if not address and (not lat or not lon):
            return response.Response({'detail': 'Either address or coordinates are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try: 
            geocoding_fetcher = GeocodingFetcher(address=address, lat=lat, lon=lon)
            place_id = geocoding_fetcher.get_place_id()  # Get the place ID

            place_details_fetcher = PlaceDetailsFetcher(place_id=place_id)
            place_details = place_details_fetcher.get_place_details()  # Get the place details

            if place_details:
                response_data = place_details_fetcher.extract_place_details(place_details)  # Extract and format place details
                response_data['place_id'] = place_id  # Include place ID in the response
            else:
                response_data = {'detail': 'No details found for the place.'}

        except ValueError as e:
            return response.Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return response.Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response.Response(response_data, status=status.HTTP_200_OK)

    return response.Response({'detail': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

@api_view(['POST', 'GET', 'OPTIONS'])
@permission_classes([IsAuthenticated])
def place_details_new(request):
    
    if request.method == 'OPTIONS':
        return response.Response(status=status.HTTP_200_OK)

    if request.method == 'GET':
        if not request.user.is_authenticated:
            return response.Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

        return response.Response({'message': 'Provide origin address and search criteria'}, status=status.HTTP_200_OK)

    if request.method == 'POST':
        data = request.data

        origin_address = data.get('origin_address')
        origin_lat = data.get('origin_lat')
        origin_lon = data.get('origin_lon')

        if not origin_address and (not origin_lat or not origin_lon):
            return response.Response({'detail': 'Either origin address or coordinates are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            place_details_fetcher = PlaceDetailsFetcher(
                  # Make sure to replace this with your actual API key
                origin_address=origin_address,
                origin_lat=origin_lat,
                origin_lon=origin_lon
            )

            place_id = place_details_fetcher.get_nearest_place_id()  # Get the nearest place ID
            place_details = place_details_fetcher.get_place_details(place_id)  # Get the place details

            if place_details:
                response_data = place_details_fetcher.extract_place_details(place_details)  # Extract and format place details
                response_data['place_id'] = place_id  # Include place ID in the response
            else:
                response_data = {'detail': 'No details found for the place.'}

        except ValueError as e:
            return response.Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return response.Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response.Response(response_data, status=status.HTTP_200_OK)

    return response.Response({'detail': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['POST', 'GET', 'OPTIONS'])
@permission_classes([IsAuthenticated])
def place_details_newer(request):
    
    if request.method == 'OPTIONS':
        return response.Response(status=status.HTTP_200_OK)

    if request.method == 'GET':
        if not request.user.is_authenticated:
            return response.Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

        return response.Response({'message': 'Provide origin address and search criteria'}, status=status.HTTP_200_OK)

    if request.method == 'POST':
        data = request.data

        origin_address = data.get('origin_address')
        origin_lat = data.get('origin_lat')
        origin_lon = data.get('origin_lon')
        radius = data.get('radius', 1000)
        search = data.get('search', "groceries")
        use_search = data.get('use_search', False)
        return_items = data.get('return_items', 3)

        if not origin_address and (not origin_lat or not origin_lon):
            return response.Response({'detail': 'Either origin address or coordinates are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            nearby_details = NearbyDetails(
                origin_address=origin_address,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                radius=radius,
                search=search,
                use_search=use_search,
                return_items=return_items
            )
            
            places = nearby_details.find_places()  # Call find_places to get the nearby places

        except ValueError as e:
            return response.Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return response.Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response_data = {
            'origin_address': nearby_details.origin_address,
            'search_results': places
        }

        return response.Response(response_data, status=status.HTTP_200_OK)

    return response.Response({'detail': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)



class LocationDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.Location.objects.all()
    serializer_class = serializers.LocationSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        # Ensure user association if necessary
        serializer.save(user=self.request.user)

    def perform_create(self, serializer):  
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        id = instance.id
        self.perform_destroy(instance)
        return response.Response({
            "message": "Location deleted successfully",
            "id": id 
        }, status=200)
   
   



   # data needed:
   # all categories in same order (so, alphabetical), with
   # number of moments sent for friend
    # grouped by helloes
    # this view at least will not include active categories

    