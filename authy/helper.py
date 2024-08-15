from django.http import HttpResponseForbidden
from functools import wraps
from django.shortcuts import get_object_or_404
from .models import User,Cat

def cat_permission(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # post = get_object_or_404(Post, id=kwargs['post_id'])
        user_id = request.user.id
        cat = get_object_or_404(Cat,id=kwargs['cat_id'])
        if not cat.can_access(user_id):
            return HttpResponseForbidden("You do not have authority to access this post. This cat is either set private or for followers only")
        return view_func(request, *args, **kwargs)
    return _wrapped_view