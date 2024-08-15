from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('room/<int:user_id>/',views.chat_room,name='room'),
    path('room/messages/<int:user_id>/',views.get_messages,name='get-messages')
]