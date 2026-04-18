from . import models
from . import serializers
from .notifications import notify_user
import datetime
from django.apps import apps
# from django.core.mail import send_mail
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Sum, Prefetch, Q, F
from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import generics, response, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import UserRateThrottle 

 

from rest_framework.views import APIView 

from django.conf import settings


# Create your views here.


class MediumPagination(PageNumberPagination):
    page_size = 30


class TenPerMinuteUserThrottle(UserRateThrottle):
    rate = '10/min'

class CreateUserView(generics.CreateAPIView):

    queryset = models.BadRainbowzUser.objects.all()
    serializer_class = serializers.CreateBadRainbowzUserSerializer
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
        'profile',
        'geckocombineddata'
        #,          # assuming OneToOneField to UserProfile
      #  'settings'
    )
              # assuming OneToOneField to UserSettings
    # ).prefetch_related(
    #     'user_categories',  # M2M relation UserCategory
    #     # Prefetch nested M2M on user_categories as needed
    #     Prefetch('user_categories__thought_capsules'),
    #     Prefetch('user_categories__images')
    # )

    user = get_object_or_404(user_qs)

    serializer = serializers.BadRainbowzUserSerializer(user)
    return JsonResponse(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_or_reset_friend_link_code(request):
    user = request.user

    code = models.FriendLinkCode.generate_code()

    obj, _ = models.FriendLinkCode.objects.update_or_create(
        user=user,
        defaults={
            'code': code,
            'expires_at': timezone.now() + datetime.timedelta(minutes=1),
        }
    )

    return response.Response({
        'code': obj.code,
        'expires_at': obj.expires_at,
    }, status=status.HTTP_200_OK)


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
    # lookup_url_kwarg = 'user_id'
 

    # def get_object(self):
    #     return self.request.user.settings   
    
    def get_object(self):
        return get_object_or_404(
            models.UserSettings.objects
                .select_related('pinned_friend', 'upcoming_friend'),
            user=self.request.user
        )
        

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs): 
        instance = self.get_object()
        if 'expo_push_token' in request.data:
            instance.expo_push_token = None
            instance.save()
            return response.Response({'status': 'Expo push token cleared'}, status=status.HTTP_204_NO_CONTENT)
        return response.Response({'error': 'Expo push token not provided'}, status=status.HTTP_400_BAD_REQUEST)

    # def get(self, request, *args, **kwargs):
    #     user = request.user

    

    # def get_queryset(self):
    #     return models.UserSettings.objects.select_related('user')
    # def get_queryset(self):
    #     return models.UserSettings.objects.select_related('user').prefetch_related(
    #         Prefetch(
    #             'user__user_categories',
    #             queryset=models.UserCategory.objects.prefetch_related('thought_capsules', 'images')
    #         )
    #     )

    # def get_object(self):
    #     user_id = self.kwargs['user_id']
    #     # Use the optimized queryset with prefetching
    #     queryset = self.get_queryset()
    #     return get_object_or_404(queryset, user__id=user_id)



class GeckoCombinedDataDetail(generics.RetrieveAPIView):
    serializer_class = serializers.UserGeckoCombinedSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return models.GeckoCombinedData.objects.get(user=self.request.user)

class GeckoCombinedDataSessionsAll(generics.ListAPIView):
    

    serializer_class = serializers.GeckoCombinedDataSessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MediumPagination

    def get_queryset(self):
        user = self.request.user 
        return models.GeckoCombinedSession.objects.filter(user=user)

    def list(self, request, *args, **kwargs):
        if request.query_params.get("nopaginate") == "true":
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return response.Response(serializer.data)
        
        return super().list(request, *args, **kwargs)


class GeckoCombinedDataSessionsTimeRange(generics.ListAPIView):
    serializer_class = serializers.GeckoCombinedDataSessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MediumPagination

    def get_queryset(self):
        user = self.request.user 
        minutes = self.request.query_params.get('minutes')

        qs = models.GeckoCombinedSession.objects.filter(user=user)

        if minutes:
            try:
                since = timezone.now() - datetime.timedelta(minutes=float(minutes))
                qs = qs.filter(started_on__gte=since)
            except (ValueError, TypeError):
                pass

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        totals = queryset.aggregate(
            total_steps=Sum('steps'),
            total_distance=Sum('distance'),
            session_count=Count('id'),
        )

        # compute total duration in python since it's derived from two fields
        total_duration = sum(
            max(0, (s.ended_on - s.started_on).total_seconds())
            for s in queryset.only('started_on', 'ended_on')
        )

        totals['total_duration_seconds'] = int(total_duration)
        total_hours = total_duration / 3600
        totals['total_hours'] = round(total_hours, 2)
        totals['steps_per_hour'] = round(totals['total_steps'] / total_hours, 1) if total_hours > 0 else 0
        totals['distance_per_hour'] = round(totals['total_distance'] / total_hours, 1) if total_hours > 0 else 0

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            resp = self.get_paginated_response(serializer.data)
            resp.data['totals'] = totals
            return resp

        serializer = self.get_serializer(queryset, many=True)
        return response.Response({'results': serializer.data, 'totals': totals})


class GeckoScoreStateView(generics.RetrieveUpdateAPIView):
    serializer_class = serializers.GeckoScoreStateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj, _ = models.GeckoScoreState.objects.get_or_create(user=self.request.user)
        obj.recompute_energy()
        return obj

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # If a streak is currently active, lock updates and return current state
        if instance.expires_at and instance.expires_at > timezone.now():
            serializer = self.get_serializer(instance)
            return response.Response(serializer.data)

        # Pull caps from GeckoConfigs
        config = models.GeckoConfigs.objects.filter(user=request.user).only(
            'max_score_multiplier', 'max_streak_length_seconds'
        ).first()
        max_multiplier = config.max_score_multiplier if config else 1
        max_streak_seconds = config.max_streak_length_seconds if config else 60

        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        if 'multiplier' in data:
            try:
                requested = int(data['multiplier'])
            except (TypeError, ValueError):
                return response.Response(
                    {'multiplier': 'Must be an integer.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if requested > max_multiplier:
                data['multiplier'] = max_multiplier

        # Determine expires_at from passed-in expiration_length (seconds),
        # capped at max_streak_length_seconds. Fall back to max if missing/invalid.
        requested_length = data.pop('expiration_length', None)
        length_seconds = max_streak_seconds
        if requested_length is not None:
            try:
                parsed = int(requested_length)
                if 0 < parsed <= max_streak_seconds:
                    length_seconds = parsed
            except (TypeError, ValueError):
                pass
        data['expires_at'] = timezone.now() + datetime.timedelta(seconds=length_seconds)

        serializer = self.get_serializer(
            instance, data=data, partial=kwargs.pop('partial', False)
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        instance.recompute_energy()
        instance.refresh_from_db()
        return response.Response(self.get_serializer(instance).data)
        # return response.Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dev_reset_energy(request):
    if not request.user.is_superuser:
        return response.Response(status=status.HTTP_403_FORBIDDEN)
    obj, _ = models.GeckoScoreState.objects.get_or_create(user=request.user)
    obj.energy = 1.0
    obj.surplus_energy = 0.0
    obj.revives_at = None
    obj.energy_updated_at = timezone.now()
    obj.save(update_fields=['energy', 'surplus_energy', 'revives_at', 'energy_updated_at'])
    return response.Response(serializers.GeckoScoreStateSerializer(obj).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dev_deplete_energy(request):
    if not request.user.is_superuser:
        return response.Response(status=status.HTTP_403_FORBIDDEN)
    obj, _ = models.GeckoScoreState.objects.get_or_create(user=request.user)
    obj.energy = 0.0
    obj.surplus_energy = 0.0
    obj.revives_at = None
    obj.energy_updated_at = timezone.now()
    obj.save(update_fields=['energy', 'surplus_energy', 'revives_at', 'energy_updated_at'])
    return response.Response(serializers.GeckoScoreStateSerializer(obj).data)


class GeckoEnergyLogView(generics.ListAPIView):
    serializer_class = serializers.GeckoEnergyLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MediumPagination

    def get_queryset(self):
        return models.GeckoEnergyLog.objects.filter(
            user=self.request.user
        ).order_by('-recorded_at')

    def list(self, request, *args, **kwargs):
        if request.query_params.get("nopaginate") == "true":
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return response.Response(serializer.data)
        return super().list(request, *args, **kwargs)


def gecko_analytics_dashboard(request):
    User = models.GeckoEnergySyncSample._meta.get_field('user').related_model
    user_ids = models.GeckoEnergySyncSample.objects.values_list('user_id', flat=True).distinct()
    users = User.objects.filter(id__in=user_ids).order_by('username')
    return render(request, 'gecko_analytics.html', {'users': users})


class GeckoEnergyLogAnalyticsView(generics.ListAPIView):
    serializer_class = serializers.GeckoEnergyLogAnalyticsSerializer
    permission_classes = [AllowAny]
    pagination_class = MediumPagination

    def get_queryset(self):
        qs = models.GeckoEnergyLog.objects.all().order_by('recorded_at')
        since = self.request.query_params.get('since')
        until = self.request.query_params.get('until')
        user_id = self.request.query_params.get('user_id')
        if since:
            parsed = parse_datetime(since)
            if parsed:
                qs = qs.filter(recorded_at__gte=parsed)
        if until:
            parsed = parse_datetime(until)
            if parsed:
                qs = qs.filter(recorded_at__lt=parsed)
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs

    def list(self, request, *args, **kwargs):
        if request.query_params.get('nopaginate') == 'true':
            serializer = self.get_serializer(self.filter_queryset(self.get_queryset()), many=True)
            return response.Response(serializer.data)
        return super().list(request, *args, **kwargs)


class GeckoEnergySyncSampleAnalyticsView(generics.ListAPIView):
    serializer_class = serializers.GeckoEnergySyncSampleAnalyticsSerializer
    permission_classes = [AllowAny]
    pagination_class = MediumPagination

    def get_queryset(self):
        qs = models.GeckoEnergySyncSample.objects.all().order_by('created_at')
        since = self.request.query_params.get('since')
        until = self.request.query_params.get('until')
        user_id = self.request.query_params.get('user_id')
        trigger = self.request.query_params.get('trigger')
        if since:
            parsed = parse_datetime(since)
            if parsed:
                qs = qs.filter(created_at__gte=parsed)
        if until:
            parsed = parse_datetime(until)
            if parsed:
                qs = qs.filter(created_at__lt=parsed)
        if user_id:
            qs = qs.filter(user_id=user_id)
        if trigger:
            qs = qs.filter(trigger=trigger)
        return qs

    def list(self, request, *args, **kwargs):
        if request.query_params.get('nopaginate') == 'true':
            serializer = self.get_serializer(self.filter_queryset(self.get_queryset()), many=True)
            return response.Response(serializer.data)
        return super().list(request, *args, **kwargs)


class GeckoEnergySyncSampleView(generics.ListAPIView):
    serializer_class = serializers.GeckoEnergySyncSampleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MediumPagination

    def get_queryset(self):
        qs = models.GeckoEnergySyncSample.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

        trigger = self.request.query_params.get('trigger')
        if trigger:
            qs = qs.filter(trigger=trigger)

        exclude = self.request.query_params.getlist('exclude_trigger')
        if exclude:
            qs = qs.exclude(trigger__in=exclude)

        since_raw = self.request.query_params.get('since')
        if since_raw:
            since_dt = parse_datetime(since_raw)
            if since_dt is not None:
                qs = qs.filter(created_at__gte=since_dt)

        until_raw = self.request.query_params.get('until')
        if until_raw:
            until_dt = parse_datetime(until_raw)
            if until_dt is not None:
                qs = qs.filter(created_at__lte=until_dt)

        return qs

    def list(self, request, *args, **kwargs):
        if request.query_params.get("nopaginate") == "true":
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return response.Response(serializer.data)
        return super().list(request, *args, **kwargs)


class GeckoConfigsView(generics.RetrieveUpdateAPIView):
    serializer_class = serializers.GeckoConfigsSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj, created = models.GeckoConfigs.objects.get_or_create(user=self.request.user)
        return obj

    def get_serializer_context(self):
        context = super().get_serializer_context()
        local_hour_str = self.request.query_params.get("local_hour")
        local_hour = None
        if local_hour_str is not None:
            try:
                parsed = int(local_hour_str)
                if 0 <= parsed <= 23:
                    local_hour = parsed
            except (TypeError, ValueError):
                local_hour = None
        if local_hour is None:
            local_hour = timezone.now().hour
        context["local_hour"] = local_hour
        return context
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gecko_config_choices(request):
    return response.Response({
        'personality_types': [{'value': v, 'label': l} for v, l in models.Personality.choices],
        'memory_types': [{'value': v, 'label': l} for v, l in models.Memory.choices],
        'active_hours_types': [{'value': v, 'label': l} for v, l in models.ActivityHours.choices],
        'story_types': [{'value': v, 'label': l} for v, l in models.Story.choices],
    })

class UserProfileDetail(generics.RetrieveUpdateAPIView):
    serializer_class = serializers.UserProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'user_id'

    def get_object(self):
        user_id = self.kwargs['user_id']
        return get_object_or_404(models.UserProfile, user__id=user_id)

class AddPointsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = serializers.AddPointsSerializer(data=request.data)
        if not serializer.is_valid():
            return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount = serializer.validated_data['amount']
        reason = serializer.validated_data['reason']

        with transaction.atomic():
            models.PointsLedger.objects.create(
                user=request.user,
                amount=amount,
                reason=reason,
            )
            models.UserProfile.objects.filter(user=request.user).update(
                total_points=F('total_points') + amount
            )

        profile = models.UserProfile.objects.get(user=request.user)
        return response.Response(
            {'total_points': profile.total_points},
            status=status.HTTP_200_OK
        )


class PointsLedgerView(generics.ListAPIView):
    serializer_class = serializers.PointsLedgerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return models.PointsLedger.objects.filter(user=self.request.user)
    
class GeckoPointsLedgerView(generics.ListAPIView):
    serializer_class = serializers.GeckoPointsLedgerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MediumPagination

    def get_queryset(self):
        return models.GeckoPointsLedger.objects.filter(user=self.request.user)


    def list(self, request, *args, **kwargs):
        if request.query_params.get("nopaginate") == "true":
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return response.Response(serializer.data)
        
        return super().list(request, *args, **kwargs)

     
 

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
class MediumPagination(PageNumberPagination):
    page_size = 30

class UserCategoriesHistoryAll(generics.ListAPIView):
    serializer_class = serializers.UserCategoriesHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MediumPagination

    def get_queryset(self):
        user = self.request.user
        CompletedCapsule = apps.get_model('friends', 'CompletedThoughtCapsulez')

        only_with_capsules = self.request.query_params.get("only_with_capsules", "false").lower() == "true"
        user_category_id = self.request.query_params.get("user_category_id")
        friend_id = self.request.query_params.get("friend_id")


        filters = {"user": user}

        if friend_id:
            filters["friend_id"] = friend_id

        if user_category_id:
            filters["user_category_id"] = user_category_id

        capsule_qs = CompletedCapsule.objects.filter(**filters).select_related(
            "friend", "user", "hello", "user_category"
        ) 

        qs = models.UserCategory.objects.filter(user=user).prefetch_related(
            Prefetch("completed_thought_capsules", queryset=capsule_qs, to_attr="prefetched_capsules")
        )

        

        if only_with_capsules:
            qs = qs.annotate(capsule_count=Count('completed_thought_capsules', filter=Q(completed_thought_capsules__in=capsule_qs)))
            qs = qs.filter(capsule_count__gt=0)

        # if only_with_capsules: 
        #     # Return only UserCategories that have any prefetched capsules
        #     qs = [uc for uc in qs if uc.prefetched_capsules]
        # else:
        #     qs = qs.filter(completed_thought_capsules__user=user).distinct()

        return qs

    def get_serializer_context(self): 
        context = super().get_serializer_context()
        context['friend_id'] = self.request.query_params.get("friend_id")
        return context



class UserCategoriesHistoryCountOnly(generics.ListAPIView):
    serializer_class = serializers.UserCategoriesHistoryCountSerializer
    permission_classes = [IsAuthenticated]

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
    
 
class UserCategoriesHistoryCapsuleIdsOnly(generics.ListAPIView):
    serializer_class = serializers.UserCategoriesHistoryCapsuleIdsSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        CompletedCapsule = apps.get_model('friends', 'CompletedThoughtCapsulez')  # dynamically loaded
  
        friend_id = self.request.query_params.get("friend_id")
        only_with_capsules = self.request.query_params.get("only_with_capsules", "false").lower() == "true"

        # Build capsule filtering logic
        capsule_filter = Q(user=user)
        if friend_id:
            capsule_filter &= Q(friend_id=friend_id)

        capsule_qs = CompletedCapsule.objects.filter(capsule_filter)

        # Prefetch capsules using to_attr
        capsule_prefetch = Prefetch(
            'completed_thought_capsules',
            queryset=capsule_qs,
            to_attr='prefetched_capsules'
        )

        qs = models.UserCategory.objects.filter(user=user).prefetch_related(capsule_prefetch)

        # Filter categories that have capsules if requested
        if only_with_capsules:
            qs = [uc for uc in qs if getattr(uc, 'prefetched_capsules', [])]

        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['friend_id'] = self.request.query_params.get("friend_id")
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



# class UserAddressesAll(generics.ListAPIView):
#     serializer_class = serializers.UserAddressSerializer
#     permissions_classes = [IsAuthenticated]

#     def get_queryset(self):
#         user = self.request.user
#         return models.UserAddress.objects.filter(user=user)


class UserAddressesAll(generics.GenericAPIView):
    serializer_class = serializers.UserAddressSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # Fetch saved addresses
        saved_qs = models.UserAddress.objects.filter(user=user)
        saved = serializers.UserAddressSerializer(saved_qs, many=True).data

        # TEMP AND CHOSEN ARE JUST STORAGE PLACES FOR FRONT END TANSTACK
        # DO NOT REFACTOR
        return response.Response({
            "saved": saved,
            "temp": [],       
            "chosen": None 
        }, status=status.HTTP_200_OK)
    
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
    

import resend

@api_view(['POST'])
@permission_classes([AllowAny])
def send_email_to_user(request):
    email_address = request.data.get('email')
    
    if not email_address:
        return response.Response({'error': 'Email address is required'}, status=400)

    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": [email_address],
            "subject": "Welcome to Our Service",
            "text": "Thank you for joining us! We are excited to have you as part of our community.",
        })
        return response.Response({'success': 'Email successfully sent'}, status=200)
    except Exception as e:
        return response.Response({'error': f'Failed to send email: {str(e)}'}, status=500)

# @api_view(['POST'])
# @permission_classes([AllowAny])
# def send_email_to_user(request):
#     """
#     Send an email to the provided email address with a predefined subject and message.
#     """
#     email_address = request.data.get('email')
    
    
#     if not email_address:
#         # print(request.data)
#         # print('no email')
#         # print(request.content_type)
#         # print(request.data)

#         return response.Response({'error': 'Email address is required'}, status=400)

#     subject = 'Welcome to Our Service'  # Predefined subject
#     message = 'Thank you for joining us! We are excited to have you as part of our community.'  # Predefined message

#     try:
       
#         # Send the email
#         send_mail(
#             subject,
#             message,
#             settings.DEFAULT_FROM_EMAIL,  # Ensure this is set in your settings.py
#             [email_address],
#         )
#         return response.Response({'success': f'Email successfully sent'}, status=200) #to {email_address}
#     except Exception as e:
#         return response.Response({'error': f'Failed to send email: {str(e)}'}, status=500)
    


class RequestPasswordResetCodeView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        if not email:
            return response.Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = models.BadRainbowzUser.objects.get(email=email)
        except models.BadRainbowzUser.DoesNotExist:
            return response.Response({"detail": "If the email exists, a reset code has been sent."}, status=status.HTTP_200_OK)

        reset_code = user.generate_password_reset_code()

        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": [email],
            "subject": "Your Password Reset Code",
            "text": f"Your password reset code is: {reset_code}",
        })

        return response.Response({"detail": "If the email exists, a reset code has been sent."}, status=status.HTTP_200_OK)


# class RequestPasswordResetCodeView(APIView):
#     permission_classes = [AllowAny]
#     def post(self, request, *args, **kwargs):
#         email = request.data.get('email')
#         if not email:
#             return response.Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             user = models.BadRainbowzUser.objects.get(email=email)
#         except models.BadRainbowzUser.DoesNotExist:
#             # Do not disclose if the email exists to prevent user enumeration
#             return response.Response({"detail": "If the email exists, a reset code has been sent."}, status=status.HTTP_200_OK)

#         # Generate and save the reset code
#         reset_code = user.generate_password_reset_code()

#         # Send the reset code via email
#         send_mail(
#             subject="Your Password Reset Code",
#             message=f"Your password reset code is: {reset_code}",
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[email],
#         )

#         return response.Response({"detail": "If the email exists, a reset code has been sent."}, status=status.HTTP_200_OK)


LIVE_SESH_DURATION = datetime.timedelta(hours=24)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_current_live_sesh(request):
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    user = request.user
    sesh = models.UserFriendCurrentLiveSesh.objects.filter(user=user).first()
    if not sesh:
        return response.Response(
            {'detail': 'No active sesh.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    partner_id = sesh.other_user_id
    now = timezone.now()

    with transaction.atomic():
        models.UserFriendCurrentLiveSesh.objects.filter(
            user_id__in=[user.id, partner_id],
        ).update(expires_at=now)

    # Force-disconnect both gecko sockets if they're connected.
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        payload = {'cancelled_by': user.id}
        for uid in (user.id, partner_id):
            async_to_sync(channel_layer.group_send)(
                f'gecko_energy_{uid}',
                {'type': 'live_sesh_cancelled', 'data': payload},
            )

    return response.Response(
        {'detail': 'Live sesh cancelled.', 'partner_id': partner_id},
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_live_sesh(request):
    user = request.user
    try:
        sesh = models.UserFriendCurrentLiveSesh.objects.select_related('other_user').get(user=user)
    except models.UserFriendCurrentLiveSesh.DoesNotExist:
        return response.Response(None, status=status.HTTP_200_OK)

    return response.Response(
        serializers.UserFriendCurrentLiveSeshSerializer(sesh).data,
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_live_sesh_invites(request):
    user = request.user
    now = timezone.now()

    sent_qs = models.UserFriendLiveSeshInvite.objects.filter(
        sender=user,
        accepted_on__isnull=True,
        invite_expires_on__gt=now
    ).select_related('sender', 'recipient').order_by('-created_on')

    pending_qs = models.UserFriendLiveSeshInvite.objects.filter(
        recipient=user,
        accepted_on__isnull=True,
        invite_expires_on__gt=now
    ).select_related('sender', 'recipient').order_by('-created_on')

    return response.Response({
        'sent': serializers.UserFriendLiveSeshInviteSerializer(sent_qs, many=True).data,
        'pending': serializers.UserFriendLiveSeshInviteSerializer(pending_qs, many=True).data,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_live_sesh_invite(request, invite_id):
    user = request.user

    try:
        invite = models.UserFriendLiveSeshInvite.objects.select_related(
            'sender', 'recipient'
        ).get(
            pk=invite_id,
            recipient=user,
            accepted_on__isnull=True,
        )
    except models.UserFriendLiveSeshInvite.DoesNotExist:
        return response.Response(
            {'detail': 'Invite not found or already accepted.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    now = timezone.now()

    # optional safety check (don’t change flow, just reject expired)
    if invite.invite_expires_on and invite.invite_expires_on <= now:
        return response.Response(
            {'detail': 'Invite expired.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    expires_at = now + LIVE_SESH_DURATION
    sender = invite.sender
    recipient = invite.recipient

    from friends.models import Friend
    sender_friend = Friend.objects.filter(
        user=sender, linked_user=recipient,
    ).only('id').first()

    recipient_friend = Friend.objects.filter(
        user=recipient, linked_user=sender,
    ).only('id').first()

    with transaction.atomic():
        invite.accepted_on = now
        invite.save(update_fields=['accepted_on', 'updated_on'])

        host_sesh, _ = models.UserFriendCurrentLiveSesh.objects.update_or_create(
            user=sender,
            defaults={
                'other_user': recipient,
                'friend': sender_friend,
                'is_host': True,
                'session_start': now,
                'expires_at': expires_at,
                'current_log': None,
            },
        )

        my_sesh, _ = models.UserFriendCurrentLiveSesh.objects.update_or_create(
            user=recipient,
            defaults={
                'other_user': sender,
                'friend': recipient_friend,
                'is_host': False,
                'session_start': now,
                'expires_at': expires_at,
                'current_log': host_sesh.current_log,
            },
        )

    notify_user(sender.id, 'live_sesh_invite_accepted', {
        'invite_id': invite.id,
        'accepted_by': recipient.id,
        'accepted_by_username': recipient.username,
        'session_start': now.isoformat(),
        'expires_at': expires_at.isoformat(),
    })

    return response.Response(
        serializers.UserFriendCurrentLiveSeshSerializer(my_sesh).data,
        status=status.HTTP_200_OK,
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decline_live_sesh_invite(request, invite_id):
    user = request.user

    try:
        invite = models.UserFriendLiveSeshInvite.objects.get(
            pk=invite_id,
            recipient=user,
            accepted_on__isnull=True,
        )
    except models.UserFriendLiveSeshInvite.DoesNotExist:
        return response.Response(
            {'detail': 'Invite not found or already handled.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    invite.invite_expires_on = timezone.now()
    invite.save(update_fields=['invite_expires_on', 'updated_on'])

    notify_user(invite.sender_id, 'live_sesh_invite_declined', {
        'invite_id': invite.id,
        'declined_by': user.id,
        'declined_by_username': user.username,
    })

    return response.Response({'status': 'declined'}, status=status.HTTP_200_OK)