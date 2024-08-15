from django.urls import path
from .views import deleteComment

app_name ='comment'

urlpatterns =[
    path('delete-comment/<int:comment_id>/',deleteComment,name='delete-comment'),
]