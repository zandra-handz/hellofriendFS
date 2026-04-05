from rest_framework import serializers
from . import models





class WelcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Welcome
        fields = '__all__'
        read_only_fields = [
            'id', 
            'created_on',

        ]


class ScoreRuleSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.ScoreRule
        fields = '__all__'
        read_only_fields = [
            'id',
            'code',
            'label',
            'points',
            'version',
            'created_on',
            'updated_on',
        ]

class WelcomeScriptLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.WelcomeScriptLedger
        fields = ['id', 'script', 'shown_at', 'created_on']
        read_only_fields = ['id', 'created_on']