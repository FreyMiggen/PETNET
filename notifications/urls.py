from django.urls import path
from notifications.views import ShowNOtifications, hideNotification

app_name = 'notifications'
urlpatterns = [
   	path('', ShowNOtifications, name='show-notifications'),
   	path('<int:noti_id>/delete', hideNotification, name='delete-notification'),

]