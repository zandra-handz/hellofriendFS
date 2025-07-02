from django.db import models
# import friends.models could cause circular import because this file imports users. using 'friends.ThoughtCapsulez' and 'friends.Image' below instead

# Create your models here.
from datetime import datetime
from . import utils


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
from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext as _
from .managers import CustomUserManager


# Create your models here.
class BadRainbowzUser(AbstractUser):

    # Username and email must be unique.
    username = models.CharField(_('username'), unique=True, max_length=150)
    email = models.EmailField(_('email address'), unique=True)

    password_reset_code = models.CharField(max_length=6, blank=True, null=True)
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
        from datetime import timedelta  # You can still use timedelta for durations
        
        code = f"{random.randint(100000, 999999)}"  # 6-digit code
        self.password_reset_code = code
        self.code_expires_at = timezone.now() + timedelta(minutes=10)  # Use timezone.now()
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
            UserProfile.objects.create(user=self)
            UserSettings.objects.create(user=self)
            UserCategory.objects.create(user=self, name='Grab bag', is_deletable=False)
            



class UserCategory(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='user_categories')
    name = models.CharField(max_length=50)
    thought_capsules = models.ManyToManyField('friends.ThoughtCapsulez', related_name='user_categories', blank=True, null=True)
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

    def delete(self, *args, **kwargs):
        if not self.is_deletable:
            raise ValidationError("This category cannot be deleted.")
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



class UserSettings(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name='settings')
    receive_notifications = models.BooleanField(default=False)
    simplify_app_for_focus = models.BooleanField(default=False)
    language_preference = models.CharField(max_length=10, choices=[('en', 'English'), ('es', 'Spanish')], blank=True)
    # Accessibility settings options for front end
    large_text = models.BooleanField(default=False)
    high_contrast_mode = models.BooleanField(default=False)
    screen_reader = models.BooleanField(default=False)
    manual_dark_mode = models.BooleanField(null=True, blank=True)
    expo_push_token = models.CharField(max_length=255, null=True, blank=True) 


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
