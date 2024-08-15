

# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
User = get_user_model()
from django.utils import timezone

class ChatRoom(models.Model):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # name = models.CharField(max_length=100)
    user1 = models.ForeignKey(User,on_delete=models.CASCADE,related_name='chat_user1')
    user2 = models.ForeignKey(User,on_delete=models.CASCADE,related_name='chat_user2')
    created_at = models.DateTimeField(auto_now_add=True)
    user1_last_visit = models.DateTimeField(null=True, blank=True)
    user2_last_visit = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user1', 'user2'], name='unique_chat_room'),
            models.UniqueConstraint(fields=['user2', 'user1'], name='unique_chat_room_reverse'),
        ]

    def clean(self):
        # Ensure user1 is not the same as user2
        if self.user1 == self.user2:
            raise ValidationError("User1 and User2 must be different.")

    def save(self, *args, **kwargs):
        self.clean()
        if self.user1.id > self.user2.id:
            # Ensure user1's id is always less than user2's id for uniqueness
            self.user1, self.user2 = self.user2, self.user1
        super().save(*args, **kwargs)

    def __str__(self):
       return f"Chat between {self.user1.get_short_name()} and {self.user2.get_short_name()}"
   
    def update_last_visit(self, user):
        now = timezone.now()
        if user == self.user1:
            self.user1_last_visit = now
        elif user == self.user2:
            self.user2_last_visit = now
        self.save()

    def get_unread_count(self, user):
        if user == self.user1:
            last_visit = self.user1_last_visit
            other_user = self.user2
        elif user == self.user2:
            last_visit = self.user2_last_visit
            other_user = self.user1
        else:
            return 0
        
        if last_visit is None:
            # If the user has never visited, all messages are unread
            return self.chatmessage_set.filter(user=other_user).count()
        
        return self.chatmessage_set.filter(
            user=other_user,
            timestamp__gt=last_visit
        ).count()

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.content



