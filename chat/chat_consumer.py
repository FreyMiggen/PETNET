from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from .models import ChatRoom, ChatMessage
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        self.rooms = await self.get_user_rooms()

        self.room_names = [f'chat_{room.id}' for room in self.rooms]

        # Subscribe chatconsumer to all rooms

        for room_name in self.room_names:
            await self.channel_layer.group_add(
                room_name,
                self.channel_name
            )
        # accept an incoming websocket    
        await self.accept()

    async def disconnect(self, close_code):
        # unsubcribe from all rooms
        for room_name in self.room_names:
            await self.channel_layer.group_discard(room_name, self.channel_name)

    async def receive(self,text_data):
        """
        This method is called whenever websocket receive a message
        from client ( user in this case)
        
        Usage:
        - Parse the JSON data received from the client, extract the message
        - Save message to the DB
        - Send the message to the room group using channel_layer.group_send
        """
        data = json.loads(text_data)
        room_id = data['room']
        room_name = f'chat_{room_id}'
        message = data['message']
        # register message in db
        last_update = await self.save_message(message,room_id)
        last_update = last_update.strftime('%Y-%m-%d %H:%M:%S')
    
        # broadcast message to room

        await self.channel_layer.group_send(
        room_name,
            {
                'type':'send_message',
                'message':message,
                'username':self.user.get_short_name(),
                'user_id': self.user.id,
                'room':room_id,
                'last_update': last_update
            }
        )

    async def send_message(self,event):
        """
        After message is broadcast to all consumer that subscribe to a room (channel group)
        We need to send this message to websocket client in browser of user to display
        """
        message = event['message']
        username = event['username']
        room_id = event['room']
        user_id = event['user_id']
        last_update = event['last_update']
        # send message to websocket client
        await self.send(text_data=json.dumps({
            'message':message,
            'username':username,
            'user_id':user_id,
            'room':room_id,
            'last_update':last_update

        }))

    @database_sync_to_async
    def save_message(self, message,room_id):
        room = ChatRoom.objects.get(id=room_id)
        ChatMessage.objects.create(
            room = room,
            user = self.user,
            content = message
        )

        # update last_visit
        room.update_last_visit(self.user)
        room.lastest_update_time = timezone.now()
        room.save()
        # return  timezone.make_aware(room.lastest_update_time, timezone.get_current_timezone())
        aware_time = room.lastest_update_time
        return aware_time.astimezone(timezone.get_current_timezone())
    
    @database_sync_to_async
    def get_user_rooms(self):
        return list(ChatRoom.objects.filter(
            Q(user1=self.user) | Q(user2=self.user)
        ))
