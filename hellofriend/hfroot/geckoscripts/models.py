
from django.db import models
from django.contrib.auth import get_user_model

# Create your models here.


class Welcome(models.Model):

    body = models.TextField()
    label = models.CharField(max_length=64, null=False, blank=False)

    is_active = models.BooleanField(default=True)
    is_experimental = models.BooleanField(default=False)
    is_easter_egg = models.BooleanField(default=False)

    # Personality — which types can use this script (all True = universal)
    personality_curious    = models.BooleanField(default=True)
    personality_scientific = models.BooleanField(default=True)
    personality_brave      = models.BooleanField(default=True)
 
    memory_amnesiac        = models.BooleanField(default=True)
    memory_remembersome    = models.BooleanField(default=True)
    memory_remembermany    = models.BooleanField(default=True)
 
    activity_hours_day             = models.BooleanField(default=True)
    activity_hours_night            = models.BooleanField(default=True)
    activity_hours_random           = models.BooleanField(default=True)

    story_learner          = models.BooleanField(default=True)
    story_nommer           = models.BooleanField(default=True)
    story_escaper          = models.BooleanField(default=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)


    def __str__(self):
        flags = []
        if self.is_experimental:
            flags.append('experimental')
        if self.is_easter_egg:
            flags.append('easter egg')
        if not self.is_active:
            flags.append('inactive')
        suffix = f" [{', '.join(flags)}]" if flags else ''
        return f"{self.label}{suffix}"


# NOTE: WelcomeScriptLedger is written by the front end only (via geckoscripts/ledger/).
# Script selection and display logic lives entirely on the front end to keep it
# fast and reactive. The front end batches entries and POSTs them in the background
# — the backend never decides what gets shown or when.
class WelcomeScriptLedger(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='welcome_script_ledger')
    script = models.ForeignKey(Welcome, on_delete=models.SET_NULL, null=True, related_name='ledger_entries')
    shown_at = models.DateTimeField()
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-shown_at']

    def __str__(self):
        return f"{self.user} — {self.script.label if self.script else 'deleted'} @ {self.shown_at}"


class ScoreRule(models.Model):
    code = models.CharField(max_length=64)
    label = models.CharField(max_length=128, blank=True)
    points = models.IntegerField(default=0)
    version = models.PositiveIntegerField(default=1)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code', 'version']
        constraints = [
            models.UniqueConstraint(fields=['code', 'version'], name='unique_scorerule_code_version'),
        ]

    def __str__(self):
        return f"{self.code}: {self.points}"





