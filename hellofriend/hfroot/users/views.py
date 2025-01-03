from . import models
from . import serializers
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from rest_framework import generics, response, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny

from rest_framework.views import APIView 

# Create your views here.

class CreateUserView(generics.CreateAPIView):

    queryset = models.BadRainbowzUser.objects.all()
    serializer_class = serializers.BadRainbowzUserSerializer
    permission_classes = [AllowAny]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    if not request.user.is_authenticated:
        return response.Response({'error': 'User not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
    
    serializer = serializers.BadRainbowzUserSerializer(request.user)
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

    def get_object(self):
        user_id = self.kwargs['user_id']
        return get_object_or_404(models.UserSettings, user__id=user_id)
    
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
   