"""petnet URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

from authy.views import UserProfileView, follow
from post.views import index,FunctionNewsFeed,searchBar


urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin_tools_stats/', include('admin_tools_stats.urls')),
    path('',index,name='newsfeed'),
    path('post/', include('post.urls')),
    path('user/', include('authy.urls')),
    # path('direct/', include('direct.urls')),
    path('stories/', include('stories.urls')),
    path('notifications/', include('notifications.urls')),
    path('chat/',include('chat.urls')),
    path('comment/',include('comment.urls')),
    path('explore/', searchBar, name='explore'),
    path('<int:user_id>/follow/<option>', follow, name='follow'),
    path('function_newsfeed/<option>/',FunctionNewsFeed, name='function-feed'),
    path('<slug:slug>/', UserProfileView.as_view(),{'type':'normal'}, name='profile'),
    path('<slug:slug>/lostpost', UserProfileView.as_view(),{'type':'lost'}, name='profile-lostpost'),
    path('<slug:slug>/foundpost', UserProfileView.as_view(),{'type':'found'}, name='profile-foundpost'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
