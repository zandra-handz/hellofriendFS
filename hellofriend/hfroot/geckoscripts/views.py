from . import models
from . import serializers

import users.models

from django.db import transaction
from django.utils.dateparse import parse_datetime

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_welcome_scripts(request):
    user = request.user

    try:
        config = users.models.GeckoConfigs.objects.get(user=user)
    except users.models.GeckoConfigs.DoesNotExist:
        return Response([], status=status.HTTP_200_OK)

    personality = config.personality_type
    memory = config.memory_type
    activity_hours = config.active_hours_type
    story = config.story_type

    personality_filter = {
        users.models.Personality.CURIOUS: 'personality_curious',
        users.models.Personality.SCIENTIFIC: 'personality_scientific',
        users.models.Personality.BRAVE: 'personality_brave',
    }
    memory_filter = {
        users.models.Memory.AMNESIAC: 'memory_amnesiac',
        users.models.Memory.REMEMBERSOME: 'memory_remembersome',
        users.models.Memory.REMEMBERMANY: 'memory_remembermany',
    }
    hours_filter = {
        users.models.ActivityHours.DAY: 'activity_hours_day',
        users.models.ActivityHours.NIGHT: 'activity_hours_night',
        users.models.ActivityHours.RANDOM: 'activity_hours_random',
    }
    story_filter = {
        users.models.Story.LEARNER: 'story_learner',
        users.models.Story.NOMMER: 'story_nommer',
        users.models.Story.ESCAPER: 'story_escaper',
    }

    filter_kwargs = {
        personality_filter[personality]: True,
        memory_filter[memory]: True,
        hours_filter[activity_hours]: True,
        story_filter[story]: True,
        'is_active': True,
    }

    scripts = models.Welcome.objects.filter(**filter_kwargs)
    serialized = serializers.WelcomeSerializer(scripts, many=True).data

    user_name = user.first_name or user.username
    for script in serialized:
        script['body'] = script['body'].format_map({'user_name': user_name})

    return Response(serialized, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_welcome_scripts(request):
    user = request.user
    entries = request.data.get('entries')
    if not isinstance(entries, list):
        return Response({'error': 'entries must be a list'}, status=status.HTTP_400_BAD_REQUEST)

    records = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        script_id = e.get('script_id')
        shown_at = parse_datetime(str(e.get('shown_at', ''))) if e.get('shown_at') else None
        if not script_id or not shown_at:
            continue
        records.append(models.WelcomeScriptLedger(
            user=user,
            script_id=script_id,
            shown_at=shown_at,
        ))

    if records:
        with transaction.atomic():
            models.WelcomeScriptLedger.objects.bulk_create(records)

    return Response({'created': len(records)}, status=status.HTTP_200_OK)
