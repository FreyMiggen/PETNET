from django.urls import path
from .views import open_inbox,chat_room,get_messages,createChatRoom

app_name = 'chat'

urlpatterns = [
    path('rooms/',open_inbox,name='inbox'),
    path('room/<int:room_id>/',chat_room,name='room'),
    path('room/messages/<int:room_id>/',get_messages,name='get-messages'),
    path('create/<int:user_id>',createChatRoom,name='create-room'),
]