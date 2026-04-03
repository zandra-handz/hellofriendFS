from rest_framework import serializers
from . import models





class WelcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Welcome
        fields = '__all__'
        read_only_fields = [
            'id',
            'user',
            'created_on',

        ]


class WelcomeScriptLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.WelcomeScriptLedger
        fields = ['id', 'script', 'shown_at', 'created_on']
        read_only_fields = ['id', 'created_on']