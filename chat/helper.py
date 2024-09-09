from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from .models import ChatRoom

def room_owner_permission(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        room_id = kwargs.get('room_id')
        if not room_id:
            return HttpResponseForbidden("Room ID is required.")

        try:
            chat_room = get_object_or_404(ChatRoom, id=room_id)
            if request.user not in [chat_room.user1, chat_room.user2]:
                return HttpResponseForbidden("You do not have permission to perform this action.")
            return view_func(request, *args, **kwargs)
        except ChatRoom.DoesNotExist:
            return HttpResponseForbidden("Chat room does not exist.")

    return _wrapped_view