from . import utils
from . import managers
import calendar
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
import datetime
import random
import re
import users.models
import uuid


# Create your models here.

def format_date(dt):
    current_year = datetime.now().year
    if dt.year == current_year:
        formatted_date = dt.strftime('%B %#d at %#I:%M %p')
    else:
        formatted_date = dt.strftime('%B %#d %Y at %#I:%M %p')

    return formatted_date


def get_yesterday():
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    return yesterday


class UpdatesTracker(models.Model):

    user = models.OneToOneField(users.models.BadRainbowzUser, on_delete=models.CASCADE)
    last_upcoming_update = models.DateField(default=get_yesterday)

    def __str__(self):

        return f'Update tracker for {self.user.username}'
    
    def upcoming_updated(self):
        self.last_upcoming_update = datetime.date.today()
        self.save() 



class Friend(models.Model):

    user = models.ForeignKey(users.models.BadRainbowzUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=64, null=False, blank=False)
    first_name = models.CharField(max_length=64, null=True, blank=True)
    last_name = models.CharField(max_length=64, null=True, blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    first_meet_entered = models.DateField(default='2024-01-01')

    next_meet = models.OneToOneField('friends.NextMeet', on_delete=models.CASCADE, null=True, blank=True, related_name='friend_next_meet')
    suggestion_settings = models.OneToOneField('friends.FriendSuggestionSettings', on_delete=models.CASCADE, null=True, blank=True, related_name='friend_friend_suggestion_settings')


    class Meta:
        ordering = ('next_meet',)
        unique_together = ('user', 'name')

    @property
    def first_meet_entered_in_words(self):
        date = self.first_meet_entered
        l = calendar.day_name[date.weekday()]
        p = date.strftime("%B") + " " + str(date.day)
        s = date.strftime("%Y")
        words = f"{l}, {p}, {s}"
        return words

    def save(self, *args, **kwargs):

        if not self.pk:
            super().save(*args, **kwargs)  # Save the Friend instance first

            # Create and save FriendSuggestionSettings
            suggestion_settings = FriendSuggestionSettings(
                friend=self,
                user=self.user,
            )
            suggestion_settings.save()

            # Create and save FriendFaves
            friend_faves = FriendFaves(
                friend=self,
                user=self.user,
            )
            friend_faves.save()

            # Create and save PastMeet

            past_meet = PastMeet(
                friend=self,
                user=self.user,
                date=self.first_meet_entered,
                # You might want to set other fields here
            )
            past_meet.save()
           

            # Create and save NextMeet
            
            next_meet = NextMeet(
                friend=self,
                friend_suggestion_settings=suggestion_settings,
                user=self.user,
            )
            next_meet.save()

            # To test
            try:
                next_meet.create_new_date_clean()
                next_meet.save()
            except Exception as e:
                print("Error creating new date for friend") 
            

            self.suggestion_settings = suggestion_settings
            self.next_meet = next_meet

            # Save the updated Friend instance
            self.save()
            
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Friend: {self.name}, {self.id}"


# A separate class to keep this data separate and secret from NextMeet and Friend
class FriendSuggestionSettings(models.Model):
    friend = models.ForeignKey(Friend, on_delete=models.CASCADE, related_name='suggestion_settings_friend')
    user = models.ForeignKey(users.models.BadRainbowzUser, on_delete=models.CASCADE)
    can_schedule = models.BooleanField(default=False)

    effort_required = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], default=2
    )
    priority_level = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)], default=2
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Friend suggestion settings"
        verbose_name_plural = "Friend suggestion settings"

    @property
    def category_limit_formula(self):
        return self.effort_required * 2

    def __str__(self):
        return f"Suggestion settings for {self.friend.name} are effort {self.effort_required}, priority {self.priority_level}"



class FriendAddress(models.Model):
    friend = models.ForeignKey('Friend', on_delete=models.CASCADE, related_name='addresses')
    user = models.ForeignKey(users.models.BadRainbowzUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=64, null=True, blank=False)
    address = models.CharField(max_length=64, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    validated_address = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_on',)
        unique_together = (('friend', 'title'), ('friend', 'address'))


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
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Friend address: {self.address}, validated: {self.validated_address}"

# All this knows is the friend it is connected to, the settings, and the last meet up it is connected to
class NextMeet(models.Model):
    friend = models.OneToOneField(Friend, on_delete=models.CASCADE, editable=False, related_name='next_meet_friend')
    friend_suggestion_settings = models.OneToOneField(FriendSuggestionSettings, on_delete=models.CASCADE, editable=False, related_name='next_meet_friend_suggestion_settings')
    user = models.ForeignKey(users.models.BadRainbowzUser, on_delete=models.CASCADE)
    date = models.DateField(default=get_yesterday)
    previous = models.ForeignKey('friends.PastMeet', on_delete=models.SET_NULL, null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)

    objects = managers.NextMeetManager()
    # Use NextMeet.objects.expired_dates() in views or utils files to reset missed dates, in conjunction with FriendSuggestionSettings

    class Meta:
        ordering = ('date',)

    def reset_date(self):
        self.date = get_yesterday()


    @property
    def days_since(self):
        if self.previous and self.previous.date:
            today = datetime.datetime.today().date()
            days_difference = (today - self.previous.date).days
            return int(days_difference)
        else:
            return None
        

    @property
    def days_since_words(self):
        if self.previous and self.previous.date:
            today = datetime.datetime.today().date()
            days_difference = (today - self.previous.date).days
            
            if days_difference == 0:
                return "today"
            elif days_difference == 1:
                return "yesterday"
            else:
                return f"{days_difference} days ago"
        else:
            return None
        

    @property
    def time_score(self):
        days_since = self.days_since
        if days_since is None:
            return None
        elif days_since > 180:
            return 6
        elif days_since > 90:
            return 5
        elif days_since > 60:
            return 4
        elif days_since > 40:
            return 3
        elif days_since > 20:
            return 2
        else:
            return 1

    def timespan(self):

        priority = self.friend_suggestion_settings.priority_level
        effort = self.friend_suggestion_settings.effort_required

        span = None

        if effort < 4:
            if effort == 1:
                span = (120, 200)
            elif effort == 2:
                span = (60, 90)
            else:
                span = (26, 40)
        else:
            if effort == 4:
                span = (6, 20)
            else:
                span = (0, 8) 

        if span:
            tiers = (span[1] - span[0]) / 3
            tiers = int(tiers)

            max = ((tiers * priority) + span[0])
            min = max - tiers

        
        else:
            # Just for debugging 
            min = 300
            max = 400

        
        return min, max
        


    # first calculation and every calculation after a logged hello
    def create_new_date_clean(self):
        min_range, max_range = self.timespan()
        random_day = random.randint(min_range, max_range)
        random_day = float(random_day)
        new_date = datetime.date.today() + datetime.timedelta(days=random_day)
        self.date = new_date
        return new_date
      
        
    # This is probably the first 'algorithm' I ever wrote and I do not have the energy or moral fortitude to sift through this chaos at this time I'm so sorry! Soon

    def create_new_date_if_needed(self):
        if self.date < datetime.date.today():

            days_since = self.days_since
            if days_since is not None:  # Check if days_since is not None
                days = int(days_since)
            else:
                days = 7
            
            y = random.randint(1, 6)
            x = 0 

            if self.friend_suggestion_settings.priority_level == 1:
                if days > 7:
                    x = 4 - self.friend_suggestion_settings.effort_required
                elif days <= 7:
                    x = days + 7
                    x = x - self.friend_suggestion_settings.effort_required
            elif self.friend_suggestion_settings.priority_level == 2:
                if days > 18:
                    x = 9 - self.friend_suggestion_settings.effort_required
                elif days <= 18:
                    x = days + 18
                    x = x - self.friend_suggestion_settings.effort_required
            elif self.friend_suggestion_settings.priority_level == 3:
                if days > 30:
                    x = 15 - self.friend_suggestion_settings.effort_required
                elif days <= 30:
                    x = days + 30
                    x = x - self.friend_suggestion_settings.effort_required
            x = x + y
            x = float(x)
            end_date = datetime.date.today() + datetime.timedelta(days=x)
            self.date = end_date
            return end_date


    @property
    def future_date_in_words(self):
        date = self.date
        l = calendar.day_name[date.weekday()]
        p = date.strftime("%B") + " " + str(date.day)
        s = date.strftime("%Y")
        words = f"{l}, {p}" #, {s}"
        return words



    # Not sure if being used
    @property
    def thought_capsules_by_category(self):
        thought_capsules = ThoughtCapsulez.objects.filter(
            friend=self.friend,
            user=self.user)

        capsules_by_category = {}
        for capsule in thought_capsules:
            category_name = capsule.category.name
            capsules_by_category.setdefault(category_name, []).append(capsule)
        return capsules_by_category


    @property
    def all_categories(self):
        categories = Category.objects.filter(
            friend=self.friend,
            user=self.user)

        return categories
    

    @property
    def active_categories(self):
        # Filter categories that have related thought capsules
        categories = Category.objects.filter(
            friend=self.friend,
            user=self.user,
            thoughtcapsulez__isnull=False
        ).distinct()

        return categories

    @property
    def inactive_categories(self):
        # Filter categories that have related thought capsules
        categories = Category.objects.filter(
            friend=self.friend,
            user=self.user,
            thoughtcapsulez__isnull=True
        ).distinct()

        return categories


    @property
    def category_activations_left(self): 
        active_category_count = self.active_categories.count()
        activations_left = self.friend_suggestion_settings.category_limit_formula - active_category_count
        return activations_left

    def save(self, *args, **kwargs):

        if not self.pk:

            self.friend.editable = True
            self.friend_suggestion_settings.editable = True

            # Creates new date that aligns with timeframes outlined in onboarding process
            self.create_new_date_clean()
            
        most_recent_past_meet = PastMeet.objects.filter(friend=self.friend).order_by('-date').first()
        self.previous = most_recent_past_meet
        
        self.create_new_date_if_needed()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date}"


class FriendFaves(models.Model):

    friend = models.OneToOneField(Friend, on_delete=models.CASCADE)
    user = models.ForeignKey(users.models.BadRainbowzUser, on_delete=models.CASCADE)
    locations = models.ManyToManyField('friends.Location', blank=True)
    
    dark_color = models.CharField(max_length=7, null=True, blank=True, help_text="Hex color code for the dark theme")
    light_color = models.CharField(max_length=7, null=True, blank=True, help_text="Hex color code for the light theme")
    
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Friend faves"
        verbose_name_plural = "Friend faves"

    def clean(self):
        
        if self.dark_color and not self.dark_color.startswith('#'):
            self.dark_color = f'#{self.dark_color}'
        if self.light_color and not self.light_color.startswith('#'):
            self.light_color = f'#{self.light_color}'
        
        # Validate color codes
        color_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        if self.dark_color and not color_pattern.match(self.dark_color):
            self.dark_color = None  # Reset to null or blank
        if self.light_color and not color_pattern.match(self.light_color):
            self.light_color = None  # Reset to null or blank

    def save(self, *args, **kwargs):
        # Always clean before saving
        self.clean()
        super().save(*args, **kwargs)

    '''
    #addresses = models.JSONField(blank=True, null=True)


    #Functions to allow for validating addresses separately from saving location instances. Not sure if there's a need

    def add_address_after_validating(self, address_data):

        address_value = address_data[0]['address']


        coordinates = utils.get_coordinates(address_value)

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

        if 'addresses' not in self.__dict__:
            self.addresses = []

        new_address_entry = {
            'title': title,
            'address': address,
            'coordinates': coordinates
        }

        self.addresses.append(new_address_entry)
        self.save()
    '''

    def __str__(self):
        return f"{self.friend.name}'s perceived or confirmed preferences"
    

class Category(models.Model):

    friend = models.ForeignKey(Friend, on_delete=models.CASCADE)
    friend_suggestion_settings = models.ForeignKey(FriendSuggestionSettings, on_delete=models.CASCADE)
    user = models.ForeignKey(users.models.BadRainbowzUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    times_used = models.PositiveIntegerField(default=0)
    item_type = models.CharField(max_length=50, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True) 

    
   # @classmethod
   # def get_category_count(cls, user, friend_id):
   #     return cls.objects.filter(user=user, friend_id=friend_id).count()
    
    @classmethod
    def get_category_count(cls, user, friend_id):
        # Get the IDs of categories associated with thought capsules
        categories_with_capsules = set(ThoughtCapsulez.objects.filter(
            user=user, 
            friend_id=friend_id
        ).values_list('category_id', flat=True))

        # Count categories that have related thought capsules
        return cls.objects.filter(
            user=user, 
            friend_id=friend_id, 
            id__in=categories_with_capsules
        ).count()
    
    @property
    def category_count(self):
        return self.get_category_count(self.user, self.friend_id)

    

    # Will probably have to get rid of this if we are differentiating active categories from just stored ones
    def save(self, *args, **kwargs):

        if not self.pk: 
            next_meet = NextMeet.objects.get(
                friend=self.friend, 
                user=self.user
            )  

            if next_meet.category_activations_left < 1:
                raise ValidationError("Category limit reached. You cannot add more categories, but you can add to or delete existing ones.")

        super().save(*args, **kwargs)



    def __str__(self):
        return f"Category: {self.name}"



class ThoughtCapsulez(models.Model):

    id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)
    friend = models.ForeignKey(Friend, on_delete=models.CASCADE)
    user = models.ForeignKey(users.models.BadRainbowzUser, on_delete=models.CASCADE)
    typed_category = models.CharField(max_length=50, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    capsule = models.CharField(max_length=750)
    # Connect an image (won't get saved in PastMeet, this is not a scrapbook) via the image model thought_capsule field
    created_on = models.DateTimeField(auto_now_add=True) 
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-category',)


    def get_existing_categories(self): 

        existing_categories = Category.objects.filter(
            friend=self.friend,
            user=self.user
        )
        return existing_categories

    def save(self, *args, **kwargs):
        if self.category: 
            
            self.typed_category = None
        elif self.typed_category: 
            # If typed_category is provided and category is not selected, create a new category
            try:
                # Check if a category with the typed_category already exists for the user and friend
                category = Category.objects.get(
                    name=self.typed_category,
                    user=self.user,
                    friend=self.friend
                )
                self.category = category
            except Category.DoesNotExist:

                friend_suggestion_settings = FriendSuggestionSettings.objects.get(
                    user=self.user,
                    friend=self.friend
                )
                # If the category doesn't exist, create a new one
                category = Category.objects.create(
                    name=self.typed_category,
                    user=self.user,
                    friend=self.friend,
                    friend_suggestion_settings=friend_suggestion_settings
                )
                self.category = category

        super().save(*args, **kwargs)

    # def get_category_choices(self):
    #    return ThoughtCapsule.objects.filter(friend=self.friend).value_list('category', flat=True).distinct()

    def __str__(self):
        return f"Thought capsule in the category {self.category}"
    


class Image(models.Model):

    friend = models.ForeignKey(Friend, on_delete=models.CASCADE)
    user = models.ForeignKey(users.models.BadRainbowzUser, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='images/', blank=True)
    image_category = models.CharField(max_length=50, default='Misc')
    title = models.CharField(max_length=50)
    image_notes = models.CharField(max_length=150, null=True, blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    # Can be connected to a capsule here, but will keep its image category as well
    thought_capsule = models.ForeignKey(ThoughtCapsulez, related_name='images', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Image: '{self.title}'"




class PastMeet(models.Model):

    TYPE_CHOICES = [
        ('via text or social media', 'via text or social media'),
        ('in person', 'in person'),
        ('happenstance', 'happenstance'),
        ('unspecified', 'unspecified'),
    ]

    id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)
    friend = models.ForeignKey(Friend, on_delete=models.CASCADE)
    user = models.ForeignKey(users.models.BadRainbowzUser, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, choices = TYPE_CHOICES, default='unspecified')  #handle multiple choice with forms.ModelMultipleChoiceField(queryset="") in person, digital, happenstance
    typed_location = models.CharField(max_length=50, null=True, blank=True)
    location_name = models.CharField(max_length=50, null=True, blank=True)
    location = models.ForeignKey('friends.Location', on_delete=models.SET_NULL, null=True, blank=True) #ie specific coffee shop, social media platform, etc, this will become key to locations
    date = models.DateField(null=True, blank=True)
    thought_capsules_shared = models.JSONField(default=dict, null=True, blank=True)
    delete_all_unshared_capsules = models.BooleanField(default=False)

    created_on = models.DateTimeField(auto_now_add=True)

    # I would like to limit the amount of times this can be viewed per year because I want to demphasize past history
    # HOWEVER this should probably apply to every entry in that friend's archive at once
    times_viewed = models.PositiveIntegerField(default=0)


    class Meta:
        ordering = ('-date',)

    def get_existing_locations(self): 

        existing_locations = Location.objects.filter(
            friend=self.friend,
            user=self.user
        )
        return existing_locations

    
    @property
    def past_date_in_words(self):
        date = self.date
        l = calendar.day_name[date.weekday()]
        p = date.strftime("%B") + " " + str(date.day)
        s = date.strftime("%Y")
        words = f"{l}, {p}" #, {s}"
        return words



    def save(self, *args, **kwargs):

        # is_update = self.pk is not None

        # Idea count limit may need to be checked here

        '''
        TO TEST LATER - introduces a time limit to how long this model is editable; incomplete

        if self.pk:
            created_on = self.created_on if self.created_on else datetime.now()
            three_days_after_created = created_on + datetime.timedelta(days=3)

            if datetime.now() > three_days_after_created:
                raise ValidationError("Updates are only allowed within 3 days of creation.")

        '''
        # if not self.pk: 


           # with transaction.atomic():

        if self.location:
            self.location.friends.add(self.friend)
            
            updated_location = self.location
            updated_location.save()

            self.location_name = self.location.title
            self.typed_location = None

        elif self.typed_location:

            try:
                location = Location.objects.get(
                    address=self.typed_location,
                    user=self.user
                )

            except Location.DoesNotExist:

                try:

                    location = Location.objects.get(
                        title=self.typed_location,
                        user=self.user
                    )

                except Location.DoesNotExist:


                    # Need to search by location_name too
                    # Or I guess we could have the location view handle all/some of this
                    if self.location_name:
                        
                        try:

                            location = Location.objects.get(
                                title=self.location_name,
                                user=self.user
                            )

                        except Location.DoesNotExist:

                            new_location = Location(
                                title=self.location_name,
                                address=self.typed_location,
                                user=self.user
                                )

                    else:

                        new_location = Location(

                            title=self.typed_location,
                            user=self.user
                            )

                    if new_location:

                        new_location.save()

                        new_location.friends.add(self.friend)
                        new_location.save()

                        location = new_location

                    else:
                        self.location = None

                self.location = location

        elif self.location_name:

            try:

                location = Location.objects.get(
                    title=self.location_name,
                    user=self.user
                )

            except Location.DoesNotExist:


                new_location = Location(
                    title=self.location_name, 
                    user=self.user
                )



                if new_location:

                    new_location.save()

                    new_location.friends.add(self.friend)
                    new_location.save()

                    location = new_location

                else:
                    self.location = None

                    

        if self.thought_capsules_shared:

            processed_categories = set()  # Set to keep track of processed categories
            for capsule_id, capsule_data in self.thought_capsules_shared.items():
                print(capsule_id)
                try:
                    capsule_shared_with_friend = ThoughtCapsulez.objects.get(id=capsule_id)
                    if capsule_shared_with_friend.category:
                        category = capsule_shared_with_friend.category
                        if category not in processed_categories:
                            category.times_used += 1 
                            category.save() 
                            processed_categories.add(category) 
                    capsule_shared_with_friend.delete()

                    if self.delete_all_unshared_capsules:
                        unshared = ThoughtCapsulez.objects.filter(friend=self.friend, user=self.user)
                        unshared.delete()
                
                except ThoughtCapsulez.DoesNotExist:
                    pass
                except ThoughtCapsulez.DoesNotExist:
                    pass
                
 

                
        super().save(*args, **kwargs)

        if self.friend.next_meet:
            try:
                self.friend.next_meet.create_new_date_clean()
            except Exception as e:
                self.friend.next_meet.reset_date()
            
            self.friend.next_meet.save()


    def __str__(self):

        return f"{self.type} meet up with {self.friend.name} on {self.date}"


# locations will not be attached to any specific friend, but friend will attach to them via the faves model
class Location(models.Model):

    TYPE_CHOICES = [
        ('1', 'location has free parking lot'),
        ('2', 'free parking lot nearby'),
        ('3', 'street parking'),
        ('4', 'fairly stressful or unreliable street parking'),
        ('5', 'no parking whatsoever'),
        ('6', 'unspecified'),
    ]

    user = models.ForeignKey(users.models.BadRainbowzUser, on_delete=models.CASCADE)
    place_id = models.CharField(max_length=255, null=True, blank=True) 
    category = models.CharField(max_length=100, null=True, blank=True)
    title = models.CharField(max_length=64, null=True, blank=False)
    address = models.CharField(max_length=64, null=True, blank=True)
    parking_score = models.CharField(
        max_length=200,
        choices=TYPE_CHOICES, 
        null=True,   
        blank=True   
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    friends = models.ManyToManyField('Friend', blank=True)
    personal_experience_info = models.CharField(max_length=750, null=True, blank=True)
    calculate_distances_only = models.BooleanField(default=False)
    validated_address = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_on',)
        unique_together = (('user', 'title', 'address'),)

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

        # Ensure unique title
        original_title = self.title
        suffix = 2
        while Location.objects.filter(user=self.user, title=self.title).exists():
            self.title = f"{original_title} ({suffix})"
            suffix += 1
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Location: {self.address}, validated: {self.validated_address}"

'''

Not implemented yet

class ConsiderTheDrive(models.Model):

    user = models.ForeignKey(users.models.BadRainbowzUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=64, unique=True, null=True)

    user_address = models.CharField(max_length=64, unique=True)
    user_lat = models.DecimalField(max_digits=9, decimal_places=6)
    user_long = models.DecimalField(max_digits=9, decimal_places=6)

    friend_address = models.CharField(max_length=64, unique=True)
    friend_lat = models.DecimalField(max_digits=9, decimal_places=6)
    friend_long = models.DecimalField(max_digits=9, decimal_places=6)

    destination_address = models.CharField(max_length=64, unique=True)
    destination_lat = models.DecimalField(max_digits=9, decimal_places=6)
    destination_long = models.DecimalField(max_digits=9, decimal_places=6)

    radius = models.PositiveIntegerField(validators=[MaxValueValidator(10000)], default=5000)
    search = models.CharField(max_length=64, unique=True, default="restaurants")
    suggested_length = models.PositiveIntegerField(validators=[MaxValueValidator(20)], default=6)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    validate_only = models.BooleanField(default=True)


    def __str__(self):
        if not self.name:
            return f"{self.id}"
        else:
            return f"{self.name}"

'''