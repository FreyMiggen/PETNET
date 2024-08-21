from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, UserManager, AbstractBaseUser, PermissionsMixin
# Create your models here.
from django.utils.text import slugify
from django.db.models.signals import post_save, post_delete
# from post.models import Post

# from django.contrib.postgres.fields import ArrayField
import os
from PIL import Image
from django.conf import settings
from django.db.models.signals import pre_save
from django.dispatch import receiver

# from .tasks import add_face_to_db, test_ce
# Create your models here.


# def user_directory_path(instance,filename):
    
#     fol = 'users/user_{0}/'.format(instance.user.id)
#     fullpath = os.path.join(settings.MEDIA_ROOT,fol)
#     if not os.path.exists(fullpath):
#         profile_pic_name = 'users/user_{0}/profile_0_{1}'.format(instance.user.id,filename)
#     else:
#         count = len(os.listdir(fullpath))
#         profile_pic_name = 'users/user_{0}/profile_{1}_{2}'.format(instance.user.id,count,filename)
    
#     return profile_pic_name
# Create your models here.


def user_directory_path(instance, filename):
    	# file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
	profile_pic_name = 'user_{0}/profile.jpg'.format(instance.user.id)
	full_path = os.path.join(settings.MEDIA_ROOT, profile_pic_name)
	

	if os.path.exists(full_path):
		os.remove(full_path)

	return profile_pic_name

class CustomUserManager(UserManager):
    def _create_user(self,email,password,**extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self,email=None,password=None,**extra_fields):
        extra_fields.setdefault('is_staff',False)
        extra_fields.setdefault('is_superuser',False)
        # extra_fields.setdefault('is_active',True)

        return self._create_user(email,password,**extra_fields)
    
    def create_superuser(self, email=None, password = None, **extra_fields):

        extra_fields.setdefault('is_staff',True)
        extra_fields.setdefault('is_superuser',True)
        # extra_fields.setdefault('is_active',True)

        return self._create_user(email,password,**extra_fields)
    
class User(AbstractBaseUser,PermissionsMixin):

    email = models.EmailField(blank=True,default='',unique=True)
    name = models.CharField(max_length=150,blank=True,default='',unique=True)

    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    # date_join = models.DateTimeField(default=timezone.now)
    objects = CustomUserManager()
    # TELL DJANGO TO USE EMAIL FIELD FOR AUTHENTICATION INSTEAD OF USERNAM
    USERNAME_FIELD = 'email'
    # SPECIFIES WHICH FIELD SHOULD BE USED AS EMAIL FIELD
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def get_short_name(self):
        return self.name or self.email.split('@')[0]
    def __str__(self):
        return self.name or self.email.split('@')[0]
    
# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    location = models.CharField(max_length=50, null=True, blank=True)
    url = models.CharField(max_length=80, null=True, blank=True)
    profile_info = models.TextField(max_length=150, null=True, blank=True)
    created = models.DateField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True)
    picture = models.ImageField(upload_to=user_directory_path, blank=True, null=True, verbose_name='Picture')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        SIZE = 250, 250

        if self.picture:
            pic = Image.open(self.picture.path)
            pic.thumbnail(SIZE, Image.LANCZOS)
            pic.save(self.picture.path)

    def __str__(self):
        return self.user.get_short_name()
		
    def get_absolute_url(self):
        return f"/{self.slug}/"
    
@receiver(pre_save, sender=Profile)
def create_profile_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        slug = slugify(instance.user.get_short_name())
        unique_slug = slug
        num = 1
        while Profile.objects.filter(slug=unique_slug).exists():
            unique_slug = '{}-{}'.format(slug, num)
            num += 1
        instance.slug = unique_slug

## CAT ##

def cat_image_directory(instance,filename):
    fol = 'cats/cat_{instance.cat.id}/face'
    cat_name=instance.cat.name
    fullpath = os.path.join(settings.MEDIA_ROOT,fol)
    if os.path.exists(fullpath) == False:
        pic_name = 'cats/cat_{0}/face/{1}_{2}'.format(instance.cat.id,cat_name,filename)
    else:
        count = len(os.listdir(fullpath))
        pic_name = 'cats/cat_{0}/face/{1}_{2}_{3}'.format(instance.cat.id,cat_name,count,filename)
    return pic_name

def embedding_vector_directory(instance,filename):
    fol = 'embedding_vector'
    # fol = os.path.join(settings.MEDIA_ROOT,fol)
    fullpath = os.path.join(fol,filename)
    return fullpath


def cat_avatar_directory(instance,filename):
    cat_name=instance.name
    pic_name= 'cats/avatar/{0}_{1}'.format(cat_name,filename)
    return pic_name


def cat_fullbody_image_directory(instance,filename):
    fol = 'cats/cat_{instance.cat.id}/body'
    cat_name=instance.cat.name
    fullpath = os.path.join(settings.MEDIA_ROOT,fol)
    if os.path.exists(fullpath) == False:
        pic_name = 'cats/cat_{0}/body/{1}_{2}'.format(instance.cat.id,cat_name,filename)
    else:
        count = len(os.listdir(fullpath))
        pic_name = 'cats/cat_{0}/body/{1}_{2}_{3}'.format(instance.cat.id,cat_name,count,filename)
    return pic_name


class PrivacyChoices:
    PUBLIC = 'public'
    PRIVATE = 'private'
    FOLLOWER = 'followers'

    CHOICES = [
        (PUBLIC, 'Public'),
        (PRIVATE, 'Private'),
        (FOLLOWER, 'Followers Only'),
    ]

class Follow(models.Model):
    follower = models.ForeignKey(User,on_delete=models.CASCADE, null=True, related_name='follower')
    following = models.ForeignKey(User,on_delete=models.CASCADE, null=True, related_name='following')

class Cat(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name='cats')
    picture = models.ImageField(upload_to=cat_avatar_directory,null=True)
    name = models.CharField(max_length=50,null=True,blank=False)
    description = models.CharField(max_length=1000,null=True,blank=True)
    embedding_vector = models.FileField(upload_to=embedding_vector_directory,null=True,blank=True)     
    in_search = models.BooleanField(default=False)
    privacy = models.CharField(max_length=10,choices=PrivacyChoices.CHOICES,default=PrivacyChoices.PUBLIC)
    
    def __str__(self):
        return self.name
    
    
    def img_fol(self):
        return os.path.normpath(os.path.join(settings.MEDIA_ROOT,f'cats/cat_{self.id}/face'))
    
    def can_access(self,user_id):
        if user_id == self.user.id:
            return True
        else:
            if self.privacy == 'public':
                return True
            elif self.privacy == 'followers':

                follow_list = Follow.objects.filter(following=self.user)
                for follow_obj in follow_list:
                    if user_id == follow_obj.follower.id:
                        return True
                return False 
            else: # private
                return False

    def is_owner(self,user_id):
        if user_id == self.user.id:
            return True
        else:
            return False
        
class CatFullBodyImage(models.Model):
    cat = models.ForeignKey(Cat,on_delete=models.CASCADE,related_name='fullbody_images')
    pic = models.ImageField(upload_to=cat_fullbody_image_directory,null=False,blank=False)

from django.utils import timezone
from datetime import datetime

# now = timezone.make_aware(datetime.now,timezone.get_current_timezone())
class CatImageStorage(models.Model):
    cat = models.ForeignKey(Cat,on_delete=models.CASCADE,related_name='images')
    pic = models.ImageField(upload_to=cat_image_directory,null=False,blank=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    
    def img_fol(self):
        return os.path.normpath(os.path.join(settings.MEDIA_ROOT,f'cats/cat_{self.cat.id}'))
    

## DONT USE THIS ONE
class CatBodyImage(models.Model):
    cat = models.ForeignKey(Cat,on_delete=models.CASCADE,related_name='body_images')
    pic = models.ImageField(upload_to=cat_fullbody_image_directory,null=False,blank=False)



def create_user_profile(sender, instance, created, **kwargs):
	if created:
		Profile.objects.create(user=instance)

def save_user_profile(sender, instance, **kwargs):
	instance.profile.save()


post_save.connect(create_user_profile, sender=User)
post_save.connect(save_user_profile, sender=User)

from django.db.models.signals import pre_save
from django.dispatch import receiver
from notifications.models import Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver(pre_save, sender=Cat)
def create_notification_on_embedding_vector_change(sender, instance, **kwargs):
    try:
        original_cat = Cat.objects.get(id=instance.id)
        if instance.embedding_vector!= original_cat.embedding_vector:
            # Create a new Notification instance
            Notification.objects.create(
                # your notification fields here, e.g.
                cat=original_cat,
                user=original_cat.user,
                notification_type=6
            )

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{original_cat.user.id}",
                {"type": "send_notification",
                    "message":{
                        "action":"embedding_completed",
                    }}
            )

    except Cat.DoesNotExist:
        # This is a new Cat instance, no need to create a notification
        pass