from django import forms
from post.models import Post, LostPost,FoundPost,PostFileContent
from authy.models import Cat
from django.forms import modelformset_factory
# from image_uploader_widget.widgets import ImageUploaderWidget
from authy.models import PrivacyChoices
from django.utils import timezone

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class NewPostForm(forms.ModelForm):
	content = MultipleFileField(label='Add images to your post',required=True)
	caption = forms.CharField(widget=forms.Textarea(attrs={'class': 'input is-medium'}), required=True)
	tags = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)

	class Meta:
		model = Post
		fields = ('content', 'caption', 'tags')


class NewLostPostForm(forms.ModelForm):
	content = MultipleFileField(label='Add images to your post',required=True)
	# content = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))

	fullbody_img = MultipleFileField(label='Add fullbody images to your post',required=False)

	caption = forms.CharField(
		widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your caption here...','class':'textarea',}),
		max_length=1500,
		required=True,
	)

	geotag = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)

	lost_time = forms.DateTimeField(
		widget = forms.DateInput(
			attrs = {
				'class':'form-control',
				'type':'datetime-local',
			}),
			initial='2024-08-13'	
	)
	class Meta:
		model = LostPost
		fields = ('content', 'caption','geotag','fullbody_img','lost_time',)

	def __init__(self, *args, **kwargs):
		self.user = kwargs.pop('user', None)
		super(NewLostPostForm, self).__init__(*args, **kwargs)

	def save(self,commit=True):
		instance = super(NewLostPostForm, self).save(commit=False)
		if self.user:
			instance.user = self.user
		if commit:
			instance.save()
		return instance
    		

class NewFoundPostForm(forms.ModelForm):
	content = MultipleFileField(label='Add images to your post',required=True)

	fullbody_img = MultipleFileField(label='Add fullbody images to your post',required=True)

	# content = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))
	caption = forms.CharField(widget=forms.Textarea(attrs={'class': 'input is-medium'}), required=True)
	#tags = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)
	geotag = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)


	found_time = forms.DateTimeField(
		widget = forms.DateInput(
			attrs = {
				'class':'form-control',
				'type':'datetime-local',
			}),
		input_formats=['%Y-%m-%dT%H:%M'],  # Format for datetime-local input
        initial=timezone.localtime().strftime('%Y-%m-%dT%H:%M')
		)
	

	# found_time = forms.DateTimeField(
	# 	widget = forms.DateInput(
	# 		attrs = {
	# 			'class':'form-control',
	# 			'type':'datetime-local',
	# 		}),
	# 		initial='2024-08-13'	
	# )
	class Meta:
		model = FoundPost
		fields = ('content', 'caption','geotag','fullbody_img','found_time',)

	def __init__(self, *args, **kwargs):
		self.user = kwargs.pop('user', None)
		# current_time = timezone.localtime()
		# self.initial['found_time'] = current_time.strftime('%Y-%m-%dT%H:%M')
		super(NewFoundPostForm, self).__init__(*args, **kwargs)

	def save(self,commit=True):
		instance = super(NewFoundPostForm, self).save(commit=False)
		if self.user:
			instance.user = self.user
		if commit:
			instance.save()
		return instance
	
	def clean_found_time(self):
		found_time = self.cleaned_data.get('found_time')
		if found_time:
			if timezone.is_naive(found_time):
				return timezone.make_aware(found_time,timezone.get_current_timezone())
			else:
				return found_time
		return found_time

class PostCreateWithImagesForm(forms.ModelForm):
	caption = forms.CharField(
		widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your caption here...','class':'textarea',}),
		max_length=1500,
		required=True,
	)

	tags = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)

	content = MultipleFileField(
			
			label='Add images to your post',required=True)
	
	privacy = forms.ChoiceField(
        choices=PrivacyChoices.CHOICES,
        initial=PrivacyChoices.PUBLIC,
        widget=forms.Select(attrs={'class': 'select'}),
    )
	cats = forms.ModelMultipleChoiceField(
		queryset = Cat.objects.none(),
		widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'style': 'width: 100%; display: inline-block;'
        }),
		required=False,  # Making cats optional
		help_text="Optional: Select cats to associate with this post."
	)

	class Meta:
		model = Post
		fields = ['caption', 'tags','cats','content','privacy']
    
	def __init__(self, *args, **kwargs):
		user = kwargs.pop('user', None)
		super(PostCreateWithImagesForm, self).__init__(*args, **kwargs)
		if user is not None:
			self.fields['cats'].queryset = Cat.objects.filter(user=user)


	def clean(self):
		cleaned_data = super().clean()
		content = self.files.get('content')
		caption = cleaned_data.get('caption')
		cats = cleaned_data.get('cats')

		if not content:
			raise forms.ValidationError("Please upload at least one image.")
		
		if not caption and not cats:
			raise forms.ValidationError("Please provide either a caption or select at least one cat.")

		return cleaned_data


		

class PostEditForm(forms.ModelForm):
	caption = forms.CharField(
		widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your caption here...','class':'textarea',}),
		max_length=1500,
		required=True,
	)
	tags = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)
    # new_content = forms.FileField(
    #     label='Add new images to your post',
    #     required=False,
    #     widget=forms.ClearableFileInput(attrs={'multiple': True})
    # )

	new_content = MultipleFileField(
		label='Add images to your post',
		required=False
	)
	delete_content = forms.MultipleChoiceField(
		required=False,
		widget=forms.CheckboxSelectMultiple,
		choices=[],  # We'll set these dynamically in __init__
	)
	cats = forms.ModelMultipleChoiceField(
		queryset=Cat.objects.none(),
		widget=forms.SelectMultiple(attrs={
			'class': 'form-control',
			'style': 'width: 100%; display: inline-block;'
		}),
		required=False,
		help_text="Optional: Select cats to associate with this post."
	)
		
	privacy = forms.ChoiceField(
        choices=PrivacyChoices.CHOICES,
        # initial=PrivacyChoices.PUBLIC,
        widget=forms.Select(attrs={'class': 'select'}),
    )

	class Meta:
		model = Post
		fields = ['caption', 'tags', 'cats','privacy']

	def __init__(self, *args, **kwargs):
		user = kwargs.pop('user', None)
		instance = kwargs.get('instance')
		super().__init__(*args, **kwargs)
		if user is not None:
			self.fields['cats'].queryset = Cat.objects.filter(user=user)
		if instance:
			self.fields['delete_content'].choices = [
				(content.id, f"Delete {content.file.name}")
				for content in instance.content.all()
			]

	def clean(self):
		cleaned_data = super().clean()
		new_content = cleaned_data.get('new_content')
		delete_content = cleaned_data.get('delete_content')
		
		if not new_content and not self.instance.content.exists():
			raise forms.ValidationError("Your post must have at least one image.")
		
		return cleaned_data
	

class LostPostEditForm(forms.ModelForm):
	caption = forms.CharField(
		widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your caption here...','class':'textarea',}),
		max_length=1500,
		required=True,
	)

	lost_time = forms.DateTimeField(
		widget = forms.DateInput(
			attrs = {
				'class':'form-control',
				'type':'datetime-local',
			}),
		input_formats=['%Y-%m-%dT%H:%M'],  # Format for datetime-local input
        # initial=timezone.now().strftime('%Y-%m-%dT%H:%M')
				
	)

	new_content = MultipleFileField(
		label='Add images to your post',
		required=False
	)
	delete_content = forms.MultipleChoiceField(
		required=False,
		widget=forms.CheckboxSelectMultiple,
		choices=[],  # We'll set these dynamically in __init__
	)

	fullbody_new_content = MultipleFileField(
		label='Add images to your post',
		required=False
	)

	fullbody_delete_content = forms.MultipleChoiceField(
		required=False,
		widget=forms.CheckboxSelectMultiple,
		choices=[],  # We'll set these dynamically in __init__
	)

	geotag = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)


		

	class Meta:
		model = Post
		fields = ['caption', 'cats','lost_time','geotag']

	def __init__(self, *args, **kwargs):
		user = kwargs.pop('user', None)
		instance = kwargs.get('instance')
		super().__init__(*args, **kwargs)
		if instance.lost_time:
                # Convert the datetime to local time and format it for the input
			local_time = timezone.localtime(self.instance.lost_time)
			self.initial['lost_time'] = local_time.strftime('%Y-%m-%dT%H:%M')

		if user is not None:
			self.fields['cats'].queryset = Cat.objects.filter(user=user)
		if instance:
			self.fields['delete_content'].choices = [
				(content.id, f"Delete {content.file.name}")
				for content in instance.content.all()
			]

			self.fields['fullbody_delete_content'].choices = [
				(content.id, f"Delete {content.file.name}")
				for content in instance.fullbody_img.all()
			]

	def clean(self):
		cleaned_data = super().clean()
		new_content = cleaned_data.get('new_content')
		delete_content = cleaned_data.get('delete_content')
		
		if not new_content and not self.instance.content.exists():
			raise forms.ValidationError("Your post must have at least one image.")
		
		return cleaned_data
	
	def clean_lost_time(self):
		lost_time = self.cleaned_data.get('lost_time')
		if lost_time:
			if timezone.is_naive(lost_time):
				return timezone.make_aware(lost_time,timezone.get_current_timezone())
			else:
				return lost_time
		return lost_time


# class NewLostPostForm(forms.ModelForm):
# 	cat = forms.ModelChoiceField(
# 		queryset=Cat.objects.none(),
# 		widget=forms.Select(attrs={
# 			'class': 'form-control',
# 			'style': 'width: 100%; display: inline-block;',
# 			'id': 'cat-select'
# 		}),
# 		required=False,
# 		help_text="Optional: Select a cat to associate with this post."
# 	)
# 	content = MultipleFileField(
# 		label='Add face images to your post',
# 		required=False
# 	)

# 	fullbody_img = MultipleFileField(
# 		label='Add full body images to your post',
# 		required=False
# 	)
# 	cat_images = forms.MultipleChoiceField(
# 		choices=[],
# 		widget=forms.CheckboxSelectMultiple(attrs={'id': 'cat-images'}),
# 		required=False,
# 		label="Select cat images to include"
# 	)
# 	caption = forms.CharField(
# 		widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your caption here...', 'class': 'textarea'}),
# 		max_length=1500,
# 		required=True,
# 	)
# 	geotag = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)

# 	lost_time = forms.SplitDateTimeField(
# 		widget=forms.SplitDateTimeWidget(
# 			date_attrs={'type': 'date'},
# 			time_attrs={'type': 'time'},
# 		),
# 		label='Lost Date and Time',
# 		required=False
# 	)

# 	class Meta:
# 		model = LostPost
# 		fields = ('cats', 'content', 'caption', 'geotag', 'fullbody_img', 'lost_time',)

# 	def __init__(self, *args, **kwargs):
# 		user = kwargs.pop('user', None)
# 		super(NewLostPostForm, self).__init__(*args, **kwargs)
# 		if user is not None:
# 			self.fields['cats'].queryset = Cat.objects.filter(user=user)

# 	def clean(self):
# 		cleaned_data = super().clean()
# 		content = cleaned_data.get('content')
# 		cat_images = cleaned_data.get('cat_images')
		
# 		if not content and not cat_images:
# 			raise forms.ValidationError("You must either upload new images or select existing cat images.")
		
# 		return cleaned_data