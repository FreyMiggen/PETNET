from django.urls import path
from authy.views import Signup, PasswordChange, PasswordChangeDone, EditProfile, add_cat, CatDetail, createEmbeddingVector,deleteCatImg,addCatImage, viewCat, catAlbum, viewcatImageStorage, logoutView
from django.contrib.auth import views as authViews 
from authy.views import editCat,submitFeedback,sucessFeeback,createCatFood
app_name= 'authy'

urlpatterns = [
   	
    path('profile/edit', EditProfile, name='edit-profile'),
   	path('signup/', Signup, name='signup'),
   	path('login/', authViews.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/',logoutView,name='logout'),
   	# path('logout/', authViews.LogoutView.as_view(next_page='authy:signup'), name='logout'),
   	path('changepassword/', PasswordChange, name='change_password'),
   	path('changepassword/done', PasswordChangeDone, name='change_password_done'),
   	path('passwordreset/', authViews.PasswordResetView.as_view(), name='password_reset'),
   	path('passwordreset/done', authViews.PasswordResetDoneView.as_view(), name='password_reset_done'),
   	path('passwordreset/<uidb64>/<token>/', authViews.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
   	path('passwordreset/complete/', authViews.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('add_cat/',add_cat,name='add-cat'),
    # path('<slug>/<int:user_id>/',viewCat,name='cat-list'),
    path('cats/<int:cat_id>/',CatDetail,name='cat-detail'),
    path('cats/add/<int:cat_id>/',addCatImage,name='add-cat-img'),
    path('cats/create-emb-vector/<int:cat_id>/',createEmbeddingVector,name='create-emb-vector'),
    path('cat-img/delete/<int:post_id>',deleteCatImg,name='cat-img-delete'),
	path('cats/<int:cat_id>/album/',catAlbum,name='cat-album'),
    path('cats/<int:cat_id>/image/<type>',viewcatImageStorage,name='cat-image'),
    path('cats/edit/<int:cat_id>/',editCat,name='edit-cat'),
    path('feedback/',submitFeedback,name='submit-feedback'),
    path('feedback/success/',sucessFeeback,name='success-feedback'),
    path('cat/food/<int:cat_id>',createCatFood,name='cat-food'),
    
]

