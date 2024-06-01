from . import models
from . import serializers
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from rest_framework import generics, response, status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated, AllowAny

from rest_framework.views import APIView 

# Create your views here.

class CreateUserView(generics.CreateAPIView):

    queryset = models.BadRainbowzUser.objects.all()
    serializer_class = serializers.BadRainbowzUserSerializer
    permission_classes = [AllowAny]


@api_view(['GET'])
@login_required
def get_current_user(request):
    serializer = serializers.BadRainbowzUserSerializer(request.user)
    return JsonResponse(serializer.data)


class AddAddressView(generics.UpdateAPIView):
    serializer_class = serializers.BadRainbowzUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user_id = self.kwargs['user_id']
        try:
            return models.BadRainbowzUser.objects.get(id=user_id)
        except models.BadRainbowzUser.DoesNotExist:
            raise serializers.ValidationError("User does not exist")

    def put(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        address_data = request.data.get('address')  # Extract address data from request
        title_data = request.data.get('title')  # Extract title data from request
        if address_data and title_data:
            instance.add_address({'address': address_data, 'title': title_data})  # Pass address and title data
            instance.save()
            return response.Response("Address added successfully", status=status.HTTP_201_CREATED)
        else:
            return response.Response("Address data is required", status=status.HTTP_400_BAD_REQUEST)


class AddAddressesView(APIView):
    permission_classes = [IsAuthenticated] 

    def post(self, request, user_id, *args, **kwargs):
        serializer = serializers.AddAddressSerializer(data=request.data)
        if serializer.is_valid():
            address_data = serializer.validated_data
            user = request.user
            if user_id == user.id:  # Ensure the authenticated user matches the provided user_id
                user.add_address(address_data)
                return response.Response("Address added successfully", status=status.HTTP_201_CREATED)
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
            for address in addresses:
                if address.get('title') == title_to_delete:  # Check if the address title matches
                    addresses.remove(address)  # Remove the matching address
                    user.addresses = addresses
                    user.save()
                    return response.Response("Address deleted successfully", status=status.HTTP_204_NO_CONTENT)
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

class UserProfileDetail(generics.RetrieveUpdateAPIView):
    serializer_class = serializers.UserProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'user_id'

    def get_object(self):
        user_id = self.kwargs['user_id']
        return get_object_or_404(models.UserProfile, user__id=user_id)
    

