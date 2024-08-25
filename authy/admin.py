from django.contrib import admin
from authy.models import Profile, User, Cat, CatImageStorage, Follow, CatFood
# Register your models here.

admin.site.register(User)
admin.site.register(Profile)
admin.site.register(Cat)
admin.site.register(CatImageStorage)
admin.site.register(Follow)
admin.site.register(CatFood)
