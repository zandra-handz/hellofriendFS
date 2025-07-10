from . import models
from . import serializers
from django.apps import apps
from django.core.mail import send_mail
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from rest_framework import generics, response, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny


from rest_framework.views import APIView 

from django.conf import settings

# Create your views here.

class CreateUserView(generics.CreateAPIView):

    queryset = models.BadRainbowzUser.objects.all()
    serializer_class = serializers.BadRainbowzUserSerializer
    permission_classes = [AllowAny]


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_current_user(request):
#     if not request.user.is_authenticated:
#         return response.Response({'error': 'User not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
    
#     request.user.check_subscription_active()
    
#     serializer = serializers.BadRainbowzUserSerializer(request.user)
#     return JsonResponse(serializer.data)





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    if not request.user.is_authenticated:
        return response.Response({'error': 'User not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

    # Use select_related and prefetch_related to optimize nested fetches
    user_qs = models.BadRainbowzUser.objects.filter(pk=request.user.pk).select_related(
        'profile',          # assuming OneToOneField to UserProfile
        'settings'          # assuming OneToOneField to UserSettings
    ).prefetch_related(
        'user_categories',  # M2M relation UserCategory
        # Prefetch nested M2M on user_categories as needed
        Prefetch('user_categories__thought_capsules'),
        Prefetch('user_categories__images')
    )

    user = get_object_or_404(user_qs)

    serializer = serializers.BadRainbowzUserSerializer(user)
    return JsonResponse(serializer.data)



@api_view(['POST'])
@login_required
def add_address_to_current_user(request):
    user = request.user

    serializer = serializers.BadRainbowzUserAddressSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()  # Save the updated user object with the added address
        return response.Response("Address added successfully", status=status.HTTP_201_CREATED)
    else:
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class PasswordResetCodeValidationView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = serializers.PasswordResetCodeValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
         
        validated_data = serializer.validated_data
         
        return response.Response({
            "detail": "Reset code and email are valid.",
            "email": validated_data['email'],
            "reset_code": validated_data['reset_code']
        }, status=status.HTTP_200_OK)


class UpdateSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        user = request.user
        serializer = serializers.UpdateSubscriptionSerializer(instance=user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response({"detail": "Subscription updated successfully."}, status=status.HTTP_200_OK)

class PasswordResetConfirmView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = serializers.PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data
        serializer.save(user, request.data.get('new_password'))

        return response.Response({"detail": "Password has been reset successfully."}, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = serializers.ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']
            
            # Change the password
            user.set_password(new_password)
            user.save()

            # Update the session authentication hash to avoid the user being logged out
            update_session_auth_hash(request, user)

            return response.Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)
        
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    



class AddAddressView(APIView):
    permission_classes = [IsAuthenticated] 

    def post(self, request, user_id, *args, **kwargs):
        serializer = serializers.AddAddressSerializer(data=request.data)
        if serializer.is_valid():
            address_data = serializer.validated_data
            user = request.user
            if user_id == user.id:  # Ensure the authenticated user matches the provided user_id
                user.add_address(address_data)
                return response.Response(address_data, status=status.HTTP_201_CREATED)
            else:
                return response.Response("Unauthorized", status=status.HTTP_403_FORBIDDEN)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, *args, **kwargs):
        user = request.user
        address_data = request.data
        if 'address_index' in kwargs:
            address_index = kwargs['address_index']
            addresses = user.addresses
            if address_index < len(addresses):
                addresses[address_index].update(address_data)
                user.addresses = addresses
                user.save()
                return response.Response("Address updated successfully", status=status.HTTP_200_OK)
            else:
                return response.Response("Address index out of range", status=status.HTTP_404_NOT_FOUND)
        else:
            return response.Response("Address index not provided", status=status.HTTP_400_BAD_REQUEST)


class DeleteAddressView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        title_to_delete = request.data.get('title', None)  # Get the title from the request data

        if title_to_delete is not None:
            addresses = user.addresses
            
            # Create a copy of the addresses to modify
            updated_addresses = [address for address in addresses if address.get('title') != title_to_delete]
            
            if len(updated_addresses) < len(addresses):
                # An address was deleted
                user.addresses = updated_addresses
                user.save()
                return response.Response("Address deleted successfully", status=status.HTTP_200_OK)
            else:
                return response.Response("Address not found", status=status.HTTP_404_NOT_FOUND)
        else:
            return response.Response("Title not provided", status=status.HTTP_400_BAD_REQUEST)




class UserSettingsDetail(generics.RetrieveUpdateAPIView):
    serializer_class = serializers.UserSettingsSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'user_id'

    def get_queryset(self):
        return models.UserSettings.objects.select_related('user').prefetch_related(
            Prefetch(
                'user__user_categories',
                queryset=models.UserCategory.objects.prefetch_related('thought_capsules', 'images')
            )
        )

    def get_object(self):
        user_id = self.kwargs['user_id']
        # Use the optimized queryset with prefetching
        queryset = self.get_queryset()
        return get_object_or_404(queryset, user__id=user_id)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs): 
        instance = self.get_object()
        if 'expo_push_token' in request.data:
            instance.expo_push_token = None
            instance.save()
            return response.Response({'status': 'Expo push token cleared'}, status=status.HTTP_204_NO_CONTENT)
        return response.Response({'error': 'Expo push token not provided'}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileDetail(generics.RetrieveUpdateAPIView):
    serializer_class = serializers.UserProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'user_id'

    def get_object(self):
        user_id = self.kwargs['user_id']
        return get_object_or_404(models.UserProfile, user__id=user_id)




class UserCategoriesView(generics.ListCreateAPIView):
    serializer_class = serializers.UserCategorySerializer
    permission_classes = [IsAuthenticated]

    # def get_queryset(self):
    #     user = self.request.user
    #     return models.UserCategory.objects.filter(user=user)
    
    def get_queryset(self):
        user = self.request.user
        return models.UserCategory.objects.filter(user=user).prefetch_related('thought_capsules', 'images')

        
    def perform_create(self, serializer):
        # Save the UserCategory linked to current user first (without M2M)
        user_category = serializer.save(user=self.request.user)

        # After saving, update ManyToMany fields if they exist in validated_data
        thought_capsules = self.request.data.get('thought_capsules', [])
        images = self.request.data.get('images', [])

        if thought_capsules:
            # Assuming these are lists of IDs
            user_category.thought_capsules.set(thought_capsules)
        if images:
            user_category.images.set(images)

        user_category.save()

 
# on front end, add query parameter ?only_with_capsules=true to end of url to get only relevant catagories
class UserCategoriesFriendHistoryAll(generics.ListAPIView):
    serializer_class = serializers.UserCategoriesFriendHistorySerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'friend_id'

    def get_queryset(self):
        user = self.request.user
        friend_id = self.kwargs.get(self.lookup_url_kwarg)
        only_with_capsules = self.request.query_params.get("only_with_capsules", "false").lower() == "true"

        CompletedCapsule = apps.get_model('friends', 'CompletedThoughtCapsulez')

        capsule_filter = CompletedCapsule.objects.filter(user=user)
        if friend_id:
            capsule_filter = capsule_filter.filter(friend_id=friend_id)

        capsule_filter = capsule_filter.select_related('hello', 'user_category')  # ✅ optimized

        qs = models.UserCategory.objects.filter(user=user).prefetch_related(
            Prefetch('completed_thought_capsules', queryset=capsule_filter, to_attr='prefetched_capsules')
        )

        if only_with_capsules and friend_id:
            qs = qs.filter(completed_thought_capsules__friend_id=friend_id).distinct()

        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['friend_id'] = self.kwargs.get(self.lookup_url_kwarg)
        return context

# on front end, add query parameter ?only_with_capsules=true to end of url to get only non-empty catagories
 

class UserCategoriesHistoryAll(generics.ListAPIView):
    serializer_class = serializers.UserCategoriesHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        CompletedCapsule = apps.get_model('friends', 'CompletedThoughtCapsulez')

        only_with_capsules = self.request.query_params.get("only_with_capsules", "false").lower() == "true"
        friend_id = self.request.query_params.get("friend_id")

        capsule_qs = CompletedCapsule.objects.filter(user=user)
        if friend_id:
            capsule_qs = capsule_qs.filter(friend_id=friend_id)

        capsule_qs = capsule_qs.select_related("friend", "user", "hello", "user_category")

        qs = models.UserCategory.objects.filter(user=user).prefetch_related(
            Prefetch("completed_thought_capsules", queryset=capsule_qs, to_attr="prefetched_capsules")
        )

        if only_with_capsules:
            # This filtering is still necessary to only return categories with any relevant capsules
            if friend_id:
                qs = qs.filter(completed_thought_capsules__user=user, completed_thought_capsules__friend_id=friend_id).distinct()
            else:
                qs = qs.filter(completed_thought_capsules__user=user).distinct()

        return qs

    def get_serializer_context(self): 
        context = super().get_serializer_context()
        context['friend_id'] = self.request.query_params.get("friend_id")
        return context



class UserCategoriesHistoryCountOnly(generics.ListAPIView):
    serializer_class = serializers.UserCategoriesHistorySerializer
    permission_classes = [IsAuthenticated]

    # def get_queryset(self):
    #     user = self.request.user
    #     qs = models.UserCategory.objects.filter(user=user)

    #     only_with_capsules = self.request.query_params.get("only_with_capsules", "false").lower() == "true"
    #     if only_with_capsules:
    #         qs = qs.filter(completed_thought_capsules__user=user).distinct()

    #     return qs
    
    def get_queryset(self):
        user = self.request.user

        qs = models.UserCategory.objects.filter(user=user).annotate(
            capsule_count=Count('completed_thought_capsules', filter=Q(completed_thought_capsules__user=user))
        )

        only_with_capsules = self.request.query_params.get("only_with_capsules", "false").lower() == "true"
        if only_with_capsules:
            qs = qs.filter(capsule_count__gt=0)

        return qs

    def get_serializer_context(self): 
        context = super().get_serializer_context()
        context['request'] = self.request
        return context



class UserCategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.UserCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return models.UserCategory.objects.filter(user=user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        id = instance.id
        self.perform_destroy(instance)
        return response.Response({
            "message": "Moment deleted successfully",
            "id": id 
        }, status=200)



class UserAddressesAll(generics.ListAPIView):
    serializer_class = serializers.UserAddressSerializer
    permissions_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return models.UserAddress.objects.filter(user=user)


class UserAddressesValidated(generics.ListAPIView):
    serializer_class = serializers.UserAddressSerializer
    permissions_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return models.UserAddress.objects.filter(user=user, validated_address=True)


class UserAddressCreate(generics.CreateAPIView):
    serializer_class = serializers.UserAddressSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserAddressDetail(generics.RetrieveUpdateAPIView, generics.DestroyAPIView):
    serializer_class = serializers.UserAddressSerializer
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        user = self.request.user 
        return models.UserAddress.objects.filter(user=user)
    


@api_view(['POST'])
@permission_classes([AllowAny])
def send_email_to_user(request):
    """
    Send an email to the provided email address with a predefined subject and message.
    """
    email_address = request.data.get('email')
    
    if not email_address:
        return response.Response({'error': 'Email address is required'}, status=400)

    subject = 'Welcome to Our Service'  # Predefined subject
    message = 'Thank you for joining us! We are excited to have you as part of our community.'  # Predefined message

    try:
        # Send the email
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,  # Ensure this is set in your settings.py
            [email_address],
        )
        return response.Response({'success': f'Email successfully sent to {email_address}'}, status=200)
    except Exception as e:
        return response.Response({'error': f'Failed to send email: {str(e)}'}, status=500)
    


class RequestPasswordResetCodeView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        if not email:
            return response.Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = models.BadRainbowzUser.objects.get(email=email)
        except models.BadRainbowzUser.DoesNotExist:
            # Do not disclose if the email exists to prevent user enumeration
            return response.Response({"detail": "If the email exists, a reset code has been sent."}, status=status.HTTP_200_OK)

        # Generate and save the reset code
        reset_code = user.generate_password_reset_code()

        # Send the reset code via email
        send_mail(
            subject="Your Password Reset Code",
            message=f"Your password reset code is: {reset_code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

        return response.Response({"detail": "If the email exists, a reset code has been sent."}, status=status.HTTP_200_OK)
   