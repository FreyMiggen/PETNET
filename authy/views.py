from django.shortcuts import render, redirect, get_object_or_404
from authy.forms import SignupForm, ChangePasswordForm, ProfileUpdateForm,AddCatForm, AddCatImage, EditCatForm, FeedbackForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import get_user_model
from authy.models import Profile, Cat, CatImageStorage, Follow
from post.models import Post, Stream, LostPost, FoundPost
from django.db import transaction
from django.template import loader
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from django.contrib.auth import logout
from django.urls import resolve
from post.tasks import createEmbeddingCat
from django.views.decorators.http import require_POST
from .helper import cat_permission,cat_owner_permission
User = get_user_model()
# Create your views here.

def showUser(request):
	if request.user.is_authenticated:
		profile = get_object_or_404(Profile,user=request.user)
	return {'requesting_profile':profile}



from django.db.models import Case, When, Value, BooleanField, Exists, OuterRef
from django.db.models.functions import Coalesce

class UserProfileView(TemplateView):

	template_name = 'profile.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		slug = self.kwargs.get('slug')
		profile = get_object_or_404(Profile, slug=slug)
		user = profile.user
		requesting_profile = get_object_or_404(Profile, user=self.request.user)
		url_name = resolve(self.request.path).url_name

		type = self.kwargs.get('type', 'normal')

		if type == 'lost':
			posts = LostPost.objects.filter(user=user).order_by('-posted')
		elif type == 'found':
			posts = FoundPost.objects.filter(user=user).order_by('-posted')
		else:

			# CAN OPTIMIZE USING DATABASE QUERY ANNOTATE WHEN CASE
			if self.request.user == user:
				posts = Post.objects.filter(user=user).order_by('-posted')
			else:
				# posts = [post for post in Post.objects.filter(user=user).order_by('-posted') if post.can_access(self.request.user.id)]
				user_id = self.request.user.id
				# Subquery to check if the user is following the post's owner
				following_subquery = Follow.objects.filter(
					follower_id=user_id,
					following_id=OuterRef('user_id')
				)

				posts = Post.objects.filter(user=user).annotate(
					can_access=Case(
						When(privacy='public', then=Value(True)),
						When(privacy='followers', then=Exists(following_subquery)),
						default=Value(False),
						output_field=BooleanField()
					)
				).filter(can_access=True).order_by('-posted')

        # Profile info box
		posts_count =posts.count()
		following_count = Follow.objects.filter(follower=user).count()
		followers_count = Follow.objects.filter(following=user).count()

        # Follow status
		follow_status = Follow.objects.filter(following=user, follower=self.request.user).exists()

		# Pagination
		paginator = Paginator(posts, 8)
		page_number = self.request.GET.get('page')
		posts_paginator = paginator.get_page(page_number)

		context.update({
			'profile': profile,
			'posts': posts,
			'following_count': following_count,
			'followers_count': followers_count,
			'posts_count': posts_count,
			'follow_status': follow_status,
			'url_name': url_name,
			'requesting_profile': requesting_profile,
			'type':type
		})

		return context

	@classmethod
	def as_view(cls, **initkwargs):
		view = super().as_view(**initkwargs)
		view.initkwargs = initkwargs
		return view
    	


def Signup(request):
	if request.method == 'POST':
		form = SignupForm(request.POST)
		if form.is_valid():
			username = form.cleaned_data.get('name')
			email = form.cleaned_data.get('email')
			password = form.cleaned_data.get('password')
			User.objects.create_user(name=username, email=email, password=password)
			return redirect('authy:login')
	else:
		form = SignupForm()
	
	context = {
		'form':form,
	}

	return render(request, 'signup.html', context)


@login_required
def PasswordChange(request):
	user = request.user
	if request.method == 'POST':
		form = ChangePasswordForm(request.POST,user=user)
		if form.is_valid():
			new_password = form.cleaned_data.get('new_password')
			user.set_password(new_password)
			user.save()
			update_session_auth_hash(request, user)
			return redirect('change_password_done')
	else:
		form = ChangePasswordForm(instance=user,user=user)

	context = {
		'requesting_profile':request.user.profile,
		'form':form,
	}

	return render(request, 'change_password_test.html', context)

def PasswordChangeDone(request):
	profile = request.user.profile
	return render(request, 'authy:change_password_done.html',{'requesting_profile':profile})


@login_required
def EditProfile(request):
	user = request.user
	profile = Profile.objects.get(user=user)

	if request.method == 'POST':
		form = ProfileUpdateForm(request.POST, request.FILES,instance=profile)
		if form.is_valid():

			form.save()
			return redirect('profile',slug=profile.slug)
	else:
		form = ProfileUpdateForm(instance=profile)

	context = {
		'form':form,
		'profile':profile,
		'requesting_profile':profile
	}

	return render(request, 'edit_profile.html', context)

@login_required
def logoutView(request):
	if request.method == 'POST':
		 # Get the 'next' parameter or use 'dashboard' as the default
		action = request.POST.get('action')
		profile = get_object_or_404(Profile,user=request.user)
		
		if action == 'Confirm':
			logout(request)
		
			return redirect('authy:login')  # Redirect to the login page after logout
		else:
			return redirect('profile',slug=profile.slug)
    			
			# return redirect(next_url)  # Redirect to the dashboard (or any other relevant page)

	return render(request, 'logout.html',{})

@login_required
def follow(request, user_id, option):
	"""
	Handle all logic for follow. Do not use model signal for follow unless for creating notification
	"""
	following = get_object_or_404(User, id=user_id)

	try:
		f, created = Follow.objects.get_or_create(follower=request.user, following=following)
		if int(option) == 0:
			f.delete()
			Stream.objects.filter(following=following, user=request.user).update(hidden=True)
			
		else:
			posts = Post.objects.all().filter(user=following).order_by('-posted')[:25]

			with transaction.atomic():
				for post in posts:
					stream,created = Stream.objects.get_or_create(post=post, user=request.user, date=post.posted, following=following)
					if not created:
						stream.hidden = False
						stream.save()
					

		return HttpResponseRedirect(reverse('profile', args=[following.profile.slug]))
		
	except User.DoesNotExist:
		return HttpResponseRedirect(reverse('profile', args=[following.profile.slug]))
	

@login_required
def add_cat(request):
	profile = get_object_or_404(Profile,user=request.user)
	if request.method == 'POST':
		form = AddCatForm(request.POST,request.FILES, user=request.user)

		if form.is_valid():
    	
			cat = form.save()
			# images = request.FILES.getlist('images')

			# cat.fullbody_img.set(images)
			# for image in images:
			# 	CatImageStorage.objects.create(cat=cat,pic=image)

			messages.success(request, f'Your cat {cat.name} has been added successfully!')
			return redirect('authy:cat-detail', cat_id=cat.id)  # Assuming you have a 'cat_detail' URL
	else:
		form = AddCatForm(user=request.user)

	context = {'form':form,
				'requesting_profile':profile,
				'profile':profile }
	return render(request, 'add_cat.html', context)

@login_required(login_url='authy:login')
@cat_owner_permission
def editCat(request,cat_id):
	cat = get_object_or_404(Cat,id=cat_id)
	if request.method == "POST":
		form = EditCatForm(request.POST,request.FILES,instance=cat)
		if form.is_valid():
			form.save()
			return redirect('authy:cat-detail',cat_id=cat_id)
	else:
		form = EditCatForm(instance=cat)
		return render(request,'edit_cat.html',{'cat':cat,'form':form,'requesting_profile':request.user.profile})
	

@login_required(login_url='authy:login')
@cat_permission
def CatDetail(request,cat_id):
	profile = get_object_or_404(Profile,user=request.user)
	cat = Cat.objects.get(id=cat_id)
	context = {'cat':cat,'requesting_profile':profile}
	return render(request,'cat_detail_test.html',context)

	# if cat.can_access(request.user.id):
	# 	context = {'cat':cat,'requesting_profile':profile}
	# 	return render(request,'cat_detail_test.html',context)
	# else:
	# 	context = {'requesting_profile':profile,'message':'This cat is either private or only accessible for followers!'}
	# 	return render(request,'cat_detail_test.html',context=context)

	# if cat.is_owner(request.user.id):
	# 	if request.method == "POST":
	# 		img_form = AddCatImage(request.POST,request.FILES)
	# 		if img_form.is_valid():
	# 			pic_list = request.FILES.getlist('pic')
	# 			for pic in pic_list:
	# 				pic =CatImageStorage(cat=cat,pic=pic)
	# 				pic.save()
	# 			messages.success(request,'Image has been added!')
	# 		return redirect('authy:cat-detail',cat_id=cat.id)
	# 	else:
	# 		img_form = AddCatImage()
    		
	# 	context = {'cats':cats,'cat':cat,'img_list':CatImageStorage.objects.filter(cat = cat),'requesting_profile':profile,'form':img_form}
	# else:
	# 	context = {'cats':cats,'message':'You do not have permission to access this page','requesting_profile':profile}

	# return render(request,'cat_detail_test.html',context)

from .models import CatFullBodyImage
from .forms import AddCatBodyImage
from django.http import HttpResponseForbidden

@login_required(login_url='authy:login')
@cat_permission
def viewcatImageStorage(request,cat_id,type):
	profile = get_object_or_404(Profile,user=request.user)
	cat = Cat.objects.get(id=cat_id)
	owner = cat.user
	cats = Cat.objects.filter(user=owner)
	
	if request.method == "POST":
		if cat.user == request.user:
			if type == 'face':
				img_form = AddCatImage(request.POST,request.FILES)
				if img_form.is_valid():
					pic_list = img_form.cleaned_data['pic']

					for pic in pic_list:
						CatImageStorage.objects.create(cat=cat,pic=pic)
					messages.success(request,'Image has been added!')
				return redirect('authy:cat-image',cat_id=cat.id,type='face')
			else: # type == body
    				
				img_form = AddCatBodyImage(request.POST,request.FILES)
				if img_form.is_valid():
					pic_list = img_form.cleaned_data['pic']
					for pic in pic_list:
						CatFullBodyImage.objects.create(cat=cat,pic=pic)
					messages.success(request,'Image has been added!')
				return redirect('authy:cat-image',cat_id=cat.id,type='body')
    				
		else:
			return HttpResponseForbidden('You di=o not have authority to do this action!')
	else: # request is get
		if type == 'face':
			img_form = AddCatImage()
			img_list = CatImageStorage.objects.filter(cat=cat)
		else:
			img_form = AddCatBodyImage()
			img_list = CatFullBodyImage.objects.filter(cat=cat)
		
		if cat.user == request.user:
			check = True
		else:
			check =False
    		
		context = {'cats':cats,'cat':cat,'img_list':img_list,'requesting_profile':profile,'form':img_form,'check':check}


	return render(request,'cat_image_storage.html',context)

from .models import CatFullBodyImage


def catAlbum(request,cat_id):
	profile = get_object_or_404(Profile,user=request.user)
	cat = get_object_or_404(Cat,id=cat_id)
	post_list = Post.objects.filter(cats=cat)
	context={'post_list':post_list,'cat':cat,'requesting_profile':profile}
	return render(request,'cat_album.html',context)

@login_required(login_url='authy:login')
def viewCat(request,slug):
	user = request.user
	profile = get_object_or_404(Profile,slug=slug)
	cat_list = Cat.objects.filter(user=profile.user)
	if user == profile.user:
		cats = cat_list
		checked=True
	else:
		checked = False
		cats = []
		for cat in cat_list:
			if cat.can_access(request.user.id):
				cats.append(cat)
	
	return render(request,'cat_list.html',{'cats':cats,'requesting_profile':request.user.profile,'checked':checked})


# FIX THIS CODE
@login_required(login_url='authy:login')
@require_POST
def createEmbeddingVector(request,cat_id):
	# only for onwer of cat

	user = request.user
	# cat_list = user.cats.all()
	cat = Cat.objects.get(id=cat_id)

	if cat.user == user:
		
			# create embedding vector
			# add_face_to_db.delay(cat_id)
		if len(cat.images.all())>= 6:
			createEmbeddingCat.delay(cat_id)
				
			return JsonResponse({'success':True,'message':'Task is given to Celery!'})
		else:
			return JsonResponse({'success':False,'message':'Để tạo vector đặc trưng phải có ít nhất 6 ảnh khuôn mặt!'})
	else:
		return JsonResponse({'success':False,'message':'You do not have authority to do this action!'})


@login_required(login_url='authy:login')
def deleteCatImg(request, post_id):
    post = get_object_or_404(CatImageStorage, id=post_id)
    if request.method == 'POST':
        post.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required(login_url='authy:login')
def addCatImage(request,cat_id):
	# user = request.user
	# cat_list = user.cats.all()
	cat = Cat.objects.get(id=cat_id)
	profile = get_object_or_404(Profile,user=request.user)
	if request.method == 'POST':
		img_form = AddCatImage(request.POST,request.FILES)
		if img_form.is_valid():
			pic = img_form.cleaned_data['pic']
			CatImageStorage.objects.create(cat=cat,pic=pic)
			return redirect('authy:cat-detail',cat_id=cat.id)
		else:
			return render(request,'add_cat_img.html',{'form':AddCatImage(),'requesting_profile':profile})
	else:
		form = AddCatImage()
		return render(request,'add_cat_img.html',{'form':form,'cat':cat,'requesting_profile':profile})
	

# def LostStream(request):
# 	lostposts = LostPost.objects.all().order_by('-created')

@login_required(login_url='authy:login')
def submitFeedback(request):
	if request.method == 'POST':
		form = FeedbackForm(request.POST)
		if form.is_valid():
			feedback = form.save(commit=False)
			feedback.user = request.user
			feedback.save()
			return redirect('authy:success-feedback')
	else:
		form = FeedbackForm()
	return render(request, 'feedback_submit.html', {'form': form,'requesting_profile':request.user.profile})


@login_required(login_url='authy:login')
def sucessFeeback(request):
	if request.method == 'POST':
			# Get the 'next' parameter or use 'dashboard' as the default
		action = request.POST.get('action')
		profile = get_object_or_404(Profile,user=request.user)
	
		if action == 'Confirm':
		
			return redirect('authy:submit-feedback')  
		else:
			return redirect('newsfeed')
			
	return render(request, 'feedback_success.html',{'requesting_profile':request.user.profile})


from .models import CatFood
from .forms import CatFoodForm
@login_required(login_url='authy:login')
@cat_owner_permission
def createCatFood(request,cat_id):
	cat = get_object_or_404(Cat,id=cat_id)

	if request.method == 'POST':
		form = CatFoodForm(request.POST,request.FILES)
		if form.is_valid():
			catfood = form.save(commit=False)
			catfood.cat = cat
			catfood.save()
			return redirect('authy:cat-food',cat_id=cat_id)
	else:
		form = CatFoodForm()
		
		return render(request,'catfood.html',{'requesting_profile':request.user.profile,'form':form,'cat':cat})