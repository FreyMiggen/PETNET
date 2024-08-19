from django.shortcuts import render, redirect, get_object_or_404
from django.template import loader
from django.http import HttpResponse,JsonResponse
from django.views.decorators.http import require_GET,require_POST

from notifications.models import Notification
# Create your views here.
from authy.models import Profile
def ShowNOtifications(request):
	user = request.user
	notifications = Notification.objects.filter(user=user,hidden=False).order_by('-date')
	Notification.objects.filter(user=user, is_seen=False).update(is_seen=True)

	template = loader.get_template('notifications.html')
	profile = get_object_or_404(Profile,user=user)
	context = {
		'notifications': notifications,
		'requesting_profile': profile
	}

	return HttpResponse(template.render(context, request))

# def DeleteNotification(request, noti_id):
# 	user = request.user
# 	Notification.objects.filter(id=noti_id, user=user).delete()
# 	return redirect('show-notifications')


def CountNotifications(request):
	count_notifications = 0
	if request.user.is_authenticated:
		count_notifications = Notification.objects.filter(user=request.user, is_seen=False,hidden=False).count()
		

	return {'count_notifications':count_notifications}


def hideNotification(request,noti_id):
	
	notify = Notification.objects.get(id=noti_id)
	if notify.user == request.user:
		notify.hidden=True
		notify.save()
		return redirect('notifications:show-notifications')
	else:
		return JsonResponse({'success':False,'message':'You do not have authority'})
		


