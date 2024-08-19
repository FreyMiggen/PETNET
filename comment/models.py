from django.db import models
from post.models import BasePost
from django.contrib.auth import get_user_model
from notifications.models import Notification

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()
# Create your models here.

class Comment(models.Model):
	post = models.ForeignKey(BasePost, on_delete=models.CASCADE, related_name='comments')
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	body = models.TextField()
	date = models.DateTimeField(auto_now_add=True)




#Comment
@receiver(post_save, sender=Comment)
def user_comment_post(sender, instance, **kwargs):
 
	comment = instance
	post = comment.post
	text_preview = comment.body[:90]
	sender = comment.user

	# update comment_count for post
	post.comment_count = post.comment_count+1
	post.save()

	# create a notification for owner of post
	notify = Notification(post=post, sender=sender, user=post.user, text_preview=text_preview, notification_type=2)
	notify.save()

        # Send real-time notification
	channel_layer = get_channel_layer()
	async_to_sync(channel_layer.group_send)(
		f"user_{post.user.id}",  # Notify the post owner
		{
			"type": "send_notification",
			"message": {
				"action": "new_comment",
				"comment_user": comment.user.get_short_name(),
				"comment_text": text_preview,
			}
		}
	)

@receiver(post_delete, sender=Comment)
def user_del_comment_post(sender, instance, **kwargs):
	comment = instance
	post = comment.post
	sender = comment.user
		# update comment_count for post
	post.comment_count = post.comment_count-1
	post.save()

	try:
		notify = Notification.objects.filter(post=post, sender=sender, notification_type=2).latest('date')
		count = 0
		for item in list(notify):
			if item.is_seen == False:
				count+=1
		
		notify.hidden = True
		notify.save()

		if count > 0:

			# Send real-time notification for comment deletion if the comment is not seen yet => discount count_notification
			channel_layer = get_channel_layer()
			async_to_sync(channel_layer.group_send)(
				f"user_{post.user.id}",  # Notify the post owner
				{
					"type": "send_notification",
					"message": {
						"action": "delete_comment",
						"count":count,

					}
				}
			)
	except:
		# in this case, the post is deleted => all comments are deleted => trigger user_del_comment_post
		print('All related comments are deleted')
