
# Create your views here.
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import ChatMessage,ChatRoom
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_GET
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
def chat_room(request, user_id):
    user2 = get_object_or_404(User, id=user_id)
    current_user = request.user
    other_user = get_object_or_404(User,id=user_id)

    if user_id < current_user.id:

        chat_room,created = ChatRoom.objects.get_or_create(user1=other_user,user2=current_user)
    else:
        chat_room, created = ChatRoom.objects.get_or_create(user2=other_user,user1=current_user)
    # if the chat room has already existed, load 20 most recent messages
    if not created:
        messages = ChatMessage.objects.filter(room=chat_room)
        messages = messages.order_by('-timestamp')[:50]
        # take the message that is the most far in history
        # messages is a list of message from latest -> far in history
        if len(messages)>0:
            last_message_id = messages[len(messages)-1].id
        else:
            messages = list()
            last_message_id=None
            
    else:
        messages = list()
        last_message_id = None

    # GET A LIST OF ALL USERS THAT THE REQUEST USER HAVE CONNECTED TO
    all_chat_rooms = ChatRoom.objects.filter(
            Q(user1=current_user) | Q(user2=current_user)
    )

    other_users = list()
    for room in all_chat_rooms:
        if room.user1 == current_user:
            other_users.append(room.user2)
        else:
            other_users.append(room.user1)

    return render(request, 'room_test.html', {
        'user2': user2,
        'messages':messages,
        'last_message_id':last_message_id,
        'other_users':other_users,
        'requesting_profile':current_user.profile,
    })


def get_messages(request, user_id):
    current_user = request.user
    other_user = get_object_or_404(User,id=user_id)
    if user_id < current_user.id:

        chat_room = ChatRoom.objects.get(user1=other_user,user2=current_user)
    else:
        chat_room = ChatRoom.objects.get(user2=other_user,user1=current_user)
    

    before_id = request.GET.get('before_id')
    messages = ChatMessage.objects.filter(room=chat_room)
    if before_id:
        messages = messages.filter(id__lt=before_id)
    messages = messages.order_by('-timestamp')[:50]
    
    return JsonResponse({
        'messages': [
            {
                'id': msg.id,
                'content': msg.content,
                'user_id': msg.user.id,
                'timestamp': msg.timestamp.isoformat()
            } for msg in reversed(messages)
        ]
    })

@login_required
def open_inbox(request):

    ## open the 
    current_user = request.user

    all_chat_rooms = ChatRoom.objects.filter(
            Q(user1=current_user) | Q(user2=current_user)
    ).order_by('-lastest_update_time')

    other_users = list()
    for room in all_chat_rooms:
        if room.user1 == current_user:
            other_users.append(room.user2)
        else:
            other_users.append(room.user1)

    # get the unread_message
    unread_counts=[]
    for room in all_chat_rooms:
        if current_user == room.user1:
            unread_message = ChatMessage.objects.filter(room=room).filter(timestamp__range=(room.user1_last_visit,room.lastest_update_time)).count()
            unread_counts.append(unread_message)
        else:
            unread_message = ChatMessage.objects.filter(room=room).filter(timestamp__range=(room.user2_last_visit,room.lastest_update_time)).count()
            unread_counts.append(unread_message)

    # get the chat room that is most recent active
    results =[{'room':room,'other_user':other_user,'unread':unread} for (room,other_user,unread) in zip(all_chat_rooms,other_users,unread_counts)]
    
    return render(request,'inbox.html',{'results':results})


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