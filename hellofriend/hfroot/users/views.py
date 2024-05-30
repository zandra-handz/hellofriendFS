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


class AddAddressView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = serializers.AddAddressSerializer(data=request.data)
        if serializer.is_valid():
            address_data = serializer.validated_data
            user = request.user
            user.add_address(address_data)
            return response.Response("Address added successfully", status=status.HTTP_201_CREATED)
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

    def delete(self, request, *args, **kwargs):
        user = request.user
        if 'address_index' in kwargs:
            address_index = kwargs['address_index']
            addresses = user.addresses
            if address_index < len(addresses):
                del addresses[address_index]
                user.addresses = addresses
                user.save()
                return response.Response("Address deleted successfully", status=status.HTTP_204_NO_CONTENT)
            else:
                return response.Response("Address index out of range", status=status.HTTP_404_NOT_FOUND)
        else:
            return response.Response("Address index not provided", status=status.HTTP_400_BAD_REQUEST)

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
    

