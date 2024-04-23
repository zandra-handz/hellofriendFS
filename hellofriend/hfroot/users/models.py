from django.db import models

# Create your models here.
from datetime import datetime


def format_date(dt):
    current_year = datetime.now().year
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
from django.db.models.signals import post_save
from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext as _
from .managers import CustomUserManager
from .utils import get_coordinates


# Create your models here.
class BadRainbowzUser(AbstractUser):

    # Username and email must be unique.
    username = models.CharField(_('username'), unique=True, max_length=150)
    email = models.EmailField(_('email address'), unique=True)

    addresses = models.JSONField(blank=True, null=True)
    phone_number = models.CharField(_('phone number'), max_length=15, blank=True, null=True)
    is_active_user = models.BooleanField(default=True)
    is_inactive_user = models.BooleanField(default=False)
    is_banned_user = models.BooleanField(default=False)
    created_on = models.DateTimeField(default=timezone.now)
    last_updated_at = models.DateTimeField(auto_now=True)

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
    
    def add_address(self, address_data):
        """
        Add address if valid.
        """
        address_value = address_data[0]['address']
        coordinates = get_coordinates(address_value)

        if coordinates:
            if 'addresses' not in self.__dict__:
                self.addresses = []
            
            new_address_entry = {
                'title': address_data[0]['title'],
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
            UserProfile.objects.create(user=self)
            UserSettings.objects.create(user=self)


class UserSettings(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name='settings')
    receive_notifications = models.BooleanField(default=False)
    language_preference = models.CharField(max_length=10, choices=[('en', 'English'), ('es', 'Spanish')], blank=True)

    # Accessibility settings options for front end
    large_text = models.BooleanField(default=False)
    high_contrast_mode = models.BooleanField(default=False)
    screen_reader = models.BooleanField(default=False)

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
    gender = models.CharField(_('gender'), max_length=10, choices=[('NB', 'Non-Binary'), ('M', 'Male'), ('F', 'Female'), ('O', 'Other'), ('No answer', 'Uninterested in answering this')], blank=True, default='')

    def __str__(self):
        return f"Profile for {self.user.username}"


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
