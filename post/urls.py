from django.urls import path
from post.views import index, NewPost, PostDetails, tags, like, favorite,  LostPostDetails, findSimilar,like, comparison,NewFunctionPost,findCat,updateEmail,deletePost,edit_post,edit_lostpost,updateEmailandSchedule

app_name = 'post'
urlpatterns = [
   	path('', index, name='index'),
   	path('newpost/', NewPost, name='newpost'),
   	path('<uuid:post_id>/', PostDetails, name='postdetails'),
   	path('<uuid:post_id>/like', like, name='postlike'),
   	path('<uuid:post_id>/favorite', favorite, name='postfavorite'),
   	path('tag/<slug:tag_slug>', tags, name='tags'),
    path('like/<uuid:post_id>',like,name='like-post'),
    path('compare/<uuid:lost_id>/<uuid:found_id>',comparison,name='compare'),
    path('lostpost/<uuid:post_id>', LostPostDetails, name='lostpostdetails'),
     path('find-similar/<uuid:post_id>/', findSimilar, name='find-similar-ajax'),
     path('find-cat/<uuid:post_id>',findCat,name='find-cat'),
     path('update-email/<uuid:post_id>/',updateEmail,name='update-email'),
     path('update-schedule/<uuid:post_id>/',updateEmail,name='update-schedule'),
     path('update-email-schedule/<uuid:post_id>/',updateEmailandSchedule,name='update-email-schedule'),
     path('delete-post/<uuid:post_id>/',deletePost,name='delete-post'),
     path('edit-post/<uuid:post_id>/',edit_post,name='edit-post'),
     path('edit-lostpost/<uuid:post_id>/',edit_lostpost,name='edit-lost-post'),
     path('lost-found-post/<option>/',NewFunctionPost,name='new-function-post'),
    
]