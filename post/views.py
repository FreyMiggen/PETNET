from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
import json
from post.models import Stream, Post, Tag, Likes, PostFileContent, LostPost, FoundPost, CandidateMatch,BasePost
from post.forms import NewLostPostForm, NewFoundPostForm,PostCreateWithImagesForm, PostEditForm
from stories.models import Story, StoryStream
from django.forms import modelformset_factory
from comment.models import Comment
from comment.forms import CommentForm
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView
from django.core.validators import validate_email
from django.forms import modelformset_factory, inlineformset_factory

from django.contrib.auth.decorators import login_required
from django import forms
from django.urls import reverse
from authy.models import Profile
from .tasks import createEmbedding, matchCat
from django.core.cache import cache
from celery.result import AsyncResult
import time
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import datetime
from django.contrib import messages
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string
import itertools
# Create your views here.
@login_required(login_url='authy:login')
@require_GET
def index(request):
	user = request.user
	followed_posts = Stream.objects.filter(user=user,hidden=False).order_by('-date')
	followed_posts = [stream.post for stream in followed_posts]
	#     # Calculate the timestamp for 20 days ago
	time_threshold = timezone.now() - timedelta(hours=480)

	# # Query to retrieve the posts with the highest likes, posted in the last 10 days
	top_posts = Post.objects.filter(
		posted__gte=time_threshold,  # Posts from the last 48 hours
		is_hidden=False,
		privacy = 'public',  # Exclude hidden posts
	).order_by('-likes')  # Order by likes in descending order and limit to 20 posts

	posts = list(itertools.chain(followed_posts,top_posts))

	profile = get_object_or_404(Profile,user=user)
		
	paginator = Paginator(posts,5) # show 2 post per page


	if request.headers.get('x-requested-with') == 'XMLHttpRequest':
		page = int(request.GET.get('page'))
		page_obj = paginator.get_page(page)
    	
		likes = [post_item.has_liked(request.user.id) for post_item in page_obj]
		results = []
		for post_item, like in zip(page_obj, likes):
			post_html = render_to_string('post_item.html', {
				'post_item': post_item,
				'liked': like,
				'requesting_profile': request.user.profile
			}, request=request)
			results.append({'html': post_html,'test':'kim'})
		return JsonResponse({'results': results,'has_next': page_obj.has_next(),'number':page})
	else:
		page_obj = paginator.get_page(1)
		likes =[post_item.has_liked(request.user.id) for post_item in page_obj]

		results= [{'post_item':post_item,'liked':like} for (post_item,like) in zip(page_obj,likes)]		

		template = loader.get_template('index.html')

		context = {
		'post_items': results,
		
		'requesting_profile':profile
		}

		return HttpResponse(template.render(context, request))

@login_required(login_url='authy:login')
def FunctionNewsFeed(request,option):
	if option == 'lost':
		posts = LostPost.objects.all().order_by('-posted')
	else:
		posts = FoundPost.objects.all().order_by('-posted')

	# likes =[post_item.has_liked(request.user.id) for post_item in posts]

	# results= [{'post_item':post_item,'liked':like} for (post_item,like) in zip(posts,likes)]

	
	paginator = Paginator(posts, 2)  # Show 10 posts per page
	# count = paginator.count

	if request.headers.get('x-requested-with') == 'XMLHttpRequest':
		page = int(request.GET.get('page'))
		page_obj = paginator.get_page(page)
		likes = [post_item.has_liked(request.user.id) for post_item in page_obj]
		results = []
		for post_item, like in zip(page_obj, likes):
			post_html = render_to_string('function_post_item.html', {
				'post_item': post_item,
				'liked': like,
				'requesting_profile': request.user.profile
			}, request=request)

			results.append({'html': post_html})
		return JsonResponse({'results': results, 'option':option,'has_next': page_obj.has_next(),'number':page})
	else:
		page_obj = paginator.get_page(1)
		likes = [post_item.has_liked(request.user.id) for post_item in page_obj]
		results = [{'post_item': post_item, 'liked': like} for post_item, like in zip(page_obj, likes)]

		return render(request, 'function_newsfeed.html', {
			'post_items': results,
			'requesting_profile': request.user.profile,
			'page_obj': page_obj,
			'option':option,
		})

@login_required(login_url='authy:login')
def PostDetails(request, post_id):
	try:
		post = get_object_or_404(Post, id=post_id)
		tags = post.tags.all()
		privacy = post.privacy
		found = False
	except:
		post= get_object_or_404(FoundPost,id=post_id)
		tags = []
		privacy = 'public'
		found = True
	
	# if isinstance(post,Post):
	# 	post = get_object_or_404(Post,id=post_id)
	
	
	user = request.user
	profile = Profile.objects.get(user=user)
	favorited = Likes.objects.filter(user=request.user,post=post)
	if favorited:
		liked = True
	else:
		liked=False

	#comment
	comments = Comment.objects.filter(post=post).order_by('date')
	
	if request.user.is_authenticated:
		profile = Profile.objects.get(user=user)
		#For the color of the favorite button

		# if profile.favorites.filter(id=post_id).exists():
		# 	favorited = True

	#Comments Form
	if request.method == 'POST':
		form = CommentForm(request.POST)
		if form.is_valid():
			comment = form.save(commit=False)
			comment.post = post
			comment.user = user
			comment.save()
					

			return HttpResponseRedirect(reverse('post:postdetails', args=[post_id]))
	else:
		form = CommentForm()


	template = loader.get_template('post_detail_test.html')

	context = {
		'post':post,
		'profile':profile,
		'form':form,
		'comments':comments,
		'requesting_profile':profile,
		'status':liked,
		'tags':tags,
		'privacy':privacy,
		'found':found
	}

	return HttpResponse(template.render(context, request))


@login_required
def NewPost(request):
	user = request.user
	profile = get_object_or_404(Profile,user=user)

	if request.method == 'POST':
		form = PostCreateWithImagesForm(request.POST, request.FILES, user=user)

		if form.is_valid():
			files = request.FILES.getlist('content')
			caption = form.cleaned_data.get('caption')
			cats = form.cleaned_data.get('cats')
			tags_form = form.cleaned_data.get('tags')
			tags_list = list(tags_form.split(','))
			privacy = form.cleaned_data.get('privacy')

			post = Post.objects.create(caption=caption,user=user,privacy=privacy)

			for tag in tags_list:
				slug = slugify(tag)
				tag_obj, created = Tag.objects.get_or_create(slug=slug)
				if created:
					tag_obj.title = tag
					tag_obj.save()

				post.tags.add(tag_obj)

			for file in files:
				file_instance = PostFileContent(file=file, user=user)
				file_instance.save()
				post.content.add(file_instance)

			if cats:
				post.cats.set(cats)

			url = reverse('profile',args=[profile.slug])
			return redirect(url)

	else:
		form = PostCreateWithImagesForm(user=user)

	context = {
		'form':form,
		'profile':profile,
		'requesting_profile':profile,
	}

	return render(request, 'newpost.html', context)


@login_required
def NewFunctionPost(request,option):
	user = request.user
	profile = get_object_or_404(Profile,user=user)

	if request.method == 'POST':
		if option=='lost':
			form = NewLostPostForm(request.POST, request.FILES,user=request.user)
		else:
			form = NewFoundPostForm(request.POST, request.FILES,user=request.user)

		if form.is_valid():
			post_form = form.save(commit=False)
			fullbody_files = request.FILES.getlist('fullbody_img')
			files = request.FILES.getlist('content')
			caption = form.cleaned_data.get('caption')
			geotag = form.cleaned_data.get('geotag')
			# tags_form = form.cleaned_data.get('tags')
			# tags_list = list(tags_form.split(','))

			if option=='lost':
				# lost_time = form.cleaned_data('lost_time')
				lost_time = form.cleaned_data.get('lost_time')
				post = LostPost.objects.create(caption=caption, user=user,geotag=geotag,lost_time=lost_time)
			else:
				found_time = form.cleaned_data.get('found_time')
				post = FoundPost.objects.create(caption=caption, user=user,geotag=geotag,found_time=found_time)

			# for tag in tags_list:
			# 	slug = slugify(tag)
			# 	tag_obj, created = Tag.objects.get_or_create(slug=slug)
			# 	if created:
			# 		tag_obj.title = tag.strip()
			# 	post.tags.add(tag_obj)
			
			for file in files:
				file_instance = PostFileContent(file=file, user=user)
				file_instance.save()
				post.content.add(file_instance)

			for file in fullbody_files:
				file_instance = PostFileContent(file=file, user=user)
				file_instance.save()
				post.fullbody_img.add(file_instance)
    		
			
			if option == 'lost':
				createEmbedding.apply_async(args=[post.id],kwargs={'found':False,'field_name':'embedding'})
				url = reverse('post:lostpostdetails',kwargs={'post_id':post.id})
			else:
				createEmbedding.apply_async(args=[post.id],kwargs={'found':True,'field_name':'embedding'})
				url = reverse('post:postdetails',kwargs={'post_id':post.id})

			## UPON CREATED, REDIRECT TO LOST POST DETAIL
			
			return redirect(url)
	else:
		if option=='lost':
			form = NewLostPostForm(user=request.user)
		else:
			form = NewFoundPostForm(user=request.user)

	context = {
		'type':option,
		'form':form,
		'profile':profile,
		'requesting_profile':profile
	}

	return render(request, 'newlostpost.html', context)


# from itertools import chain
@login_required
def LostPostDetails(request, post_id):
	post = get_object_or_404(LostPost, id=post_id)
	user = request.user
	owner = post.user
	profile = get_object_or_404(Profile,user = request.user)
	#comment
	comments = Comment.objects.filter(post=post).order_by('date')
	privacy = 'public'
	favorited = Likes.objects.filter(user=request.user,post=post)
	files = list(post.fullbody_img.all())+ list(post.content.all())
	if favorited:
		liked = True
	else:
		liked=False
	
	profile = Profile.objects.get(user=request.user)
		#For the color of the favorite button

		# if profile.favorites.filter(id=post_id).exists():
		# 	favorited = True

	# ONLY OWNER OF POST ALLOW TO SEE RUN BUTTON
	if user == owner:
		check = True
	else:
		check = False
	#Comments Form
	if request.method == 'POST':
		form = CommentForm(request.POST)
		if form.is_valid():
			comment = form.save(commit=False)
			comment.post = post
			comment.user = user
			comment.save()
			return HttpResponseRedirect(reverse('lost-post-detail', args=[post_id]))
	else:
		form = CommentForm()


	template = loader.get_template('lostpost_detail.html')

	context = {
		'post':post,
		'profile':profile,
		'form':form,
		'comments':comments,
		'requesting_profile':profile,
		'check':check,
		'post_id':post_id,
		'privacy': privacy,
		'status':liked,
		'files':files,

	}

	return HttpResponse(template.render(context, request))


@login_required
@require_GET
def findSimilar(request,post_id):
	#	ONLY USER WHO CREATED THE LOST POST IS ALLOWED TO RUN SIMILAR TASK
	post = get_object_or_404(LostPost,id=post_id)
	if request.user != post.user:
		return render(request,'test.html',{'error':"You do not have access"})


	task = matchCat.apply_async(args=[post_id],kwargs={'in_batch':False})

	while True:
		state = AsyncResult(task.id).state
		if state == 'SUCCESS':
			# Retrieve the posts with the corresponding IDs
			matched_candidates = CandidateMatch.objects.filter(user=request.user,lostpost=post).order_by("-updated")[:10]

			# sort matches in ascending score order 
			sorted_matches = sorted(matched_candidates,key=lambda x:x.score)

			data = list()
			for i in range(len(sorted_matches)):
				temp = {'original_url':sorted_matches[i].foundpost.get_absolute_url(),
						'url':sorted_matches[i].foundpost.get_compare_url(post_id),
						'score':round(sorted_matches[i].score,2),
						'posted':sorted_matches[i].foundpost.posted,
						'username':sorted_matches[i].foundpost.user.get_short_name()}
				data.append(temp)
			# similar_posts = matched_candidates.matched.all()
			return JsonResponse(data,safe=False)


			# create a notification
			# CREATE A NOTIFICATION FOR USER
	
		time.sleep(1)  # Wait for a second before checking again

def tags(request, tag_slug):
	tag = get_object_or_404(Tag, slug=tag_slug)
	posts = Post.objects.filter(tags=tag).order_by('-posted')

	template = loader.get_template('tag.html')

	context = {
		'posts':posts,
		'tag':tag,
	}

	return HttpResponse(template.render(context, request))



@login_required
@require_POST
def like(request, post_id):
	"""
	When a user is already logged in, allow them to like a post
	user - user
	post_id: id of the post the user wants to like
	"""
	user = request.user
	post = BasePost.objects.get(id=post_id)
	current_likes = post.likes
	liked = Likes.objects.filter(user=user, post=post).count()

	if not liked:
		like = Likes.objects.create(user=user, post=post)
		#like.save()
		current_likes = current_likes + 1
		status = 'liked'

	else:
		Likes.objects.filter(user=user, post=post).delete()
		current_likes = current_likes - 1
		status = 'unliked'

	# using update to avoid triggering post_save signal
	BasePost.objects.filter(id=post_id).update(likes=current_likes)
	# post.likes = current_likes
	# post.save()

	return JsonResponse({'likes':post.likes,'status':status})

@login_required
def favorite(request, post_id):
	user = request.user
	post = Post.objects.get(id=post_id)
	profile = Profile.objects.get(user=user)

	if profile.favorites.filter(id=post_id).exists():
		profile.favorites.remove(post)

	else:
		profile.favorites.add(post)

	return HttpResponseRedirect(reverse('postdetails', args=[post_id]))



# class FunctionNewFeed(TemplateView):
# 	template_name = "function_post.html"
# 	def get_context_data(self, **kwargs):
# 		context = super().get_context_data(**kwargs)
# 		type = self.kwargs.get('type')
# 		if type == 'lost':
# 			post_items = LostPost.objects.all().order_by('posted')
# 		else:
# 			post_items = FoundPost.objects.all().order_by('posted')
		
# 		profile = get_object_or_404(Profile,user=self.request.user)

# 		context.update({
# 			'post_items':post_items,
# 			'requesting_profile':profile
# 		})

# 		return context
# 	@classmethod
# 	def as_view(cls,**initkwargs):
# 		view = super().as_view(**initkwargs)
# 		view.initkwargs = initkwargs
# 		return view
    		

@login_required()
def comparison(request,lost_id,found_id):

	lost = get_object_or_404(LostPost,id=lost_id)
	found = get_object_or_404(FoundPost,id=found_id)
	posts = [lost,found]

	profile = get_object_or_404(Profile,user=request.user)
	owner_id = found.user.id
	if request.method == 'POST':
		is_matched = request.POST.get('is_matched')
		if is_matched == 'yes':
			lost.is_found = True
			found.is_matched = True
			messages.success(request,"Posts have been marked as matched!.")
    		# redirect
			url = reverse('chat:room', kwargs={'user_id': owner_id})
			
			return redirect('chat:room',user_id=owner_id)	
			# redirect user to inbox to the owner of foundpost
			# system send notification to onwer of foundpost, at the same time, create a chat room for two people
			


	context = {'posts':posts, 'requesting_profile':profile}
	return render(request,'comparison.html',context)


# RENDER PAGE AFTER CLICK BUTTON 'TÌM MÈO LẠC'
@login_required()
def findCat(request,post_id):
	lostpost = get_object_or_404(LostPost,id=post_id)
	profile = get_object_or_404(Profile,user=request.user)
	if lostpost.user == request.user:
		# render the page that allow users to view all Matchhistory

		if request.method == 'POST':
			email = request.POST.get('email','')
			try:
				validate_email(email)
				lostpost.email = email
				lostpost.save()
				return HttpResponseRedirect(reverse('post:find-cat', args=[post_id]))

			except forms.ValidationError:
				messages.error(request, 'Invalid email address')
				return HttpResponseRedirect(reverse('post:find-cat', args=[post_id]))
			

		else:
    		# RETURN PERFECT MATCH + CANDIDATE MATCH 
			match_candidates = CandidateMatch.objects.filter(lostpost=lostpost,threshold=False).order_by('score')

			match_candidates = [{'match':match,'url':match.foundpost.get_compare_url(post_id)}
					   for match in match_candidates
					   ]
			perfect_candidates = CandidateMatch.objects.filter(lostpost=lostpost,threshold=True).order_by('-created')

			perfect_candidates = [{'match':match,'url':match.foundpost.get_compare_url(post_id)}
			for match in perfect_candidates
			]

			

			return render(request,'match_candidate_test.html',{'post_id':lostpost.id, 'requesting_profile':profile,'email':lostpost.email,'checked':lostpost.schedule,
													  'match_candidates':match_candidates,
													  'perfect_candidates':perfect_candidates})
	else:
		return HttpResponse('You are not allowed to access this page!')

def searchBar(request):
	# not login required
    query = request.GET.get('q', '')
    category = request.GET.get('category', 'people')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if category == 'people':
        results = Profile.objects.filter(
            Q(user__name__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
    elif category == 'post':
        results = Post.objects.filter(caption__icontains=query)
    elif category == 'lostpost':
        results = LostPost.objects.filter(caption__icontains=query)
    elif category == 'foundpost':
        results = FoundPost.objects.filter(caption__icontains=query)
    else:
        results = []

    if start_date and end_date and category != 'people':
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        results = results.filter(created_at__range=[start_date, end_date])

    paginator = Paginator(results, 10)  # Show 10 results per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'query': query,
        'category': category,
        'page_obj': page_obj,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'explore.html', context)

# @require_POST
# @login_required()
# def updateEmail(request,post_id):
# 	email = request.POST.get('email','')
# 	try:
# 		validate_email(email)
# 	except validate_email.message:
		
# 	lostpost = get_object_or_404(LostPost,id=post_id)
# 	lostpost.email = email
# 	messages.success(request,'Success')
# 	return redirect('post:find-cat',args=[post_id])

from django.db import transaction
@login_required
def edit_post(request, post_id):
	post = get_object_or_404(Post, id=post_id, user=request.user)

	if request.method == 'POST':
		form = PostEditForm(request.POST, request.FILES, instance=post, user=request.user)
		if form.is_valid():
			with transaction.atomic():
				edited_post = form.save(commit=False)
				
				# Handle tags
				tags = form.cleaned_data.get('tags').split(',')
				edited_post.tags.clear()
				for tag in tags:
					slug = slugify(tag.strip())
					tag_obj, created = Tag.objects.get_or_create(slug=slug)
					if created:
						tag_obj.title = tag
						tag_obj.save()
					edited_post.tags.add(tag_obj)
					
				
				# Handle content deletion
				content_to_delete = form.cleaned_data.get('delete_content', [])
				PostFileContent.objects.filter(id__in=content_to_delete).delete()
				
				# Handle new content
				new_files = request.FILES.getlist('new_content')
				for file in new_files:
					newfile=PostFileContent.objects.create(file=file, user=request.user)
					post.content.add(newfile)
				
				# handle cats
				cats = form.cleaned_data.get('cats')
				edited_post.cats.clear()
				for cat in cats:
					post.cats.add(cat)
	
				edited_post.save()
				
			
			messages.success(request, 'Post updated successfully!')
			return redirect('post:postdetails', post_id=post.id)  # Assuming you have a post detail view
	else:
		initial_data = {
			'caption': post.caption,
			'tags': ', '.join([tag.title for tag in post.tags.all()]),
			'cats': post.cats.all(),
		}
		form = PostEditForm(instance=post, initial=initial_data, user=request.user)

		context = {
			'form': form,
			'post': post,
			'requesting_profile':get_object_or_404(Profile,user=request.user),
		}
		return render(request, 'edit_post_test.html', context)

from .forms import LostPostEditForm
from authy.models import CatFullBodyImage
@login_required
def edit_lostpost(request, post_id):
	post = get_object_or_404(LostPost, id=post_id, user=request.user)

	if request.method == 'POST':
		form = LostPostEditForm(request.POST, request.FILES, instance=post, user=request.user)
		if form.is_valid():
			with transaction.atomic():
				edited_post = form.save(commit=False)
				
	
				# Handle content deletion
				content_to_delete = form.cleaned_data.get('delete_content', [])
				PostFileContent.objects.filter(id__in=content_to_delete).delete()
				
				# Handle new content
				new_files = request.FILES.getlist('new_content')
				for file in new_files:
					newfile=PostFileContent.objects.create(file=file, user=request.user)
					post.content.add(newfile)

				# Handle fullbody image deletion

				fullbody_content_to_delete = form.cleaned_data.get('fullbody_delete_content', [])
				PostFileContent.objects.filter(id__in=fullbody_content_to_delete).delete()
				
				# Handle new content
				new_files = request.FILES.getlist('fullbody_new_content')
				for file in new_files:
					newfile=PostFileContent.objects.create(file=file, user=request.user)
					post.fullbody_img.add(newfile)
				
				# # handle cats
				# cats = form.cleaned_data.get('cats')
				# edited_post.cats.clear()
				# for cat in cats:

				# 	post.cats.add(cat)
	

				edited_post.save()
				
			
			messages.success(request, 'LostPost updated successfully!')
			return redirect('post:lostpostdetails', post_id=post.id)  # Assuming you have a post detail view
	else:
		initial_data = {
			'caption': post.caption,
			# 'tags': ', '.join([tag.title for tag in post.tags.all()]),
			# 'cats': post.cats.all(),
		}
		form = LostPostEditForm(instance=post, initial=initial_data, user=request.user)

		context = {
			'form': form,
			'post': post,
			'requesting_profile':get_object_or_404(Profile,user=request.user),
		}
		return render(request, 'edit_lostpost.html', context)


@login_required
@require_POST
def updateEmail(request, post_id):
	
	data = json.loads(request.body)
	email = data.get('new_email')
	lostpost = get_object_or_404(LostPost, id=post_id)
	if request.user == lostpost.user:
		try:
			validate_email(email)
			
			lostpost.email = email
			lostpost.save()  # Don't forget to save the changes
			
			return JsonResponse({'success': True})

		except forms.ValidationError:
			messages.error(request, 'Invalid email address')
			
			return JsonResponse({'success':False,'message':'Invalid email address'})
	else:
			return JsonResponse({'success':False,'message':'You do not have authority to do this action!'})



@login_required
@require_POST
def updateSchedule(request, post_id):
	
	data = json.loads(request.body)
	checked = data.get('checked')
	lostpost = get_object_or_404(LostPost, id=post_id)

	if checked == 'yes':
		lostpost.schedule = True
	else:
		lostpost.schedule = False

	lostpost.save()	
	return JsonResponse({'success': True})

@login_required
@require_POST
def updateEmailandSchedule(request,post_id):
		
	data = json.loads(request.body)
	checked = data.get('checked')
	email = data.get('email')
	lostpost = get_object_or_404(LostPost, id=post_id)

	try:
		validate_email(email)
		
		lostpost.email = email
		lostpost.save()  # Don't forget to save the changes
		
		

	except forms.ValidationError:
		return JsonResponse({'success':False,'message':"Invalid Email Address!"})

	if checked == 'yes':
		lostpost.schedule = True
	else:
		lostpost.schedule = False


	lostpost.save()	
	return JsonResponse({'success': True})


@login_required
@require_POST
def deletePost(request, post_id):
	
	post = get_object_or_404(BasePost,id=post_id)
	if request.user == post.user:
		post.delete()
	
		return JsonResponse({'success': True})
	else:
		return JsonResponse({'success':False,'message':'You do not have authority!'})

@login_required
def matchView(request):
	if request.method == 'POST':
		is_matched = request.POST.get('is_matched')
		lost_id = request.POST.get('lost_id')
		found_id = request.POST.get('found_id')
		lost_post = LostPost.objects.get(id=lost_id)
		found_post = FoundPost.objects.get(pk=found_id)
		owner_id = found_post.user.id
		if is_matched == 'yes':
		# redirect
			return redirect('chat:room',user_id=owner_id)		

	else:
		return redirect('post:lostpostdetails',post_id=lost_id)

from .forms import CatLostPost 
from authy.models import Cat, CatImageStorage, CatFullBodyImage
from django.http import HttpResponseForbidden
@login_required()
def createCatLostPost(request,cat_id):
	cat = get_object_or_404(Cat,id=cat_id)
	if cat.user != request.user:
		return HttpResponseForbidden('You are not authorized to do this action!')
	else:
		if request.method == 'POST':
			form = CatLostPost(request.POST,cat=cat)
			if form.is_valid():
				geotag = form.cleaned_data.get('geotag')
				lost_time = form.cleaned_data.get('lost_time')
				caption = form.cleaned_data.get('caption')

				post = LostPost.objects.create(user=cat.user,cat=cat,
								   geotag=geotag,lost_time=lost_time,caption=caption,
								   embedding = cat.embedding_vector)


				# remember to use embedding file of cat for post
				
				# post.embedding = cat.embedding_vector
				face_chosen_content = form.cleaned_data.get('face_chosen_content', [])
				face_chosen_files = CatImageStorage.objects.filter(id__in=face_chosen_content)
				for file in face_chosen_files:
					newfile = PostFileContent.objects.create(file=file.pic,user=cat.user)
					post.content.add(newfile)

				fullbody_chosen_content = form.cleaned_data.get('fullbody_chosen_content',[])
				fullbody_chosen_files = CatFullBodyImage.objects.filter(id__in=fullbody_chosen_content)
				for file in fullbody_chosen_files:
					newfile = PostFileContent.objects.create(file=file.pic,user=cat.user)
					post.fullbody_img.add(newfile)

				# post.save()
			
				return redirect('post:lostpostdetails',post_id=post.id)
		else:
			form = CatLostPost(cat=cat)
			return render(request,'cat_lostpost.html',{'requesting_profile':request.user.profile,
											  'cat':cat,'form':form})
			
	
				

