from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from authy.models import Profile,Cat,CatImageStorage, PrivacyChoices, CatFood

User = get_user_model()
def ForbiddenUsers(value):
	forbidden_users = ['admin', 'css', 'js', 'authenticate', 'login', 'logout', 'administrator', 'root',
	'email', 'user', 'join', 'sql', 'static', 'python', 'delete']
	if value.lower() in forbidden_users:
		raise ValidationError('Invalid name for user, this is a reserverd word.')

def InvalidUser(value):
	if '@' in value or '+' in value or '-' in value:
		raise ValidationError('This is an Invalid user, Do not user these chars: @ , - , + ')

def UniqueEmail(value):
	if User.objects.filter(email__iexact=value).exists():
		raise ValidationError('User with this email already exists.')

def UniqueUser(value):
	if User.objects.filter(name__iexact=value).exists():
		raise ValidationError('User with this username already exists.')

class SignupForm(forms.ModelForm):
	name = forms.CharField(widget=forms.TextInput(attrs={'class':'input is-medium'}), max_length=30, required=True,)
	email = forms.CharField(widget=forms.EmailInput(attrs={'class':'input is-medium'}), max_length=100, required=True,)
	password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'input is-medium'}))
	confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'input is-medium'}), required=True, label="Confirm your password.")

	class Meta:

		model = User
		fields = ('name', 'email', 'password')

	def __init__(self, *args, **kwargs):
		super(SignupForm, self).__init__(*args, **kwargs)
		self.fields['name'].validators.append(ForbiddenUsers)
		self.fields['name'].validators.append(InvalidUser)
		self.fields['name'].validators.append(UniqueUser)
		self.fields['email'].validators.append(UniqueEmail)

	def clean(self):
		super(SignupForm, self).clean()
		password = self.cleaned_data.get('password')
		confirm_password = self.cleaned_data.get('confirm_password')

		if password != confirm_password:
			self._errors['password'] = self.error_class(['Passwords do not match. Try again'])
		return self.cleaned_data

class ChangePasswordForm(forms.ModelForm):
	
	old_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input is-medium'}), label="Old password", required=True)
	new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input is-medium'}), label="New password", required=True)
	confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input is-medium'}), label="Confirm new password", required=True)

	class Meta:
		model = User
		fields = ('id', 'old_password', 'new_password', 'confirm_password')
	def __init__(self,*args,**kwargs):
		self.user = kwargs.pop('user')
		super(ChangePasswordForm,self).__init__(*args,**kwargs)

	def clean(self):
		super(ChangePasswordForm, self).clean()
		# id = self.cleaned_data.get('id')
		old_password = self.cleaned_data.get('old_password')
		new_password = self.cleaned_data.get('new_password')
		confirm_password = self.cleaned_data.get('confirm_password')
		
		if not self.user.check_password(old_password):
			self._errors['old_password'] =self.error_class(['Old password do not match.'])
		if new_password != confirm_password:
			self._errors['new_password'] =self.error_class(['Passwords do not match.'])
		return self.cleaned_data


class ProfileUpdateForm(forms.ModelForm):
	picture = forms.ImageField(required=False)
	first_name = forms.CharField(widget=forms.TextInput(attrs={'class':'input is-medium'}),max_length=50, required=False)
	last_name = forms.CharField(widget=forms.TextInput(attrs={'class':'input is-medium'}),max_length=50, required=False)
	location = forms.CharField(widget=forms.TextInput(attrs={'class':'input is-medium'}),max_length=50, required=False)
	profile_info = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your bio here...','class':'textarea',}), max_length=150, required=False)

	class Meta:
		model = Profile
		fields = ('picture','first_name', 'last_name', 'location', 'profile_info')

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

	
class AddCatForm(forms.ModelForm):
	# images = MultipleFileField(label='Select image files',required=True)
    # images = forms.FileField(widget=forms.ClearableFileInput(attrs={'allow_multiple_selected': True}), required=False)
	picture = forms.ImageField(required=True)
	description = forms.CharField(
		widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your description here...','class':'textarea',}),
		max_length=1500,
		required=True,
	)


	name = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)

	privacy = forms.ChoiceField(
        choices=PrivacyChoices.CHOICES,
        initial=PrivacyChoices.PUBLIC,
        widget=forms.Select(attrs={'class': 'select'}),
    )
	
	class Meta:
		model = Cat
		fields = ['name', 'description', 'in_search','picture','privacy']
		widgets = {
			'in_search': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
		}

	def __init__(self, *args, **kwargs):
    		
	# we pop the user from the kwargs. This allows us to pass the user when instantiating the form.
		self.user = kwargs.pop('user', None)
		super(AddCatForm, self).__init__(*args, **kwargs)

	def save(self, commit=True):
		instance = super(AddCatForm, self).save(commit=False)
		if self.user:
			instance.user = self.user
		if commit:
			instance.save()
		return instance

class EditCatForm(forms.ModelForm):
    	
	picture = forms.ImageField(required=True)
	description = forms.CharField(
		widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your description here...','class':'textarea',}),
		max_length=1500,
		required=True,
	)


	name = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)

	privacy = forms.ChoiceField(
        choices=PrivacyChoices.CHOICES,
        initial=PrivacyChoices.PUBLIC,
        widget=forms.Select(attrs={'class': 'select'}),
    )
	
	class Meta:
		model = Cat
		fields = ['name', 'description','picture','privacy']
    	
	def __init__(self,*args,**kwargs):
		cat = kwargs.get('instance')
		super().__init__(*args, **kwargs)




from .models import CatFullBodyImage
class AddCatImage(forms.ModelForm):
	pic = MultipleFileField(label='Select image files',required=True)

	class Meta:
		model = CatImageStorage
		fields = ('pic',)

class AddCatBodyImage(forms.ModelForm):
	pic = MultipleFileField(label='Select image files',required=True)

	class Meta:
		model = CatFullBodyImage
		fields = ('pic',)


from django import forms
from .models import Feedback, FavoriteChoices

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'textarea', 'placeholder': 'Enter your feedback here...'}),
        }

class CatFoodForm(forms.ModelForm):
	name = forms.CharField(widget=forms.TextInput(attrs={'class': 'input is-medium'}), required=True)
	picture = forms.ImageField()
	description = forms.CharField(
		widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your description here...','class':'textarea',}),
		max_length=1000,
		required=False,
	)
	choice = forms.ChoiceField(        
		choices=FavoriteChoices.CHOICES,
        initial=FavoriteChoices.LIKE,
        widget=forms.Select(attrs={'class': 'select'}),)
	
	class Meta:
		model = CatFood
		fields= ['name','picture','description','choice']