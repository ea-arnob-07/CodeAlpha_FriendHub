from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class StyledAuthenticationForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "form-input", "placeholder": "Username", "autocomplete": "username"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-input", "placeholder": "Password", "autocomplete": "current-password"}
        )


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    terms = forms.BooleanField(
        label="I agree to the Terms of Use and Privacy Policy",
        error_messages={"required": "You must accept the terms to continue."},
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email", "password1", "password2")

    def clean_username(self):
        username = self.cleaned_data["username"].strip().lower()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-input"}),
            "last_name": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email


class ProfileUpdateForm(forms.ModelForm):
    remove_avatar = forms.BooleanField(required=False)
    remove_cover = forms.BooleanField(required=False)

    class Meta:
        model = Profile
        fields = ("avatar", "cover_photo", "bio", "location", "website")
        widgets = {
            "avatar": forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
            "cover_photo": forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
            "bio": forms.Textarea(attrs={"class": "form-input", "rows": 4, "maxlength": 240}),
            "location": forms.TextInput(attrs={"class": "form-input"}),
            "website": forms.URLInput(attrs={"class": "form-input", "placeholder": "https://example.com"}),
        }

