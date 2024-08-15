from typing import Any
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.dispatch import receiver

from django.db.models.signals import post_save, post_delete,pre_save
from django.utils.text import slugify
from django.urls import reverse
from authy.models import Cat, PrivacyChoices, Follow
from notifications.models import Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
User = get_user_model()

# Create your models here.

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'user_{0}/{1}'.format(instance.user.id, filename)


class Tag(models.Model):
	title = models.CharField(max_length=75, verbose_name='Tag')
	slug = models.SlugField(null=False, unique=True)

	class Meta:
		verbose_name='Tag'
		verbose_name_plural = 'Tags'

	def get_absolute_url(self):
		return reverse('post:tags', args=[self.slug])
		
	def __str__(self):
		return self.title

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.title)
		return super().save(*args, **kwargs)

class PostFileContent(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='content_owner')
	file = models.FileField(upload_to=user_directory_path)



# Selected: for followers
class BasePost(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	# type = models.CharField(max_length=1,choices=POST_TYPES)
	content =  models.ManyToManyField(PostFileContent, related_name='contents')
	caption = models.TextField(max_length=1500, verbose_name='Caption')
	posted = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	likes = models.IntegerField(default=0)
	is_hidden = models.BooleanField(default=False)
	comment_count = models.IntegerField(default=0)
	
	
	def __str__(self):
		return str(f"{self.user.get_short_name()}-{self.posted}")

	def get_absolute_url(self):
			return reverse('post:postdetails', args=[str(self.id)])
	
	def has_liked(self,user_id):
		all_likes = Likes.objects.filter(post=self)
		for like in all_likes:
			if like.user.id == user_id:
				return True
		return False
	
class Post(BasePost):
	cats = models.ManyToManyField(Cat,related_name='cat_posts',blank=True)
	tags = models.ManyToManyField(Tag, related_name='tags',blank=True)
	privacy = models.CharField(max_length=10,choices=PrivacyChoices.CHOICES,default=PrivacyChoices.PUBLIC)
	
	# def get_absolute_url(self):
	# 	return reverse('post:postdetails', args=[str(self.id)])
	def can_access(self,user_id):
		if self.user.id == user_id:
			return True
		else:
			if self.privacy=='public':
				return True
			elif self.privacy =='followers':
				follow_list = Follow.objects.filter(following=self.user)
				for follow_obj in follow_list:
					if user_id == follow_obj.follower.id:
						return True
				return False 
			else:
				return False


def embedding_directory(instance,filename):
	return f'embeddings/{filename}'
	

class LostPost(BasePost):
	cat = models.ForeignKey(Cat,related_name='cat_lost_posts',null=True, blank=True,on_delete=models.CASCADE)
	geotag = models.CharField(max_length=255,null=False,blank=False)
	search_active = models.BooleanField(default=True)
	is_found = models.BooleanField(default=False)
	embedding = models.FileField(upload_to=embedding_directory,null=True)
	lost_time = models.DateTimeField(null=True,blank=True)
	fullbody_img = models.ManyToManyField(PostFileContent, related_name='lost_fullbody',blank=True)
	email = models.EmailField(null=True,blank=True)
	schedule = models.BooleanField(default=False)

	def get_absolute_url(self):
		return reverse('post:lostpostdetails',args=[str(self.id)])
	

	# def save_embedding(sender, instance, *args, **kwargs):
	# 	post = instance
	# 	notify = SystemNotification(user=post.user, notification_type=1)
	# 	notify.save()

class FoundPost(BasePost):
	geotag = models.CharField(max_length=255,null=False,blank=False)
	found_time= models.DateTimeField(null=True,blank=True)
	search_active = models.BooleanField(default=True)
	is_matched = models.BooleanField(default=False)
	embedding = models.FileField(upload_to=embedding_directory,null=True)
	fullbody_img = models.ManyToManyField(PostFileContent, related_name='found_fullbody')

	# def get_absolute_url(self):
	# 	return reverse('post:postdetails', args=[str(self.id)])

	def get_compare_url(self,lost_id):
		return reverse('post:compare', args=[str(lost_id), str(self.id)])
	

class CandidateMatch(models.Model):
	user = models.ForeignKey(User,on_delete=models.CASCADE)
	lostpost = models.ForeignKey(LostPost,on_delete=models.CASCADE)
	foundpost = models.ForeignKey(FoundPost,on_delete=models.CASCADE,related_name="match",null=True)
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)
	score = models.FloatField(default=1.)
	threshold = models.BooleanField(default=False)




class Stream(models.Model):
	"""
	Create a Stream for each follower when the user they following
	create a post
	"""
	following = models.ForeignKey(User, on_delete=models.CASCADE,null=True, related_name='stream_following')
	user = models.ForeignKey(User, on_delete=models.CASCADE)   
	post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True)
	date = models.DateTimeField()

	def add_post(sender, instance, *args, **kwargs):
		post = instance
		user = post.user
		followers = Follow.objects.all().filter(following=user)
		
		# hot_posts = Post.objects.all().order_by("-likes")
		for follower in followers:
			stream = Stream(post=post, user=follower.follower, date=post.posted, following=user)
			stream.save()
		

class Likes(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_like')
	post = models.ForeignKey(BasePost, on_delete=models.CASCADE, related_name='post_like')


post_save.connect(Stream.add_post, sender=Post)


# # FOLLOW

@receiver(post_save,sender=Likes)
def like_notify(sender,instance,**kwargs):

	like = instance
	post = like.post
	notify = Notification(post=post, sender=like.user, user=post.user, notification_type=1)
	notify.save()
	# send realtime-notification

	channel_layer = get_channel_layer()

	async_to_sync(channel_layer.group_send)(
		f"user_{post.user.id}",
		{
			"type": "send_notification",
			"message": {
            "action": "new_like",

            }
		}
	)

@receiver(post_save,sender=Follow)
def follow_notify(sender,instance,**kwargs):
	follow = instance
	# sender = follow.follower
	following = follow.following
	notify = Notification(sender=follow.follower, user=following, notification_type=3)
	notify.save()

	# send realtime-notification
	channel_layer = get_channel_layer()

	async_to_sync(channel_layer.group_send)(
		f"user_{following.id}",
		{
			"type": "send_notification",
			"message": {
            "action": "new_follow",

            }
		}
	)

@receiver(post_delete,sender=Likes)
def unlike_notify(sender,instance,**kwargs):
	like = instance
	post = like.post
	notify = Notification.objects.filter(post=post, sender=like.user, notification_type=1)[0]
	if notify.is_seen:
		check = False
	else:
		check=True
	notify.delete()

	# if the follow notification is not seen yet => minus 1 from count_notification
	if check:
			# send realtime-notification
		channel_layer = get_channel_layer()

		async_to_sync(channel_layer.group_send)(
			f"user_{post.user.id}",
			{
				"type": "send_notification",
				"message": {
				"action": "delete_like",

				}
				
			}
		)



@receiver(post_delete,sender=Follow)
def unfollow_notify(sender, instance, **kwargs):
	follow = instance
	following = follow.following

	notify = Notification.objects.filter(sender=follow.follower, user=following, notification_type=3)
	if len(notify)>=1:
		notify= notify[0]
		if notify.is_seen:
			check = False
		else:
			check = True

		notify.delete()

		if check:
			# send realtime-notification
			channel_layer = get_channel_layer()

			async_to_sync(channel_layer.group_send)(
				f"user_{following.id}",
				{
					"type": "send_notification",
					"message": {
						'action':'delete_follow'
					}
				}
			)
			


# Embedding created
@receiver(pre_save, sender=LostPost)
@receiver(pre_save, sender=FoundPost)
def post_pre_save(sender, instance, **kwargs):
    if instance.pk:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.caption != instance.caption:
            print(f"The caption has changed from {old_instance.caption} to {instance.caption}")
            
            Notification.objects.create(
                post=instance,
                user=instance.user,
                notification_type=4
            )

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{instance.user.id}",
                {
                    "type": "send_notification",
                    "message": f"Your {sender.__name__.lower()} caption has been updated.",
                }
            )

