from . import models
from . import serializers
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated, AllowAny

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
    

