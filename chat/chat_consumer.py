from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from .models import ChatRoom, ChatMessage
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # self.room_id = self.scope['url_route']['kwargs']['room_id']
        # self.room_group_name = f'chat_{self.room_id}'
        self.user1 = self.scope['user']
        if not self.user1.is_authenticated:
            await self.close()
            return

        self.user2_id = self.scope['url_route']['kwargs']['user_id']
        self.user2 = await self.get_user(self.user2_id)
        if not self.user2:
            await self.close()
            return
        # create or get room
        self.room = await self.get_or_create_room()
        self.room_group_name =f'chat_{self.room.id}'



        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # # get unread messages
        # unread_count = await self.get_unread_count()
        # # Send unread count to the user

        # await self.send(text_data=json.dumps(
        #     {'type':'unread_count',
        #     'count': unread_count}
        # ))

        # ESTABLISH THE WEBSOCKET CONNECTION
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        # update time last visit
        await self.update_last_visit()
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        This method is called whenever websocket receive a message
        from client ( user in this case)
       
        Usage:
        - Parse the JSON data received from the client, extract the message
        - Save message to the DB
        - Send the message to the room group useing channel_layer.group_send
        """
        # Process received a message
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # register the message in the db
        await self.save_message(message)

        # send message to room group

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'send_message',
                'message': message,
                'username':self.user1.get_short_name(),
                'user_id': self.user1.id,
            }
        )
                

    async def send_message(self, event):
        """
        This method is used to send a message to the WebSocket connect
        Usage:
        - It is called when a message is received from the channel layer
        - After receive method broadcast message to all users in the room using
        group_send, for each user in the room, their consumer's send_message
        is called to sends this message to each individual user (client)
        """
        message = event['message']
        username = event['username']
        user_id = event['user_id']
        # Send a message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username,
            'user_id': user_id,
        }))

    @database_sync_to_async
    def save_message(self, message):
        ChatMessage.objects.create(
            room = self.room,
            user = self.user1,
            content = message
        )

    @database_sync_to_async
    def get_user(self,user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_or_create_room(self):
        if self.user1.id < self.user2.id:

            room, created = ChatRoom.objects.get_or_create(
                            user1 = self.user1,
                            user2 = self.user2
            )
        else:
            room, created = ChatRoom.objects.get_or_create(
                user1=self.user2,
                user2=self.user1
            )

        return room

    @database_sync_to_async
    def update_last_visit(self):
        self.room.update_last_visit(self.user1)
    
    # @database_sync_to_async
    # def get_unread_count(self):
    #     return self.room.get_unread_count(self.user1)


    





    