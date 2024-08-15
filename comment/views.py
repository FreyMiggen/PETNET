from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Comment
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
# Create your views here.
@login_required
@require_POST
def deleteComment(request,comment_id):
    comment = get_object_or_404(Comment,id=comment_id)
    # only allow to delete if requesting_user is the owner of the post or owner of the comment
    if comment.post.user == request.user or comment.user == request.user:
        comment.delete()
        return JsonResponse({'success':True})
    else:
        return JsonResponse({'success':False,'message':'You do not have authority to do this action!'})
