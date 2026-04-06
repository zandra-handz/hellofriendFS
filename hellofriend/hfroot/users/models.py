
from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
# from django.contrib.postgres.fields import ArrayField
from django.db import models
# import friends.models could cause circular import because this file imports users. using 'friends.ThoughtCapsulez' and 'friends.Image' below instead

# Create your models here.
from datetime import datetime, timedelta
from . import utils
from . import constants
 


def format_date(dt):
    current_year = datetime.now().year #change to timezone.now in future?
    if dt.year == current_year:
        formatted_date = dt.strftime('%B %#d at %#I:%M %p')
    else:
        formatted_date = dt.strftime('%B %#d %Y at %#I:%M %p')

    return formatted_date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.db import models, transaction
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext as _
from .managers import CustomUserManager


# Create your models here.
class BadRainbowzUser(AbstractUser):

    # Username and email must be unique.
    username = models.CharField(_('username'), unique=True, max_length=150)
    email = models.EmailField(_('email address'), unique=True)

    password_reset_code = models.CharField(max_length=128, blank=True, null=True)
    code_expires_at = models.DateTimeField(blank=True, null=True)

    addresses = models.JSONField(blank=True, null=True)
    phone_number = models.CharField(_('phone number'), max_length=15, blank=True, null=True)
    is_active_user = models.BooleanField(default=True)

    is_subscribed_user = models.BooleanField(default=False)
    subscription_id = models.CharField(max_length=150, blank=True, null=True)
    subscription_expiration_date = models.DateTimeField(null=True, blank=True)

    is_inactive_user = models.BooleanField(default=False)
    is_banned_user = models.BooleanField(default=False)
    is_test_user = models.BooleanField(default=False)
    created_on = models.DateTimeField(default=timezone.now)
    last_updated_at = models.DateTimeField(auto_now=True)

    app_setup_complete = models.BooleanField(default=False)

    # I think this can be taken out because already exists automatically.
    last_login_at = models.DateTimeField(blank=True, null=True)

    login_attempts = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ('email',)  

    objects = CustomUserManager()

    class Meta:
        ordering = ['username']

    def __str__(self):
        return self.username
    

    def generate_password_reset_code(self):
        import random
        from datetime import timedelta
        from django.contrib.auth.hashers import make_password

        code = f"{random.randint(100000, 999999)}"  # 6-digit code — raw code returned to send in email
        self.password_reset_code = make_password(code)  # store hash, never the raw code
        self.code_expires_at = timezone.now() + timedelta(minutes=10)
        self.save()
        return code
        
    def update_subscription(self, subscription_id, expiration_date, is_subscribed=True):
        self.subscription_id = subscription_id
        self.subscription_expiration_date = expiration_date
        self.is_subscribed_user = is_subscribed
        self.save()


    def check_subscription_active(self):
        if self.is_subscribed_user:

            if self.subscription_expiration_date:
                active = self.subscription_expiration_date > timezone.now()
                if not active:
                    self.is_subscribed_user = False 
                    self.save()
            else:
                self.is_subscribed_user = False 
                self.save()

    
    def add_address(self, address_data):
        """
        Add address if valid.
        """

        print(address_data)
        if self.addresses is None:
            self.addresses = []

        address_value = address_data['address']  # Access 'address' directly
        coordinates = utils.get_coordinates(address_value)

        if coordinates:
            new_address_entry = {
                'title': address_data['title'],  # Access 'title' directly
                'address': address_value,
                'coordinates': coordinates
            }

            self.addresses.append(new_address_entry)
            self.save()
            return True
        return False

    
    def add_validated_address(self, title, address, coordinates):
        """
        Append validated address to addresses list.
        """
        if self.addresses is None:
            self.addresses = []

        if 'addresses' not in self.__dict__:
            self.addresses = []

        new_address_entry = {
            'title': title,
            'address': address,
            'coordinates': coordinates
        }

        self.addresses.append(new_address_entry)
        self.save()

    def save(self, *args, **kwargs):
        created = not self.pk  # Check if the instance is being created
        super().save(*args, **kwargs)  # Call the original save method

        # If the instance is being created, create UserProfile and UserSettings
        if created:
            with transaction.atomic():
                UserProfile.objects.create(user=self)
                UserSettings.objects.create(user=self)
                GeckoConfigs.objects.create(user=self)
                GeckoScoreState.objects.create(user=self)
                GeckoCombinedData.objects.create(user=self) 
                UserCategory.objects.create(user=self, name='Grab bag', is_deletable=False)
                


class UserCategory(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='user_categories')
    
    name = models.CharField(max_length=50)
    thought_capsules = models.ManyToManyField('friends.ThoughtCapsulez', related_name='user_categories', blank=True, null=True)
    
    completed_thought_capsules = models.ManyToManyField(
    'friends.CompletedThoughtCapsulez',
    related_name='user_categories',
    blank=True
    )
   
    images = models.ManyToManyField('friends.Image', related_name='user_categories', blank=True, null=True)
    # Can add more as needed
    description = models.CharField(max_length=5000, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    max_active = models.PositiveIntegerField(default=20)
    is_in_top_five = models.BooleanField(default=False)
    is_deletable = models.BooleanField(default=True)


    class Meta:
        ordering = ('name',) # order alphabetically in ascending order
        verbose_name = "User Category"
        verbose_name_plural = "User Categories"
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_user_category_name')
        ]

    @classmethod
    def get_or_create_grab_bag_category(cls, user):
        return cls.objects.get_or_create(
            user=user,
            name='Grab bag',
            defaults={
                'is_deletable': False,
                'is_active': True,
                'is_in_top_five': False,
            }
        )
 

    def clean(self): 
        if self.is_active:
            active_count = UserCategory.objects.filter(user=self.user, is_active=True).exclude(pk=self.pk).count()
            if active_count >= self.max_active:
                raise ValidationError(f"User can have at most {self.max_active} active categories.")

    def save(self, *args, **kwargs):
        self.full_clean() # runs all validation checks on model, beyond the ones added in clean()
        super().save(*args, **kwargs)

    # def delete(self, *args, **kwargs):
    #     if not self.is_deletable:
    #         raise ValidationError("This category cannot be deleted.")
    #     super().delete(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not self.is_deletable:
            raise ValidationError("This category cannot be deleted.")

        with transaction.atomic():
            # Avoid circular import by fetching model dynamically
            ThoughtCapsulez = apps.get_model('friends', 'ThoughtCapsulez')

            # Get or create the 'Grab bag' for this user
            grab_bag, _ = UserCategory.get_or_create_grab_bag_category(self.user)

            # Reassign all related thought capsules to the Grab bag
            ThoughtCapsulez.objects.filter(user_category=self).update(user_category=grab_bag)

            super().delete(*args, **kwargs)




    def __str__(self):
        return f"Category: '{self.name}'"
 





class UserAddress(models.Model): 
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='address')
   
    title = models.CharField(max_length=64, null=True, blank=False)
    address = models.CharField(max_length=64, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    validated_address = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ('-created_on',)
        unique_together = (('user', 'title'), ('user', 'address'))

    def calculate_coordinates(self):

        if not self.address:
            self.address = self.title
 
        coordinates = utils.get_coordinates(self.address)

        if coordinates:
            self.latitude = coordinates[0]
            self.longitude = coordinates[1]
            self.validated_address = True 

    
    def save(self, *args, **kwargs):

        if not self.pk:
            self.calculate_coordinates()

        if self.is_default:
            UserAddress.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)

        super().save(*args, **kwargs)


    def __str__(self):
        return f"User address: {self.address}, validated: {self.validated_address}"


# decided against for now, adding to settings instead
# class UserAutoSelectSettings(models.Model):
#     user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='user_friend_select_settings')
    # pinned_friend = models.ForeignKey(
    #     'friends.Friend', 
    #     related_name='pinned_in_auto_select_settings', 
    #     blank=True, 
    #     null=True, 
    #     on_delete=models.SET_NULL
    # )
    # upcoming_friend = models.ForeignKey(
    #     'friends.Friend', 
    #     related_name='upcoming_in_auto_select_settings', 
    #     blank=True, 
    #     null=True, 
    #     on_delete=models.SET_NULL
    # )
#     created_on = models.DateTimeField(auto_now_add=True)
#     updated_on = models.DateTimeField(auto_now=True)

#     class Meta:
#         verbose_name = "User auto settings"
#         verbose_name_plural = "User auto settings"

#     def __str__(self):
#         return f"Auto select settings for {self.user.username}"
    

class UserSettings(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name='settings')
    receive_notifications = models.BooleanField(default=False)
    simplify_app_for_focus = models.BooleanField(default=False)

    # going to deprecate, too hard to read/follow ###################
    lock_in_next = models.BooleanField(default=False) # a boolean to use to automatically select next friend when user logs in
    lock_in_custom_string = models.CharField(max_length=1000, null=True, blank=True) # did not want a connection to friends table, but can store id or name here and set/retrieve on front end to automatically select friend chosen by user on log in
    #################################################################

    language_preference = models.CharField(max_length=10, choices=[('en', 'English'), ('es', 'Spanish')], blank=True)
    # Accessibility settings options for front end
    large_text = models.BooleanField(default=False)
    high_contrast_mode = models.BooleanField(default=False)
    screen_reader = models.BooleanField(default=False)
    manual_dark_mode = models.BooleanField(null=True, blank=True)
    expo_push_token = models.CharField(max_length=255, null=True, blank=True) 
    user_default_category = models.ForeignKey(UserCategory, null=True, blank=True, on_delete=models.SET_NULL)

    pinned_friend = models.ForeignKey(
        'friends.Friend', 
        related_name='pinned_in_settings', 
        blank=True, 
        null=True, 
        on_delete=models.SET_NULL
    )
    upcoming_friend = models.ForeignKey(
        'friends.Friend', 
        related_name='upcoming_in_settings', 
        blank=True, 
        null=True, 
        on_delete=models.SET_NULL
    )
    use_auto_select = models.BooleanField(default=False)

    # front end controls, toggles on/off as needed. this does not interact with anything in the backend
    # setting this to null on the friend home screen on front end, in friend header component (as of 3/31/2026)
    new_friend = models.ForeignKey(
        'friends.Friend', 
        related_name='new_friend_in_settings', 
        blank=True, 
        null=True, 
        on_delete=models.SET_NULL
    )

    created_on = models.DateTimeField(default=timezone.now) # timezone here because I need to backfill existing instances
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User settings"
        verbose_name_plural = "User settings"

    def __str__(self):
        return f"Settings for {self.user.username}"
    
class UserProfile(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name='profile')
    
    first_name = models.CharField(_('first name'), max_length=30, blank=True, default='')
    last_name = models.CharField(_('last name'), max_length=30, blank=True, default='')
    date_of_birth = models.DateField(_('date of birth'), blank=True, null=True)
    
    #profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    gender = models.CharField(_('gender'), max_length=10, choices=[('NB', 'Non-Binary'), ('M', 'Male'), ('F', 'Female'), ('O', 'Other'), ('No answer', 'No answer')], blank=True, default='')
    total_points = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    

class Memory(models.IntegerChoices):
    AMNESIAC = 1, "Amnesiac",
    REMEMBERSOME = 2, "Remember Some",
    REMEMBERMANY = 3, "Remember Many"


class Personality(models.IntegerChoices):
    CURIOUS = 1, "Curious",
    SCIENTIFIC = 2, "Scientific",
    BRAVE = 3, "Brave"
    

class ActivityHours(models.IntegerChoices):
    DAY = 1, "Day",
    NIGHT = 2, "Night",
    RANDOM = 3, "Random"


class Story(models.IntegerChoices):
    LEARNER = 1, "Learner", 
    NOMMER = 2, "Nommer",
    ESCAPER = 3, "Escaper"


class GeckoScoreState(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name='geckoscorestate')
    base_multiplier = models.PositiveIntegerField(default=1)
    multiplier = models.PositiveIntegerField(default=1)

    expires_at = models.DateTimeField(default=timezone.now)


    energy = models.FloatField(default=1.0)
    surplus_energy = models.FloatField(default=0.0)
    energy_updated_at = models.DateTimeField(default=timezone.now)
    revives_at = models.DateTimeField(null=True, blank=True)




    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def recompute_energy(self):
        now = timezone.now()
        elapsed = (now - self.energy_updated_at).total_seconds()
        if elapsed <= 0:
            return

        configs = getattr(self.user, 'geckoconfigs', None)
        stamina = getattr(configs, 'stamina', 1.0) if configs else 1.0
        max_active_hours = getattr(configs, 'max_active_hours', 16) if configs else 16
        full_rest_hours = 24 - max_active_hours
        recharge_per_second = 1.0 / (full_rest_hours * 3600)
        streak_recharge_per_second = recharge_per_second * 0.5

        sessions = self.user.geckocombinedsession_set.filter(
            ended_on__gt=self.energy_updated_at
        )
        new_steps = sum(s.steps or 0 for s in sessions)
        active_seconds = sum(
            max(0, (s.ended_on - s.started_on).total_seconds())
            for s in sessions
            if s.started_on and s.ended_on
        )
        rest_seconds = max(0, elapsed - active_seconds)

        streak_is_active = (
            self.multiplier > self.base_multiplier
            and self.expires_at > self.energy_updated_at
        )

        if streak_is_active and active_seconds > 0:
            streak_end = min(self.expires_at, now)
            streak_seconds = max(0, (streak_end - self.energy_updated_at).total_seconds())
            streak_ratio = min(1.0, streak_seconds / elapsed)

            streak_active_seconds = active_seconds * streak_ratio
            streak_steps = new_steps * (streak_active_seconds / active_seconds)
            normal_steps = new_steps - streak_steps

            fatigue = (
                (normal_steps * constants.STEP_FATIGUE_PER_STEP)
                + (streak_steps * constants.STEP_FATIGUE_PER_STEP * constants.STREAK_FATIGUE_MULTIPLIER)
            )
            recharge = (
                (rest_seconds * recharge_per_second)
                + (streak_active_seconds * streak_recharge_per_second)
            )
        else:
            fatigue = new_steps * constants.STEP_FATIGUE_PER_STEP
            recharge = rest_seconds * recharge_per_second

        effective_recharge = recharge * stamina
        effective_fatigue = fatigue / stamina

        net = effective_recharge - effective_fatigue

        if net >= 0:
            room_in_main = 1.0 - self.energy
            if net <= room_in_main:
                self.energy += net
            else:
                self.energy = 1.0
                self.surplus_energy = min(
                    constants.SURPLUS_CAP,
                    self.surplus_energy + (net - room_in_main)
                )
        else:
            drain = -net
            if self.surplus_energy >= drain:
                self.surplus_energy -= drain
            else:
                drain -= self.surplus_energy
                self.surplus_energy = 0.0
                self.energy = max(0.0, self.energy - drain)

        revival_seconds = getattr(configs, 'max_duration_till_revival', 60) if configs else 60

        if self.energy <= 0.0:
            if self.revives_at and now >= self.revives_at:
                self.energy = 0.05
                self.revives_at = None
            elif not self.revives_at:
                self.revives_at = now + timedelta(seconds=revival_seconds)
        else:
            self.revives_at = None

        self.energy_updated_at = now
        self.save(update_fields=["energy", "surplus_energy", "energy_updated_at", "revives_at"])

        latest_session = sessions.order_by('-ended_on').first()
        GeckoEnergyLog.objects.create(
            user=self.user, energy=self.energy,
            surplus_energy=self.surplus_energy, steps=new_steps,
            friend=latest_session.friend if latest_session else None,
            recorded_at=now,
        )
        if now.hour == 0 and now.minute < 2:
            GeckoEnergyLog.prune_old(self.user)





class GeckoEnergyLog(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='geckoenergylog_set')
    energy = models.FloatField()
    surplus_energy = models.FloatField()
    steps = models.PositiveIntegerField(default=0)
    friend = models.ForeignKey('friends.Friend', on_delete=models.SET_NULL, null=True, blank=True)
    recorded_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['user', 'recorded_at']),
        ]

    @classmethod
    def prune_old(cls, user, cutoff_days=365):
        cls.objects.filter(
            user=user,
            recorded_at__lt=timezone.now() - timedelta(days=cutoff_days),
        ).delete()


class GeckoConfigs(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name='geckoconfigs')
    
    
    
    personality_type = models.IntegerField(choices=Personality.choices, default=Personality.CURIOUS)
    memory_type = models.IntegerField(choices=Memory.choices, default=Memory.AMNESIAC)
    active_hours_type = models.IntegerField(choices=ActivityHours.choices, default=ActivityHours.DAY)
    story_type = models.IntegerField(choices=Story.choices, default=Story.LEARNER)

    stamina = models.FloatField(default=1.0)  # 0.5 = low stamina, 1.0 = normal, 2.0 = high



    # I would prefer this. it only works with postgres so won't work in local
    # active_hours = ArrayField(
    #     models.SmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(23)]),
    #     size=24,
    #     default=list,
    #     blank=True,
    #     )

    max_active_hours = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)], default=(16))
    max_duration_till_revival = models.PositiveIntegerField(default=60)  # seconds at 0 energy before auto-revival
    max_score_multiplier = models.PositiveIntegerField(default=3)
    max_streak_length_seconds = models.PositiveIntegerField(default=10)

    active_hours = models.JSONField(default=list, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Gecko configuration for {self.user.username}"
    
    
    def build_default_active_hours(self):
        n = min(max(int(self.max_active_hours), 1), 24)

        if self.active_hours_type == ActivityHours.DAY:
            start = 12 - (n // 2)
            return [(start + i) % 24 for i in range(n)]

        if self.active_hours_type == ActivityHours.NIGHT:
            start = (0 - (n // 2)) % 24
            return [(start + i) % 24 for i in range(n)]

        if self.active_hours_type == ActivityHours.RANDOM:
            step = 24 / n
            hours = []
            seen = set()

            for i in range(n):
                hour = int(round(i * step)) % 24
                if hour not in seen:
                    seen.add(hour)
                    hours.append(hour)

            if len(hours) < n:
                for hour in range(24):
                    if hour not in seen:
                        seen.add(hour)
                        hours.append(hour)
                    if len(hours) == n:
                        break

            return hours

        start = 12 - (n // 2)
        return [(start + i) % 24 for i in range(n)]

    def save(self, *args, **kwargs):
        is_create = self.pk is None

        if is_create and not self.active_hours:
            self.active_hours = self.build_default_active_hours()

        old_active_hours_type = None
        old_max_active_hours = None
        old_active_hours = None

        if not is_create:
            old = GeckoConfigs.objects.get(pk=self.pk)
            old_active_hours_type = old.active_hours_type
            old_max_active_hours = old.max_active_hours
            old_active_hours = old.active_hours

        super().save(*args, **kwargs)
        self.user.geckoscorestate.recompute_energy()



        
class GeckoSleepChangeLog(models.Model):
    user = models.ForeignKey(
        'users.BadRainbowzUser',
        on_delete=models.CASCADE,
        related_name='gecko_sleep_change_logs',
    )

    active_hours_type = models.IntegerField(
        choices=ActivityHours.choices,
        default=ActivityHours.DAY,
    )

    max_active_hours = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        default=16,
    )

    active_hours = models.JSONField(default=list, blank=True)

    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_on']
        indexes = [
            models.Index(fields=['user', 'created_on']),
        ]

    def __str__(self):
        return f"Sleep change for {self.user.username} on {self.created_on}"
    
class GeckoCombinedData(models.Model):
    user = models.OneToOneField('users.BadRainbowzUser', on_delete=models.CASCADE)
    
    total_steps = models.PositiveIntegerField(default=0)
    total_distance = models.PositiveIntegerField(default=0)
    total_duration = models.PositiveIntegerField(default=0)
    # energy level ?

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    total_gecko_points = models.PositiveIntegerField(default=0)



class GeckoPointsLedger(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='gecko_points_ledger')
    friend = models.ForeignKey('friends.Friend', on_delete=models.SET_NULL, null=True, blank=True)
    friend_session = models.ForeignKey(
        'friends.GeckoDataSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='points_ledger_entries'
    )
    combined_session = models.ForeignKey(
        'users.GeckoCombinedSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='points_ledger_entries'
    )
    
    amount = models.IntegerField()
    reason = models.CharField(max_length=100, blank=True)
    code = models.PositiveIntegerField(null=True, blank=True)
    multiplier = models.PositiveIntegerField(default=1)

    timestamp_earned = models.DateTimeField(default=timezone.now)

    updated_on = models.DateTimeField(auto_now=True)
    created_on = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-created_on']


    

    def __str__(self):
        return f"{self.user.username} + {self.amount})"

 
    


# class GeckoCombinedDaily(models.Model):
#     user = models.ForeignKey('users.BadRainbowzUser', on_delete=models.CASCADE)
#     date = models.DateField(default=timezone.localdate)
  
#     steps = models.PositiveIntegerField(default=0)
#     distance = models.PositiveIntegerField(default=0)
#     duration = models.PositiveIntegerField(default=0)

#     created_on = models.DateTimeField(auto_now_add=True)
#     updated_on = models.DateTimeField(auto_now=True)

#     class Meta:
#         unique_together = ('user', 'date')
#         ordering = ['-date']



class GeckoCombinedSession(models.Model):
    user = models.ForeignKey('users.BadRainbowzUser', on_delete=models.CASCADE)
    friend = models.ForeignKey('friends.Friend', on_delete=models.SET_NULL, null=True, blank=True)
    points_earned = models.PositiveIntegerField(default=0)
    steps = models.PositiveIntegerField(default=0)
    distance = models.PositiveIntegerField(default=0)
    started_on = models.DateTimeField()
    ended_on = models.DateTimeField()
    created_on = models.DateTimeField(auto_now_add=True)
 

    class Meta:
        ordering = ['-started_on']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['user', 'started_on']),
            models.Index(fields=['user', 'ended_on']),
        ]

    @property
    def duration_seconds(self):
        return int((self.ended_on - self.started_on).total_seconds())
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.user.geckoscorestate.recompute_energy()

class PointsLedger(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='points_ledger')
    amount = models.IntegerField()
    reason = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} +{self.amount} ({self.reason})"


'''
Not sure I will use this in this project, given I have a whole app for friends

class FriendProfile(models.Model):
    id = models.BigAutoField(primary_key=True)
    #friend = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='friend_of')
    nickname = models.CharField(max_length=255, default='')
    created_on = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_on']

        verbose_name = "User friendship"
        verbose_name_plural = "User friendships"

    def __str__(self):

        date = self.created_on 
        date = format_date(date)

        return f"{self.friend.username} ({self.nickname}) since {self.created_on}"
'''



'''
maybe this could be a friend visit model 

class UserVisit(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='visits')
    location_name = models.CharField(max_length=255)
    location_latitude = models.FloatField(default=0.0)
    location_longitude = models.FloatField(default=0.0)
    visit_created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-visit_created_on']


    def __str__(self):

        date = self.visit_created_on
        date = format_date(date)

        return f"{self.user.username} visited {self.location_name} on {date}"
'''
