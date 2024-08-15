from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your models here.
NOTIFICATION_TYPES = ((1,'Like'),(2,'Comment'), (3,'Follow'),(4,'LostEmbedding'),(5,'FoundEmbedding,'),(6,'CatEmbedding'))

# class Notification(models.Model):
# 	post = models.ForeignKey('post.Post', on_delete=models.CASCADE, related_name="noti_post", blank=True, null=True)
# 	sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="noti_from_user")
# 	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="noti_to_user")
# 	notification_type = models.IntegerField(choices=NOTIFICATION_TYPES)
# 	text_preview = models.CharField(max_length=90, blank=True)
# 	date = models.DateTimeField(auto_now_add=True)
# 	is_seen = models.BooleanField(default=False)


class Notification(models.Model):
	post = models.ForeignKey('post.BasePost', on_delete=models.CASCADE, related_name="post_noti", blank=True, null=True)
	cat = models.ForeignKey('authy.Cat',on_delete=models.CASCADE,related_name='embedding_vector_noti',blank=True,null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="noti_to_user")
	notification_type = models.IntegerField(choices=NOTIFICATION_TYPES)
	text_preview = models.CharField(max_length=90, blank=True,null=True)
	date = models.DateTimeField(auto_now_add=True)
	is_seen = models.BooleanField(default=False)
	sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="noti_from_user",null=True)

# class UserNotification(Notification):
# 	sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="noti_from_user")


