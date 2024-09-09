
# Create your views here.
from django.shortcuts import render, get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import ChatMessage,ChatRoom
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_GET
from django.http import HttpResponseForbidden
from .helper import room_owner_permission
User = get_user_model()


def CountMessages(request):
    count_messages = 0
    if request.user.is_authenticated:
        current_user = request.user

        all_chat_rooms = ChatRoom.objects.filter(
                Q(user1=current_user) | Q(user2=current_user)
        )

        # get the unread_message
        for room in all_chat_rooms:
            if current_user == room.user1:
                unread_message = ChatMessage.objects.filter(room=room).filter(timestamp__range=(room.user1_last_visit,room.lastest_update_time)).count()
                
                
            else:
                unread_message = ChatMessage.objects.filter(room=room).filter(timestamp__range=(room.user2_last_visit,room.lastest_update_time)).count()
                
            count_messages+=unread_message

    return {'count_messages':count_messages}

@login_required
def createChatRoom(request,user_id):

    user = request.user
    current_partner = get_object_or_404(User,id=user_id)

    # GET CURRENT ROOM
    # if no room exist => create one
    created = False
    if user_id < user.id:
        current_room,created = ChatRoom.objects.get_or_create(user1=current_partner,user2=user)
    else:
        current_room,created = ChatRoom.objects.get_or_create(user1=user,user2=current_partner)

    if created:
        current_room.lastest_update_time = current_room.created_at
        current_room.user1_last_visit = current_room.created_at
        current_room.user2_last_visit = current_room.created_at
        current_room.save()
   

    return redirect('chat:room',room_id=current_room.id)

@login_required
@room_owner_permission
def chat_room(request, room_id):
    user = request.user
    current_room = get_object_or_404(ChatRoom,id=room_id)
    current_partner = current_room.get_partner(user)
    # when a user visit a room, set the last_time_visit to now
    # this will automatically set unread_count to zero (hope so :))
    current_room.update_last_visit(user)

   

    # return a list of all rooms that the user in
    rooms = ChatRoom.objects.filter(
        Q(user1=user) | Q(user2=user)
    ).order_by('-lastest_update_time')
    unread_counts = list()
    for room in rooms:
        if user == room.user1:
            unread_message = ChatMessage.objects.filter(room=room).filter(timestamp__range=(room.user1_last_visit,room.lastest_update_time)).count()
            unread_counts.append(unread_message)
        else:
            unread_message = ChatMessage.objects.filter(room=room).filter(timestamp__range=(room.user2_last_visit,room.lastest_update_time)).count()
            unread_counts.append(unread_message)

    messages = current_room.room_messages.all().order_by('-timestamp')
    has_message = False
    if len(messages)>20:
        has_message = True

    messages = messages[:20]
    # take the message that is the most far in history
    # messages is a list of message from latest -> far in history
    
    
    if len(messages)>0:
        last_message_id = messages[len(messages)-1].id
    else:
        # messages = list()
        last_message_id=None
    
    partners = [room.get_partner(user) for room in rooms]

    room_items = [{'room':room,'partner':partner,'unread':unread} for (room,partner,unread) in zip(rooms,partners,unread_counts)]


    return render(request,'room.html',{'room_items':room_items,'current_room':current_room,
                                            'current_partner':current_partner,
                                            'messages':messages,
                                            'last_message_id':last_message_id,
                                            'has_message':has_message})



def get_messages(request, room_id):
    chat_room = get_object_or_404(ChatRoom,id=room_id)
    if request.user.is_authenticated and request.user in [chat_room.user1,chat_room.user2]:
        before_id = request.GET.get('before_id')
        messages = ChatMessage.objects.filter(room=chat_room)
        if before_id:
            messages = messages.filter(id__lt=before_id)

        has_message = False
        if len(messages) > 20:
            has_message = True
    
        messages = messages.order_by('-timestamp')[:20]

        return JsonResponse({
            'messages': [
                {
                    'id': msg.id,
                    'content': msg.content,
                    'user_id': msg.user.id,
                    'timestamp': msg.timestamp.isoformat()
                } for msg in reversed(messages)
            ],
            'has_message':has_message
        })
    else:
        return JsonResponse({
        'success': False
        })

@login_required
def open_inbox(request):

    current_user = request.user
    rooms = ChatRoom.objects.filter(
        Q(user1=current_user) | Q(user2=current_user)
    ).order_by('-lastest_update_time')
    partners = [room.get_partner(current_user) for room in rooms]
	
    unread_counts = list()
    for room in rooms:
        if current_user == room.user1:
            unread_message = ChatMessage.objects.filter(room=room).filter(timestamp__range=(room.user1_last_visit,room.lastest_update_time)).count()
            unread_counts.append(unread_message)
        else:
            unread_message = ChatMessage.objects.filter(room=room).filter(timestamp__range=(room.user2_last_visit,room.lastest_update_time)).count()
            unread_counts.append(unread_message)
    
    room_items = [{'room':room,'partner':partner,'unread':unread,'latest_message':room.get_latest_message()} 
                  for (room,partner,unread) in zip(rooms,partners,unread_counts)]
    
    return render(request,'inbox.html',{'room_items':room_items})
    


@login_required
@require_GET
def get_unread_counts(request):
    user = request.user
    chat_rooms = ChatRoom.objects.filter(user1=user) | ChatRoom.objects.filter(user2=user)
    other_users = []
    unread_counts = dict()
    for room in chat_rooms:
        if room.user1 == user:
            other_users.append(room.user2)
        else:
            other_users.append(room.user1)
    
    unread_counts = {
        str(other_user.id): room.get_unread_count(user)
        for other_user,room in zip(other_users,chat_rooms)
    }
    return JsonResponse(unread_counts)